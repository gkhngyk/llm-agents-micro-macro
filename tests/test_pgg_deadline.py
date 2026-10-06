"""Mock tests of the request deadline (llm_client) and the stall watchdog (pgg_game).

(a) a hanging attempt is abandoned at its deadline, logged as transport /
deadline and retried; (b) every attempt hangs: the usual exhaustion; the
abandoned threads end; (c) the watchdog stops a run as "stalled" and --resume
completes it; (d) a run written by the earlier code (summary without the new
settings) resumes with other deadline / stall values. No network, no ../.env.
"""

import contextlib
import io
import json
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import httpx
import openai

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_llm_client_logging import MESSAGES, SCHEMA, LoggingTestBase, _resp  # noqa: E402
from test_pgg_game import CARD_A, CARD_B  # noqa: E402
from test_pgg_guards import CostAPI  # noqa: E402
from test_pgg_resume import GEMINI, ResumeBase, _rows, _tree  # noqa: E402

import llm_client  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Engine, RunStopped  # noqa: E402


def _until(predicate, timeout=5.0) -> bool:
    """Wait (without time.sleep, which the test bases mock) until predicate() holds."""
    end = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > end:
            return False
        threading.Event().wait(0.01)
    return True


class Hang:
    """create() side effect: the calls listed in `hang` block until release()."""

    def __init__(self, replies, hang, late_reply=None):
        self.replies = list(replies)
        self.hang = set(hang)
        self.late_reply = late_reply           # what a released call returns (None: raises)
        self.event = threading.Event()
        self.n = 0

    def __call__(self, **kwargs):
        self.n += 1
        if self.n in self.hang:
            self.event.wait(30)
            if self.late_reply is None:
                raise ConnectionError("released")
            return self.late_reply
        return self.replies.pop(0)

    def release(self):
        self.event.set()


# --------------------------------------------------------------------------
# (a) + (b) llm_client: deadline, retry, exhaustion, no thread left behind
# --------------------------------------------------------------------------

