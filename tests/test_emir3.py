"""Mock tests of task #73 (EMIR 3, Part 3: 3a-3e). No network, no ../.env, no game call.

(3a) reasoning_capped per model: Mistral's rule max(reasoning_tokens,
completion_tokens) >= max_tokens - 4096, the others reasoning_tokens alone;
rows and summary show both numbers. (3b) the new q2 sentence: every prompt the
engine sends with today's abstract_v3 / story_A equals the prompt of the files
as they were before task #73 (commit 533aca8) except that sentence. (3c) a
rule-comprehension call whose max_invalid is used up does not stop the run:
comp_missing row, logged event, counted apart from the decisions' invalid-rate
cap. (3d) "kind" is required, the linter runs unless kind "abstract", the
verdict per frame is in the summary and every segment entry. (3e) the cards
file is locked by cards_sha256 (run, dry run).
"""

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_frame_lock import K2_SENTENCE, NEW_SENTENCE, STORY_A, _sha, _story_variant  # noqa: E402
from test_frames import V3, FrameBase, _comp_reply, _main  # noqa: E402
from test_minipilot import MINIPILOT_CONFIG  # noqa: E402
from test_pgg_game import CARD_A, ROOT, FakeAPI, _payload  # noqa: E402
from test_pgg_guards import CostAPI  # noqa: E402

import cerceve_linter  # noqa: E402
import llm_client  # noqa: E402
import pgg_cost  # noqa: E402
import pgg_frames  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Engine, FrameError  # noqa: E402

PRE_TASK_COMMIT = "533aca8"          # frames as EMIR 2 left them (q2 with the +3 / -3 example)
CARDS_V3 = ROOT / "cards" / "pilot_cards_v3.json"


def _usage(reasoning, completion):
    return {"prompt_tokens": 100, "completion_tokens": completion,
            "completion_tokens_details": {"reasoning_tokens": reasoning}, "cost": 0.0001}


# --------------------------------------------------------------------------
# (3a) reasoning_capped rule per model
# --------------------------------------------------------------------------

class ReasoningCapRule(FrameBase):
    def test_rules_and_offline_copy_agree(self):
        limit = 16000 - llm_client.REASONING_RESERVE_TOKENS          # 11904
        cases = [((5000, 12000), False, True),      # M1 pattern reversed: completion decides
                 ((13000, 9000), True, True),       # reasoning > completion (11 of 18 in M1)
                 ((limit, 10), True, True), ((limit - 1, limit - 1), False, False),
                 ((None, 12000), None, True), ((None, None), None, None)]
        for (r, c), want_default, want_mistral in cases:
            usage = {"completion_tokens": c} if c is not None else {}
            if r is not None:
                usage["completion_tokens_details"] = {"reasoning_tokens": r}
            with self.subTest(r=r, c=c):
                for fn in (llm_client.reasoning_capped, pgg_game._offline_reasoning_capped):
                    self.assertEqual(fn(usage, 16000), want_default)
                    self.assertEqual(fn(usage, 16000, "reasoning"), want_default)
                    self.assertEqual(fn(usage, 16000, "max_reasoning_completion"), want_mistral)
        self.assertEqual(llm_client.REASONING_CAP_RULES, pgg_game.OfflineLLM.REASONING_CAP_RULES)
        for fn in (llm_client.reasoning_capped, pgg_game._offline_reasoning_capped):
            with self.assertRaises(ValueError):
                fn({}, 16000, "completion")
        with self.assertRaisesRegex(ValueError, r"reasoning_cap_rule\[mistral\] must be one of"):
            Engine(self.fcfg(reasoning_cap_rule={"mistral": "completion"}))
        with self.assertRaisesRegex(ValueError, "reasoning_cap_rule for models not in the run"):
            Engine(self.fcfg(reasoning_cap_rule={"gemini": "max_reasoning_completion"}))

    def test_rows_and_summary_show_both_numbers(self):
        # every response: reasoning 5000, completion 12000 (max_tokens 16000, limit 11904)
        self.use(CostAPI(usage_fn=lambda kw: _usage(5000, 12000)))
        Engine(self.fcfg(max_tokens=16000,
                         reasoning_cap_rule={"mistral": "max_reasoning_completion"})).run()
        rows = self.rows()
        for r in rows:
            self.assertEqual((r["reasoning_tokens"], r["completion_tokens"]), (5000, 12000))
            mistral = r["model_key"] == "mistral"
            self.assertEqual(r["reasoning_cap_rule"],
                             "max_reasoning_completion" if mistral else "reasoning")
            self.assertIs(r["reasoning_capped"], mistral)
        summary = json.loads((self.tmp / "runs" / "fr" / "fr_summary.json").read_text())
        self.assertEqual(summary["reasoning_cap_rules"],
                         {"deepseek": "reasoning", "mistral": "max_reasoning_completion",
                          "gpt": "reasoning"})
        pm = summary["per_model"]
        n_mi = sum(r["model_key"] == "mistral" for r in rows)
        self.assertEqual(pm["v/mi"]["n_reasoning_capped"], n_mi)
        self.assertEqual(pm["v/ds"]["n_reasoning_capped"], 0)
        self.assertEqual(pm["v/mi"]["reasoning_tokens"], 5000 * pm["v/mi"]["n_responses"])
        self.assertEqual(pm["v/mi"]["completion_tokens"], 12000 * pm["v/mi"]["n_responses"])
        self.assertEqual(pm["v/mi"]["n_reasoning_over_completion"], 0)
        # cost stays usage.cost (priced from completion), not changed by the rule
        self.assertAlmostEqual(pm["v/mi"]["cost_usd"], 0.0001 * pm["v/mi"]["n_responses"])
        # the raw log records the rule next to the flag
        succ = [e for e in self.raw_log_of("fr") if e.get("model") == "v/mi" and "reasoning_capped" in e]
        self.assertTrue(succ)
        self.assertTrue(all(e["reasoning_cap_rule"] == "max_reasoning_completion" for e in succ))

    def test_reasoning_over_completion_is_counted(self):
        self.use(CostAPI(usage_fn=lambda kw: _usage(900, 300)))
        Engine(self.fcfg(reasoning_cap_rule={"mistral": "max_reasoning_completion"})).run()
        summary = json.loads((self.tmp / "runs" / "fr" / "fr_summary.json").read_text())
        for slug, s in summary["per_model"].items():
            self.assertEqual(s["n_reasoning_over_completion"], s["n_responses"], slug)
        self.assertEqual(summary["n_reasoning_over_completion"],
                         sum(s["n_responses"] for s in summary["per_model"].values()))

    def raw_log_of(self, run):
        path = self.tmp / "runs" / run / "raw_calls.jsonl"
        return [json.loads(x) for x in path.read_text().splitlines()]


