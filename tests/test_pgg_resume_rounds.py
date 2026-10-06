"""Mock tests of A1: round-level resume, discarded responses, the run lock and
cut-off last lines. No network, no ../.env, no real run directory.

(a) a run cut off in round k and resumed has the prompts and the valid rows of
an uninterrupted run (N and P); (b) a partly written round is superseded and
played again, earlier rounds are kept; rows of the code before A1 (a unit
re-run from round 1) still read; (c) accepted answers without a row are
logged as "pgg_discarded" (live, or found on resume) and counted per model;
(d) a cut-off last line survives any number of resumes; (e) a second process
or Engine is refused by the lock, a stale lock is taken over; (f) read only,
skipped where it does not exist: the pilot_v2_20261005 directory (written by
the code before A1) gives a resume plan without problems and is not changed.
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import time
import unittest
import zlib
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_pgg_game import CARD_A, CARD_B, ROOT, FakeAPI, _payload  # noqa: E402
from test_pgg_guards import CostAPI  # noqa: E402
from test_pgg_resume import MODELS2, ResumeBase, _killer, _rows, _tree  # noqa: E402
from test_pgg_deadline import HangAPI, _until  # noqa: E402

import llm_client  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Engine, GameParams, RunLocked, RunStopped  # noqa: E402

ONE = {"m1": "v/m1"}


def _history_reply(kwargs, content):
    """content_fn: a contribution that depends on the whole prompt (history included)."""
    kind, agent, rnd, _ = FakeAPI.parse(kwargs)
    if kind != "contribute":
        return content
    user = kwargs["messages"][-1]["content"]
    return _payload({"contribution": zlib.crc32(user.encode()) % 21, "rationale": "r"})


def _prompts(calls) -> dict:
    """(step, agent, round) -> messages of the LAST call for that decision."""
    out = {}
    for c in calls:
        kind, agent, rnd, others = FakeAPI.parse(c)
        out[(kind, agent, rnd, others)] = c["messages"]
    return out


def _decision_keys(calls) -> list:
    return [FakeAPI.parse(c) for c in calls]


def _comparable(rows) -> dict:
    """Rows by decision, without the fields that differ between runs (ts, segment)."""
    return {(r["unit"], r["step"], r["round"], r["agent_id"], r.get("others_mean")):
            {k: v for k, v in r.items() if k not in ("ts", "segment", "elapsed_s")} for r in rows}


def _raw(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


class RoundBase(ResumeBase):
    def gcfg(self, runs, **kw):
        """1 model, 1 card, one group game of 4 rounds (16 calls under N, 32 under P)."""
        base = dict(run="eq", runs_dir=runs, cards=[CARD_A], models=dict(ONE),
                    arms=("group",), params=GameParams(rounds=4), groups_per_cell=1,
                    budget_usd=1.0, invalid_rate_cap=None)
        base.update(kw)
        return self.cfg(results_dir=None, **base)

    def dirs(self, *names):
        out = []
        for name in names:
            d = self.tmp / name
            d.mkdir()
            out.append(d)
        return out

    def uninterrupted(self, runs, **kw):
        api = CostAPI(content_fn=_history_reply)
        self.use(api)
        Engine(self.gcfg(runs, **kw)).run()
        return api, _rows(runs / "eq" / "eq.jsonl")

    def cut_and_resume(self, runs, at, **kw):
        """Segment 0 cut off by SIGTERM at the at-th call, then resumed to the end."""
        api0 = CostAPI()
        kill = _killer(api0, at)
        api0.content_fn = lambda k, c: kill(k, _history_reply(k, c))
        self.use(api0)
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            Engine(self.gcfg(runs, **kw)).run()
        api1 = CostAPI(content_fn=_history_reply)
        self.use(api1)
        engine = Engine(self.gcfg(runs, **kw))
        engine.run(resume=True)
        return engine, api0, api1


# --------------------------------------------------------------------------
# (a) cut off in round k and resumed == uninterrupted
# --------------------------------------------------------------------------

class CutResumeEqualsUninterrupted(RoundBase):
    """The same mock answers (a function of the prompt) in both runs: equal prompts
    can only come from an equal history, equal rows only from equal prompts."""

    def check(self, condition, at, n_calls, cut_round, n_discarded):
        a, b = self.dirs(f"A{condition}{at}", f"B{condition}{at}")
        api_a, rows_a = self.uninterrupted(a, conditions=(condition,))
        self.assertEqual(len(api_a.calls), n_calls)
        engine, api0, api1 = self.cut_and_resume(b, at, conditions=(condition,))

        # prompts: the last call per decision equals the uninterrupted run's call
        both = api0.calls + api1.calls
        self.assertEqual(_prompts(both), _prompts(api_a.calls))
        # decisions asked twice: only those of the cut round
        keys = _decision_keys(both)
        twice = {k for k in keys if keys.count(k) > 1}
        self.assertTrue(twice and {k[2] for k in twice} == {cut_round}, twice)
        # segment 1 starts at the cut round: earlier rounds are not asked again
        self.assertEqual(min(k[2] for k in _decision_keys(api1.calls)), cut_round)

        # rows: the valid rows equal the uninterrupted run's rows (seeds included)
        valid = engine.valid_rows()
        self.assertEqual(len(valid), len(rows_a))
        self.assertEqual(_comparable(valid), _comparable(rows_a))
        summary = json.loads((b / "eq" / "eq_summary.json").read_text())
        self.assertEqual(summary["units"]["n_complete"], 1)
        self.assertEqual(summary["superseded_rows"], [])
        if cut_round > 1:
            self.assertEqual(summary["resume_points"], [{
                "unit": summary["unit_order"][0], "from_round": cut_round,
                "rounds_kept": cut_round - 1, "kept_from_segments": [0]}])
        else:                                     # no row yet: the unit starts again
            self.assertEqual(summary["resume_points"], [])
        self.assertEqual(summary["n_discarded"], n_discarded)
        self.assertEqual(summary["per_model"]["v/m1"]["n_discarded"], n_discarded)

    def test_condition_N(self):
        # at = killed call; 4 calls per round
        for at, cut_round, n_discarded in ((6, 2, 1), (9, 3, 0), (16, 4, 3)):
            with self.subTest(at=at):
                self.check("N", at, 16, cut_round, n_discarded)

    def test_condition_P_history_with_punishment(self):
        # 8 calls per round: 4 contribute, then 4 punish; rows only for whole rounds
        for at, cut_round, n_discarded in ((7, 1, 6), (12, 2, 3), (21, 3, 4)):
            with self.subTest(at=at):
                self.check("P", at, 32, cut_round, n_discarded)


# --------------------------------------------------------------------------
# (b) partly written rounds; rows of the code before A1
# --------------------------------------------------------------------------

class PartialRounds(RoundBase):
    def test_partly_written_round_is_superseded_and_played_again(self):
        a, b = self.dirs("A", "B")
        _, rows_a = self.uninterrupted(a)
        # segment 0 cut off at call 13 (rounds 1-3 complete); then the last two
        # rows (round 3, agents 3 and 4) are lost, as if killed while writing
        api0 = CostAPI()
        kill = _killer(api0, 13)
        api0.content_fn = lambda k, c: kill(k, _history_reply(k, c))
        self.use(api0)
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            Engine(self.gcfg(b)).run()
        results = b / "eq" / "eq.jsonl"
        lines = results.read_text().splitlines(keepends=True)
        self.assertEqual(len(lines), 12)
        results.write_text("".join(lines[:10]))
        unit = Engine(self.gcfg(b), llm=pgg_game.OfflineLLM()).unit_specs()[0].label

        plan = Engine(self.gcfg(b), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(plan.problems, [])
        self.assertEqual(plan.superseded, [{"unit": unit, "segment": 0, "rounds": [3],
                                            "n_rows": 2}])
        self.assertEqual(plan.resume_points[0]["from_round"], 3)
        self.assertEqual([c["agent_id"] for _, _, c in plan.unmarked_discarded], [3, 4])

        api1 = CostAPI(content_fn=_history_reply)
        self.use(api1)
        engine = Engine(self.gcfg(b))
        engine.run(resume=True)
        self.assertEqual(len(api1.calls), 8)                      # rounds 3 and 4 only
        self.assertEqual(_comparable(engine.valid_rows()), _comparable(rows_a))
        summary = json.loads((b / "eq" / "eq_summary.json").read_text())
        self.assertEqual(summary["superseded_rows"], plan.superseded)
        self.assertEqual(summary["n_superseded_rows"], 2)
        self.assertEqual(summary["n_discarded"], 2)
        found = [e for e in _raw(b / "eq" / "raw_calls.jsonl")
                 if e.get("event") == "pgg_discarded"]
        self.assertEqual([(e["reason"], e["segment"], e["call"]["segment"], e["call"]["round"],
                           e["call"]["agent_id"], e["discarded"]) for e in found],
                         [("found_on_resume", 1, 0, 3, 3, True),
                          ("found_on_resume", 1, 0, 3, 4, True)])

    def test_last_row_cut_in_the_middle(self):
        a, b = self.dirs("A", "B")
        _, rows_a = self.uninterrupted(a)
        api0 = CostAPI()
        kill = _killer(api0, 13)
        api0.content_fn = lambda k, c: kill(k, _history_reply(k, c))
        self.use(api0)
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            Engine(self.gcfg(b)).run()
        results = b / "eq" / "eq.jsonl"
        data = results.read_bytes()
        last_start = data.rstrip(b"\n").rfind(b"\n") + 1
        results.write_bytes(data[:last_start + 40])               # row 12 cut after 40 bytes
        plan = Engine(self.gcfg(b), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(plan.problems, [])
        self.assertEqual((plan.truncated_last_line["line"], plan.truncated_last_line["n_bytes"]),
                         (12, 40))
        self.assertEqual(plan.superseded[0]["rounds"], [3])
        self.assertEqual(plan.superseded[0]["n_rows"], 3)
        api1 = CostAPI(content_fn=_history_reply)
        self.use(api1)
        engine = Engine(self.gcfg(b))
        engine.run(resume=True)
        self.assertEqual(_comparable(engine.valid_rows()), _comparable(rows_a))
        summary = json.loads((b / "eq" / "eq_summary.json").read_text())
        self.assertEqual(summary["n_truncated_lines"], 1)
        self.assertEqual(summary["n_discarded"], 1)               # the cut row's answer
        self.assertEqual(results.read_bytes()[:last_start + 40], data[:last_start + 40])

    def test_partly_written_schedule_runs_again_whole(self):
        self.use(CostAPI())
        Engine(self.rcfg()).run()
        rows = _rows(self.results)
        iso = [i for i, r in enumerate(rows) if r["arm"] == "isolated"]
        drop = set(iso[-2:])                       # the last schedule loses 2 of its 5 rows
        unit = rows[iso[-1]]["unit"]
        self.results.write_text("".join(json.dumps(r) + "\n" for i, r in enumerate(rows)
                                        if i not in drop))
        engine, api = self.resume()
        engine.run(resume=True)
        self.assertEqual(len(api.calls), 5)
        summary = self.summary_now()
        self.assertEqual(summary["superseded_rows"], [{"unit": unit, "segment": 0, "rounds": None,
                                                       "n_rows": 3}])
        self.assertEqual(summary["resume_points"], [{"unit": unit, "from_round": None,
                                                     "rounds_kept": 0, "kept_from_segments": []}])
        self.assertEqual(summary["n_discarded"], 2)
        self.assertEqual(summary["units"]["n_complete"], 8)
        self.assertEqual(len(engine.valid_rows()), 52)

    def test_rows_of_the_code_before_A1_rerun_from_round_1(self):
        """pilot_v2_20261005: a partial unit was run again from round 1 in a later segment."""
        first, _ = self.interrupted_run()            # unit 2: round 1 in segment 0
        u2 = first.unit_specs()[2].label
        old = [r for r in _rows(self.results) if r["unit"] == u2]
        rerun = [{**r, "segment": 1} for r in old] + [{**r, "segment": 1, "round": 2} for r in old]
        with open(self.results, "a") as f:
            f.write("".join(json.dumps(r) + "\n" for r in rerun))
        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(plan.problems, [])
        self.assertEqual(plan.complete[u2], 1)
        self.assertEqual(plan.superseded, [{"unit": u2, "segment": 0, "rounds": [1],
                                            "n_rows": 4}])
        self.assertEqual(plan.segment, 2)
        # a complete unit with rows in a later segment does not fit
        with open(self.results, "a") as f:
            f.write(json.dumps({**old[0], "segment": 2}) + "\n")
        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertTrue(any("is complete in segment(s) [1] and has rows in segment 2" in p
                            for p in plan.problems), plan.problems)

    def test_stored_earnings_must_match_the_decisions(self):
        self.interrupted_run()                       # unit 2 keeps round 1
        rows = _rows(self.results)
        rows[-1]["payoff"] += 1
        self.results.write_text("".join(json.dumps(r) + "\n" for r in rows))
        engine, api = self.resume()
        with self.assertRaisesRegex(ValueError, "stored earnings differ"):
            engine.run(resume=True)
        self.assertEqual(api.calls, [])

    def test_history_must_start_at_round_1(self):
        engine = Engine(self.rcfg(), llm=pgg_game.OfflineLLM())
        rec = pgg_game.RoundRecord(2, [1, 2, 3, 4], [0.0] * 4)
        with self.assertRaisesRegex(ValueError, "not rounds 1..1"):
            engine.play_group("m1", [CARD_A] * 4, "N", 0, history=[rec])


# --------------------------------------------------------------------------
# (c) discarded responses
# --------------------------------------------------------------------------

class Discarded(RoundBase):
    def test_answer_of_a_given_up_round_is_marked_live(self):
        first, _ = self.interrupted_run(cost=0.01)
        u2 = first.unit_specs()[2]
        events = self.raw_events("pgg_discarded")
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual((e["discarded"], e["reason"], e["session_id"], e["segment"]),
                         (True, "round_not_completed", u2.session_id, 0))
        self.assertEqual(e["call"], {"segment": 0, "step": "contribute", "round": 2,
                                     "agent_id": 1, "others_mean": None})
        summary = self.summary_now()
        slug = MODELS2[u2.model_key]
        self.assertEqual(summary["per_model"][slug]["n_discarded"], 1)
        self.assertEqual(summary["segments"][-1]["n_discarded"], 1)
        # every raw-log record of a decision carries its "call"
        success = [r for r in _raw(self.raw) if "response_parsed" in r and "event" not in r]
        self.assertEqual(len(success), 21)
        self.assertTrue(all(r["call"]["segment"] == 0 for r in success))
        # the discarded response stays in the cost: 21 responses x 0.01
        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertAlmostEqual(plan.prior_cost_usd, 0.21, places=9)
        self.assertEqual(plan.unmarked_discarded, [])
        engine, _ = self.resume(cost=0.01)
        engine.run(resume=True)
        summary = self.summary_now()
        self.assertEqual(summary["n_discarded"], 1)
        self.assertEqual(summary["per_model"][slug]["n_discarded"], 1)
        self.assertEqual([s["n_discarded"] for s in summary["segments"]], [1, 0])
        self.assertEqual(len(self.raw_events("pgg_discarded")), 1)    # not marked twice

    def test_killed_process_left_no_mark_found_on_resume(self):
        self.interrupted_run()
        kept = [r for r in _raw(self.raw) if r.get("event") != "pgg_discarded"]
        self.raw.write_text("".join(json.dumps(r) + "\n" for r in kept))
        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(len(plan.unmarked_discarded), 1)
        engine, _ = self.resume()
        engine.run(resume=True)
        events = self.raw_events("pgg_discarded")
        self.assertEqual([(e["reason"], e["segment"], e["call"]["segment"]) for e in events],
                         [("found_on_resume", 1, 0)])
        summary = self.summary_now()
        self.assertEqual(summary["n_discarded"], 1)
        self.assertEqual(self.raw_events("pgg_run_resume")[0]["n_discarded_found"], 1)

    def test_raw_log_of_the_code_before_A1_is_matched_by_prompt(self):
        self.interrupted_run()
        old = []
        for r in _raw(self.raw):
            if r.get("event") == "pgg_discarded":
                continue
            r.pop("call", None)
            old.append(r)
        self.raw.write_text("".join(json.dumps(r) + "\n" for r in old))
        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(plan.problems, [])
        self.assertEqual(sum(s["n_discarded"] for s in plan.prior_stats.values()), 1)
        (_, _, call), = plan.unmarked_discarded
        self.assertEqual((call["step"], call["round"], call["agent_id"]), ("contribute", 2, 1))

    def test_invalid_payload_is_not_an_accepted_answer(self):
        def bad_once(kwargs, content):
            if len(api.calls) == 1:
                return _payload({"contribution": 99})
            return content
        api = CostAPI(content_fn=bad_once)
        self.use(api)
        Engine(self.rcfg()).run()
        for strip in (False, True):                 # with "call", and an older log without
            with self.subTest(older_log=strip):
                if strip:
                    recs = _raw(self.raw)
                    for r in recs:
                        r.pop("call", None)
                    self.raw.write_text("".join(json.dumps(r) + "\n" for r in recs))
                plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
                self.assertEqual(sum(s["n_invalid"] for s in plan.prior_stats.values()), 1)
                self.assertEqual(sum(s["n_discarded"] for s in plan.prior_stats.values()), 0)
                self.assertEqual(plan.unmarked_discarded, [])

    def test_answers_whose_rows_cannot_be_written_after_a_stall(self):
        api = HangAPI(12)                            # unit 1, round 1, agent 4 hangs
        self.use(api)
        self.addCleanup(_until, lambda: llm_client.abandoned_attempts_alive() == 0)
        self.addCleanup(api.release)
        engine = Engine(self.rcfg(request_deadline_s=60, stall_timeout_s=0.3))
        with self.assertRaisesRegex(RunStopped, "stalled"):
            engine.run()
        api.release()                                # the round completes, the file is closed
        engine._wait_pools()
        events = self.raw_events("pgg_discarded")
        self.assertEqual([(e["reason"], e["call"]["agent_id"]) for e in events],
                         [("row_not_written", a) for a in range(1, 5)])
        engine2, api2 = self.resume(request_deadline_s=60, stall_timeout_s=0.3)
        engine2.run(resume=True)
        summary = self.summary_now()
        self.assertEqual(summary["n_discarded"], 4)
        self.assertEqual(summary["segments"][0]["n_discarded"], 4)
        self.assertEqual(len(self.raw_events("pgg_discarded")), 4)
        self.assertEqual(summary["units"]["n_remaining"], 0)


# --------------------------------------------------------------------------
# (d) cut-off last line: any number of resumes
# --------------------------------------------------------------------------

class CutOffLastLine(RoundBase):
    HALF = b'{"run": "r1", "half a ro'

    def partial_records(self):
        path = self.run_dir / "r1.partial.jsonl"
        return _raw(path) if path.exists() else []

    def test_three_resumes_in_a_row(self):
        self.interrupted_run()
        with open(self.results, "ab") as f:
            f.write(self.HALF)
        before = self.results.read_bytes()
        counts = []
        for k in range(3):
            engine, api = self.resume()
            engine.run(resume=True)                  # the second used to be refused
            summary = self.summary_now()
            counts.append((len(api.calls), summary["files"]["results"]["lines"],
                           summary["n_truncated_lines"], len(engine.valid_rows())))
            self.assertEqual(summary["truncated_lines"][0]["line"], 21)
            self.assertEqual(summary["truncated_lines"][0]["n_bytes"], len(self.HALF))
        # 20 rows + the cut line + 32 new rows; then nothing left to do
        self.assertEqual(counts, [(32, 53, 1, 52), (0, 53, 1, 52), (0, 53, 1, 52)])
        self.assertEqual(self.results.read_bytes()[:len(before)], before)   # still in the file
        recs = self.partial_records()
        self.assertEqual(len(recs), 1)                                      # recorded once
        self.assertEqual((recs[0]["line"], recs[0]["found_in_segment"], recs[0]["text"]),
                         (21, 1, self.HALF.decode()))
        self.assertEqual([s["segment"] for s in self.summary_now()["segments"]], [0, 1, 2, 3])

    def test_two_resumes_with_work_left(self):
        self.interrupted_run()
        with open(self.results, "ab") as f:
            f.write(self.HALF)
        api = CostAPI()
        api.content_fn = _killer(api, 10)
        self.use(api)
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            Engine(self.rcfg()).run(resume=True)
        engine, api = self.resume()
        engine.run(resume=True)
        summary = self.summary_now()
        self.assertEqual(summary["units"]["n_remaining"], 0)
        self.assertEqual(len(engine.valid_rows()), 52)
        n_rows = sum(s["n_rows"] for s in summary["segments"])
        self.assertEqual(summary["files"]["results"]["lines"], n_rows + 1)    # + the cut line
        self.assertEqual(len(self.partial_records()), 1)

    def test_a_broken_line_that_was_not_recorded_is_still_refused(self):
        self.interrupted_run()
        with open(self.results, "ab") as f:
            f.write(b"not json\n")
        engine, api = self.resume()
        with self.assertRaisesRegex(ValueError, "line 21: not a JSON object"):
            engine.run(resume=True)
        self.assertEqual(api.calls, [])

    def test_a_record_does_not_cover_another_line_content(self):
        self.interrupted_run()
        with open(self.results, "ab") as f:
            f.write(self.HALF)
        engine, _ = self.resume()
        engine.run(resume=True)
        data = self.results.read_bytes()
        self.results.write_bytes(data.replace(self.HALF, self.HALF.replace(b"half", b"HALF")))
        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertTrue(any("line 21: not a JSON object" in p for p in plan.problems))

    def test_cut_off_raw_log_line_is_closed_before_the_next_segment(self):
        self.interrupted_run()
        with open(self.raw, "ab") as f:
            f.write(b'{"ts": 1, "event": "half')
        engine, _ = self.resume()
        engine.run(resume=True)
        resume = self.raw_events_tolerant("pgg_run_resume")
        self.assertEqual([(e["segment"], e["raw_log_cut_line_closed"]) for e in resume],
                         [(1, True)])
        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(plan.segment, 2)
        self.assertEqual(plan.problems, [])

    def raw_events_tolerant(self, name):
        out = []
        for line in self.raw.read_text().splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("event") == name:
                out.append(rec)
        return out


# --------------------------------------------------------------------------
# (e) run lock
# --------------------------------------------------------------------------

HOLD_LOCK = (
    "import sys, time\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "import pgg_game\n"
    "pgg_game.acquire_run_lock(Path(sys.argv[2]))\n"
    "print('locked', flush=True)\n"
    "time.sleep(60)\n")


class RunLock(RoundBase):
    def lock_path(self):
        return self.run_dir / "r1.lock"

    def hold_in_child(self):
        child = subprocess.Popen([sys.executable, "-c", HOLD_LOCK, str(ROOT), str(self.lock_path())],
                                 stdout=subprocess.PIPE, text=True)
        self.addCleanup(lambda: (child.kill(), child.wait()))
        self.assertEqual(child.stdout.readline().strip(), "locked")
        return child

    def test_lock_is_removed_after_every_kind_of_end(self):
        self.interrupted_run()                                    # signal
        self.assertFalse(self.lock_path().exists())
        engine, _ = self.resume(max_tokens=1234)                  # refused (config)
        with self.assertRaises(ValueError):
            engine.run(resume=True)
        self.assertFalse(self.lock_path().exists())
        engine, _ = self.resume()
        engine.run(resume=True)                                   # normal end
        self.assertFalse(self.lock_path().exists())
        summary = self.summary_now()
        self.assertEqual(summary["lock"]["pid"], os.getpid())
        self.assertIsNone(summary["lock"]["stale_lock"])
        self.assertEqual(summary["segments"][-1]["lock"]["path"], str(self.lock_path()))

    def test_second_engine_is_refused_while_the_first_runs(self):
        refused = []

        def second(kwargs, content):
            if len(api.calls) == 3:
                for resume in (True, False):
                    try:
                        Engine(self.rcfg()).run(resume=resume)
                    except RunLocked as e:
                        refused.append(str(e))
            return content
        api = CostAPI(content_fn=second)
        self.use(api)
        Engine(self.rcfg()).run()
        self.assertEqual(len(refused), 2, refused)
        self.assertIn(f"PID {os.getpid()}", refused[0])
        self.assertEqual(len(api.calls), 52)          # the refused engines sent nothing
        self.assertEqual(len(_rows(self.results)), 52)
        self.assertFalse(self.lock_path().exists())

    def test_live_process_refuses_then_stale_lock_is_taken_over(self):
        self.interrupted_run()
        child = self.hold_in_child()
        before = _tree(self.run_dir)
        engine, api = self.resume()
        with self.assertRaisesRegex(RunLocked, f"PID {child.pid}"):
            engine.run(resume=True)
        self.assertEqual(api.calls, [])
        self.assertEqual(_tree(self.run_dir), before)
        # the CLI says so and stops
        cards = self.tmp / "cards.json"
        cards.write_text(json.dumps([{"card_id": c.card_id, "style": c.style, "text": c.text}
                                     for c in (CARD_A, CARD_B)]))
        argv = ["--run", "r1", "--cards", str(cards), "--models", "gemini", "--rounds", "2",
                "--groups-per-cell", "1", "--isolated-reps", "1",
                "--runs-dir", str(self.tmp / "runs"), "--resume", "--dry-run"]
        with contextlib.redirect_stdout(io.StringIO()) as out:
            pgg_game.main(argv)
        self.assertIn(f"Kilit: PID {child.pid}", out.getvalue())
        self.assertIn("sahibi yaşıyor", out.getvalue())
        self.assertEqual(_tree(self.run_dir), before)

        child.kill()
        child.wait()                                  # its PID is gone: the lock is stale
        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual((plan.lock["state"], plan.lock["pid"]), ("stale", child.pid))
        engine, api = self.resume()
        engine.run(resume=True)
        self.assertEqual(len(api.calls), 32)
        summary = self.summary_now()
        self.assertEqual(summary["lock"]["stale_lock"]["pid"], child.pid)
        taken = self.raw_events("pgg_stale_lock_taken_over")
        self.assertEqual(len(taken), 1)
        self.assertEqual(taken[0]["lock"]["stale_lock"]["pid"], child.pid)
        self.assertFalse(self.lock_path().exists())

    def test_cli_run_refused_by_a_live_lock(self):
        self.interrupted_run()
        child = self.hold_in_child()
        cards = self.tmp / "cards.json"
        cards.write_text(json.dumps([{"card_id": c.card_id, "style": c.style, "text": c.text}
                                     for c in (CARD_A, CARD_B)]))
        argv = ["--run", "r1", "--cards", str(cards), "--models", "v/m1,v/m2", "--rounds", "2",
                "--groups-per-cell", "1", "--isolated-reps", "1", "--budget-usd", "1.0",
                "--invalid-rate-cap", "0.5", "--runs-dir", str(self.tmp / "runs"), "--resume"]
        before = _tree(self.run_dir)
        self.create.reset_mock()
        with mock.patch.dict(llm_client.MODELS_KNOWN, MODELS2, clear=True), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            code = pgg_game.main(argv)
        self.assertEqual(code, 1)
        self.assertIn("HATA", err.getvalue())
        self.assertIn(f"PID {child.pid}", err.getvalue())
        self.create.assert_not_called()
        self.assertEqual(_tree(self.run_dir), before)

    def test_unreadable_and_foreign_locks(self):
        self.interrupted_run()
        lock = self.lock_path()
        lock.write_text("")                           # being written by its creator
        engine, api = self.resume()
        with self.assertRaisesRegex(RunLocked, "being written"):
            engine.run(resume=True)
        old = time.time() - 60
        os.utime(lock, (old, old))                    # left behind empty: stale
        engine, api = self.resume()
        engine.run(resume=True)
        self.assertEqual(self.summary_now()["lock"]["stale_lock"]["unreadable"], True)
        lock.write_text(json.dumps({"pid": os.getpid() + 10 ** 6, "host": "other-host",
                                    "started_at": 1.0}))
        engine, api = self.resume()
        with self.assertRaisesRegex(RunLocked, "other-host"):
            engine.run(resume=True)
        self.assertEqual(api.calls, [])

    def test_dead_pid_lock_functions(self):
        path = self.tmp / "x.lock"
        proc = subprocess.Popen([sys.executable, "-c", "pass"])
        proc.wait()
        path.write_text(json.dumps({"pid": proc.pid, "host": pgg_game.socket.gethostname(),
                                    "started_at": 1.0}))
        self.assertEqual(pgg_game.read_run_lock(path)["state"], "stale")
        got = pgg_game.acquire_run_lock(path)
        self.assertEqual(got["stale_lock"]["pid"], proc.pid)
        self.assertEqual(pgg_game.read_run_lock(path)["state"], "alive")
        with self.assertRaises(RunLocked):
            pgg_game.acquire_run_lock(path)
        pgg_game.release_run_lock(got)
        self.assertIsNone(pgg_game.read_run_lock(path))


# --------------------------------------------------------------------------
# (f) the real pilot v2 directory, read only
# --------------------------------------------------------------------------

PILOT_CONFIG = ROOT / "configs" / "pilot.json"
PILOT_V2_DIR = Path(json.loads(PILOT_CONFIG.read_text(encoding="utf-8"))["runs_dir"]) \
    / "pilot_v2_20261005"


@unittest.skipUnless((PILOT_V2_DIR / "pilot_v2_20261005.jsonl").is_file(),
                     "pilot_v2_20261005 run directory not on this machine")
class PilotV2ReadOnly(unittest.TestCase):
    def dry_run(self, *extra):
        argv = ["--config", str(PILOT_CONFIG), "--run", "pilot_v2_20261005",
                "--resume", "--dry-run", *extra]
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = pgg_game.main(argv)
        return code, out.getvalue()

    def test_resume_dry_run_reads_the_old_directory_and_writes_nothing(self):
        before = _tree(PILOT_V2_DIR)
        # segment 4 ran with 300 / 900 s; configs/pilot.json leaves the new
        # defaults 900 / 1800 s: reported as a difference, the resume would stop
        code, text = self.dry_run()
        self.assertEqual(code, 1, text)
        self.assertIn("Süre sınırları: request_deadline_s=900, stall_timeout_s=1800", text)
        self.assertIn("FARKLI (segment 4'e göre): request_deadline_s 300 -> 900, "
                      "stall_timeout_s 900 -> 1800", text)
        self.assertIn("SORUN (sürdürme başlamaz):", text)
        self.assertIn("--allow-timeout-change", text)
        self.assertNotIn("Config tutarlı", text)
        # the hidden reasoning cap: 10 accepted DeepSeek answers at 11 904 tokens
        self.assertIn("max_tokens - 4096 = 11904", text)
        self.assertIn("kabul edilen kararlarda: deepseek 10, gpt 0, gemini 0", text)
        code, text = self.dry_run("--allow-timeout-change")
        self.assertEqual(code, 0, text)
        self.assertIn("--allow-timeout-change verildi", text)
        self.assertEqual(_tree(PILOT_V2_DIR), before)
        self.assertIn("Önceki segmentler: [0, 1, 2, 3, 4]", text)
        self.assertIn("tamam 72; yarım (kaldığı turdan sürer) 0", text)
        self.assertEqual(text.count("  superseded: "), 6)      # its 6 superseded_units
        self.assertIn("(segment 0, tur [1, 2, 3, 4, 5, 6, 7], 28 satır)", text)
        # 1795 accepted responses, 1772 rows
        self.assertIn("bütçede: 23 (deepseek 20, gpt 1, gemini 2)", text)
        self.assertIn("Config tutarlı", text)


if __name__ == "__main__":
    unittest.main()