class RequestDeadline(LoggingTestBase):
    def setUp(self):
        super().setUp()
        self.assertEqual(llm_client.abandoned_attempts_alive(), 0)

    def hang(self, *args, **kw):
        hang = Hang(*args, **kw)
        self.create.side_effect = hang
        # cleanups run last-in first-out: release, then wait for the threads
        self.addCleanup(_until, lambda: llm_client.abandoned_attempts_alive() == 0)
        self.addCleanup(hang.release)
        return hang

    def test_hanging_attempt_is_abandoned_logged_and_retried(self):
        late = []
        hang = self.hang([_resp('{"action": 1}')], hang={1},
                         late_reply=_resp('{"action": 9}'))
        started = time.monotonic()
        out = llm_client.call_llm_valid(
            "m", MESSAGES, schema=SCHEMA, session_id="s", is_valid=lambda c: True,
            request_deadline_s=0.2, on_late_response=late.append)
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(out, ({"action": 1}, 0))
        self.assertEqual(self.create.call_count, 2)
        retry, ok = self.records()
        self.assertEqual((retry["error_kind"], retry["error_subkind"], retry["error_type"]),
                         ("transport", "deadline", "RequestDeadlineExceeded"))
        self.assertIs(retry["retrying"], True)
        self.assertEqual((retry["attempt"], retry["request_deadline_s"]), (0, 0.2))
        self.assertGreaterEqual(retry["elapsed_s"], 0.2)
        self.assertEqual(retry["abandoned_attempts_alive"], 1)
        self.assertIsNone(retry["finish_reason"])
        self.assertNotIn("usage", retry)                 # no response arrived
        self.assertEqual((ok["attempt"], ok["response_parsed"]), (1, {"action": 1}))
        # the abandoned call answers later: logged as late_response, not a decision
        hang.release()
        self.assertTrue(_until(lambda: llm_client.abandoned_attempts_alive() == 0))
        self.assertTrue(_until(lambda: len(self.records()) == 3))
        late_rec = self.records()[-1]
        self.assertEqual((late_rec["event"], late_rec["abandoned"], late_rec["attempt"]),
                         ("late_response", "deadline", 0))
        self.assertNotIn("response_parsed", late_rec)
        self.assertEqual(late_rec["response_raw"], '{"action": 9}')
        self.assertEqual(len(late), 1)

    def test_every_attempt_hangs_exhausts_as_before(self):
        hang = self.hang([], hang={1, 2, 3})
        counts = {}
        with self.assertRaisesRegex(RuntimeError, "failed after 3 attempts"):
            llm_client._call_llm_counted("m", MESSAGES, schema=SCHEMA, session_id="s",
                                         max_retries=3, request_deadline_s=0.1)
        self.assertEqual(self.create.call_count, 3)
        recs = self.records()
        self.assertEqual(len(recs), 4)                   # 3 attempts + the final record
        self.assertTrue(all(r.get("retrying") for r in recs[:3]))
        self.assertEqual([r["error_subkind"] for r in recs], ["deadline"] * 4)
        final = recs[-1]
        self.assertNotIn("retrying", final)
        self.assertEqual((final["attempt"], final["error_kind"], final["error_type"]),
                         (3, "transport", "RequestDeadlineExceeded"))
        self.assertEqual(llm_client.abandoned_attempts_alive(), 3)
        # call_llm_valid: same exhaustion, its counts stay at zero
        hang2 = self.hang([], hang={1, 2, 3, 4})
        with self.assertRaises(RuntimeError):
            llm_client.call_llm_valid("m", MESSAGES, schema=SCHEMA, session_id="s",
                                      is_valid=lambda c: True, counts=counts,
                                      request_deadline_s=0.05)
        self.assertEqual(counts, {"n_invalid": 0, "n_parse_fail": 0, "n_provider_error": 0,
                                  "n_transport": 0, "n_deadline": 4, "n_provider_mismatch": 0})
        # released: every abandoned thread ends; an error after the deadline logs nothing
        n = len(self.records())
        hang.release()
        hang2.release()
        self.assertTrue(_until(lambda: llm_client.abandoned_attempts_alive() == 0))
        self.assertEqual(len(self.records()), n)

    def test_fast_call_leaves_no_thread(self):
        self.create.side_effect = [_resp('{"action": 1}')]
        before = threading.active_count()
        self.assertEqual(self.call(request_deadline_s=5), {"action": 1})
        self.assertTrue(_until(lambda: threading.active_count() <= before))
        self.assertEqual(llm_client.abandoned_attempts_alive(), 0)
        self.assertNotIn("error_subkind", self.records()[-1])

    def test_default_and_invalid_deadline(self):
        self.assertEqual(llm_client.DEFAULT_REQUEST_DEADLINE_S, 900.0)
        with self.assertRaises(ValueError):
            self.call(request_deadline_s=0)
        self.create.assert_not_called()

    def test_records_go_to_the_log_the_call_started_with(self):
        hang = self.hang([_resp('{"action": 1}')], hang={1}, late_reply=_resp('{"action": 2}'))
        self.call(request_deadline_s=0.1)
        other = self.log_path.parent / "other.jsonl"
        previous = llm_client.set_log_path(other)
        self.addCleanup(llm_client.set_log_path, previous)
        hang.release()
        self.assertTrue(_until(lambda: len(self.records()) == 3))
        self.assertFalse(other.exists())


