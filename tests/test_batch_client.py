"""Mock tests for batch_client (no network, no ../.env, dummy key, temp log dir)."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Dummy key and a no-op load_dotenv, so importing never reads ../.env.
os.environ["OPENROUTER_API_KEY"] = "test-dummy"
with mock.patch("dotenv.load_dotenv", lambda *a, **k: False):
    import llm_client
    import batch_client
from batch_client import BatchItem

FAKE_KEY = "sk-fake-for-tests"
SCHEMA = {"type": "object", "properties": {"action": {"type": "integer"}}}


def item(cid, step="contribution", **kw):
    return BatchItem(cid, [{"role": "user", "content": f"q {cid}"}], SCHEMA, step, **kw)


def ok_row(cid, content='{"action": 3}', model="snap-2026-10", finish="stop", usage=None):
    if usage is None:
        usage = {"prompt_tokens": 10, "completion_tokens": 40, "total_tokens": 50,
                 "completion_tokens_details": {"reasoning_tokens": 30}}
    return {"id": f"batch_req_{cid}", "custom_id": cid, "error": None,
            "response": {"status_code": 200, "request_id": f"rid-{cid}", "body": {
                "model": model, "usage": usage,
                "choices": [{"message": {"content": content}, "finish_reason": finish}]}}}


def err_row(cid):
    return {"id": f"batch_req_{cid}", "custom_id": cid, "response": None,
            "error": {"type": "server_error", "message": "boom", "param": None,
                      "error_type": "provider_unavailable"}}


class FakeOpenRouter:
    """Stands in for the API. `script` is a list, one entry per created batch:
    {"statuses": [...polled in order, last repeats], "results": fn(custom_ids)}."""

    def __init__(self, script):
        self.script = list(script)
        self.created = []      # POST payloads
        self.headers = []
        self.polls = 0
        self.on_first_get = None
        self._state = {}       # batch_id -> [script entry, polls so far]
        self.client = httpx.Client(transport=httpx.MockTransport(self.handle))

    def handle(self, request):
        self.headers.append(dict(request.headers))
        if request.method == "POST":
            payload = json.loads(request.content)
            self.created.append(payload)
            bid = f"batch_{len(self.created)}"
            self._state[bid] = [self.script[len(self.created) - 1], 0, payload]
            return httpx.Response(202, json={"id": bid, "object": "batch",
                                             "status": "validating"})
        bid = request.url.path.rsplit("/", 1)[1]
        self.polls += 1
        if self.polls == 1 and self.on_first_get:
            self.on_first_get(bid)
        entry, n, payload = self._state[bid]
        self._state[bid][1] += 1
        statuses = entry["statuses"]
        status = statuses[min(n, len(statuses) - 1)]
        results = None
        if status == "completed":
            ids = [r["custom_id"] for r in payload["requests"]]
            results = entry["results"](ids)
        return httpx.Response(200, json={
            "id": bid, "status": status, "results": results,
            "request_counts": {"total": len(payload["requests"])}})


class BatchTestBase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.raw_calls = root / "logs" / "raw_calls.jsonl"
        self.registry = root / "logs" / "batches.jsonl"
        self.raw_dir = root / "logs" / "batch_raw"
        for p in (
            mock.patch.object(llm_client, "LOG_PATH", self.raw_calls),
            mock.patch.object(batch_client, "BATCH_LOG_PATH", self.registry),
            mock.patch.object(batch_client, "BATCH_RAW_DIR", self.raw_dir),
            mock.patch.object(batch_client.time, "sleep"),
        ):
            p.start()
            self.addCleanup(p.stop)

    def runner(self, fake, **kw):
        http = batch_client.OpenRouterBatchHttp(FAKE_KEY, http=fake.client)
        return batch_client.BatchRunner(http, **kw)

    @staticmethod
    def read(path):
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines()]


def all_ok(ids):
    return [ok_row(c) for c in ids]


class IdPersistence(BatchTestBase):
    def test_batch_id_is_on_disk_before_waiting(self):
        fake = FakeOpenRouter([{"statuses": ["validating", "in_progress", "completed"],
                                "results": all_ok}])
        seen = {}

        def on_first_get(bid):
            recs = self.read(self.registry)  # state at the very first poll
            seen["recs"] = recs

        fake.on_first_get = on_first_get
        res = self.runner(fake).run("gemini", [item("a"), item("b")])
        self.assertTrue(res.ok)
        self.assertEqual(len(seen["recs"]), 1)
        rec = seen["recs"][0]
        self.assertEqual(rec["event"], "submitted")
        self.assertEqual(rec["batch_id"], "batch_1")
        self.assertEqual(rec["model"], "google/gemini-3.8-flash")
        self.assertEqual(rec["step"], "contribution")
        self.assertEqual(rec["custom_ids"], ["a", "b"])
        self.assertEqual(rec["attempt"], 1)
        self.assertIn("ts", rec)

    def test_raw_results_are_saved_on_completion(self):
        fake = FakeOpenRouter([{"statuses": ["completed"], "results": all_ok}])
        self.runner(fake).run("gpt", [item("a")])
        saved = json.loads((self.raw_dir / "batch_1.json").read_text())
        self.assertEqual(saved["status"], "completed")
        self.assertEqual(saved["results"][0]["custom_id"], "a")
        fin = self.read(self.registry)[-1]
        self.assertEqual(fin["event"], "finished")
        self.assertEqual(fin["status"], "completed")
        self.assertTrue(fin["raw_path"].endswith("batch_1.json"))

    def test_create_is_not_retried_after_a_server_error(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(500, text="oops")

        http = batch_client.OpenRouterBatchHttp(
            FAKE_KEY, http=httpx.Client(transport=httpx.MockTransport(handler)))
        with self.assertRaises(batch_client.BatchApiError):
            batch_client.BatchRunner(http).run("gpt", [item("a")])
        self.assertEqual(len(calls), 1)  # a second POST could bill a second batch
        self.assertEqual(self.read(self.registry), [])


class Matching(BatchTestBase):
    def test_results_matched_by_custom_id_not_order(self):
        def shuffled(ids):
            rows = [ok_row(c, content=json.dumps({"action": int(c[1:])})) for c in ids]
            return list(reversed(rows))

        fake = FakeOpenRouter([{"statuses": ["completed"], "results": shuffled}])
        res = self.runner(fake).run("deepseek", [item("p1"), item("p2"), item("p3")])
        self.assertEqual(res.parsed, {"p1": {"action": 1}, "p2": {"action": 2},
                                      "p3": {"action": 3}})
        # the per-request log row of each custom_id carries its own answer
        by_id = {r["custom_id"]: r for r in self.read(self.raw_calls)}
        self.assertEqual(by_id["p2"]["response_parsed"], {"action": 2})

    def test_request_log_fields(self):
        fake = FakeOpenRouter([{"statuses": ["completed"],
                                "results": lambda ids: [ok_row(c, model="vendor/snap-9") for c in ids]}])
        self.runner(fake).run("gemini", [item("a")])
        rec = self.read(self.raw_calls)[0]
        self.assertEqual(rec["batch_id"], "batch_1")
        self.assertEqual(rec["custom_id"], "a")
        self.assertEqual(rec["model"], "google/gemini-3.8-flash")
        self.assertEqual(rec["model_snapshot"], "vendor/snap-9")
        self.assertEqual(rec["finish_reason"], "stop")
        self.assertEqual(rec["usage"]["completion_tokens"], 40)
        self.assertEqual(rec["reasoning_tokens"], 30)
        self.assertEqual(rec["response_raw"], '{"action": 3}')
        self.assertEqual(rec["batch_result_raw"]["custom_id"], "a")
        self.assertEqual(rec["attempt"], 1)
        self.assertIsNone(rec["invalid_reason"])

    def test_missing_row_counts_as_provider_error(self):
        fake = FakeOpenRouter([
            {"statuses": ["completed"], "results": lambda ids: [ok_row("a")]},
            {"statuses": ["completed"], "results": all_ok}])
        res = self.runner(fake).run("gpt", [item("a"), item("b")])
        self.assertEqual(res.counts["provider_error"], 1)
        self.assertEqual([r["custom_id"] for r in fake.created[1]["requests"]], ["b"])


class InvalidReasons(BatchTestBase):
    def test_three_reasons_counted_and_requeued(self):
        def first(ids):
            return [
                ok_row("good"),
                err_row("perr"),
                ok_row("trunc", content='{"action": 1', finish="length"),
                ok_row("junk", content="not json at all"),
                ok_row("neg", content='{"action": -5}'),
            ]

        fake = FakeOpenRouter([
            {"statuses": ["completed"], "results": first},
            {"statuses": ["completed"], "results": all_ok}])
        items = [item(c) for c in ("good", "perr", "trunc", "junk", "neg")]
        res = self.runner(fake).run(
            "gpt", items, is_valid=lambda p: p["action"] >= 0)
        self.assertTrue(res.ok)
        self.assertEqual(res.counts["provider_error"], 1)
        self.assertEqual(res.counts["bad_json"], 2)       # length + broken JSON
        self.assertEqual(res.counts["invalid_value"], 1)
        self.assertEqual(res.counts["n_batch_resubmit"], 0)
        # only the four invalid ones went into the second batch
        second = [r["custom_id"] for r in fake.created[1]["requests"]]
        self.assertEqual(second, ["perr", "trunc", "junk", "neg"])
        self.assertEqual(res.attempts, {"good": 1, "perr": 2, "trunc": 2, "junk": 2, "neg": 2})
        self.assertEqual(len(res.batch_ids), 2)
        reasons = {(r["custom_id"], r["attempt"]): r["invalid_reason"]
                   for r in self.read(self.raw_calls)}
        self.assertEqual(reasons[("perr", 1)], "provider_error")
        self.assertEqual(reasons[("trunc", 1)], "bad_json")
        self.assertEqual(reasons[("neg", 1)], "invalid_value")
        self.assertIsNone(reasons[("neg", 2)])

    def test_validator_that_raises_is_invalid_value(self):
        fake = FakeOpenRouter([
            {"statuses": ["completed"], "results": lambda ids: [ok_row(c, '{"x": 1}') for c in ids]},
            {"statuses": ["completed"], "results": all_ok}])
        res = self.runner(fake).run("gpt", [item("a")], is_valid=lambda p: p["action"] > 0)
        self.assertEqual(res.counts["invalid_value"], 1)
        self.assertTrue(res.ok)

    def test_attempt_limit_leaves_unresolved_and_never_codes_invalid(self):
        bad = lambda ids: [ok_row(c, '{"action": -1}') for c in ids]
        fake = FakeOpenRouter([{"statuses": ["completed"], "results": bad}] * 2)
        res = self.runner(fake).run(
            "gpt", [item("a")], is_valid=lambda p: p["action"] >= 0, max_attempts=2)
        self.assertFalse(res.ok)
        self.assertEqual(res.parsed, {})
        self.assertEqual(res.unresolved, {"a": "invalid_value"})
        self.assertEqual(res.counts["invalid_value"], 2)
        self.assertEqual(len(fake.created), 2)


class BatchLevelFailure(BatchTestBase):
    def test_expired_batch_is_resent_whole_and_counted(self):
        fake = FakeOpenRouter([
            {"statuses": ["in_progress", "expired"], "results": None},
            {"statuses": ["in_progress", "completed"], "results": all_ok}])
        res = self.runner(fake).run("deepseek", [item("a"), item("b"), item("c")])
        self.assertTrue(res.ok)
        self.assertEqual(res.counts["n_batch_resubmit"], 1)
        self.assertEqual(res.counts["n_batch_failed"], 1)
        self.assertEqual(sum(res.counts[r] for r in batch_client.REASONS), 0)
        first = [r["custom_id"] for r in fake.created[0]["requests"]]
        second = [r["custom_id"] for r in fake.created[1]["requests"]]
        self.assertEqual(first, second)
        self.assertEqual(res.attempts, {"a": 2, "b": 2, "c": 2})
        recs = self.read(self.registry)
        self.assertEqual([(r["event"], r["attempt"], r["status"]) for r in recs if "status" in r],
                         [("submitted", 1, "validating"), ("finished", 1, "expired"),
                          ("submitted", 2, "validating"), ("finished", 2, "completed")])

    def test_failed_and_cancelled_also_resend(self):
        for status in ("failed", "cancelled"):
            with self.subTest(status=status):
                fake = FakeOpenRouter([
                    {"statuses": [status], "results": None},
                    {"statuses": ["completed"], "results": all_ok}])
                res = self.runner(fake).run("gpt", [item("a")])
                self.assertEqual(res.counts["n_batch_resubmit"], 1)
                self.assertTrue(res.ok)

    def test_resubmit_limit(self):
        fake = FakeOpenRouter([{"statuses": ["expired"], "results": None}] * 2)
        res = self.runner(fake).run("gpt", [item("a")], max_attempts=2)
        self.assertEqual(res.unresolved, {"a": "batch_expired"})
        self.assertEqual(res.counts["n_batch_failed"], 2)
        self.assertEqual(res.counts["n_batch_resubmit"], 1)  # the 2nd failure sends nothing
        self.assertEqual(len(fake.created), 2)

    def test_transient_poll_error_is_tolerated(self):
        state = {"n": 0}

        def handler(request):
            if request.method == "POST":
                return httpx.Response(202, json={"id": "b1", "status": "validating"})
            state["n"] += 1
            if state["n"] == 1:
                return httpx.Response(503, text="try later")
            return httpx.Response(200, json={"id": "b1", "status": "completed",
                                             "results": [ok_row("a")]})

        http = batch_client.OpenRouterBatchHttp(
            FAKE_KEY, http=httpx.Client(transport=httpx.MockTransport(handler)))
        res = batch_client.BatchRunner(http).run("gpt", [item("a")])
        self.assertTrue(res.ok)
        self.assertEqual(state["n"], 2)


class TemperatureAndPayload(BatchTestBase):
    def test_temperature_not_sent_and_logged_default(self):
        fake = FakeOpenRouter([{"statuses": ["completed"], "results": all_ok}])
        self.runner(fake).run("gemini", [item("a")])
        payload = fake.created[0]
        self.assertNotIn("temperature", json.dumps(payload))
        self.assertEqual(self.read(self.raw_calls)[0]["temperature"], "default")

    def test_payload_shape_and_secrets(self):
        fake = FakeOpenRouter([{"statuses": ["completed"], "results": all_ok}])
        self.runner(fake).run("deepseek", [item("a")])
        p = fake.created[0]
        cfg = batch_client.BATCH_MODELS["deepseek"]
        self.assertEqual(p["model"], "deepseek/deepseek-v4.1-flash")  # no ":batch"
        self.assertEqual(p["provider"], {"only": cfg["provider_only"]})
        self.assertEqual(p["endpoint"], "/v1/chat/completions")
        self.assertEqual(p["completion_window"], "24h")
        body = p["requests"][0]["body"]
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["max_tokens"], cfg["max_tokens"])
        self.assertEqual(body["reasoning_effort"], cfg["reasoning_effort"])
        self.assertNotIn("model", body)
        self.assertIn("Respond with ONLY a JSON object", body["messages"][-1]["content"])
        self.assertEqual(fake.headers[0]["authorization"], f"Bearer {FAKE_KEY}")
        for rec in self.read(self.raw_calls) + self.read(self.registry):
            self.assertNotIn(FAKE_KEY, json.dumps(rec))

    def test_model_config_is_consistent_with_llm_client(self):
        self.assertEqual(set(batch_client.BATCH_MODELS), set(llm_client.MODELS))
        for key, cfg in batch_client.BATCH_MODELS.items():
            self.assertFalse(cfg["model"].endswith(":batch"))
            self.assertEqual(cfg["model"] + ":batch", llm_client.MODELS[key])
            self.assertTrue(cfg["provider_only"])
            self.assertTrue(cfg["reasoning_effort"])
            self.assertGreaterEqual(cfg["max_tokens"], 4000)


class MixedBatchRejected(BatchTestBase):
    def test_mixed_response_format_raises_before_any_call(self):
        fake = FakeOpenRouter([])
        items = [item("a"), item("b", response_format={"type": "json_schema"})]
        with self.assertRaises(batch_client.BatchValidationError):
            self.runner(fake).run("gemini", items)
        self.assertEqual(fake.created, [])
        self.assertEqual(self.read(self.registry), [])

    def test_mixed_step_types_raise_before_any_call(self):
        fake = FakeOpenRouter([])
        items = [item("a", step="contribution"), item("b", step="punishment")]
        with self.assertRaises(batch_client.BatchValidationError):
            self.runner(fake).run("gemini", items)
        self.assertEqual(fake.created, [])

    def test_submit_checks_too(self):
        fake = FakeOpenRouter([])
        with self.assertRaises(batch_client.BatchValidationError):
            self.runner(fake).submit(
                "gpt", [item("a"), item("b", response_format={"type": "text"})])
        self.assertEqual(fake.created, [])

    def test_duplicate_or_empty_custom_id_and_empty_batch(self):
        for items in ([item("a"), item("a")], [item("")], []):
            with self.subTest(n=len(items)):
                with self.assertRaises(batch_client.BatchValidationError):
                    batch_client.validate_items(items)

    def test_step_type_is_written_to_the_batch_record(self):
        fake = FakeOpenRouter([{"statuses": ["completed"], "results": all_ok}])
        self.runner(fake).run("gpt", [item("a", step="punishment")])
        self.assertEqual(self.read(self.registry)[0]["step"], "punishment")


if __name__ == "__main__":
    unittest.main()