# --------------------------------------------------------------------------
# (3b) prompts: only the q2 sentence changed
# --------------------------------------------------------------------------

def _git_show(rev_path: str) -> bytes | None:
    try:
        return subprocess.run(["git", "show", rev_path], cwd=ROOT, capture_output=True,
                              check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None


class PromptsOnlyQ2Changed(FrameBase):
    def test_every_sent_prompt_equal_except_q2(self):
        old = {}
        for label, rel in (("abstract_v3", "frames/abstract_v3.json"),
                           ("story", "frames/story_A.json")):
            data = _git_show(f"{PRE_TASK_COMMIT}:{rel}")
            if data is None:
                self.skipTest(f"git object {PRE_TASK_COMMIT}:{rel} not available")
            old[label] = self.tmp / f"old_{label}.json"
            old[label].write_bytes(data)
        # EMIR 2's files are the ones the config locked before this task
        self.assertEqual(_sha(old["abstract_v3"]),
                         "9bdc919a0eebe1991e69212e9144e6ef49622da0f20cd9886bd94ded312bf163")
        self.assertEqual(_sha(old["story"]),
                         "4e38eb4891071419659a1b3f26b2c1a80a77fe88e3be74cc559b1f7575e49977")

        # (i) every text of both frames as the engine renders it (cerceve_linter.render_all:
        # system, rules, every round and position, punishment step, isolated values,
        # rule comprehension, response schemas), cards v3
        for label, new in (("abstract_v3", V3), ("story", STORY_A)):
            with self.subTest(label):
                _, parts_old = cerceve_linter.render_all(ROOT, old[label], CARDS_V3)
                _, parts_new = cerceve_linter.render_all(ROOT, new, CARDS_V3)
                self.assertEqual(len(parts_old), len(parts_new))
                self.assertGreater(len(parts_new), 1000)
                diff = [(o, n) for o, n in zip(parts_old, parts_new) if o != n]
                self.assertTrue(diff)
                for o, n in diff:
                    self.assertEqual(o[:3], n[:3])
                    self.assertTrue(o[0].startswith("kural_anlama_") and o[2] == "çerçeve", o[:3])
                    self.assertEqual(o[3].count(K2_SENTENCE), 1)
                    self.assertEqual(o[3].replace(K2_SENTENCE, NEW_SENTENCE), n[3])
                self.assertEqual(len(diff), sum(o[0].startswith("kural_anlama_")
                                                and o[2] == "çerçeve" for o in parts_old))

        # (ii) the messages the engine sends (abstract_v3; the mock API reads its texts)
        def sent(path, run):
            self.use(CostAPI())
            Engine(self.fcfg(run=run, frame_files={"abstract_v3": str(path)},
                             conditions=("N", "P"),
                             frames={"abstract_v3": ["deepseek", "mistral", "gpt"]})).run()
            return sorted(json.dumps(c["messages"], ensure_ascii=False) for c in self.api.calls)

        before = sent(old["abstract_v3"], "old")
        after = sent(V3, "new")
        self.assertEqual(len(before), len(after))
        self.assertGreater(len(after), 100)
        changed = [b for b in before if K2_SENTENCE in b]
        # every rule-comprehension prompt (and only those) carried the old sentence once
        self.assertTrue(changed)
        self.assertTrue(all("RULE CHECK" in b and b.count(K2_SENTENCE) == 1
                            for b in changed))
        self.assertFalse([a for a in after if K2_SENTENCE in a])
        # replacing the sentence turns the old prompts into the new ones, byte for byte
        self.assertEqual(sorted(b.replace(K2_SENTENCE, NEW_SENTENCE) for b in before), after)
        n_same = sum(b == a for b, a in zip(before, after))
        self.assertEqual(len(after) - n_same, len(changed))


# --------------------------------------------------------------------------
# (3c) rule comprehension does not stop the run
# --------------------------------------------------------------------------

class ComprehensionMissing(FrameBase):
    def one(self, **kw):
        return self.fcfg(models={"deepseek": "v/ds"}, frames={"abstract_v3": ["deepseek"]},
                         frame_files=None, cards=[CARD_A], **kw)

    def test_max_invalid_used_up_writes_comp_missing_and_goes_on(self):
        bad = _payload({"q1": "28", "q2": -6})                    # string: outside the schema
        # agent 1: max_invalid (2) + 1 invalid payloads -> given up; then valid answers
        replies = [bad, bad, bad] + [_payload({"q1": 28, "q2": -6})] * 4
        self.use(CostAPI(content_fn=_comp_reply(replies)))
        # a cap so tight that 3 decision invalids would stop the run
        engine = Engine(self.one(max_invalid=2, invalid_rate_cap=0.01))
        engine.run()
        self.assertIsNone(engine.stop_reason)
        rows = self.rows()
        comp = {(r["arm"], r["agent_id"]): r for r in rows if r["step"] == "comprehension"}
        miss = comp[("group", 1)]
        self.assertIs(miss["comp_missing"], True)
        self.assertEqual(miss["comp_missing_reason"], "max_invalid")
        self.assertEqual((miss["comp_q1_answer"], miss["comp_q1_correct"], miss["comp_n_correct"]),
                         (None, None, None))
        self.assertEqual(miss["n_invalid"], 3)
        self.assertEqual(miss["step"], "comprehension")
        self.assertTrue(all(comp[k]["comp_missing"] is False for k in comp if k != ("group", 1)))
        # the game and the schedule are complete
        self.assertEqual(len([r for r in rows if r["step"] == "contribute"]), 8)
        self.assertEqual(len([r for r in rows if r["step"] == "isolated"]), 2)
        # logged
        log = [json.loads(x) for x in
               (self.tmp / "runs" / "fr" / "raw_calls.jsonl").read_text().splitlines()]
        ev = [e for e in log if e.get("event") == "pgg_comprehension_missing"]
        self.assertEqual(len(ev), 1)
        self.assertEqual((ev[0]["reason"], ev[0]["n_invalid"], ev[0]["call"]["agent_id"]),
                         ("max_invalid", 3, 1))
        self.assertFalse([e for e in log if e.get("event") == "pgg_run_aborted"])
        # counted apart, outside the decisions' cap; the cost is in the budget
        summary = json.loads((self.tmp / "runs" / "fr" / "fr_summary.json").read_text())
        s = summary["per_model"]["v/ds"]
        self.assertEqual((s["n_invalid"], s["n_parse_fail"]), (0, 0))
        self.assertEqual((s["n_comp_invalid"], s["n_comp_parse_fail"], s["n_comp_missing"]),
                         (3, 0, 1))
        self.assertEqual((summary["n_comp_invalid"], summary["n_comp_missing"]), (3, 1))
        self.assertEqual(s["n_responses"], len(self.api.calls))
        self.assertAlmostEqual(s["cost_usd"], 0.0001 * len(self.api.calls))
        c = summary["comprehension"]["per_model_frame"]["deepseek"]["abstract_v3"]
        self.assertEqual((c["n"], c["n_missing"], c["n_invalid"]), (4, 1, 3))
        self.assertIn("comp_missing", summary["comprehension"]["rule"])

    def test_decision_invalids_still_hit_the_cap(self):
        # the same cap stops the run on decision invalids (the cap is not switched off)
        first = {"done": 0}

        def content(kwargs, default):
            if FakeAPI.parse(kwargs)[0] == "contribute" and first["done"] < 2:
                first["done"] += 1
                return _payload({"contribution": "x"})
            return default

        self.use(CostAPI(content_fn=content))
        engine = Engine(self.one(invalid_rate_cap=0.01))
        self.assertEqual(engine.cfg.invalid_limit("deepseek"), 0)   # floor(0.01 x 10 decisions)
        try:
            engine.run()
        except pgg_game.RunStopped:
            pass
        self.assertEqual(engine.stopped_models.get("deepseek"), "invalid_rate_cap")

    def test_cap_is_a_share_of_the_decision_calls(self):
        cfg = self.one(invalid_rate_cap=0.05)
        with_comp = cfg.planned_calls_per_model("deepseek")
        decisions = cfg.planned_calls_per_model("deepseek", comprehension=False)
        self.assertEqual(with_comp - decisions, 5)        # 4 agents + 1 schedule
        self.assertEqual(cfg.invalid_limit("deepseek"), int(0.05 * decisions))
        # the committed design: 1200 / 600 calls with comprehension (per model x frame
        # 480 contribute + 60 isolated + 60 comprehension), 1080 / 540 decisions
        raw = json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8"))
        s = pgg_game.settings_from_args(pgg_game.build_parser().parse_args(
            ["--config", str(MINIPILOT_CONFIG)]))
        models = pgg_game.resolve_models(raw["models"], pgg_cost.KNOWN_MODELS)
        cfg = pgg_game.run_config("x", s, models, {"results_dir": self.tmp})
        self.assertEqual({k: cfg.planned_calls_per_model(k) for k in cfg.models},
                         {"deepseek": 1200, "mistral": 600, "gpt": 1200})
        self.assertEqual({k: cfg.planned_calls_per_model(k, comprehension=False)
                          for k in cfg.models},
                         {"deepseek": 1080, "mistral": 540, "gpt": 1080})
        self.assertEqual({k: cfg.invalid_limit(k) for k in cfg.models},
                         {"deepseek": 54, "mistral": 27, "gpt": 54})


# --------------------------------------------------------------------------
# (3d) kind required, linter by default, verdict in the summary
# --------------------------------------------------------------------------

class LinterByDefault(FrameBase):
    def test_kind_is_required(self):
        raw = json.loads(STORY_A.read_text(encoding="utf-8"))
        del raw["kind"]
        with self.assertRaisesRegex(pgg_frames.FrameError, r"kind: missing; required"):
            pgg_frames.validate_frame(raw, "t")
        path = self.tmp / "no_kind.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaisesRegex(FrameError, "kind"):
            Engine(self.fcfg(frame_files={"story": str(path)}))
        # the dry run too
        conf = json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8"))
        conf["frame_files"]["story"] = {"path": str(path), "sha256": _sha(path)}
        conf_path = self.tmp / "mp.json"
        conf_path.write_text(json.dumps(conf), encoding="utf-8")
        code, out, err = _main("--dry-run", "--config", str(conf_path))
        self.assertEqual(code, 1)
        self.assertIn("kind", err)
        self.assertNotIn("TOPLAM", out)
        self.create.assert_not_called()

    def test_story_kind_is_linted_and_abstract_is_exempt(self):
        # the frame linter runs on a story frame by default: a forbidden root stops it
        path = _story_variant(self.tmp, lambda r: r["rules"].append({"text": "- A game."}))
        with self.assertRaisesRegex(FrameError, "story frame 'story'.*forbidden roots"):
            Engine(self.fcfg(frame_files={"story": str(path)}))
        # the same file declared abstract is exempt
        path2 = _story_variant(self.tmp, lambda r: (r["rules"].append({"text": "- A game."}),
                                                     r.update(kind="abstract")), "as_abs.json")
        Engine(self.fcfg(frame_files={"story": str(path2)}))

    def test_verdict_in_the_summary_and_every_segment(self):
        # the mock API cannot play story_A's texts: the run uses the fixture
        # (kind abstract); story_A's verdict is checked on the config
        want_story = {"frame_id": "story_A_jar", "kind": "story", "sha256": _sha(STORY_A),
                      "lint": "passed"}
        audit = self.fcfg(frame_files={"story": str(STORY_A)}).frame_audit()
        self.assertEqual({f: audit["story"][f] for f in want_story}, want_story)
        self.assertIn("no forbidden root", audit["story"]["reason"])
        self.use(CostAPI())
        Engine(self.fcfg()).run()
        summary = json.loads((self.tmp / "runs" / "fr" / "fr_summary.json").read_text())
        want = {
            "abstract_v3": {"frame_id": "abstract_v3", "kind": "abstract", "sha256": _sha(V3),
                            "lint": "exempt"},
            "story": {"frame_id": "story_fixture", "kind": "abstract",
                      "sha256": _sha(self.story), "lint": "exempt"}}
        self.assertTrue(summary["segments"])
        for seg in summary["segments"]:
            audit = seg["frame_audit"]
            self.assertEqual({k: {f: v[f] for f in want[k]} for k, v in audit.items()}, want)
            self.assertIn("kind \"abstract\" declared", audit["abstract_v3"]["reason"])

    def test_legacy_abstract_v2_only_as_the_default(self):
        cfg = self.cfg(run="v2", results_dir=self.tmp / "results")          # no frames
        audit = cfg.frame_audit()
        self.assertEqual(list(audit), [pgg_game.DEFAULT_FRAME])
        self.assertEqual((audit[pgg_game.DEFAULT_FRAME]["lint"],
                          audit[pgg_game.DEFAULT_FRAME]["kind"]), ("exempt", None))
        self.assertIn("frozen frame of pilot v2", audit[pgg_game.DEFAULT_FRAME]["reason"])

    def test_committed_frames(self):
        raw = json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8"))
        for label, spec in raw["frame_files"].items():
            f = pgg_game.load_frame_file(label, spec)
            self.assertIn("kind", json.loads(Path(f.path).read_text(encoding="utf-8")))
            audit = pgg_game.frame_audit(label, f, pgg_game.GameParams(), with_frames=True)
            self.assertEqual(audit["lint"], "exempt" if label == "abstract_v3" else "passed")


# --------------------------------------------------------------------------
# (3e) cards lock
# --------------------------------------------------------------------------

class CardsLock(FrameBase):
    def test_check(self):
        sha = hashlib.sha256(CARDS_V3.read_bytes()).hexdigest()
        self.assertEqual(pgg_game.check_cards_lock(CARDS_V3, sha), sha)
        self.assertEqual(pgg_game.check_cards_lock(CARDS_V3, None), sha)
        with self.assertRaisesRegex(ValueError, "cards_sha256 locks .* no run starts"):
            pgg_game.check_cards_lock(CARDS_V3, "0" * 64)
        for bad in ("abc", "A" * 64, 5):
            with self.assertRaisesRegex(ValueError, "64 lower-case hex"):
                pgg_game.check_cards_lock(CARDS_V3, bad)

    def changed_cards_config(self, **extra) -> Path:
        cards = self.tmp / "cards.json"
        cards.write_bytes(CARDS_V3.read_bytes() + b"\n")          # one byte more
        raw = json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8"))
        raw.update(cards=str(cards), **extra)                     # cards_sha256: v3's
        path = self.tmp / "mp_cards.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        return path

    def test_dry_run_fails(self):
        code, out, err = _main("--dry-run", "--config", str(self.changed_cards_config()))
        self.assertEqual(code, 1)
        self.assertIn("HATA: kartlar: cards: sha256 of", err)
        self.assertNotIn("TOPLAM", out)
        self.create.assert_not_called()

    def test_real_run_fails_before_any_call(self):
        self.use(CostAPI())
        conf = self.changed_cards_config(prereg_approved=True, run="cards_mock",
                                         runs_dir=str(self.tmp / "runs"))
        code, _, err = _main("--config", str(conf))
        self.assertEqual(code, 1)
        self.assertIn("cards_sha256 locks", err)
        self.create.assert_not_called()
        self.assertFalse((self.tmp / "runs" / "cards_mock").exists())


if __name__ == "__main__":
    unittest.main()
