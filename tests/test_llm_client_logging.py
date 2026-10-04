"""Mock tests for the logging behaviour of llm_client (no network, no ../.env)."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx
import openai

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Dummy key and a no-op load_dotenv, so importing never reads ../.env.
os.environ["OPENROUTER_API_KEY"] = "test-dummy"
with mock.patch("dotenv.load_dotenv", lambda *a, **k: False):
    import llm_client

SCHEMA = {"type": "object", "properties": {"action": {"type": "integer"}}}
MESSAGES = [{"role": "user", "content": "hi"}]


def _resp(content, model="m-snapshot-1"):
    r = mock.Mock()
    r.model = model
    r.choices = [mock.Mock()]
    r.choices[0].message.content = content
    r.usage = None
    return r


class LoggingTestBase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.log_path = Path(tmp.name) / "logs" / "raw_calls.jsonl"
        for p in (
            mock.patch.object(llm_client, "LOG_PATH", self.log_path),
            mock.patch.object(llm_client, "_client"),
            mock.patch.object(llm_client.time, "sleep"),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.create = llm_client._client.chat.completions.create

    def records(self):
        if not self.log_path.exists():
            return []
        return [json.loads(line) for line in self.log_path.read_text().splitlines()]

    def call(self, **kw):
        return llm_client.call_llm("m", MESSAGES, schema=SCHEMA, session_id="s", **kw)


class CallLlmLogging(LoggingTestBase):
    def test_intermediate_failure_is_logged(self):
        self.create.side_effect = [ValueError("boom"), _resp('{"action": 1}')]
        self.assertEqual(self.call(), {"action": 1})
        recs = self.records()
        self.assertEqual(len(recs), 2)
        retry, ok = recs
        self.assertEqual(retry["error_type"], "ValueError")
        self.assertEqual(retry["error"], "boom")
        self.assertEqual(retry["attempt"], 0)
        self.assertIs(retry["retrying"], True)
        for key in ("ts", "model", "session_id", "temperature", "messages"):
            self.assertIn(key, retry)
        self.assertEqual(ok["attempt"], 1)
        self.assertNotIn("error", ok)
        self.assertEqual(ok["response_parsed"], {"action": 1})

    def test_success_record_has_model_snapshot(self):
        self.create.side_effect = [_resp('{"action": 1}', model="vendor/m-2026-10-01")]
        self.call()
        ok = self.records()[-1]
        self.assertEqual(ok["model_snapshot"], "vendor/m-2026-10-01")
        for key in ("response_raw", "response_parsed", "usage", "attempt", "degraded"):
            self.assertIn(key, ok)

    def test_degraded_flag(self):
        self.create.side_effect = [_resp('Sure! Here it is: {"action": 2} Hope it helps.')]
        self.assertEqual(self.call(), {"action": 2})
        self.assertIs(self.records()[-1]["degraded"], True)

        self.create.side_effect = [_resp('{"action": 3}')]
        self.assertEqual(self.call(), {"action": 3})
        self.assertIs(self.records()[-1]["degraded"], False)

    def test_all_attempts_fail(self):
        self.create.side_effect = ConnectionError("down")
        with self.assertRaises(RuntimeError):
            self.call(max_retries=3)
        self.assertEqual(self.create.call_count, 3)
        recs = self.records()
        self.assertEqual(len(recs), 4)  # 3 intermediate + 1 final
        self.assertTrue(all(r.get("retrying") for r in recs[:3]))
        final = recs[-1]
        self.assertNotIn("retrying", final)
        self.assertEqual(final["attempt"], 3)
        self.assertEqual(final["error_type"], "ConnectionError")
        self.assertIn("down", final["error"])
        self.assertEqual(final["messages"], MESSAGES)

    def test_log_write_failure_is_not_retried(self):
        self.create.side_effect = [_resp('{"action": 1}')] * 4
        with mock.patch.object(llm_client, "_append_log", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.call()
        self.assertEqual(self.create.call_count, 1)

    def test_retry_log_write_failure_is_not_an_api_error(self):
        self.create.side_effect = [ValueError("boom"), _resp('{"action": 1}')]
        with mock.patch.object(llm_client, "_append_log", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.call()
        self.assertEqual(self.create.call_count, 1)


def _status_error(code):
    req = httpx.Request("POST", "https://example.invalid/v1/chat/completions")
    return openai.APIStatusError(
        f"status {code}", response=httpx.Response(code, request=req), body=None)


class ErrorKindLogging(LoggingTestBase):
    def test_connection_error_is_transport(self):
        req = httpx.Request("POST", "https://example.invalid")
        self.create.side_effect = [openai.APIConnectionError(request=req), _resp('{"action": 1}')]
        self.assertEqual(self.call(), {"action": 1})
        retry = self.records()[0]
        self.assertEqual(retry["error_kind"], "transport")
        self.assertEqual(retry["error_type"], "APIConnectionError")
        self.assertNotIn("status_code", retry)

    def test_timeout_and_httpx_transport_are_transport(self):
        req = httpx.Request("POST", "https://example.invalid")
        self.create.side_effect = [
            openai.APITimeoutError(request=req), httpx.ReadError("reset"), _resp('{"action": 1}')]
        self.call()
        self.assertEqual([r["error_kind"] for r in self.records()[:2]], ["transport"] * 2)

    def test_status_error_is_http_with_status_code(self):
        self.create.side_effect = [_status_error(503), _resp('{"action": 1}')]
        self.assertEqual(self.call(), {"action": 1})
        retry = self.records()[0]
        self.assertEqual(retry["error_kind"], "http")
        self.assertEqual(retry["status_code"], 503)
        self.assertEqual(retry["error_type"], "APIStatusError")

    def test_other_error_kind(self):
        self.create.side_effect = [ValueError("boom"), _resp('{"action": 1}')]
        self.call()
        self.assertEqual(self.records()[0]["error_kind"], "other")

    def test_empty_or_none_content_is_parse(self):
        self.create.side_effect = [_resp(None), _resp(""), _resp('{"action": 1}')]
        self.assertEqual(self.call(), {"action": 1})
        retries = self.records()[:2]
        self.assertEqual([r["error_kind"] for r in retries], ["parse", "parse"])

    def test_final_failure_record_has_last_error_kind(self):
        self.create.side_effect = [_status_error(503), _status_error(502)]
        with self.assertRaises(RuntimeError):
            self.call(max_retries=2)
        final = self.records()[-1]
        self.assertNotIn("retrying", final)
        self.assertEqual(final["error_kind"], "http")
        self.assertEqual(final["status_code"], 502)

        self.create.side_effect = [ValueError("x"), _resp("not json at all")]
        with self.assertRaises(RuntimeError):
            self.call(max_retries=2)
        self.assertEqual(self.records()[-1]["error_kind"], "parse")


class ParseFailCount(LoggingTestBase):
    def valid(self, **kw):
        return llm_client.call_llm_valid(
            "m", MESSAGES, schema=SCHEMA, session_id="s", is_valid=lambda c: c["action"] >= 0, **kw)

    def test_two_parse_failures_then_valid(self):
        self.create.side_effect = [_resp("nope"), _resp("{broken"), _resp('{"action": 4}')]
        out = self.valid(return_parse_fail=True)
        self.assertEqual(out, ({"action": 4}, 0, 2))
        recs = self.records()
        parse_recs = [r for r in recs if r.get("error_kind") == "parse"]
        self.assertEqual(len(parse_recs), 2)
        self.assertTrue(all(r["error_type"] == "JSONDecodeError" for r in parse_recs))
        self.assertFalse(any(r.get("invalid") for r in recs))

    def test_default_return_is_two_tuple(self):
        self.create.side_effect = [_resp("nope"), _resp('{"action": 4}')]
        out = self.valid()
        self.assertEqual(out, ({"action": 4}, 0))
        self.assertEqual(len(out), 2)

    def test_call_llm_still_returns_dict(self):
        self.create.side_effect = [_resp("nope"), _resp('{"action": 4}')]
        self.assertEqual(self.call(), {"action": 4})

    def test_invalid_payload_counts_n_invalid_not_n_parse_fail(self):
        self.create.side_effect = [_resp('{"action": -1}'), _resp('{"action": 5}')]
        self.assertEqual(self.valid(return_parse_fail=True), ({"action": 5}, 1, 0))

    def test_parse_fail_accumulates_across_invalid_retries(self):
        self.create.side_effect = [
            _resp("nope"), _resp('{"action": -1}'), _resp("nope"), _resp("nope"), _resp('{"action": 2}')]
        self.assertEqual(self.valid(return_parse_fail=True), ({"action": 2}, 1, 3))

    def test_exhausted_call_carries_parse_fail_count(self):
        self.create.side_effect = [_resp("nope")] * 2
        with self.assertRaises(RuntimeError) as cm:
            self.call(max_retries=2)
        self.assertEqual(cm.exception.n_parse_fail, 2)


class TemperatureDefault(LoggingTestBase):
    def test_default_sends_no_temperature_and_logs_default(self):
        self.create.side_effect = [ValueError("boom"), _resp('{"action": 1}')]
        self.call()
        for kwargs in (c.kwargs for c in self.create.call_args_list):
            self.assertNotIn("temperature", kwargs)
        self.assertEqual([r["temperature"] for r in self.records()], ["default", "default"])

    def test_explicit_temperature_keeps_old_behaviour(self):
        self.create.side_effect = [_resp('{"action": 1}')]
        self.call(temperature=0.7)
        self.assertEqual(self.create.call_args.kwargs["temperature"], 0.7)
        self.assertEqual(self.records()[-1]["temperature"], 0.7)

    def test_call_llm_valid_default_also_sends_none(self):
        self.create.side_effect = [_resp('{"action": 1}')]
        llm_client.call_llm_valid(
            "m", MESSAGES, schema=SCHEMA, session_id="s", is_valid=lambda c: True)
        self.assertNotIn("temperature", self.create.call_args.kwargs)
        self.assertEqual(self.records()[-1]["temperature"], "default")

    def test_default_max_tokens_is_raised(self):
        self.create.side_effect = [_resp('{"action": 1}')]
        self.call()
        self.assertEqual(self.create.call_args.kwargs["max_tokens"], llm_client.DEFAULT_MAX_TOKENS)
        self.assertGreater(llm_client.DEFAULT_MAX_TOKENS, 500)


class ModelsDict(unittest.TestCase):
    def test_models_are_this_studys_and_old_ones_kept_apart(self):
        self.assertEqual(set(llm_client.MODELS), {"deepseek", "gpt", "gemini"})
        self.assertEqual(llm_client.MODELS, {
            "deepseek": "deepseek/deepseek-v4.1-flash",
            "gpt": "openai/gpt-6-luna",
            "gemini": "google/gemini-2.5-flash-lite",
        })
        self.assertFalse(any(":" in v for v in llm_client.MODELS.values()))
        self.assertEqual(set(llm_client.MODELS_ULTIMATUM), {"haiku", "gemma", "gptoss"})
        self.assertFalse(set(llm_client.MODELS.values()) & set(llm_client.MODELS_ULTIMATUM.values()))


class FinishReasonLogging(LoggingTestBase):
    def resp(self, content, finish_reason):
        r = _resp(content)
        r.choices[0].finish_reason = finish_reason
        return r

    def test_stop_is_logged(self):
        self.create.side_effect = [self.resp('{"action": 1}', "stop")]
        self.assertEqual(self.call(), {"action": 1})
        self.assertEqual(self.records()[-1]["finish_reason"], "stop")

    def test_length_is_logged_on_success_and_on_failed_attempt(self):
        # Truncated half-JSON: parse failure, retried; the retry is also cut off, then succeeds.
        self.create.side_effect = [
            self.resp('{"action": ', "length"),
            self.resp('{"action": 1}', "length"),
        ]
        self.assertEqual(self.call(), {"action": 1})
        retry, ok = self.records()
        self.assertEqual(retry["error_kind"], "parse")
        self.assertEqual(retry["finish_reason"], "length")
        self.assertEqual(ok["finish_reason"], "length")

    def test_none_or_missing_is_null(self):
        none_resp = self.resp('{"action": 1}', None)
        missing = self.resp('{"action": 2}', None)
        del missing.choices[0].finish_reason  # attribute absent altogether
        no_choice_attr = mock.Mock(spec=["model", "usage", "choices"])
        no_choice_attr.model, no_choice_attr.usage = "m", None
        no_choice_attr.choices = [mock.Mock(spec=["message"])]
        no_choice_attr.choices[0].message.content = '{"action": 3}'
        for resp, expected in ((none_resp, {"action": 1}), (missing, {"action": 2}),
                               (no_choice_attr, {"action": 3})):
            self.create.side_effect = [resp]
            self.assertEqual(self.call(), expected)
            rec = self.records()[-1]
            self.assertIn("finish_reason", rec)
            self.assertIsNone(rec["finish_reason"])

    def test_non_string_value_is_null(self):
        # A bare Mock attribute (as in the other tests' _resp) must not leak into the log.
        self.create.side_effect = [_resp('{"action": 1}')]
        self.call()
        self.assertIsNone(self.records()[-1]["finish_reason"])

    def test_failed_attempt_without_response_is_null(self):
        self.create.side_effect = [ConnectionError("down"), self.resp('{"action": 1}', "stop")]
        self.call()
        retry, ok = self.records()
        self.assertIn("finish_reason", retry)
        self.assertIsNone(retry["finish_reason"])
        self.assertEqual(ok["finish_reason"], "stop")

    def test_final_failure_record_has_finish_reason(self):
        self.create.side_effect = [self.resp('{"action": ', "length")] * 2
        with self.assertRaises(RuntimeError):
            self.call(max_retries=2)
        recs = self.records()
        self.assertEqual([r["finish_reason"] for r in recs], ["length"] * 3)
        self.assertNotIn("retrying", recs[-1])

        self.create.side_effect = [ConnectionError("down")] * 2
        with self.assertRaises(RuntimeError):
            self.call(max_retries=2)
        self.assertIsNone(self.records()[-1]["finish_reason"])

    def test_existing_fields_unchanged(self):
        self.create.side_effect = [self.resp('{"action": 1}', "stop")]
        self.call()
        ok = self.records()[-1]
        for key in ("ts", "model", "session_id", "temperature", "messages", "response_raw",
                    "response_parsed", "usage", "model_snapshot", "attempt", "degraded"):
            self.assertIn(key, ok)


class CallLlmValidLogging(LoggingTestBase):
    def test_invalid_payload_is_labelled(self):
        self.create.side_effect = [_resp('{"action": -1}'), _resp('{"action": 5}')]
        out = llm_client.call_llm_valid(
            "m", MESSAGES, schema=SCHEMA, session_id="s",
            is_valid=lambda c: c["action"] >= 0)
        self.assertEqual(out, ({"action": 5}, 1))
        recs = self.records()
        invalid = [r for r in recs if r.get("invalid")]
        self.assertEqual(len(invalid), 1)
        self.assertEqual(invalid[0]["event"], "invalid_payload")
        self.assertEqual(invalid[0]["n_invalid"], 0)
        self.assertEqual(invalid[0]["response_parsed"], {"action": -1})
        self.assertEqual(invalid[0]["session_id"], "s")
        self.assertEqual(len(recs), 3)  # 2 call records + 1 invalid label

    def test_valid_payload_writes_no_invalid_record(self):
        self.create.side_effect = [_resp('{"action": 5}')]
        out = llm_client.call_llm_valid(
            "m", MESSAGES, schema=SCHEMA, session_id="s", is_valid=lambda c: True)
        self.assertEqual(out, ({"action": 5}, 0))
        self.assertFalse(any(r.get("invalid") for r in self.records()))


if __name__ == "__main__":
    unittest.main()
