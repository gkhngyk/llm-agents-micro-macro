"""Mock tests of task #79 (EMIR 4, 4b + 4c). No network, no ../.env, no real run directory.

(a) 4b: a round cut off by SIGINT after 2 of its 4 agents were accepted is
resumed with those 2 answers reused from <run>.accepted.jsonl: only the
missing agents are called (counted on the mock), and every request of the
resumed segment is byte for byte the request of an uninterrupted run, for
abstract_v3 and story_A with rule comprehension on; the same for a cut inside
the rule-comprehension calls and inside the isolated schedule (rows written
one by one); an answer that arrives after the signal is reused too; reused
answers are not discarded; an answer asked with another prompt is not reused
("prompt_changed"); a record cut off in the accepted-answers file is skipped;
a new run never takes an existing accepted-answers file.
(b) 4c: every attempt is logged as "attempt_started" before its request is
sent, with an attempt_id that its result record carries; an attempt cut off
in flight (the process killed) is counted as orphaned, per model and step,
also from the raw log on --resume; attempt records change neither the cost
nor the budget.
(c) a run directory in the format of the code before #79 (no accepted-answers
file, no attempt events, rows without answer_segment / reused) opens with
--resume --dry-run without problems and writes nothing; it also resumes.
"""

import contextlib
import io
import json
import os
import signal
import sys
import time
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_frame_lock import _sha  # noqa: E402
from test_frames import _main  # noqa: E402
from test_minipilot import MINIPILOT_CONFIG, MINIPILOT_PROVIDERS  # noqa: E402
from test_pgg_game import _payload  # noqa: E402
from test_pgg_guards import CostAPI, GuardTestBase  # noqa: E402
from test_pgg_k3_k5 import K5Config, TwoFrameAPI, _prompt_reply, _request  # noqa: E402
from test_pgg_resume import MODELS2, ResumeBase, _killer, _rows, _tree  # noqa: E402
from test_pgg_resume_rounds import _comparable  # noqa: E402
from test_pgg_deadline import HangAPI, _until  # noqa: E402

import llm_client  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Engine, RunStopped  # noqa: E402