class DeadlineHook(unittest.TestCase):
    """The response hook cuts an abandoned attempt's response, so its thread ends."""

    def trickle(self, stop):
        def handler(request):
            def body():
                while not stop.is_set():
                    yield b" "                   # keep-alive bytes, never a whole body
                    stop.wait(0.02)
            return httpx.Response(200, stream=_Iter(body()))
        return handler

    @staticmethod
    def client(handler):
        return httpx.Client(transport=httpx.MockTransport(handler),
                            event_hooks={"response": [llm_client._cut_at_deadline]})

    def test_client_uses_the_hook_and_keeps_the_environment_proxy(self):
        self.assertIn(llm_client._cut_at_deadline,
                      llm_client._client._client.event_hooks["response"])
        # a custom transport would make httpx drop the proxy of the environment
        with mock.patch.dict("os.environ", {"HTTPS_PROXY": "http://proxy.invalid:3128"}):
            http = llm_client._new_http_client()
        self.assertTrue(any(m is not None for m in http._mounts.values()))
        self.assertIn(llm_client._cut_at_deadline, http.event_hooks["response"])

    def test_trickling_body_is_cut_at_the_deadline(self):
        stop = threading.Event()
        self.addCleanup(stop.set)
        client = self.client(self.trickle(stop))
        llm_client._attempt_local.deadline = time.monotonic() + 0.15
        self.addCleanup(setattr, llm_client._attempt_local, "deadline", None)
        started = time.monotonic()
        with self.assertRaises(httpx.ReadTimeout) as cm:
            client.get("https://example.invalid/")
        self.assertIsInstance(cm.exception, llm_client._DeadlineReadTimeout)
        self.assertLess(time.monotonic() - started, 2)
        # without a deadline (e.g. call_decisions) nothing is cut
        llm_client._attempt_local.deadline = None
        ok = self.client(lambda r: httpx.Response(200, content=b"{}"))
        self.assertEqual(ok.get("https://example.invalid/").content, b"{}")

    def test_abandoned_thread_ends_through_the_hook(self):
        stop = threading.Event()
        self.addCleanup(stop.set)
        client = self.client(self.trickle(stop))
        with self.assertRaises(llm_client.RequestDeadlineExceeded):
            llm_client._call_with_deadline(lambda: client.get("https://example.invalid/").read(),
                                           0.15)
        # the server never stops sending; the thread still ends
        self.assertTrue(_until(lambda: llm_client.abandoned_attempts_alive() == 0, timeout=3))

    def test_through_the_openai_sdk(self):
        """The SDK reads the body after the hook: cut at the deadline, normal bodies pass."""
        stop = threading.Event()
        self.addCleanup(stop.set)
        completion = {"id": "x", "object": "chat.completion", "created": 0, "model": "m",
                      "choices": [{"index": 0, "finish_reason": "stop",
                                   "message": {"role": "assistant", "content": '{"a": 1}'}}]}

        def sdk(handler):
            return openai.OpenAI(base_url="https://example.invalid/v1", api_key="test-dummy",
                                 max_retries=0, http_client=self.client(handler))

        def create(client):
            return client.chat.completions.create(model="m", messages=MESSAGES)

        slow = sdk(self.trickle(stop))
        with self.assertRaises(llm_client.RequestDeadlineExceeded):
            llm_client._call_with_deadline(lambda: create(slow), 0.15)
        self.assertTrue(_until(lambda: llm_client.abandoned_attempts_alive() == 0, timeout=3))
        fast = sdk(lambda r: httpx.Response(200, json=completion))
        resp = llm_client._call_with_deadline(lambda: create(fast), 5)
        self.assertEqual(resp.choices[0].message.content, '{"a": 1}')


class _Iter(httpx.SyncByteStream):
    def __init__(self, it):
        self.it = it

    def __iter__(self):
        yield from self.it


# --------------------------------------------------------------------------
# (c) watchdog: stalled run, then --resume to the end
# --------------------------------------------------------------------------

class HangAPI(CostAPI):
    """CostAPI whose at-th call blocks until release() (a call that never ends)."""

    def __init__(self, at, **kw):
        super().__init__(**kw)
        self.at = at
        self.event = threading.Event()
        self.content_fn = self._content

    def _content(self, kwargs, content):
        if len(self.calls) == self.at:
            self.event.wait(30)
        return content

    def release(self):
        self.event.set()


