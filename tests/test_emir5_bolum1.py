"""Mock tests of EMIR 5 Bölüm 1 (task #90). No network, no ../.env, no real run directory.

M1 reuse safety: request_sha256 is the sha256 of the canonical JSON of the
request body sent (everything but session_id: model, messages with the answer
instruction, max_tokens, response_format, provider routing); it is in every
raw-log record of a call, in every row and in <run>.accepted.jsonl, and the
reuse check compares it (records of the code before #90: prompt_sha256). An
answer of a segment that ran another git_commit stops the resume before any
call and any write (or, with --discard-reuse-on-code-change, is discarded
"code_changed" and asked again). A reused answer passes is_valid again
("reuse_invalid", n_reuse_invalid).
M2: cut / reuse / byte-identical requests with workers=4 and parallel_units=3,
for abstract_v3 and story_A.
M3: the lock is released when the last status.json cannot be written, and the
run's own error is not hidden by it.
M4: answer_format schema_text / example_object / json_schema_strict; in A and B
"rationale" is required in the prompt and in what is checked / enforced.
"""

import contextlib
import hashlib
import io
import json
import os
import shutil
import signal
import sys
import threading
import time
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_answer_format import EXAMPLE_INTRO  # noqa: E402
from test_pgg_a4_a5 import CLEAN  # noqa: E402
from test_pgg_game import CARD_A, CARD_B, FakeAPI, _payload  # noqa: E402
from test_pgg_guards import CostAPI  # noqa: E402
from test_pgg_k3_k5 import K5Config, TwoFrameAPI, _prompt_reply, _request  # noqa: E402
from test_pgg_resume import GEMINI, ResumeBase, _rows, _tree  # noqa: E402
from test_pgg_resume_rounds import _comparable  # noqa: E402

import llm_client  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Engine, GameParams, RunStopped  # noqa: E402

PINNED = {"m1": {"slug": "prov-a/fp8", "name": "Prov A", "quantizations": ["fp8"]}}


