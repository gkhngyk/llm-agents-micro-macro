"""Mock tests of resuming an interrupted run (--resume) and of SIGINT / SIGTERM.

(a) complete units are not called again; (b) a partial unit runs again from
its start and the earlier rows stay byte for byte; (c) budget and invalid-rate
cap go on across segments; (d) a config difference stops before any call;
(e) a signal gives stop_reason "interrupted". No network, no ../.env.
"""

import contextlib
import hashlib
import io
import json
import os
import signal
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_pgg_game import CARD_A, CARD_B, ROOT, _payload  # noqa: E402
from test_pgg_guards import CostAPI, GuardTestBase  # noqa: E402

import llm_client  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Card, Engine, GameParams, RunStopped  # noqa: E402

MODELS2 = {"m1": "v/m1", "m2": "v/m2"}
GEMINI = {"gemini": "google/gemini-2.5-flash-lite"}


def _killer(api, at: int, sig=signal.SIGTERM, wait=True):
    """content_fn: the at-th call sends `sig` to this process (an in-flight call cut off)."""
    def content_fn(kwargs, content):
        if len(api.calls) == at:
            os.kill(os.getpid(), sig)
            if wait:                       # main thread: the handler raises in this loop
                for _ in range(10 ** 7):
                    pass
                raise AssertionError("the signal handler did not interrupt the run")
        return content
    return content_fn


def _tree(path: Path) -> dict:
    """sha256 of every file below path."""
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob("*")) if p.is_file()}