def _raw(path: Path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def _key(kwargs) -> tuple:
    """(session, kind, agent, round, others_mean) of a request (abstract_v3 and story_A)."""
    return (kwargs["extra_body"]["session_id"], *TwoFrameAPI.parse(kwargs))


def _signal_and_wait(api, at, engine_box, sig=signal.SIGINT):
    """content_fn: the at-th call sends `sig`, waits until the engine has seen it and
    then answers (a call in flight when the run was interrupted)."""
    def content_fn(kwargs, content):
        if len(api.calls) == at:
            os.kill(os.getpid(), sig)
            deadline = time.monotonic() + 10
            while engine_box[0]._interrupted is None and time.monotonic() < deadline:
                time.sleep(0.005)
        return content
    return content_fn


class _Killed(BaseException):
    """The process dies in the middle of a request (no result record is written)."""


# --------------------------------------------------------------------------
# (a) 4b: cut in the middle of a round / the comprehension / a schedule
# --------------------------------------------------------------------------

class MidRoundSigint(K5Config, ResumeBase):
    """1 group game of 4 rounds (4 comprehension + 16 contributions, calls 1-20), then
    1 schedule (1 comprehension + 3 values, calls 21-24); workers 1, SIGINT."""

    def run_pair(self, frame, at, in_flight=False):
        a, b = self.tmp / f"A{frame}{at}{in_flight}", self.tmp / f"B{frame}{at}{in_flight}"
        a.mkdir()
        b.mkdir()
        api_a = TwoFrameAPI(content_fn=_prompt_reply)
        self.use(api_a)
        Engine(self.kcfg(a, frame)).run()
        self.assertEqual(len(api_a.calls), 24)

        api0 = TwoFrameAPI()
        engine0 = Engine(self.kcfg(b, frame))
        kill = (_signal_and_wait(api0, at, [engine0]) if in_flight
                else _killer(api0, at, sig=signal.SIGINT))
        api0.content_fn = lambda k, c: kill(k, _prompt_reply(k, c))
        self.use(api0)
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            engine0.run()
        self.assertEqual(engine0._interrupted, "SIGINT")
        api1 = TwoFrameAPI(content_fn=_prompt_reply)
        self.use(api1)
        engine = Engine(self.kcfg(b, frame))
        engine.run(resume=True)
        summary = json.loads((b / "k5" / "k5_summary.json").read_text())
        return api_a, api0, api1, engine, summary, b

    def assert_same_requests(self, api_a, api0, api1, in_flight=False):
        """Every request sent (segment 0 and the resumed segment 1) is, byte for byte,
        a request of the uninterrupted run, and the answered ones (all but the cut-off
        call) are exactly the uninterrupted run's requests. The four rule-comprehension
        requests of a homogeneous group are the same bytes (no agent number, no seed),
        so the requests are compared as multisets."""
        want = Counter(_request(c) for c in api_a.calls)
        self.assertEqual(sum(want.values()), 24)
        self.assertLessEqual({_request(c) for c in api0.calls + api1.calls}, set(want))
        answered = api0.calls if in_flight else api0.calls[:-1]
        self.assertEqual(Counter(_request(c) for c in answered + api1.calls), want)
        # and per decision (session, kind, agent, round, others_mean) the same bytes
        by_a = {_key(c): _request(c) for c in api_a.calls}
        for c in api0.calls + api1.calls:
            self.assertEqual(_request(c), by_a[_key(c)], _key(c))

    def assert_rows_as_uninterrupted(self, engine, a_dir):
        rows_a = _rows(a_dir / "k5" / "k5.jsonl")
        valid = engine.valid_rows()
        self.assertEqual(_comparable(valid), _comparable(rows_a))
        return valid

    def test_group_round_cut_after_two_of_four_agents(self):
        # calls 9 and 10 (round 2, agents 1-2) accepted, call 11 (agent 3) cut off
        for frame in ("abstract_v3", "story_A"):
            with self.subTest(frame=frame):
                api_a, api0, api1, engine, summary, b = self.run_pair(frame, 11)
                self.assert_same_requests(api_a, api0, api1)
                # only the missing agents of round 2, then rounds 3-4 and the schedule
                asked = [TwoFrameAPI.parse(c)[:3] for c in api1.calls]
                self.assertEqual([k for k in asked if k[2] == 2],
                                 [("contribute", 3, 2), ("contribute", 4, 2)])
                self.assertEqual(len(api1.calls), 2 + 8 + 4)
                self.assertEqual(len(api0.calls) + len(api1.calls), 24 + 1)  # + the cut call
                valid = self.assert_rows_as_uninterrupted(engine, self.tmp / f"A{frame}11False")
                reused = sorted((r["round"], r["agent_id"], r["answer_segment"], r["segment"])
                                for r in valid if r["reused"])
                self.assertEqual(reused, [(2, 1, 0, 1), (2, 2, 0, 1)])
                self.assertEqual((summary["n_answers_reused"], summary["n_discarded"]), (2, 0))
                self.assertEqual(summary["accepted_answers"]["n_pending"], 0)
                self.assertEqual(summary["superseded_rows"], [])

    def test_comprehension_cut_after_two_of_four_agents(self):
        # rule-comprehension rows are written one by one: agents 1-2 are on disk
        # when call 3 (agent 3) is cut off; segment 1 asks agents 3-4 only
        for frame in ("abstract_v3", "story_A"):
            with self.subTest(frame=frame):
                api_a, api0, api1, engine, summary, b = self.run_pair(frame, 3)
                self.assert_same_requests(api_a, api0, api1)
                comp1 = [c for c in api1.calls if TwoFrameAPI.parse(c)[0] == "comprehension"
                         and "group" in c["extra_body"]["session_id"]]
                self.assertEqual(len(comp1), 2)
                self.assertEqual(len(api1.calls), 2 + 16 + 4)
                valid = self.assert_rows_as_uninterrupted(engine, self.tmp / f"A{frame}3False")
                comp = sorted((r["agent_id"], r["segment"], r["reused"]) for r in valid
                              if r["step"] == "comprehension" and r["arm"] == "group")
                self.assertEqual(comp, [(1, 0, False), (2, 0, False), (3, 1, False),
                                        (4, 1, False)])
                self.assertEqual(summary["superseded_rows"], [])
                self.assertEqual(summary["n_discarded"], 0)
                # round 1 is accepted with rows of two segments
                self.assertEqual(summary["resume_points"][0]["from_round"], 1)

    def test_isolated_cut_after_one_value(self):
        # call 21 = the schedule's comprehension, 22 = value 0, 23 (value 10) cut off
        for frame in ("abstract_v3", "story_A"):
            with self.subTest(frame=frame):
                api_a, api0, api1, engine, summary, b = self.run_pair(frame, 23)
                self.assert_same_requests(api_a, api0, api1)
                self.assertEqual([TwoFrameAPI.parse(c)[3] for c in api1.calls], [10, 20])
                valid = self.assert_rows_as_uninterrupted(engine, self.tmp / f"A{frame}23False")
                iso = sorted((r["step"], -1 if r.get("others_mean") is None else r["others_mean"],
                              r["segment"]) for r in valid if r["arm"] == "isolated")
                self.assertEqual(iso, [("comprehension", -1, 0), ("isolated", 0, 0),
                                       ("isolated", 10, 1), ("isolated", 20, 1)])
                self.assertEqual(summary["superseded_rows"], [])
                self.assertEqual(summary["n_discarded"], 0)

    def test_answer_arriving_after_the_signal_is_reused(self):
        # call 11 (round 2, agent 3) is in flight when SIGINT comes and answers
        # after it: journaled, reused; nothing is asked twice
        for frame in ("abstract_v3", "story_A"):
            with self.subTest(frame=frame):
                api_a, api0, api1, engine, summary, b = self.run_pair(frame, 11, in_flight=True)
                self.assert_same_requests(api_a, api0, api1, in_flight=True)
                self.assertEqual(len(api0.calls), 11)
                self.assertEqual([TwoFrameAPI.parse(c)[:3] for c in api1.calls][:1],
                                 [("contribute", 4, 2)])
                self.assertEqual(len(api0.calls) + len(api1.calls), 24)
                self.assert_rows_as_uninterrupted(engine, self.tmp / f"A{frame}11True")
                self.assertEqual((summary["n_answers_reused"], summary["n_discarded"]), (3, 0))
                raw = _raw(b / "k5" / "raw_calls.jsonl")
                self.assertEqual([e for e in raw if e.get("event") == "pgg_discarded"], [])

    def test_resume_plan_lists_the_answers_to_reuse(self):
        api0 = TwoFrameAPI()
        api0.content_fn = _killer(api0, 11, sig=signal.SIGINT)
        self.use(api0)
        runs = self.tmp / "P"
        runs.mkdir()
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            Engine(self.kcfg(runs, "abstract_v3")).run()
        engine = Engine(self.kcfg(runs, "abstract_v3"), llm=pgg_game.OfflineLLM())
        plan = engine.resume_plan()
        self.assertEqual(plan.problems, [])
        unit = engine.unit_specs()[0].label
        self.assertEqual(sorted(plan.reuse[unit]),
                         [("contribute", 2, 1, None), ("contribute", 2, 2, None)])
        self.assertEqual(plan.unmarked_discarded, [])
        self.assertEqual(plan.journal["n_records"], 4 + 4 + 2)
        self.assertEqual((plan.journal["n_used"], plan.journal["n_reusable"]), (8, 2))
        text = pgg_game.resume_report(engine, plan)
        self.assertIn("çağrısız yeniden kullanılacak 2", text)
        self.assertIn("contribute tur 2 ajan 1 (segment 0)", text)


# --------------------------------------------------------------------------
# (a) 4b: discards, prompt check, cut-off records, new runs
# --------------------------------------------------------------------------

class ReuseGuards(ResumeBase):
    def journal(self):
        return self.run_dir / "r1.accepted.jsonl"

    def test_answer_with_another_prompt_is_discarded_and_asked(self):
        self.interrupted_run()                   # unit 2: round 2 agent 1 accepted
        recs = _raw(self.journal())
        recs[-1]["request_sha256"] = "0" * 64     # task #90 (prompt_sha256 before)
        self.journal().write_text("".join(json.dumps(r) + "\n" for r in recs))
        engine, api = self.resume()
        engine.run(resume=True)
        self.assertEqual(len(api.calls), 32)
        events = self.raw_events("pgg_discarded")
        self.assertEqual([(e["reason"], e["call"]["round"], e["call"]["agent_id"])
                          for e in events], [("prompt_changed", 2, 1)])
        summary = self.summary_now()
        self.assertEqual((summary["n_discarded"], summary["n_answers_reused"]), (1, 0))
        # the next plan counts it with segment 0 (from the raw log)
        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(plan.segments[0]["n_discarded"], 1)
        self.assertEqual(plan.journal["n_unused"], 1)

    def test_cut_off_record_is_skipped_and_closed(self):
        self.interrupted_run()
        with open(self.journal(), "ab") as f:
            f.write(b'{"run": "r1", "half a rec')
        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(plan.problems, [])
        self.assertEqual((plan.journal["n_cut_lines"], plan.journal["n_reusable"]), (1, 1))
        engine, api = self.resume()
        engine.run(resume=True)
        self.assertEqual(len(api.calls), 31)
        self.assertEqual([e["accepted_answers_cut_line_closed"]
                          for e in self.raw_events("pgg_run_resume")], [True])
        self.assertEqual(self.summary_now()["accepted_answers"]["n_cut_lines"], 1)

    def test_new_run_refuses_an_existing_accepted_answers_file(self):
        self.run_dir.mkdir(parents=True)
        self.journal().write_text("")
        engine, api = self.resume()
        with self.assertRaisesRegex(ValueError, "accepted answers of an earlier run"):
            engine.run()
        self.assertEqual(api.calls, [])
        self.assertFalse(self.results.exists())

    def test_every_accepted_answer_is_journaled_before_its_row(self):
        seen = []

        def check(kwargs, content):
            # when a call is sent, every row on disk has its answer journaled
            rows = _rows(self.results) if self.results.exists() else []
            calls = {(r["session_id"], tuple(r["key"])) for r in _raw(self.journal())} \
                if self.journal().exists() else set()
            seen.append(all((r["session_id"], (r["step"], r["round"], r["agent_id"],
                                               r.get("others_mean"))) in calls for r in rows))
            return content
        api = CostAPI(content_fn=check)
        self.use(api)
        Engine(self.rcfg()).run()
        self.assertEqual(len(seen), 52)
        self.assertTrue(all(seen))
        recs = _raw(self.journal())
        self.assertEqual(len(recs), 52)
        self.assertEqual({r["segment"] for r in recs}, {0})
        self.assertEqual(self.summary_now()["files"]["accepted_answers"]["lines"], 52)
        self.assertEqual(self.summary_now()["accepted_answers"]["n_used"], 52)


# --------------------------------------------------------------------------
# (b) 4c: attempt_started
# --------------------------------------------------------------------------

class AttemptStarted(ResumeBase):
    FIELDS = {"ts", "event", "model", "session_id", "run", "segment", "unit", "step", "round",
              "agent_id", "others_mean", "request", "attempt", "attempt_seq", "attempt_id",
              "call", "request_sha256"}

    def test_logged_before_the_request_and_matched_by_its_result(self):
        last = []

        def before_send(kwargs, content):
            # inside the request: the raw log's last record is this attempt's start
            last.append(_raw(self.raw)[-1])
            return content
        self.use(CostAPI(content_fn=before_send))
        engine = Engine(self.rcfg())
        engine.run()
        self.assertEqual(len(last), 52)
        self.assertTrue(all(r["event"] == "attempt_started" for r in last))
        raw = _raw(self.raw)
        started = [r for r in raw if r.get("event") == "attempt_started"]
        self.assertEqual(len(started), 52)
        self.assertTrue(all(set(r) == self.FIELDS for r in started), set(started[0]))
        results = {r["attempt_id"]: r for r in raw if "event" not in r and "attempt_id" in r}
        self.assertEqual(set(results), {r["attempt_id"] for r in started})
        specs = {s.session_id: s.label for s in engine.unit_specs()}
        for r in started:
            res = results[r["attempt_id"]]
            self.assertLess(raw.index(r), raw.index(res))
            self.assertEqual((r["session_id"], r["call"], r["attempt"]),
                             (res["session_id"], res["call"], res["attempt"]))
            self.assertEqual(r["unit"], specs[r["session_id"]])
            self.assertEqual((r["step"], r["round"], r["agent_id"], r["others_mean"],
                              r["segment"]), (r["call"]["step"], r["call"]["round"],
                                              r["call"]["agent_id"], r["call"]["others_mean"], 0))
            self.assertEqual((r["request"], r["attempt"], r["attempt_seq"]), (0, 0, 1))
        summary = self.summary_now()
        self.assertEqual((summary["n_attempt_started"], summary["n_attempt_finished"],
                          summary["n_attempt_orphaned"]), (52, 52, 0))
        table = summary["attempts"]["per_model_step"]
        self.assertEqual({m: {s: v["n_attempt_started"] for s, v in t.items()}
                          for m, t in table.items()},
                         {"v/m1": {"contribute": 8 + 8, "isolated": 10},
                          "v/m2": {"contribute": 8 + 8, "isolated": 10}})
        self.assertEqual(summary["attempts"]["segments_without_attempt_log"], [])

    def test_retries_and_re_requests_are_attempts_of_their_own(self):
        replies = iter([_payload({"contribution": 99}), "not json"])

        def first_two_bad(kwargs, content):
            if len(api.calls) <= 2:
                return next(replies)
            return content
        api = CostAPI(content_fn=first_two_bad)
        self.use(api)
        Engine(self.rcfg()).run()
        started = [r for r in _raw(self.raw) if r.get("event") == "attempt_started"]
        first = [r for r in started if (r["session_id"], r["call"])
                 == (started[0]["session_id"], started[0]["call"])]
        # invalid payload (request 0), then a parse failure retried (request 1, attempt 0)
        # and the valid answer (request 1, attempt 1)
        self.assertEqual([(r["request"], r["attempt"], r["attempt_seq"]) for r in first],
                         [(0, 0, 1), (1, 0, 2), (1, 1, 3)])
        summary = self.summary_now()
        self.assertEqual((summary["n_attempt_started"], summary["n_attempt_finished"]), (54, 54))

    def test_orphaned_attempt_of_a_killed_process_is_counted_on_resume(self):
        def die(kwargs, content):
            if len(api.calls) == 22:               # unit 2 (m1, card A), round 2, agent 2
                raise _Killed()
            return content
        api = CostAPI(content_fn=die)
        self.use(api)
        with self.assertRaises(_Killed):
            Engine(self.rcfg()).run()
        raw = _raw(self.raw)
        started = [r for r in raw if r.get("event") == "attempt_started"]
        finished = {r["attempt_id"] for r in raw if "event" not in r and "attempt_id" in r}
        orphans = [r for r in started if r["attempt_id"] not in finished]
        self.assertEqual([(r["step"], r["round"], r["agent_id"]) for r in orphans],
                         [("contribute", 2, 2)])
        first = self.summary_now()
        self.assertEqual(first["n_attempt_orphaned"], 1)          # in flight at the summary
        slug = orphans[0]["model"]
        # the mock exception ends only its unit; the queued units go on (a real kill
        # would stop them too), so what segment 1 asks is counted from the journal
        n_journal = len(_raw(self.run_dir / "r1.accepted.jsonl"))

        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(plan.problems, [])
        self.assertEqual(plan.segments[0]["n_attempt_orphaned"], 1)
        self.assertEqual(plan.segments[0]["attempts_logged"], True)
        with contextlib.redirect_stdout(io.StringIO()):
            text = pgg_game.resume_report(Engine(self.rcfg(), llm=pgg_game.OfflineLLM()), plan)
        self.assertIn("önceki segmentlerde: 1", text)

        engine, api2 = self.resume()
        engine.run(resume=True)
        self.assertEqual(len(api2.calls), 52 - n_journal)
        summary = self.summary_now()
        self.assertEqual(summary["n_answers_reused"], 1)     # agent 1 of round 2
        self.assertEqual([s["n_attempt_orphaned"] for s in summary["segments"]], [1, 0])
        self.assertEqual(summary["attempts"]["n_attempt_orphaned_earlier_segments"], 1)
        self.assertEqual(summary["n_attempt_orphaned"], 1)
        self.assertEqual(summary["attempts"]["per_model_step"][slug]["contribute"]
                         ["n_attempt_orphaned"], 1)
        self.assertEqual(summary["per_model"][slug]["n_attempt_started"]
                         - summary["per_model"][slug]["n_attempt_finished"], 1)
        resume = self.raw_events("pgg_run_resume")[0]
        self.assertEqual(resume["n_attempt_orphaned_earlier_segments"], 1)
        self.assertEqual(summary["units"]["n_remaining"], 0)

    def test_deadline_record_and_late_response_carry_the_attempt_id(self):
        api = HangAPI(3)
        self.use(api)
        self.addCleanup(_until, lambda: llm_client.abandoned_attempts_alive() == 0)
        self.addCleanup(api.release)
        Engine(self.rcfg(request_deadline_s=0.2, stall_timeout_s=30)).run()
        api.release()
        self.assertTrue(_until(lambda: llm_client.abandoned_attempts_alive() == 0))
        raw = _raw(self.raw)
        deadline = [r for r in raw if r.get("error_subkind") == "deadline"]
        late = [r for r in raw if r.get("event") == "late_response"]
        self.assertEqual(len(deadline), 1)
        self.assertEqual(len(late), 1)
        self.assertEqual(late[0]["attempt_id"], deadline[0]["attempt_id"])
        started = [r for r in raw if r.get("event") == "attempt_started"
                   and (r["session_id"], r["call"])
                   == (deadline[0]["session_id"], deadline[0]["call"])]
        self.assertEqual([(r["attempt"], r["attempt_seq"]) for r in started], [(0, 1), (1, 2)])
        self.assertEqual(started[0]["attempt_id"], deadline[0]["attempt_id"])
        summary = self.summary_now()
        self.assertEqual((summary["n_attempt_started"], summary["n_attempt_orphaned"]), (53, 0))

    def test_cost_and_budget_are_unchanged_by_attempt_records(self):
        self.use(CostAPI(cost=0.01))
        engine = Engine(self.rcfg())
        engine.run()
        summary = self.summary_now()
        self.assertAlmostEqual(summary["total_cost_usd"], 0.52, places=9)
        self.assertEqual(summary["n_attempt_started"], 52)
        specs = engine.unit_specs()
        offline = Engine(self.rcfg(), llm=pgg_game.OfflineLLM())
        with_attempts = offline._scan_raw_log(self.raw, specs)["per_segment"]
        stripped = self.tmp / "stripped.jsonl"
        stripped.write_text("".join(
            json.dumps({k: v for k, v in r.items() if k != "attempt_id"}) + "\n"
            for r in _raw(self.raw) if r.get("event") != "attempt_started"))
        without = offline._scan_raw_log(stripped, specs)["per_segment"]
        for k in MODELS2:
            for field in ("cost_usd", "n_responses", "n_accepted", "n_invalid",
                          "n_parse_fail", "n_cost_estimated", "deadline_cost_usd"):
                self.assertEqual(with_attempts[0][k][field], without[0][k][field], field)
        self.assertEqual(sum(with_attempts[0][k]["n_attempt_started"] for k in MODELS2), 52)
        self.assertEqual(sum(without[0][k]["n_attempt_started"] for k in MODELS2), 0)

    def test_budget_stop_starts_no_attempt(self):
        # 0.01 per response, cap 0.035: the 5th call is refused before it is started
        self.use(CostAPI(cost=0.01))
        with self.assertRaisesRegex(RunStopped, "budget"):
            Engine(self.rcfg(budget_usd=0.035)).run()
        summary = self.summary_now()
        self.assertAlmostEqual(summary["total_cost_usd"], 0.04, places=9)
        self.assertEqual(sum(s["n_responses"] for s in summary["per_model"].values()), 4)
        self.assertEqual((summary["n_attempt_started"], summary["n_attempt_orphaned"]), (4, 0))


# --------------------------------------------------------------------------
# (c) a run directory of the code before #79 (mini-pilot layout)
# --------------------------------------------------------------------------

# fields and events that the code before #79 did not write
NEW_KEYS = {"answer_segment", "reused", "attempt_id", "n_answers_reused", "n_attempt_started",
            "n_attempt_finished", "n_attempt_orphaned", "attempt_started_by_step",
            "attempt_finished_by_step", "attempts", "attempts_logged", "accepted_answers",
            "n_answers_reusable", "n_rows_kept_pending", "n_attempt_orphaned_earlier_segments",
            "accepted_answers_cut_line_closed"}
NEW_EVENTS = {"attempt_started", "pgg_answer_reused"}


def _old(value):
    """value without the fields of NEW_KEYS, at any depth."""
    if isinstance(value, dict):
        return {k: _old(v) for k, v in value.items() if k not in NEW_KEYS}
    if isinstance(value, list):
        return [_old(v) for v in value]
    return value


class OldFormatDirectory(GuardTestBase):
    RUN = "fx_old"

    def config(self) -> Path:
        cards = self.tmp / "cards.json"
        cards.write_text(json.dumps([
            {"card_id": "x_minimal", "style": "minimal", "city": "X", "text": "Fake card X."}]),
            encoding="utf-8")
        (self.tmp / "runs").mkdir(exist_ok=True)
        raw = json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8"))
        raw.update({
            "prereg_approved": True, "run": self.RUN, "cards": str(cards), "cities": ["X"],
            "cards_sha256": _sha(cards), "groups_per_cell": 1, "isolated_reps": 1,
            "budget_usd": 1.0, "invalid_rate_cap": 0.5, "workers": 1, "parallel_units": 1,
            "runs_dir": str(self.tmp / "runs"), "params": {"rounds": 2}, "isolated_round_no": 2,
        })
        path = self.tmp / "mp.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        return path

    def setUp(self):
        super().setUp()
        self.names = {model: name for _, model, name, _ in MINIPILOT_PROVIDERS.values()}
        self.run_dir = self.tmp / "runs" / self.RUN

    def old_api(self):
        return TwoFrameAPI(provider_fn=lambda k: self.names[k["model"]])   # story frames too

    def to_old_format(self):
        """Rewrite the run directory as the code before #79 left it."""
        (self.run_dir / f"{self.RUN}.accepted.jsonl").unlink()
        for path in self.run_dir.glob("*.jsonl"):
            recs = [json.loads(x) for x in path.read_text().splitlines()]
            path.write_text("".join(json.dumps(_old(r)) + "\n" for r in recs
                                    if r.get("event") not in NEW_EVENTS))
        for path in self.run_dir.glob(f"{self.RUN}_summary*.json"):
            path.write_text(json.dumps(_old(json.loads(path.read_text())), indent=2))

    def test_resume_dry_run_opens_it_read_only_and_it_resumes(self):
        api = self.old_api()
        api.content_fn = _killer(api, 30, sig=signal.SIGINT)      # in the middle of a round
        self.use(api)
        code, _, err = _main("--config", str(self.config()))
        self.assertEqual(code, 1, err)
        self.assertIn("interrupted", err)
        self.to_old_format()
        self.assertFalse(any("answer_segment" in x or "attempt_started" in x
                             for p in self.run_dir.glob("*.jsonl")
                             for x in p.read_text().splitlines()))
        before = _tree(self.tmp / "runs")
        self.create.reset_mock()
        code, out, err = _main("--config", str(self.config()), "--resume", "--dry-run")
        self.assertEqual(code, 0, out + err)
        self.assertIn("Config tutarlı; sorun yok.", out)
        self.assertIn("dosya yok (#79 öncesi kod ya da hiç cevap yok)", out)
        self.assertIn("deneme logu olmayan segmentler (#79 öncesi kod): [0]", out)
        self.assertNotIn("SORUN", out)
        self.create.assert_not_called()
        self.assertEqual(_tree(self.tmp / "runs"), before)        # nothing written

        # and the new code resumes it to the end (the cut round is asked again
        # whole: there are no accepted answers to reuse)
        self.use(self.old_api())
        code, out, err = _main("--config", str(self.config()), "--resume")
        self.assertEqual(code, 0, err)
        summary = json.loads((self.run_dir / f"{self.RUN}_summary.json").read_text())
        units = summary["units"]
        self.assertEqual((units["n_units"], units["n_complete"], units["n_partial"],
                          units["n_remaining"]), (10, 10, 0, 0))
        self.assertEqual(summary["n_answers_reused"], 0)
        self.assertEqual(summary["attempts"]["segments_without_attempt_log"], [0])
        # 5 (model, frame) pairs x (4 + 8 group rows, 1 + 5 isolated rows) = 90
        lines = summary["files"]["results"]["lines"]
        self.assertEqual(lines - summary["n_superseded_rows"], 90)


if __name__ == "__main__":
    unittest.main()
