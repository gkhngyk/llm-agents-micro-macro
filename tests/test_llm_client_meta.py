"""Mock tests for llm_client's reasoning_effort and meta parameters (no network)."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Dummy key and a no-op load_dotenv, so importing never reads ../.env.
os.environ["OPENROUTER_API_KEY"] = "test-dummy"
with mock.patch("dotenv.load_dotenv", lambda *a, **k: False):
    import llm_client

SCHEMA = {"type": "object", "properties": {"action": {"type": "integer"}}}
MESSAGES = [{"role": "user", "content": "hi"}]


def _resp(content, reasoning="thoughts", finish_reason="stop"):
    message = SimpleNamespace(content=content, reasoning=reasoning)
    usage = SimpleNamespace(model_dump=lambda: {"completion_tokens": 7})
    return SimpleNamespace(
        model="snap-2", usage=usage,
        choices=[SimpleNamespace(message=message, finish_reason=finish_reason)])


class ReasoningEffortAndMeta(unittest.TestCase):
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
        return [json.loads(x) for x in self.log_path.read_text().splitlines()]

    def valid(self, **kw):
        return llm_client.call_llm_valid(
            "m", MESSAGES, schema=SCHEMA, session_id="s", is_valid=lambda c: c["action"] >= 0, **kw)

    def test_default_sends_no_reasoning_and_keeps_extra_body(self):
        self.create.side_effect = [_resp('{"action": 1}')]
        self.valid()
        self.assertEqual(self.create.call_args.kwargs["extra_body"], {"session_id": "s"})
        self.assertEqual(self.records()[-1]["reasoning_effort"], "default")

    def test_reasoning_effort_is_sent_and_logged(self):
        self.create.side_effect = [ValueError("boom"), _resp('{"action": 1}')]
        self.valid(reasoning_effort="medium")
        for call in self.create.call_args_list:
            self.assertEqual(call.kwargs["extra_body"],
                             {"session_id": "s", "reasoning": {"effort": "medium"}})
        self.assertEqual([r["reasoning_effort"] for r in self.records()], ["medium", "medium"])

    def test_meta_holds_the_accepted_response(self):
        self.create.side_effect = [
            _resp('{"action": -1}', reasoning="first"), _resp('{"action": 3}', reasoning="second")]
        meta = {}
        out = self.valid(return_parse_fail=True, meta=meta)
        self.assertEqual(out, ({"action": 3}, 1, 0))
        self.assertGreaterEqual(meta.pop("elapsed_s"), 0)       # seconds of the accepted attempt
        self.assertEqual(meta, {"model_snapshot": "snap-2", "finish_reason": "stop",
                                "usage": {"completion_tokens": 7}, "reasoning": "second",
                                "reasoning_capped": None})

    def test_missing_or_non_string_reasoning_is_none(self):
        no_field = _resp('{"action": 1}')
        del no_field.choices[0].message.reasoning
        for resp in (no_field, _resp('{"action": 1}', reasoning=None),
                     _resp('{"action": 1}', reasoning="  "),
                     _resp('{"action": 1}', reasoning=mock.Mock())):
            self.create.side_effect = [resp]
            meta = {}
            self.valid(meta=meta)
            self.assertIsNone(meta["reasoning"])

    def test_call_llm_passes_both_through(self):
        self.create.side_effect = [_resp('{"action": 1}')]
        meta = {}
        llm_client.call_llm("m", MESSAGES, schema=SCHEMA, session_id="s",
                            reasoning_effort="low", meta=meta)
        self.assertEqual(self.create.call_args.kwargs["extra_body"]["reasoning"], {"effort": "low"})
        self.assertEqual(meta["finish_reason"], "stop")


if __name__ == "__main__":
    unittest.main()