class StallWatchdog(ResumeBase):
    def hang_api(self, at):
        api = HangAPI(at)
        self.use(api)
        self.addCleanup(_until, lambda: llm_client.abandoned_attempts_alive() == 0)
        self.addCleanup(api.release)
        return api

    def test_stall_stops_the_run_and_resume_completes_it(self):
        api = self.hang_api(at=12)         # unit 1 (group game), round 1
        engine = Engine(self.rcfg(request_deadline_s=60, stall_timeout_s=0.3))
        started = time.monotonic()
        with self.assertRaisesRegex(RunStopped, "stalled"):
            engine.run()
        self.assertLess(time.monotonic() - started, 10)       # not the 60 s deadline
        self.assertTrue(engine.stalled)
        self.assertEqual(len(api.calls), 12)
        summary = self.summary_now()
        self.assertEqual(summary["stop_reason"], "stalled")
        self.assertTrue(summary["stalled"])
        seg = summary["segments"][-1]
        self.assertEqual((seg["stop_reason"], seg["stalled"]), ("stalled", True))
        self.assertEqual((seg["request_deadline_s"], seg["stall_timeout_s"]), (60, 0.3))
        self.assertLessEqual({"git_commit", "git_dirty", "files_sha256", "source", "code_dir"},
                             set(seg["code_version"]))
        self.assertEqual(set(seg["code_version"]["files_sha256"]), set(pgg_game.CODE_FILES))
        self.assertEqual(summary["units"]["n_complete"], 1)
        self.assertEqual(summary["files"]["results"]["lines"], 8)
        stopped = self.raw_events("pgg_run_stopped")
        self.assertEqual([e["reason"] for e in stopped], ["stalled"])
        self.assertGreaterEqual(stopped[0]["idle_s"], 0.3)
        lines = self.results.read_bytes()

        # the hung call ends later: no row is written for the stopped run
        api.release()
        engine._wait_pools()
        self.assertEqual(self.results.read_bytes(), lines)

        engine2, api2 = self.resume(request_deadline_s=60, stall_timeout_s=0.3)
        engine2.run(resume=True)
        summary = self.summary_now()
        self.assertIsNone(summary["stop_reason"])
        self.assertEqual(summary["units"]["n_remaining"], 0)
        self.assertEqual([s["stop_reason"] for s in summary["segments"]], ["stalled", None])
        self.assertEqual(len(api2.calls), 8 * 3 + 5 * 4)       # units 1-7

    def test_deadline_below_the_stall_timeout_retries_without_stalling(self):
        api = self.hang_api(at=3)
        engine = Engine(self.rcfg(request_deadline_s=0.2, stall_timeout_s=30))
        engine.run()
        self.assertFalse(engine.stalled)
        deadline = [json.loads(x) for x in self.raw.read_text().splitlines()
                    if json.loads(x).get("error_subkind") == "deadline"]
        self.assertEqual(len(deadline), 1)
        self.assertEqual(deadline[0]["error_kind"], "transport")
        summary = self.summary_now()
        self.assertEqual(summary["units"]["n_remaining"], 0)
        self.assertEqual(len(api.calls), 52 + 1)               # one call sent twice
        # the abandoned call answers later: billed, logged, counted on resume
        api.release()
        self.assertTrue(_until(lambda: llm_client.abandoned_attempts_alive() == 0))
        late = self.raw_events("late_response")
        self.assertEqual(len(late), 1)
        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(sum(s["n_responses"] for s in plan.prior_stats.values()), 52 + 1)

    def test_parallel_units_stall(self):
        api = self.hang_api(at=5)
        engine = Engine(self.rcfg(parallel_units=3, workers=2, request_deadline_s=60,
                                  stall_timeout_s=0.3))
        # the other units go on and keep the log busy; the stall comes once they are done
        with self.assertRaisesRegex(RunStopped, "stalled"):
            engine.run()
        summary = self.summary_now()
        self.assertEqual(summary["stop_reason"], "stalled")
        self.assertEqual(summary["units"]["n_remaining"], 1)
        api.release()
        engine._wait_pools()
        engine2, _ = self.resume(parallel_units=3, workers=2, request_deadline_s=60,
                                 stall_timeout_s=0.3)
        engine2.run(resume=True)
        self.assertEqual(self.summary_now()["units"]["n_remaining"], 0)

    def test_settings_are_validated_and_recorded(self):
        for name in ("request_deadline_s", "stall_timeout_s"):
            for bad in (0, -1, "5", True):
                with self.subTest(name=name, value=bad), self.assertRaises(ValueError):
                    self.rcfg(**{name: bad}).validate()
        self.use(CostAPI())
        engine = Engine(self.rcfg())
        self.assertEqual((engine.deadline, engine.stall_timeout), (900.0, 1800.0))
        engine.run()
        summary = self.summary_now()
        self.assertEqual((summary["request_deadline_s"], summary["stall_timeout_s"]),
                         (900.0, 1800.0))
        start = self.raw_events("pgg_run_start")[0]
        self.assertEqual((start["request_deadline_s"], start["stall_timeout_s"]), (900.0, 1800.0))
        self.assertEqual(start["code_version"], summary["segments"][-1]["code_version"])
        self.assertEqual(pgg_game.OfflineLLM.DEFAULT_REQUEST_DEADLINE_S,
                         llm_client.DEFAULT_REQUEST_DEADLINE_S)

    def test_exit_after_stall_only_with_stuck_threads(self):
        with mock.patch.object(pgg_game.os, "_exit") as exit_:
            pgg_game._exit_after_stall(1)
            exit_.assert_not_called()
            release = threading.Event()
            stuck = threading.Thread(target=release.wait, args=(30,))
            stuck.start()
            try:
                with contextlib.redirect_stderr(io.StringIO()):
                    pgg_game._exit_after_stall(1)
            finally:
                release.set()
                stuck.join()
            exit_.assert_called_once_with(1)