def _raw(path: Path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def _sent_sha(kwargs) -> str:
    """sha256 of the JSON body the OpenAI client sends for these create() kwargs
    (extra_body merged into the body), without session_id; headers and the
    client timeout are not part of the body."""
    body = {k: kwargs[k] for k in ("model", "messages", "max_tokens", "temperature",
                                   "response_format") if k in kwargs}
    body.update(kwargs.get("extra_body") or {})
    body.pop("session_id", None)
    text = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _with_commit(commit):
    return mock.patch.object(pgg_game, "code_version",
                             return_value={**CLEAN, "git_commit": commit})


# --------------------------------------------------------------------------
# M1 request_sha256
# --------------------------------------------------------------------------

class RequestHash(ResumeBase):
    def journal(self):
        return self.run_dir / "r1.accepted.jsonl"

    def test_canonical_json_without_the_session_id(self):
        self.assertEqual(
            llm_client.request_sha256({"b": 1, "a": "ç", "session_id": "s"}),
            hashlib.sha256('{"a":"ç","b":1}'.encode("utf-8")).hexdigest())

    def test_records_rows_and_journal_carry_the_hash_of_what_was_sent(self):
        # workers 1, parallel_units 1: the i-th attempt_started is the i-th request
        api = CostAPI(provider_fn=lambda k: "Prov A" if k["model"] == "v/m1" else "Prov B")
        self.use(api)
        Engine(self.rcfg(providers=PINNED | {"m2": {"slug": "prov-b", "name": "Prov B"}})).run()
        self.assertEqual(len(api.calls), 52)
        self.assertEqual({"quantizations" in k["extra_body"]["provider"] for k in api.calls},
                         {True, False})
        raw = _raw(self.raw)
        started = [r for r in raw if r.get("event") == "attempt_started"]
        self.assertEqual([r["request_sha256"] for r in started], [_sent_sha(k) for k in api.calls])
        by_attempt = {r["attempt_id"]: r for r in raw if "event" not in r and "attempt_id" in r}
        for r in started:
            self.assertEqual(by_attempt[r["attempt_id"]]["request_sha256"], r["request_sha256"])
        success = Counter(r["request_sha256"] for r in raw
                          if "response_parsed" in r and "event" not in r)
        rows = _rows(self.results)
        self.assertEqual(Counter(r["request_sha256"] for r in rows), success)
        journal = _raw(self.journal())
        self.assertTrue(all("request_sha256" in r and "prompt_sha256" not in r for r in journal))
        self.assertEqual(Counter(r["request_sha256"] for r in journal), success)

    def test_hash_covers_the_whole_request_but_the_session_id(self):
        schema = {"type": "object", "required": ["contribution"],
                  "properties": {"contribution": {"type": "integer", "minimum": 0, "maximum": 20},
                                 "rationale": {"type": "string"}}}
        prov = pgg_game.provider_routing(PINNED["m1"])
        base = dict(model="v/m", messages=[{"role": "system", "content": "s"},
                                           {"role": "user", "content": "u"}],
                    schema=schema, session_id="s1", max_tokens=16000, provider=prov)

        def h(**kw):
            return llm_client.request_sha256(llm_client.request_body(**{**base, **kw}))
        ref = h()
        self.assertEqual(h(session_id="another session"), ref)
        self.assertEqual(h(answer_format="schema_text"), ref)
        variants = {
            "model": h(model="v/other"),
            "message": h(messages=[{"role": "system", "content": "s"},
                                   {"role": "user", "content": "u2"}]),
            "schema": h(schema={**schema, "required": ["contribution", "rationale"]}),
            "max_tokens": h(max_tokens=8000),
            "order": h(provider={**prov, "order": ["x"]}),
            "only": h(provider={**prov, "only": ["x"]}),
            "allow_fallbacks": h(provider={**prov, "allow_fallbacks": True}),
            "require_parameters": h(provider={**prov, "require_parameters": False}),
            "quantizations": h(provider={**prov, "quantizations": ["bf16"]}),
            "no provider": h(provider=None),
            "temperature": h(temperature=0.4),
            "reasoning": h(reasoning_effort="low"),
            "example_object": h(answer_format="example_object"),
            "json_schema_strict": h(answer_format="json_schema_strict"),
        }
        self.assertEqual(len(set(variants.values()) | {ref}), len(variants) + 1, variants)

    def legacy_record(self, api, ok: bool) -> None:
        """Rewrite the reusable journal record as the code before #90 wrote it."""
        recs = _raw(self.journal())
        rec = recs[-1]                                   # unit 2, round 2, agent 1
        self.assertEqual(tuple(rec["key"][:3]), ("contribute", 2, 1))
        call = next(k for k in api.calls if k["extra_body"]["session_id"] == rec["session_id"]
                    and FakeAPI.parse(k)[:3] == ("contribute", 1, 2))
        content = call["messages"][-1]["content"]
        schema = json.loads(content.rsplit("matching this schema:\n", 1)[1])
        messages = call["messages"][:-1] + [
            {**call["messages"][-1], "content": content.split("\n\nRespond with ONLY")[0]}]
        del rec["request_sha256"]
        rec["prompt_sha256"] = (pgg_game.prompt_sha256(call["model"], messages, schema)
                                if ok else "0" * 64)
        self.journal().write_text("".join(json.dumps(r) + "\n" for r in recs))

    def test_record_of_the_code_before_90_is_compared_on_prompt_sha256(self):
        _, api0 = self.interrupted_run()
        self.legacy_record(api0, ok=True)
        engine, api = self.resume()
        engine.run(resume=True)
        self.assertEqual(len(api.calls), 31)
        [event] = self.raw_events("pgg_answer_reused")
        self.assertEqual((event["reuse_check"], event["request_sha256"]), ("prompt_sha256", None))
        self.assertEqual(self.summary_now()["n_answers_reused"], 1)

    def test_record_of_the_code_before_90_with_another_prompt_is_asked(self):
        _, api0 = self.interrupted_run()
        self.legacy_record(api0, ok=False)
        engine, api = self.resume()
        engine.run(resume=True)
        self.assertEqual(len(api.calls), 32)
        self.assertEqual([e["reason"] for e in self.raw_events("pgg_discarded")],
                         ["prompt_changed"])


# --------------------------------------------------------------------------
# M1 git_commit of the answers to reuse
# --------------------------------------------------------------------------

class CodeChangeRefusesReuse(ResumeBase):
    A, B = "a" * 40, "b" * 40

    def test_another_commit_stops_the_resume_before_any_call_or_write(self):
        with _with_commit(self.A):
            self.interrupted_run()                       # 1 answer to reuse (segment 0)
        before = _tree(self.run_dir)
        with _with_commit(self.B):
            engine, api = self.resume()
            with self.assertRaisesRegex(
                    ValueError, r"not resumed, no call made: reuse refused \(code_changed\): 1 "
                                r"accepted answer\(s\) .* segment\(s\) \[0\] with git_commit "
                                r"\{\"0\": \"a{40}\"\}, this segment runs b{40}"):
                engine.run(resume=True)
            self.assertEqual(api.calls, [])
            self.assertEqual(_tree(self.run_dir), before)       # nothing written, no lock left
            offline = Engine(self.rcfg(), llm=pgg_game.OfflineLLM())
            plan = offline.resume_plan()
            text = pgg_game.resume_report(offline, plan)
        self.assertEqual(plan.reuse_code_check, {"now": self.B, "earlier": {"0": self.A},
                                                 "refused_segments": [0], "n_answers": 1})
        self.assertIn("git_commit of the answers to reuse", plan.config_checked)
        self.assertIn("yeniden kullanım REDDEDİLİR, sürdürme başlamaz", text)
        self.assertIn("SORUN (sürdürme başlamaz)", text)

    def test_discard_option_asks_them_again(self):
        with _with_commit(self.A):
            self.interrupted_run()
        with _with_commit(self.B):
            engine, api = self.resume(discard_reuse_on_code_change=True)
            engine.run(resume=True)
        self.assertEqual(len(api.calls), 32)
        summary = self.summary_now()
        self.assertEqual((summary["n_answers_reused"], summary["n_discarded"]), (0, 1))
        self.assertEqual([(e["reason"], e["call"]["segment"])
                          for e in self.raw_events("pgg_discarded")], [("code_changed", 0)])
        resume = self.raw_events("pgg_run_resume")[0]
        self.assertTrue(resume["discard_reuse_on_code_change"])
        self.assertEqual(resume["reuse_code_check"]["refused_segments"], [0])
        self.assertEqual(summary["units"]["n_remaining"], 0)

    def test_same_commit_reuses(self):
        with _with_commit(self.A):
            self.interrupted_run()
            engine, api = self.resume()
            engine.run(resume=True)
        self.assertEqual(len(api.calls), 31)
        self.assertEqual(self.summary_now()["n_answers_reused"], 1)
        self.assertEqual(self.raw_events("pgg_run_resume")[0]["reuse_code_check"],
                         {"now": self.A, "earlier": {}, "refused_segments": [], "n_answers": 0})

    def test_another_commit_without_answers_to_reuse_resumes(self):
        with _with_commit(self.A):
            self.interrupted_run(at=21)                  # round 2 of unit 2: nothing answered
        with _with_commit(self.B):
            plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
            self.assertEqual((plan.problems, plan.reuse), ([], {}))
            engine, api = self.resume()
            engine.run(resume=True)
        summary = self.summary_now()
        self.assertEqual(summary["units"]["n_remaining"], 0)
        self.assertEqual(summary["segments"][-1]["code_change"]["differs_from_segments"], [0])

    def test_cli_reports_the_refusal(self):
        with _with_commit(self.A):
            self.interrupted_run(at=14, models=dict(GEMINI), budget_usd=None,
                                 invalid_rate_cap=None)
        cards = self.tmp / "cards.json"
        cards.write_text(json.dumps([{"card_id": c.card_id, "style": c.style, "text": c.text}
                                     for c in (CARD_A, CARD_B)]))
        argv = ["--resume", "--run", "r1", "--cards", str(cards), "--models", "gemini",
                "--runs-dir", str(self.tmp / "runs"), "--rounds", "2", "--groups-per-cell", "1",
                "--isolated-reps", "1"]
        self.use(CostAPI())
        self.create.reset_mock()
        with _with_commit(self.B), contextlib.redirect_stderr(io.StringIO()) as err, \
                contextlib.redirect_stdout(io.StringIO()):
            code = pgg_game.main(argv)
        self.assertEqual(code, 1)
        self.assertIn("HATA: run 'r1' not resumed, no call made: reuse refused (code_changed)",
                      err.getvalue())
        self.create.assert_not_called()
        with _with_commit(self.B), contextlib.redirect_stderr(io.StringIO()) as err, \
                contextlib.redirect_stdout(io.StringIO()):
            code = pgg_game.main(argv + ["--discard-reuse-on-code-change"])
        self.assertEqual(code, 0, err.getvalue())
        self.assertEqual(self.summary_now()["units"]["n_remaining"], 0)


# --------------------------------------------------------------------------
# M1 is_valid again
# --------------------------------------------------------------------------

class ReusedAnswerIsCheckedAgain(ResumeBase):
    def edit_reusable(self, fn):
        path = self.run_dir / "r1.accepted.jsonl"
        recs = _raw(path)
        fn(recs[-1]["answer"]["parsed"])
        path.write_text("".join(json.dumps(r) + "\n" for r in recs))

    def test_invalid_answer_is_discarded_counted_and_asked(self):
        self.interrupted_run()
        self.edit_reusable(lambda p: p.update(contribution=99))
        engine, api = self.resume()
        engine.run(resume=True)
        self.assertEqual(len(api.calls), 32)
        self.assertEqual([(e["reason"], e["call"]["round"], e["call"]["agent_id"])
                          for e in self.raw_events("pgg_discarded")], [("reuse_invalid", 2, 1)])
        summary = self.summary_now()
        self.assertEqual((summary["n_reuse_invalid"], summary["n_answers_reused"],
                          summary["n_discarded"]), (1, 0, 1))
        self.assertEqual(summary["segments"][-1]["n_reuse_invalid"], 1)
        row = next(r for r in engine.valid_rows() if (r["unit"], r["round"], r["agent_id"])
                   == (engine.unit_specs()[2].label, 2, 1))
        self.assertEqual((row["segment"], row["reused"]), (1, False))
        self.assertLessEqual(row["contribution"], 20)
        # counted again from the raw log by the next plan
        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual([s["n_reuse_invalid"] for s in plan.segments], [0, 1])

    def test_missing_rationale_is_reused_by_default(self):
        self.interrupted_run()
        self.edit_reusable(lambda p: p.pop("rationale"))
        engine, api = self.resume()
        engine.run(resume=True)
        self.assertEqual((len(api.calls), self.summary_now()["n_answers_reused"]), (31, 1))

    def test_missing_rationale_is_invalid_where_every_field_is_required(self):
        for fmt in pgg_game.ALL_FIELDS_REQUIRED_FORMATS:
            with self.subTest(fmt):
                self.interrupted_run(answer_format=fmt)
                self.edit_reusable(lambda p: p.pop("rationale"))
                engine, api = self.resume(answer_format=fmt)
                engine.run(resume=True)
                self.assertEqual(len(api.calls), 32)
                self.assertEqual(self.summary_now()["n_reuse_invalid"], 1)
                shutil.rmtree(self.run_dir)                      # next subtest: a new run


# --------------------------------------------------------------------------
# M2 workers=4, parallel_units=3
# --------------------------------------------------------------------------

def _key(kwargs) -> tuple:
    return (kwargs["extra_body"]["session_id"], *TwoFrameAPI.parse(kwargs))


class ParallelCutResume(K5Config, ResumeBase):
    """1 model, 2 cards, 2 groups per cell, rounds 4, comprehension on, one frame:
    4 group games (4 + 16 calls) and 2 schedules (1 + 3 calls) = 88 calls, run with
    workers=4 and parallel_units=3."""

    def pcfg(self, runs, frame):
        return self.kcfg(runs, frame, cards=[CARD_A, CARD_B], groups_per_cell=2,
                         workers=4, parallel_units=3)

    @staticmethod
    def trigger(engine_box, pred, k, answer_after):
        """content_fn: the k-th request of the first slot (session, kind, round) that pred
        accepts sends SIGINT, waits until the engine has seen it, then answers ("not
        json" unless answer_after: then retried, refused by before_call, unanswered)."""
        lock, counts, fired = threading.Lock(), Counter(), []

        def content_fn(kwargs, content):
            content = _prompt_reply(kwargs, content)
            kind, _, rnd, _ = TwoFrameAPI.parse(kwargs)
            slot = (kwargs["extra_body"]["session_id"], kind, rnd)
            with lock:
                counts[slot] += 1
                fire = not fired and pred(slot) and counts[slot] == k
                if fire:
                    fired.append(kwargs)
            if fire:
                os.kill(os.getpid(), signal.SIGINT)
                deadline = time.monotonic() + 10
                while engine_box[0]._interrupted is None and time.monotonic() < deadline:
                    threading.Event().wait(0.005)
                if not answer_after:
                    return "not json"
            return content
        return content_fn, fired

    def run_case(self, frame, pred, k, answer_after=False):
        tag = f"{frame}{k}{answer_after}{len(list(self.tmp.iterdir()))}"
        a, b = self.tmp / f"A{tag}", self.tmp / f"B{tag}"
        a.mkdir()
        b.mkdir()
        api_a = TwoFrameAPI(content_fn=_prompt_reply)
        self.use(api_a)
        Engine(self.pcfg(a, frame)).run()
        self.assertEqual(len(api_a.calls), 88)

        api0 = TwoFrameAPI()
        engine0 = Engine(self.pcfg(b, frame))
        api0.content_fn, fired = self.trigger([engine0], pred, k, answer_after)
        self.use(api0)
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            engine0.run()
        self.assertEqual(len(fired), 1)
        self.assertLess(len(api0.calls), 88)
        api1 = TwoFrameAPI(content_fn=_prompt_reply)
        self.use(api1)
        engine = Engine(self.pcfg(b, frame))
        engine.run(resume=True)
        summary = json.loads((b / "k5" / "k5_summary.json").read_text())

        # every request of both segments is, byte for byte, the uninterrupted run's
        # request for the same decision
        by_a = {_key(c): _request(c) for c in api_a.calls}
        for c in api0.calls + api1.calls:
            self.assertEqual(_request(c), by_a[_key(c)], _key(c))
        # nothing answered is asked again, nothing is missing
        answered0 = list(api0.calls)
        if not answer_after:
            answered0.remove(fired[0])
        self.assertEqual(Counter(map(_request, answered0 + api1.calls)),
                         Counter(map(_request, api_a.calls)))
        # the valid rows are the uninterrupted run's (request_sha256 included)
        valid = engine.valid_rows()
        self.assertEqual(_comparable(valid), _comparable(_rows(a / "k5" / "k5.jsonl")))
        reused = [r for r in valid if r["reused"]]
        self.assertEqual((summary["n_answers_reused"], summary["n_discarded"]), (len(reused), 0))
        self.assertEqual(summary["units"]["n_remaining"], 0)
        self.assertEqual(summary["n_reuse_invalid"], 0)
        return summary, reused, fired[0]

    def test_group_round_cut_reuses_the_other_agents(self):
        for frame in ("abstract_v3", "story_A"):
            with self.subTest(frame=frame):
                summary, reused, fired = self.run_case(
                    frame, lambda s: s[1] == "contribute" and s[2] == 2 and "group" in s[0], 4)
                session = fired["extra_body"]["session_id"]
                cut_agent = TwoFrameAPI.parse(fired)[1]
                self.assertLessEqual({(session, 2, a) for a in {1, 2, 3, 4} - {cut_agent}},
                                     {(r["session_id"], r["round"], r["agent_id"])
                                      for r in reused})
                self.assertGreaterEqual(summary["n_answers_reused"], 3)

    def test_comprehension_cut(self):
        for frame in ("abstract_v3", "story_A"):
            with self.subTest(frame=frame):
                self.run_case(frame, lambda s: s[1] == "comprehension" and "group" in s[0], 4)

    def test_isolated_cut(self):
        for frame in ("abstract_v3", "story_A"):
            with self.subTest(frame=frame):
                self.run_case(frame, lambda s: s[1] == "isolated", 2)

    def test_answer_arriving_after_the_signal(self):
        for frame in ("abstract_v3", "story_A"):
            with self.subTest(frame=frame):
                self.run_case(frame, lambda s: s[1] == "contribute" and s[2] == 2
                              and "group" in s[0], 4, answer_after=True)


# --------------------------------------------------------------------------
# M3 the lock and the run's error when the last status.json cannot be written
# --------------------------------------------------------------------------

class LockAlwaysReleased(ResumeBase):
    def failing_final_status(self):
        original = Engine._write_status

        def write(engine, record):
            if record.get("state") == "ended":
                raise OSError("disk full (test)")
            return original(engine, record)
        return mock.patch.object(Engine, "_write_status", write)

    def lock(self):
        return self.run_dir / "r1.lock"

    def test_completed_run_reports_the_status_failure_and_releases_the_lock(self):
        self.use(CostAPI())
        with self.failing_final_status(), contextlib.redirect_stderr(io.StringIO()) as err, \
                self.assertRaisesRegex(OSError, "disk full"):
            Engine(self.rcfg()).run()
        self.assertFalse(self.lock().exists())
        self.assertIn("UYARI: son status.json yazılamadı", err.getvalue())
        self.assertEqual(self.summary_now()["units"]["n_remaining"], 0)
        [event] = self.raw_events("pgg_status_write_failed")
        self.assertEqual((event["error"], event["run_error"]), ("OSError: disk full (test)", None))
        self.assertEqual(json.loads((self.run_dir / "status.json").read_text())["state"],
                         "running")                      # the last one that was written

    def test_run_error_is_not_hidden_and_the_lock_is_released(self):
        self.use(CostAPI(cost=0.01))
        with self.failing_final_status(), contextlib.redirect_stderr(io.StringIO()), \
                self.assertRaisesRegex(RunStopped, "budget") as cm:
            Engine(self.rcfg(budget_usd=0.035)).run()
        self.assertIn("could not be written: OSError: disk full (test)",
                      " ".join(cm.exception.__notes__))
        self.assertFalse(self.lock().exists())
        [event] = self.raw_events("pgg_status_write_failed")
        self.assertTrue(event["run_error"].startswith("RunStopped: run 'r1' stopped: budget"))
        # no lock left behind: a resume is not refused as locked (it stops at the budget)
        engine, _ = self.resume(cost=0.01, budget_usd=0.035)
        with self.assertRaisesRegex(RunStopped, "budget"):
            engine.run(resume=True)

    def test_signal_and_status_failure(self):
        api = CostAPI()
        from test_pgg_resume import _killer
        api.content_fn = _killer(api, 22)
        self.use(api)
        with self.failing_final_status(), contextlib.redirect_stderr(io.StringIO()), \
                self.assertRaisesRegex(RunStopped, "interrupted"):
            Engine(self.rcfg()).run()
        self.assertFalse(self.lock().exists())


# --------------------------------------------------------------------------
# M4 answer_format
# --------------------------------------------------------------------------

class AnswerFormats(ResumeBase):
    def schemas(self):
        f = pgg_game.load_frame_file("abstract_v3", None)
        p = GameParams()
        return {"contribution": pgg_game.contribution_schema(p, True, f),
                "comprehension": f.comprehension_schema(True),
                "punishment": pgg_game.punishment_schema(p, [2, 3, 4], True, f)}

    def test_instruction_texts(self):
        s = self.schemas()["contribution"]
        msgs = [{"role": "user", "content": "Q"}]
        text = {fmt: llm_client.answer_request(msgs, s, fmt)[0][-1]["content"]
                for fmt in pgg_game.ANSWER_FORMATS}
        rf = {fmt: llm_client.answer_request(msgs, s, fmt)[1] for fmt in pgg_game.ANSWER_FORMATS}
        self.assertEqual(text["schema_text"], "Q\n\nRespond with ONLY a JSON object matching this "
                         "schema:\n" + json.dumps(s, ensure_ascii=False))
        self.assertEqual(text["example_object"],
                         "Q\n\nRespond with ONLY a JSON object of this form, with your own values "
                         "in place of the <...> " + EXAMPLE_INTRO
                         + '{"contribution": <whole number from 0 to 20>, "rationale": '
                           '"<One or two sentences on why you chose this.>"}')
        strict = llm_client.strict_json_schema(s)
        self.assertEqual(strict["required"], ["contribution", "rationale"])
        self.assertEqual(text["json_schema_strict"], "Q\n\nRespond with ONLY a JSON object "
                         "matching this schema:\n" + json.dumps(strict, ensure_ascii=False))
        self.assertEqual(rf, {"schema_text": {"type": "json_object"},
                              "example_object": {"type": "json_object"},
                              "json_schema_strict": {"type": "json_schema", "json_schema": {
                                  "name": "answer", "strict": True, "schema": strict}}})
        # rationale: optional in schema_text (as before), required in A and B
        self.assertEqual(s["required"], ["contribution"])

    def test_required_fields_present(self):
        s = self.schemas()
        ok = llm_client.required_fields_present
        self.assertTrue(ok({"contribution": 3, "rationale": ""}, s["contribution"]))
        self.assertFalse(ok({"contribution": 3}, s["contribution"]))
        self.assertFalse(ok({"contribution": "3", "rationale": "r"}, s["contribution"]))
        self.assertFalse(ok({"contribution": True, "rationale": "r"}, s["contribution"]))
        self.assertTrue(ok({"q1": 28, "q2": -6, "rationale": "r"}, s["comprehension"]))
        self.assertTrue(ok({"punishments": {"2": 0, "3": 1, "4": 0}, "rationale": "r"},
                           s["punishment"]))
        self.assertFalse(ok({"punishments": {"2": 0, "3": 1}, "rationale": "r"}, s["punishment"]))

    def test_answer_without_rationale(self):
        """Re-requested (n_invalid) in A and B; accepted in schema_text, as before."""
        for fmt, n_invalid in (("schema_text", 0), ("example_object", 1),
                               ("json_schema_strict", 1)):
            with self.subTest(fmt):
                seen = []

                def first_without(kwargs, content):
                    seen.append(1)
                    return _payload({"contribution": 5}) if len(seen) == 1 else content
                self.use(CostAPI(content_fn=first_without))
                rows = self.run_engine(run=f"t_{fmt}", answer_format=fmt, arms=("group",),
                                       params=GameParams(rounds=1))
                self.assertEqual(sum(r["n_invalid"] for r in rows), n_invalid)
                first = next(r for r in rows if r["agent_id"] == 1)
                self.assertEqual(first["rationale"] is None, n_invalid == 0)

    def test_explicit_schema_text_has_the_default_config_record_and_resumes(self):
        self.assertEqual(Engine(self.rcfg(answer_format="schema_text"),
                                llm=pgg_game.OfflineLLM()).config_record(),
                         Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).config_record())
        self.interrupted_run()
        engine, api = self.resume(answer_format="schema_text")
        engine.run(resume=True)
        self.assertEqual((len(api.calls), self.summary_now()["n_answers_reused"]), (31, 1))

    def test_other_format_on_resume_stops(self):
        self.interrupted_run()
        for fmt in ("example_object", "json_schema_strict"):
            with self.subTest(fmt):
                engine, api = self.resume(answer_format=fmt)
                with self.assertRaisesRegex(ValueError, "not resumed.*answer_format"):
                    engine.run(resume=True)
                self.assertEqual(api.calls, [])


if __name__ == "__main__":
    unittest.main()
