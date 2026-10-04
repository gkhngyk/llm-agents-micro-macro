"""Mock tests for the logging behaviour of llm_client (no network, no ../.env)."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Dummy key and a no-op load_dotenv, so importing never reads ../.env.
os.environ["OPENROUTER_API_KEY"] = "test-dummy"
with mock.patch("dotenv.load_dotenv", lambda *a, **k: False):
    import llm_client

SCHEMA = {"type": "object", "properties": {"action": {"type": "integer"}}}
MESSAGES = [{"role": "user", "content": "hi"}]


def _resp(content):
    r = mock.Mock()
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