# --------------------------------------------------------------------------
# (d) runs of the earlier code resume; the new settings are not compared
# --------------------------------------------------------------------------

# config_record keys of 58ae381 (the code pilot_v2_20261005 ran with)
CONFIG_KEYS_58AE381 = {
    "models", "providers", "seed_namespace", "max_tokens", "isolated_frame", "reasoning_effort",
    "params", "conditions", "arms", "groups_per_cell", "isolated_reps", "isolated_points",
    "max_invalid", "rationale", "budget_usd", "invalid_rate_cap", "stop_on_length",
    "check_snapshot", "cards"}
NEW_FIELDS = ("request_deadline_s", "stall_timeout_s", "code_version", "stalled")


class OldConfigResume(ResumeBase):
    def strip_new_fields(self):
        """Make the run directory look as if 58ae381 had written it."""
        summary = self.summary_now()
        for k in NEW_FIELDS:
            summary.pop(k, None)
        for seg in summary["segments"]:
            for k in NEW_FIELDS:
                seg.pop(k, None)
        self.summary_path.write_text(json.dumps(summary, indent=2) + "\n")
        raw = [json.loads(x) for x in self.raw.read_text().splitlines()]
        for rec in raw:
            if rec.get("event") in ("pgg_run_start", "pgg_run_end", "pgg_run_summary_updated"):
                for k in NEW_FIELDS:
                    rec.pop(k, None)
        self.raw.write_text("".join(json.dumps(r) + "\n" for r in raw))

    def test_config_record_is_unchanged(self):
        engine = Engine(self.rcfg(request_deadline_s=1, stall_timeout_s=2),
                        llm=pgg_game.OfflineLLM())
        self.assertEqual(set(engine.config_record()), CONFIG_KEYS_58AE381)
        other = Engine(self.rcfg(request_deadline_s=99, stall_timeout_s=999),
                       llm=pgg_game.OfflineLLM())
        self.assertEqual(engine.config_record(), other.config_record())

    def test_old_run_resumes_with_new_settings(self):
        self.interrupted_run()
        self.strip_new_fields()
        old_summary = self.summary_path.read_bytes()
        plan = Engine(self.rcfg(request_deadline_s=120, stall_timeout_s=600),
                      llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(plan.problems, [])
        self.assertIn("config", plan.config_checked)
        engine, api = self.resume(request_deadline_s=120, stall_timeout_s=600)
        engine.run(resume=True)
        summary = self.summary_now()
        self.assertEqual(summary["units"]["n_remaining"], 0)
        old, new = summary["segments"]
        self.assertNotIn("code_version", old)                    # earlier entry kept as it was
        self.assertEqual((new["request_deadline_s"], new["stall_timeout_s"]), (120, 600))
        self.assertIn("files_sha256", new["code_version"])
        self.assertEqual((self.run_dir / "r1_summary.seg0.json").read_bytes(), old_summary)
        self.assertIsNone(new["timeout_change"])
        self.assertEqual(summary["timeout_changes"], [])
        # once more with other values: segment 1 recorded 120 / 600, so this stops
        before = _tree(self.run_dir)
        engine, api = self.resume(request_deadline_s=30, stall_timeout_s=90)
        with self.assertRaisesRegex(ValueError, "differ from segment 1.*--allow-timeout-change"):
            engine.run(resume=True)
        self.assertEqual(api.calls, [])
        self.assertEqual(_tree(self.run_dir), before)
        # allowed: it runs, and the change is in the summary
        engine, api = self.resume(request_deadline_s=30, stall_timeout_s=90,
                                  allow_timeout_change=True)
        engine.run(resume=True)
        self.assertEqual(api.calls, [])
        summary = self.summary_now()
        self.assertEqual([(s.get("request_deadline_s"), s.get("stall_timeout_s"))
                          for s in summary["segments"]],
                         [(None, None), (120, 600), (30, 90)])
        change = {"from_segment": 1, "earlier": {"request_deadline_s": 120, "stall_timeout_s": 600},
                  "now": {"request_deadline_s": 30, "stall_timeout_s": 90}, "allowed": True}
        self.assertEqual(summary["segments"][-1]["timeout_change"], change)
        self.assertEqual(summary["timeout_changes"], [change])
        self.assertEqual(self.raw_events("pgg_run_resume")[-1]["timeout_change"], change)

    def test_cli_resume_dry_run_with_new_options(self):
        self.interrupted_run(at=14, models=dict(GEMINI), budget_usd=None, invalid_rate_cap=None)
        self.strip_new_fields()
        cards = self.tmp / "cards.json"
        cards.write_text(json.dumps([{"card_id": c.card_id, "style": c.style, "text": c.text}
                                     for c in (CARD_A, CARD_B)]))
        argv = ["--run", "r1", "--cards", str(cards), "--models", "gemini", "--rounds", "2",
                "--groups-per-cell", "1", "--isolated-reps", "1",
                "--runs-dir", str(self.tmp / "runs"), "--resume", "--dry-run",
                "--request-deadline", "240", "--stall-timeout", "1200"]
        before = _tree(self.tmp)
        self.create.reset_mock()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = pgg_game.main(argv)
        text = out.getvalue()
        self.assertEqual(code, 0, text)
        self.assertIn("Config tutarlı", text)
        self.assertIn("request_deadline_s=240, stall_timeout_s=1200", text)
        self.assertEqual(_tree(self.tmp), before)
        self.create.assert_not_called()
        self.assertEqual(len(_rows(self.results)), 12)


if __name__ == "__main__":
    unittest.main()