def _rows(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _sessions(api) -> list[str]:
    return [c["extra_body"]["session_id"] for c in api.calls]


class ResumeBase(GuardTestBase):
    def setUp(self):
        super().setUp()
        (self.tmp / "runs").mkdir()
        self.run_dir = self.tmp / "runs" / "r1"
        self.results = self.run_dir / "r1.jsonl"
        self.summary_path = self.run_dir / "r1_summary.json"
        self.raw = self.run_dir / "raw_calls.jsonl"

    def rcfg(self, **kw):
        # 2 models x 2 cards: units 0-3 group games (8 calls), units 4-7 schedules (5 calls)
        base = dict(run="r1", results_dir=None, runs_dir=self.tmp / "runs",
                    cards=[CARD_A, CARD_B], models=dict(MODELS2), arms=("group", "isolated"),
                    params=GameParams(rounds=2), groups_per_cell=1, isolated_reps=1,
                    budget_usd=1.0, invalid_rate_cap=0.5)
        base.update(kw)
        return self.cfg(**base)

    def interrupted_run(self, at=22, cost=0.0001, content_fn=None, **kw):
        """First segment, cut off by SIGTERM at the at-th call (22: units 0, 1 complete,
        unit 2 has its round 1 = 4 rows)."""
        api = CostAPI(cost=cost)
        kill = _killer(api, at)
        api.content_fn = (lambda k, c: kill(k, content_fn(k, c))) if content_fn else kill
        self.use(api)
        engine = Engine(self.rcfg(**kw))
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            engine.run()
        return engine, api

    def resume(self, cost=0.0001, content_fn=None, **kw):
        api = CostAPI(cost=cost, content_fn=content_fn)
        self.use(api)
        engine = Engine(self.rcfg(**kw))
        return engine, api

    def summary_now(self):
        return json.loads(self.summary_path.read_text())

    def raw_events(self, name):
        return [json.loads(x) for x in self.raw.read_text().splitlines()
                if json.loads(x).get("event") == name]


# --------------------------------------------------------------------------
# (a) + (b) complete units skipped, partial unit re-run, earlier bytes kept
# --------------------------------------------------------------------------

class ResumeUnits(ResumeBase):
    def test_complete_units_are_skipped_and_partial_unit_reruns(self):
        first, _ = self.interrupted_run()
        specs = first.unit_specs()
        self.assertEqual([s.arm for s in specs], ["group"] * 4 + ["isolated"] * 4)
        old_bytes = self.results.read_bytes()
        old_summary = self.summary_path.read_bytes()
        old_rows = _rows(self.results)
        self.assertEqual(len(old_rows), 8 + 8 + 4)
        self.assertEqual({r["segment"] for r in old_rows}, {0})

        engine, api = self.resume()
        path = engine.run(resume=True)
        self.assertEqual(path, self.results)

        # (a) only unit 2 (again, from round 1) and the untouched units are called
        called = set(_sessions(api))
        self.assertTrue(called.isdisjoint({specs[0].session_id, specs[1].session_id}))
        self.assertEqual(called, {s.session_id for s in specs[2:]})
        self.assertEqual(len(api.calls), 8 + 8 + 4 * 5)

        # (b) append-only: the old file is a byte-for-byte prefix of the new one
        new_bytes = self.results.read_bytes()
        self.assertEqual(new_bytes[:len(old_bytes)], old_bytes)
        new_rows = _rows(self.results)[len(old_rows):]
        self.assertEqual({r["segment"] for r in new_rows}, {1})
        self.assertEqual(len(new_rows), 8 + 8 + 4 * 5)
        # the partial unit runs again with the same seeds and session id
        old_u2 = {(r["round"], r["agent_id"]): r for r in old_rows if r["unit"] == specs[2].label}
        new_u2 = {(r["round"], r["agent_id"]): r for r in new_rows if r["unit"] == specs[2].label}
        self.assertEqual(len(old_u2), 4)
        self.assertEqual(len(new_u2), 8)
        for key, row in old_u2.items():
            self.assertEqual((new_u2[key]["seed"], new_u2[key]["session_id"]),
                             (row["seed"], row["session_id"]))

        superseded = [{"unit": specs[2].label, "segment": 0, "n_rows": 4}]
        summary = self.summary_now()
        self.assertEqual(summary["segment"], 1)
        self.assertTrue(summary["resumed"])
        self.assertIsNone(summary["stop_reason"])
        self.assertEqual(summary["superseded_units"], superseded)
        self.assertEqual(summary["units"], {"n_units": 8, "n_complete": 8,
                                            "n_complete_this_segment": 6,
                                            "n_partial_this_segment": 0, "n_remaining": 0})
        self.assertEqual([s["segment"] for s in summary["segments"]], [0, 1])
        self.assertEqual([s["stop_reason"] for s in summary["segments"]], ["interrupted", None])
        self.assertEqual([s["n_rows"] for s in summary["segments"]], [20, 36])
        self.assertEqual(summary["files"]["results"]["lines"], 56)
        self.assertEqual(summary["files"]["raw_log"]["lines"],
                         len(self.raw.read_text().splitlines()))
        # the previous summary was kept before it was replaced
        backup = self.run_dir / "r1_summary.seg0.json"
        self.assertEqual(backup.read_bytes(), old_summary)
        self.assertEqual(summary["files"]["summary_backups"], [str(backup)])
        # raw log: the resume event names the superseded unit
        resume = self.raw_events("pgg_run_resume")
        self.assertEqual(len(resume), 1)
        self.assertEqual(resume[0]["segment"], 1)
        self.assertEqual(resume[0]["superseded_units"], superseded)
        self.assertEqual(resume[0]["n_complete"], 2)
        self.assertEqual(resume[0]["remaining_units"], [s.label for s in specs[2:]])

    def test_a_second_resume_counts_segments_and_keeps_every_backup(self):
        self.interrupted_run()
        engine, api = self.resume()
        engine.run(resume=True)
        mid = self.results.read_bytes()
        engine, api = self.resume()
        engine.run(resume=True)                     # nothing left: no call
        self.assertEqual(api.calls, [])
        self.assertEqual(self.results.read_bytes(), mid)
        summary = self.summary_now()
        self.assertEqual(summary["segment"], 2)
        self.assertEqual([s["segment"] for s in summary["segments"]], [0, 1, 2])
        self.assertEqual(summary["superseded_units"][0]["segment"], 0)
        self.assertTrue((self.run_dir / "r1_summary.seg0.json").exists())
        self.assertEqual(json.loads((self.run_dir / "r1_summary.seg1.json").read_text())["segment"], 1)

    def test_cut_off_last_line_stays_and_new_rows_start_on_a_new_line(self):
        self.interrupted_run()
        with open(self.results, "ab") as f:
            f.write(b'{"run": "r1", "half a ro')      # killed while writing
        old = self.results.read_bytes()
        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertTrue(plan.truncated_last_line)
        self.assertEqual(plan.problems, [])
        engine, _ = self.resume()
        engine.run(resume=True)
        data = self.results.read_bytes()
        self.assertEqual(data[:len(old)], old)
        self.assertEqual(data[len(old):len(old) + 1], b"\n")
        self.assertEqual(self.summary_now()["units"]["n_complete"], 8)

    def test_without_resume_an_existing_run_is_never_overwritten(self):
        self.interrupted_run()
        before = _tree(self.run_dir)
        engine, api = self.resume()
        with self.assertRaises(FileExistsError):
            engine.run()
        self.assertEqual(api.calls, [])
        self.assertEqual(_tree(self.run_dir), before)

    def test_resume_of_a_missing_run_is_an_error(self):
        engine, api = self.resume()
        with self.assertRaisesRegex(ValueError, "nothing to resume"):
            engine.run(resume=True)
        self.assertEqual(api.calls, [])
        self.assertFalse(self.run_dir.exists())

    def test_old_format_run_is_resumed_from_its_rows(self):
        """A first run of the earlier code: rows without segment / unit, summary without config."""
        first, _ = self.interrupted_run()
        rows = _rows(self.results)
        self.results.write_text("".join(
            json.dumps({k: v for k, v in r.items() if k not in ("segment", "unit")}) + "\n"
            for r in rows))
        summary = self.summary_now()
        for k in ("config", "segments", "segment", "resumed", "units", "superseded_units",
                  "row_validity_rule", "segment_cost_usd"):
            summary.pop(k)
        self.summary_path.write_text(json.dumps(summary))
        raw = [json.loads(x) for x in self.raw.read_text().splitlines()]
        for rec in raw:
            if rec.get("event") == "pgg_run_start":
                rec.pop("config")
                rec.pop("segment")
        self.raw.write_text("".join(json.dumps(r) + "\n" for r in raw))
        old = self.results.read_bytes()

        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(plan.problems, [])
        self.assertIn("unit_order", plan.config_checked)
        self.assertIn("max_tokens", plan.config_checked)
        self.assertEqual(len(plan.complete), 2)
        self.assertEqual(plan.partial, [{"unit": first.unit_specs()[2].label, "segment": 0,
                                         "n_rows": 4}])
        # a changed card text is found in the raw log of the earlier segment
        changed = Card(CARD_A.card_id, CARD_A.style, CARD_A.text + " Changed.")
        bad = Engine(self.rcfg(cards=[changed, CARD_B]), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertTrue(any("text differs" in p for p in bad.problems), bad.problems)

        engine, api = self.resume()
        engine.run(resume=True)
        self.assertEqual(len(api.calls), 36)
        self.assertEqual(self.results.read_bytes()[:len(old)], old)
        self.assertEqual(self.summary_now()["units"]["n_complete"], 8)


# --------------------------------------------------------------------------
# (c) budget and invalid-rate cap across segments
# --------------------------------------------------------------------------

class ResumeGuards(ResumeBase):
    def test_budget_includes_the_cost_of_earlier_segments(self):
        # 21 responses arrived in segment 0 (the 22nd call was cut off): 0.21 USD
        self.interrupted_run(cost=0.01, budget_usd=0.255)
        plan = Engine(self.rcfg(budget_usd=0.255), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertAlmostEqual(plan.prior_cost_usd, 0.21, places=9)
        self.assertEqual(plan.prior_source, "raw_log")
        self.assertTrue(plan.cost_check["match"])
        engine, api = self.resume(cost=0.01, budget_usd=0.255)
        with self.assertRaisesRegex(RunStopped, "budget"):
            engine.run(resume=True)
        # 0.21 + 5 x 0.01 = 0.26 >= 0.255: the 6th call is not sent (without the
        # earlier segment 25 calls would have been allowed)
        self.assertEqual(len(api.calls), 5)
        summary = self.summary_now()
        self.assertEqual(summary["stop_reason"], "budget")
        self.assertAlmostEqual(summary["total_cost_usd"], 0.26, places=9)
        self.assertAlmostEqual(summary["segment_cost_usd"], 0.05, places=9)
        self.assertEqual(sum(m["n_responses"] for m in summary["per_model"].values()), 26)
        self.assertEqual([s["n_responses"] for s in summary["segments"]], [21, 5])

    def test_budget_reached_before_resume_sends_nothing(self):
        engine, _ = self.resume(cost=0.01, budget_usd=0.2)
        with self.assertRaisesRegex(RunStopped, "budget"):
            engine.run()                                # segment 0 ends at the budget
        engine, api = self.resume(cost=0.01, budget_usd=0.2)
        with self.assertRaisesRegex(RunStopped, "budget"):
            engine.run(resume=True)
        self.assertEqual(api.calls, [])

    def test_prior_cost_from_the_summary_when_the_raw_log_is_gone(self):
        self.interrupted_run(cost=0.01, budget_usd=0.255)
        self.raw.unlink()
        plan = Engine(self.rcfg(budget_usd=0.255), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(plan.prior_source, "summary")
        self.assertAlmostEqual(plan.prior_cost_usd, 0.21, places=9)

    def test_invalid_rate_cap_counts_earlier_segments(self):
        # 26 planned calls per model x 0.1 -> at most 2 invalid + parse-failed responses
        def bad_m1(n):
            seen = []

            def fn(kwargs, content):
                if kwargs["model"] == "v/m1" and "QUESTION" not in kwargs["messages"][-1]["content"]:
                    seen.append(1)
                    if len(seen) <= n:
                        return _payload({"contribution": 25})
                return content
            return fn

        self.interrupted_run(invalid_rate_cap=0.1, content_fn=bad_m1(2))
        summary = self.summary_now()
        self.assertEqual(summary["per_model"]["v/m1"]["n_invalid"], 2)
        self.assertEqual(summary["stopped_models"], {})
        engine, api = self.resume(invalid_rate_cap=0.1, content_fn=bad_m1(1))
        engine.run(resume=True)
        summary = self.summary_now()
        self.assertEqual(summary["per_model"]["v/m1"]["n_invalid"], 3)
        self.assertEqual(summary["stopped_models"], {"m1": "invalid_rate_cap"})
        stopped = self.raw_events("pgg_model_stopped")
        self.assertEqual((stopped[-1]["n_invalid"], stopped[-1]["limit"]), (3, 2))
        self.assertGreater(summary["units"]["n_remaining"], 0)     # m1 units left undone


# --------------------------------------------------------------------------
# (d) config differences: error before any call or write
# --------------------------------------------------------------------------

class ResumeConfig(ResumeBase):
    def test_config_difference_stops_before_any_call(self):
        self.interrupted_run()
        before = _tree(self.run_dir)
        changed_card = Card(CARD_B.card_id, CARD_B.style, CARD_B.text + " More.")
        variants = {
            "max_tokens": dict(max_tokens=1234),
            "seed_namespace": dict(seed_namespace="other"),
            "isolated_frame": dict(isolated_frame="repeated"),
            "providers": dict(providers={k: {"slug": "p", "name": "P"} for k in MODELS2}),
            "models": dict(models={"m1": "v/m1", "m2": "v/other"}),
            "cards": dict(cards=[CARD_A, changed_card]),
            "budget_usd": dict(budget_usd=2.0),
            "reasoning_effort": dict(reasoning_effort="low"),
        }
        for name, kw in variants.items():
            with self.subTest(name):
                engine, api = self.resume(**kw)
                with self.assertRaisesRegex(ValueError, f"not resumed, no call made.*{name}"):
                    engine.run(resume=True)
                self.assertEqual(api.calls, [])
                self.assertEqual(_tree(self.run_dir), before)       # nothing written
        # operational settings may change
        engine, api = self.resume(workers=2, parallel_units=2, request_timeout_s=99)
        engine.run(resume=True)
        self.assertEqual(len(api.calls), 36)

    def test_rows_of_another_design_are_refused(self):
        self.interrupted_run()
        with open(self.results, "a") as f:
            f.write(json.dumps({"run": "r1", "session_id": "pgg-r1-zz", "step": "contribute"}) + "\n")
        engine, api = self.resume()
        with self.assertRaisesRegex(ValueError, "not a unit of this run's design"):
            engine.run(resume=True)
        self.assertEqual(api.calls, [])


# --------------------------------------------------------------------------
# (e) SIGINT / SIGTERM
# --------------------------------------------------------------------------

class Signals(ResumeBase):
    def test_sigterm_and_sigint_stop_with_interrupted(self):
        for sig in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(sig.name):
                before = signal.getsignal(sig)
                api = CostAPI()
                api.content_fn = _killer(api, 10, sig)
                self.use(api)
                cfg = self.rcfg(run=f"s{sig.value}")
                with self.assertRaisesRegex(RunStopped, "interrupted"):
                    Engine(cfg).run()
                run_dir = self.tmp / "runs" / cfg.run
                summary = json.loads((run_dir / f"{cfg.run}_summary.json").read_text())
                self.assertEqual(summary["stop_reason"], "interrupted")
                self.assertEqual(summary["segments"][-1]["stop_reason"], "interrupted")
                self.assertEqual(len(api.calls), 10)             # no call after the signal
                self.assertEqual(summary["files"]["results"]["lines"], 8)   # unit 0 only
                raw = [json.loads(x) for x in (run_dir / "raw_calls.jsonl").read_text().splitlines()]
                stopped = [r for r in raw if r.get("event") == "pgg_run_stopped"]
                self.assertEqual([(r["reason"], r["signal"]) for r in stopped],
                                 [("interrupted", sig.name)])
                self.assertEqual(signal.getsignal(sig), before)   # handler restored

    def test_signal_with_parallel_units_writes_the_summary(self):
        api = CostAPI()
        api.content_fn = _killer(api, 12, wait=False)              # sent from a worker thread
        self.use(api)
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            Engine(self.rcfg(parallel_units=3, workers=2)).run()
        summary = self.summary_now()
        self.assertEqual(summary["stop_reason"], "interrupted")
        self.assertLess(len(api.calls), 52)
        self.assertEqual(len(self.raw_events("pgg_run_summary_updated")), 1)
        self.assertEqual(summary["files"]["results"]["lines"], len(_rows(self.results)))
        # and the run can be resumed to the end
        engine, _ = self.resume(parallel_units=3, workers=2)
        engine.run(resume=True)
        self.assertEqual(self.summary_now()["units"]["n_remaining"], 0)


# --------------------------------------------------------------------------
# --resume --dry-run and the offline stand-in for llm_client
# --------------------------------------------------------------------------

class ResumeDryRun(ResumeBase):
    def cards_file(self):
        path = self.tmp / "cards.json"
        path.write_text(json.dumps([{"card_id": c.card_id, "style": c.style, "text": c.text}
                                    for c in (CARD_A, CARD_B)]))
        return path

    def argv(self):
        return ["--run", "r1", "--cards", str(self.cards_file()), "--models", "gemini",
                "--rounds", "2", "--groups-per-cell", "1", "--isolated-reps", "1",
                "--runs-dir", str(self.tmp / "runs"), "--resume", "--dry-run"]

    def test_dry_run_prints_the_plan_and_writes_nothing(self):
        # 1 model x 2 cards: group, group, schedule, schedule; cut off in unit 1, round 2
        self.interrupted_run(at=14, models=dict(GEMINI), budget_usd=None, invalid_rate_cap=None,
                             max_invalid=3)
        argv = self.argv()
        before = _tree(self.tmp)
        self.create.reset_mock()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = pgg_game.main(argv)
        text = out.getvalue()
        self.assertEqual(code, 0, text)
        self.assertIn("tamam 1; yarım (satırı var, baştan koşulacak) 1", text)
        self.assertIn("kalan (koşulacak) 3", text)
        self.assertIn("gemini 18; toplam 18", text)               # 8 + 5 + 5
        self.assertIn("yeni segment: 1", text)
        self.assertIn("Config tutarlı", text)
        self.assertEqual(_tree(self.tmp), before)
        self.create.assert_not_called()

    def test_dry_run_needs_no_key_and_does_not_import_llm_client(self):
        self.interrupted_run(at=14, models=dict(GEMINI), budget_usd=None, invalid_rate_cap=None)
        before = _tree(self.tmp / "runs")
        env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
        script = str(ROOT / "pgg_game.py")
        code = ("import runpy, sys\n"
                f"sys.argv = [{script!r}] + sys.argv[1:]\n"
                f"sys.path.insert(0, {str(ROOT)!r})\n"
                "try:\n"
                "    runpy.run_path(sys.argv[0], run_name='__main__')\n"
                "except SystemExit:\n"
                "    pass\n"
                "print('LLM_CLIENT_IMPORTED', 'llm_client' in sys.modules)\n")
        proc = subprocess.run([sys.executable, "-c", code, *self.argv()],
                              capture_output=True, text=True, env=env, cwd=self.tmp, timeout=60)
        self.assertIn("kalan (koşulacak) 3", proc.stdout, proc.stderr)
        self.assertIn("LLM_CLIENT_IMPORTED False", proc.stdout)
        self.assertEqual(_tree(self.tmp / "runs"), before)

    def test_dry_run_reports_a_config_difference(self):
        self.interrupted_run(at=14, models=dict(GEMINI), budget_usd=None, invalid_rate_cap=None)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = pgg_game.main(self.argv() + ["--max-tokens", "999"])
        self.assertEqual(code, 1)
        self.assertIn("SORUN", out.getvalue())
        self.assertIn("config max_tokens", out.getvalue())

    def test_offline_stand_in_equals_llm_client(self):
        for parts in [("pgg", "r1", "order", "model", "m1"), ("a",), ("x", 1, None, 2.5, "ü")]:
            self.assertEqual(pgg_game.OfflineLLM.stable_seed(*parts), llm_client.stable_seed(*parts))
        self.assertEqual(pgg_game.OfflineLLM.stable_seed("a", 1, base=7),
                         llm_client.stable_seed("a", 1, base=7))
        self.assertEqual(pgg_game.OfflineLLM.DEFAULT_MAX_TOKENS, llm_client.DEFAULT_MAX_TOKENS)
        self.assertEqual(pgg_game.OfflineLLM.DEFAULT_TIMEOUT_S, llm_client.DEFAULT_TIMEOUT_S)
        self.assertEqual(pgg_game.OfflineLLM.reasoning_effort_label(None),
                         llm_client.reasoning_effort_label(None))


if __name__ == "__main__":
    unittest.main()
