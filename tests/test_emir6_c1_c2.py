"""Mock tests of EMIR 6 C1 + C2 (task #95). No network, no ../.env, no real run directory.

C1 code version lock: a --resume whose git_commit is not the first segment's is
refused before any call and any write, whether answers would be reused or not;
only --allow-code-change, and only for a config of stage 0a / 0b (no analysis
data), goes on, and then the rows of units that span two commits are marked
(code_change_span, code_commits) and the summary counts those units. Stage 1
(and a config without a stage) refuses the flag; a config cannot set it.
C2 answer_format in the cost and deadline estimates: the prompt is rendered
with the answer instruction (schema text / example object / strict schema) and
measured by one function (pgg_game._prompt_chars), which the dry-run estimate
and the deadline estimate of a run both use; schema_text keeps the numbers of
the code before.
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_emir5_bolum1 import _with_commit  # noqa: E402
from test_pgg_game import CARD_A, CARD_B  # noqa: E402
from test_pgg_guards import CostAPI  # noqa: E402
from test_pgg_k3_k5 import DeadlineEstimate  # noqa: E402
from test_pgg_resume import GEMINI, ResumeBase, _rows, _tree  # noqa: E402

import llm_client  # noqa: E402
import pgg_cost  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Engine, GameParams  # noqa: E402

ROOT = Path(pgg_game.__file__).resolve().parent
STAGE_CONFIGS = {"main.json": "1", "main_s0a_example.json": "0a",
                 "main_s0a_schema.json": "0a", "main_s0b.json": "0b"}
A, B, C = "a" * 40, "b" * 40, "c" * 40


def _cli(argv):
    with contextlib.redirect_stdout(io.StringIO()) as out, \
            contextlib.redirect_stderr(io.StringIO()) as err:
        code = pgg_game.main(argv)
    return code, out.getvalue(), err.getvalue()


# --------------------------------------------------------------------------
# C1 code version lock
# --------------------------------------------------------------------------

class CodeVersionLock(ResumeBase):
    """rcfg: 2 models x 2 cards, rounds 2. interrupted_run(at=21) cuts unit 2 after its
    round 1 (4 rows, segment 0) with nothing of round 2 answered."""

    def cut(self, commit=A, **kw):
        with _with_commit(commit):
            self.interrupted_run(at=21, **kw)

    def test_a_other_commit_without_flag_is_refused_before_any_call_or_write(self):
        for stage in (None, "0a", "0b", "1"):
            with self.subTest(stage=stage):
                self.cut(stage=stage)
                before = _tree(self.run_dir)
                with _with_commit(B):
                    engine, api = self.resume(stage=stage)
                    with self.assertRaises(ValueError) as cm:
                        engine.run(resume=True)
                    plan = Engine(self.rcfg(stage=stage), llm=pgg_game.OfflineLLM()).resume_plan()
                    text = pgg_game.resume_report(Engine(self.rcfg(stage=stage),
                                                         llm=pgg_game.OfflineLLM()), plan)
                msg = str(cm.exception)
                self.assertTrue(msg.startswith("run 'r1' not resumed, no call made: code version "
                                               "lock: segment 0 (the first) of this run ran "
                                               f"git_commit {A}, this segment would run {B}"), msg)
                self.assertIn("--allow-code-change", msg)
                self.assertEqual(api.calls, [])
                self.assertEqual(_tree(self.run_dir), before)     # nothing written, no lock
                self.assertEqual(plan.reuse, {})                  # no answer to reuse
                self.assertEqual(plan.code_lock, {
                    "first_segment": 0, "first_commit": A, "now": B, "same_as_first": False,
                    "allow_code_change": False, "stage": stage, "decision": "refused"})
                self.assertIn("FARKLI — sürdürme REDDEDİLİR", text)
                self.assertIn("SORUN (sürdürme başlamaz)", text)
                self.run_dir_reset()

    def run_dir_reset(self):
        import shutil
        shutil.rmtree(self.run_dir)

    def test_a_a_later_segment_is_compared_with_the_first(self):
        # segment 1 ran A too; a third segment with C is refused against segment 0's A
        self.cut(stage="0a")
        with _with_commit(A):
            engine, _ = self.resume(stage="0a")
            engine.run(resume=True)
        before = _tree(self.run_dir)
        with _with_commit(C):
            plan = Engine(self.rcfg(stage="0a"), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual((plan.code_lock["first_commit"], plan.code_lock["decision"]),
                         (A, "refused"))
        self.assertEqual(plan.code_change["differs_from_segments"], [0, 1])
        self.assertEqual(_tree(self.run_dir), before)

    def test_b_stage_0a_0b_with_flag_goes_on_and_marks_the_spanning_unit(self):
        for stage in ("0a", "0b"):
            with self.subTest(stage=stage):
                self.cut(stage=stage)
                n_old = len(_rows(self.results))
                with _with_commit(B):
                    engine, api = self.resume(stage=stage, allow_code_change=True)
                    plan = engine.resume_plan()
                    engine.run(resume=True)
                specs = engine.unit_specs()
                span_unit = specs[2].label                    # round 1 in segment 0 (A)
                self.assertEqual(plan.code_lock["decision"], "allowed")
                self.assertEqual(plan.code_span, {span_unit: {"segments": [0, 1],
                                                              "commits": [A, B]}})
                self.assertEqual(len(api.calls), 4 + 8 + 4 * 5)      # nothing reused
                rows = _rows(self.results)
                new = rows[n_old:]
                marked = [r for r in new if r.get("code_change_span")]
                self.assertEqual({r["unit"] for r in marked}, {span_unit})
                self.assertEqual(len(marked), 4)                      # its round 2
                self.assertTrue(all(r["code_commits"] == [A, B] for r in marked))
                self.assertTrue(all("code_change_span" not in r and "code_commits" not in r
                                    for r in new if r["unit"] != span_unit))
                # the earlier rows stay as written (append-only)
                self.assertTrue(all("code_change_span" not in r for r in rows[:n_old]))
                summary = self.summary_now()
                self.assertEqual(summary["units"]["n_remaining"], 0)
                self.assertEqual(summary["stage"], stage)
                self.assertEqual(summary["code_change_span_units"],
                                 [{"unit": span_unit, "segments": [0, 1], "commits": [A, B],
                                   "n_rows": 8}])
                self.assertEqual((summary["n_code_change_span_units"],
                                  summary["n_code_change_span_rows"]), (1, 8))
                lock = summary["segments"][-1]["code_lock"]
                self.assertEqual((lock["decision"], lock["allow_code_change"], lock["stage"]),
                                 ("allowed", True, stage))
                self.assertIsNone(summary["segments"][0].get("code_lock"))
                event = self.raw_events("pgg_run_resume")[0]
                self.assertEqual(event["code_lock"]["decision"], "allowed")
                self.assertTrue(event["allow_code_change"])
                self.assertEqual(event["code_change_span_units"], plan.code_span)
                self.run_dir_reset()

    def test_b_flag_with_the_same_commit_marks_nothing(self):
        self.cut(stage="0a")
        with _with_commit(A):
            engine, _ = self.resume(stage="0a", allow_code_change=True)
            engine.run(resume=True)
        summary = self.summary_now()
        self.assertEqual(summary["segments"][-1]["code_lock"]["decision"], "same")
        self.assertEqual((summary["code_change_span_units"], summary["n_code_change_span_units"]),
                         ([], 0))
        self.assertFalse(any("code_change_span" in r for r in _rows(self.results)))

    def test_b_answers_of_another_commit_are_still_not_reused(self):
        # interrupted_run() leaves 1 answer to reuse: the flag does not reuse it
        with _with_commit(A):
            self.interrupted_run(stage="0a")
        with _with_commit(B):
            engine, api = self.resume(stage="0a", allow_code_change=True)
            with self.assertRaisesRegex(ValueError, r"reuse refused \(code_changed\)") as cm:
                engine.run(resume=True)
            self.assertNotIn("code version lock", str(cm.exception))
            self.assertEqual(api.calls, [])
            engine, api = self.resume(stage="0a", allow_code_change=True,
                                      discard_reuse_on_code_change=True)
            engine.run(resume=True)
        self.assertEqual(len(api.calls), 32)
        self.assertEqual(self.summary_now()["n_code_change_span_units"], 1)

    def test_c_stage_1_with_flag_is_refused(self):
        self.cut(stage="1")
        before = _tree(self.run_dir)
        for commit in (A, B):                     # also with the same commit
            with self.subTest(commit=commit), _with_commit(commit):
                with self.assertRaisesRegex(ValueError, r"--allow-code-change is refused: config "
                                                        r"stage '1' holds analysis data"):
                    self.resume(stage="1", allow_code_change=True)
        self.assertEqual(_tree(self.run_dir), before)
        # a new run of stage 1 with the flag, and a config without a stage
        for stage in ("1", None):
            with self.subTest(stage=stage), self.assertRaisesRegex(
                    ValueError, "--allow-code-change is refused"):
                Engine(self.rcfg(run="r2", stage=stage, allow_code_change=True),
                       llm=pgg_game.OfflineLLM())
        self.assertFalse((self.tmp / "runs" / "r2").exists())
        with self.assertRaisesRegex(ValueError, "stage must be one of"):
            self.rcfg(stage="2").validate()

    def test_c_cli_stage_1_config_with_flag_is_refused(self):
        self.cut(stage="1", models=dict(GEMINI), budget_usd=None, invalid_rate_cap=None)
        cards = self.tmp / "cards.json"
        cards.write_text(json.dumps([{"card_id": c.card_id, "style": c.style, "text": c.text}
                                     for c in (CARD_A, CARD_B)]))
        config = self.tmp / "s1.json"
        config.write_text(json.dumps({"stage": "1"}))
        argv = ["--resume", "--config", str(config), "--run", "r1", "--cards", str(cards),
                "--models", "gemini", "--runs-dir", str(self.tmp / "runs"), "--rounds", "2",
                "--groups-per-cell", "1", "--isolated-reps", "1", "--allow-code-change"]
        before = _tree(self.run_dir)
        self.use(CostAPI())
        self.create.reset_mock()
        with _with_commit(B), mock.patch.object(pgg_game, "_llm") as llm:
            code, _, err = _cli(argv)
            self.assertEqual(code, 1)
            llm.assert_not_called()                    # refused before llm_client is used
            self.assertIn("HATA: --allow-code-change is refused: config stage '1' holds "
                          "analysis data", err)
            # the read-only plan refuses it too
            code, _, err = _cli(argv + ["--dry-run"])
            self.assertEqual(code, 1)
            self.assertIn("--allow-code-change is refused", err)
        self.create.assert_not_called()
        self.assertEqual(_tree(self.run_dir), before)
        # a config cannot set the flag
        config.write_text(json.dumps({"stage": "0a", "allow_code_change": True}))
        code, _, err = _cli(argv[:-1])
        self.assertEqual(code, 1)
        self.assertIn("\"allow_code_change\" cannot be set in a config", err)

    def test_d_same_commit_resumes_as_before(self):
        with _with_commit(A):
            self.interrupted_run(stage="1")             # 1 answer to reuse
            engine, api = self.resume(stage="1")
            plan = engine.resume_plan()
            engine.run(resume=True)
        self.assertEqual((plan.problems, plan.code_span), ([], {}))
        self.assertEqual(plan.code_lock["decision"], "same")
        self.assertIn("git_commit of the first segment (0)", plan.config_checked)
        self.assertEqual(len(api.calls), 31)
        summary = self.summary_now()
        self.assertEqual((summary["n_answers_reused"], summary["units"]["n_remaining"]), (1, 0))
        self.assertEqual((summary["n_code_change_span_units"], summary["code_changes"]), (0, []))
        self.assertFalse(any("code_change_span" in r for r in _rows(self.results)))

    def test_d_rows_of_a_same_commit_resume_equal_those_without_stage(self):
        """The lock adds nothing to the rows of a normal resume (stage only in the config record)."""
        def keys():
            return [sorted(r) for r in _rows(self.results)]
        with _with_commit(A):
            self.interrupted_run()
            self.resume()[0].run(resume=True)
            plain = keys()
            self.run_dir_reset()
            self.interrupted_run(stage="0b")
            self.resume(stage="0b")[0].run(resume=True)
        self.assertEqual(keys(), plain)

    def test_stage_is_in_the_config_record(self):
        self.assertNotIn("stage", Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).config_record())
        self.assertEqual(Engine(self.rcfg(stage="0a"),
                                llm=pgg_game.OfflineLLM()).config_record()["stage"], "0a")
        # a resume cannot change the stage (and so get the flag)
        self.cut(stage="1")
        with _with_commit(A):
            plan = Engine(self.rcfg(stage="0a"), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertIn('config stage: earlier "1", now "0a"', plan.problems)

    def test_first_segment_of_the_code_before_a5_is_not_checked(self):
        """A first segment that recorded no code version (pilot v2) cannot be checked."""
        self.cut()
        summary = self.summary_now()
        for seg in summary["segments"]:
            seg.pop("code_version")
        self.summary_path.write_text(json.dumps(summary))
        raw = [json.loads(x) for x in self.raw.read_text().splitlines()]
        for rec in raw:
            rec.pop("code_version", None)
        self.raw.write_text("".join(json.dumps(r) + "\n" for r in raw))
        with _with_commit(B):
            plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(plan.problems, [])
        self.assertEqual(plan.code_lock["decision"], "not_recorded")
        self.assertIn("not recorded (code before A5), not checked", " ".join(plan.config_checked))


class StageConfigs(unittest.TestCase):
    def test_committed_configs(self):
        for name, stage in STAGE_CONFIGS.items():
            raw = json.loads((ROOT / "configs" / name).read_text(encoding="utf-8"))
            self.assertEqual(raw["stage"], stage, name)
            self.assertIs(raw["prereg_approved"], True, name)    # task #99
            self.assertNotIn("allow_code_change", raw)

    def test_dry_run_reports_the_lock(self):
        code, out, _ = _cli(["--dry-run", "--config", str(ROOT / "configs" / "main_s0b.json")])
        self.assertEqual(code, 0)
        self.assertIn("Aşama: 0b — kod sürümü kilidi: --resume ilk segmentin commit'iyle sürer; "
                      "--allow-code-change verilebilir (analiz verisi yok)", out)
        code, out, _ = _cli(["--dry-run", "--config", str(ROOT / "configs" / "main.json"),
                             "--groups-per-cell", "10", "--allow-code-change"])
        self.assertEqual(code, 0)
        self.assertIn("--allow-code-change REDDEDİLİR", out)
        self.assertIn("HATA (gerçek koşu başlamaz): --allow-code-change is refused", out)

    def test_flag_problem(self):
        p = pgg_game.code_change_flag_problem
        self.assertIsNone(p(False, None))
        self.assertIsNone(p(False, "1"))
        self.assertIsNone(p(True, "0a"))
        self.assertIsNone(p(True, "0b"))
        self.assertIn("holds analysis data", p(True, "1"))
        self.assertIn("not a stage without analysis data", p(True, None))

    def test_code_span_units(self):
        f = pgg_game.code_span_units
        self.assertEqual(f({"u": {0, 1}, "v": {1}, "w": {0, 2}}, {0: A, 1: B, 2: A}),
                         {"u": {"segments": [0, 1], "commits": [A, B]}})
        # an unknown commit is a commit of its own
        self.assertEqual(f({"u": {0, 1}}, {0: None, 1: A}),
                         {"u": {"segments": [0, 1], "commits": [None, A]}})


# --------------------------------------------------------------------------
# C2 answer_format in the cost and deadline estimates
# --------------------------------------------------------------------------

def _sent_chars(kwargs) -> int:
    return sum(len(m["content"]) for m in kwargs["messages"])


class PromptRendering(unittest.TestCase):
    def schemas(self):
        p = GameParams()
        out = []
        for label in ("abstract_v2", "abstract_v3", "abstract_v4", "story_A"):
            f = pgg_game.load_frame_file(label, None) if label != "abstract_v2" \
                else pgg_game.default_frame()
            out += [pgg_game.contribution_schema(p, True, f),
                    pgg_game.contribution_schema(p, False, f),
                    pgg_game.punishment_schema(p, [2, 3, 4], True, f)]
            if f.has_comprehension:
                out.append(f.comprehension_schema(True))
        return out

    def test_offline_rendering_equals_llm_client(self):
        msgs = [{"role": "system", "content": "S"}, {"role": "user", "content": "Q"}]
        for schema in self.schemas():
            for fmt in (None, *pgg_game.ANSWER_FORMATS):
                with self.subTest(fmt=fmt, schema=sorted(schema.get("properties", {}))):
                    self.assertEqual(pgg_game.answer_prompt_messages(msgs, schema, fmt),
                                     llm_client.answer_request(msgs, schema, fmt)[0])
                    self.assertEqual(pgg_game._prompt_chars(msgs, schema, fmt),
                                     sum(len(m["content"]) for m in
                                         llm_client.answer_request(msgs, schema, fmt)[0]))
        self.assertEqual(pgg_game._offline_strict_json_schema(self.schemas()[0]),
                         llm_client.strict_json_schema(self.schemas()[0]))
        with self.assertRaises(ValueError):
            pgg_game.answer_prompt_messages(msgs, self.schemas()[0], "other")

    def test_schema_text_count_is_that_of_the_code_before(self):
        msgs = [{"role": "system", "content": "Sys"}, {"role": "user", "content": "Question"}]
        for schema in self.schemas():
            old = (sum(len(m["content"]) for m in msgs) + len(pgg_game.SCHEMA_PROMPT_SUFFIX)
                   + len(json.dumps(schema, ensure_ascii=False)))
            self.assertEqual(pgg_game._prompt_chars(msgs, schema), old)
            self.assertEqual(pgg_game._prompt_chars(msgs, schema, "schema_text"), old)
        # the three formats give three lengths
        lengths = {fmt: pgg_game._prompt_chars(msgs, self.schemas()[0], fmt)
                   for fmt in pgg_game.ANSWER_FORMATS}
        self.assertEqual(len(set(lengths.values())), 3, lengths)


def _s0a_estimate(answer_format, **kw):
    """design_estimate of configs/main_s0a_example.json with another answer_format."""
    cfg = json.loads((ROOT / "configs" / "main_s0a_example.json").read_text(encoding="utf-8"))
    models = pgg_game.resolve_models(cfg["models"], pgg_cost.KNOWN_MODELS)
    frame_models = pgg_game.resolve_frames(cfg["frames"], models)
    frames = pgg_game.dry_run_frames(frame_models, cfg["frame_files"], GameParams())
    cards = pgg_game.load_cards(ROOT / cfg["cards"], cfg["cities"])
    cal = pgg_game.cost_calibration_files(cfg["cost_calibration"])
    with pgg_cost.extra_overlays(cal):
        return pgg_game.design_estimate(
            models=models, frame_models=frame_models, frames=frames, n_cells=len(cards),
            params=GameParams(), conditions=("N",), arms=tuple(cfg["arms"]),
            groups_per_cell=cfg["groups_per_cell"], isolated_reps=cfg["isolated_reps"],
            n_points=len(cfg["isolated_points"]), comprehension=cfg["comprehension"],
            isolated_frame=cfg["isolated_frame"], isolated_round_no=cfg["isolated_round_no"],
            cards=cards, answer_format=answer_format, **kw)


class CostEstimateFollowsTheAnswerFormat(unittest.TestCase):
    def test_same_config_other_format_other_prompt_tokens_and_cost(self):
        est = {fmt: _s0a_estimate(fmt) for fmt in (None, *pgg_game.ANSWER_FORMATS)}
        # schema_text explicit = default
        self.assertEqual(est[None]["total_cost_usd"], est["schema_text"]["total_cost_usd"])
        self.assertEqual([r["prompt_scale"] for r in est[None]["rows"]],
                         [r["prompt_scale"] for r in est["schema_text"]["rows"]])
        costs = {fmt: est[fmt]["total_cost_usd"] for fmt in pgg_game.ANSWER_FORMATS}
        self.assertEqual(len(set(costs.values())), 3, costs)
        for fmt in pgg_game.ALL_FIELDS_REQUIRED_FORMATS:
            for r0, r in zip(est["schema_text"]["rows"], est[fmt]["rows"]):
                for kind in ("isolated", "comprehension"):
                    self.assertNotEqual(r["prompt_scale"][kind], r0["prompt_scale"][kind])
                self.assertNotEqual(r["cost_usd"], r0["cost_usd"])
        # the example object is shorter than the schema text, the strict schema longer
        iso = {fmt: est[fmt]["rows"][0]["prompt_scale"]["isolated"] for fmt in costs}
        self.assertLess(iso["example_object"], iso["schema_text"])
        self.assertGreater(iso["json_schema_strict"], iso["schema_text"])
        self.assertEqual(est["example_object"]["answer_format"], "example_object")

    def test_scale_is_the_measured_ratio_of_the_rendered_prompts(self):
        frame = pgg_game.load_frame_file("abstract_v4", None)
        cards = [CARD_A, CARD_B]
        p = GameParams()
        for fmt in pgg_game.ANSWER_FORMATS:
            sc = pgg_game.prompt_scales(frame, p, cards, isolated_frame="fixed_round",
                                        answer_format=fmt)
            mine = pgg_game.mean_prompt_chars(frame, "isolated", p, cards,
                                              isolated_frame="fixed_round", answer_format=fmt)
            # the reference is the calibration's: abstract_v2, repeated, schema_text
            ref = pgg_game.mean_prompt_chars(pgg_game.default_frame(), "isolated", p, cards,
                                             isolated_frame="repeated")
            self.assertAlmostEqual(sc["isolated"], mine / ref, places=12)

    def test_without_frames_an_a_b_format_is_scaled(self):
        base = dict(models={"gemini": GEMINI["gemini"]}, frame_models={"abstract_v2": ["gemini"]},
                    frames={"abstract_v2": pgg_game.default_frame()}, n_cells=2,
                    params=GameParams(), conditions=("N",), arms=("group", "isolated"),
                    groups_per_cell=1, isolated_reps=1, n_points=5, cards=[CARD_A, CARD_B])
        plain = pgg_game.design_estimate(**base, scale=False)
        a = pgg_game.design_estimate(**base, answer_format="example_object", scale=True)
        self.assertNotEqual(a["total_cost_usd"], plain["total_cost_usd"])

    def test_report_has_the_calibration_note(self):
        for fmt in (None, "example_object", "json_schema_strict"):
            text = pgg_game.format_design_report(_s0a_estimate(fmt))
            self.assertIn(f"cevap biçimi (answer_format) {fmt or 'schema_text'}: kalibrasyon "
                          "schema_text ile ölçüldü; A/B farkı istem uzunluğundan ölçeklendi",
                          text)

    def test_cli_dry_runs_of_the_two_0a_configs(self):
        totals = {}
        for name in ("main_s0a_example.json", "main_s0a_schema.json"):
            code, out, err = _cli(["--dry-run", "--config", str(ROOT / "configs" / name)])
            self.assertEqual(code, 0, err)
            self.assertIn("kalibrasyon schema_text ile ölçüldü; A/B farkı istem uzunluğundan "
                          "ölçeklendi", out)
            line = next(x for x in out.splitlines() if x.startswith("TOPLAM"))
            totals[name] = float(line.split("~")[1].split(" ")[0])
        self.assertNotEqual(totals["main_s0a_example.json"], totals["main_s0a_schema.json"])
        # --answer-format gives a config the estimate of the other format
        code, out, _ = _cli(["--dry-run", "--config", str(ROOT / "configs" / "main_s0a_example.json"),
                             "--answer-format", "json_schema_strict"])
        line = next(x for x in out.splitlines() if x.startswith("TOPLAM"))
        self.assertEqual(float(line.split("~")[1].split(" ")[0]), totals["main_s0a_schema.json"])

    def test_cli_main_json_with_a_placeholder_format_says_so(self):
        # task #101 (EMIR 8): the committed main.json has example_object now, so the
        # placeholder path is checked on a copy with the old placeholder value
        raw = json.loads((ROOT / "configs" / "main.json").read_text(encoding="utf-8"))
        raw["answer_format"] = "<TBD: answer format>"
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "main_placeholder.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            code, out, _ = _cli(["--dry-run", "--config", str(path), "--groups-per-cell", "10"])
        self.assertEqual(code, 0)
        self.assertIn("answer_format seçilmedi (yer tutucu): istem schema_text talimatıyla ölçüldü",
                      out)
        self.assertIn("SEÇİLMEMİŞ (gerçek koşu başlamaz): answer_format", out)
        code, out, _ = _cli(["--dry-run", "--config", str(ROOT / "configs" / "main.json"),
                             "--groups-per-cell", "10"])
        self.assertEqual(code, 0)
        self.assertNotIn("answer_format seçilmedi", out)
        self.assertIn("cevap biçimi (answer_format) example_object: kalibrasyon schema_text ile "
                      "ölçüldü", out)



class DryRunAndRunMeasureTheSamePrompt(ResumeBase):
    def test_engine_gate_estimate_uses_the_format(self):
        """Engine.design_estimate (expected-cost gate): without frames A / B are scaled too."""
        def est(**kw):
            return Engine(self.rcfg(models=dict(GEMINI), **kw),
                          llm=pgg_game.OfflineLLM()).design_estimate()
        e0, ea = est(), est(answer_format="example_object")
        self.assertIsNone(e0["rows"][0]["prompt_scale"])          # as before: not scaled
        self.assertIsNotNone(ea["rows"][0]["prompt_scale"])
        self.assertNotEqual(ea["total_cost_usd"], e0["total_cost_usd"])
        self.assertEqual(est(answer_format="schema_text")["total_cost_usd"], e0["total_cost_usd"])

    def test_isolated_prompts_sent_equal_the_dry_run_measure(self):
        """mean_prompt_chars (dry run) = the mean length of the prompts the run sends."""
        for fmt in pgg_game.ANSWER_FORMATS:
            with self.subTest(fmt=fmt):
                api = CostAPI()
                self.use(api)
                engine = Engine(self.rcfg(run=f"p_{fmt}", models=dict(GEMINI),
                                          arms=("isolated",), answer_format=fmt))
                engine.run()
                sent = [_sent_chars(k) for k in api.calls]
                self.assertEqual(len(sent), 2 * 5)
                measured = pgg_game.mean_prompt_chars(
                    pgg_game.default_frame(), "isolated", GameParams(rounds=2), [CARD_A, CARD_B],
                    isolated_frame="one_shot", answer_format=fmt)
                self.assertAlmostEqual(measured, sum(sent) / len(sent), places=9)


class DeadlineEstimateFollowsTheAnswerFormat(ResumeBase):
    cfg1 = DeadlineEstimate.cfg1
    hang_third = DeadlineEstimate.hang_third

    def test_deadline_prompt_chars_are_those_sent(self):
        lengths = {}
        for fmt in pgg_game.ANSWER_FORMATS:
            with self.subTest(fmt=fmt):
                api = CostAPI(cost=0.0001)
                release = self.hang_third(api)
                engine = Engine(self.cfg1(run=f"d_{fmt}", answer_format=fmt))
                with mock.patch.object(pgg_game, "_prompt_chars",
                                       wraps=pgg_game._prompt_chars) as measure:
                    engine.run()
                [event] = [json.loads(x) for x in
                           (self.tmp / "runs" / f"d_{fmt}" / "raw_calls.jsonl").read_text()
                           .splitlines() if json.loads(x).get("event")
                           == "pgg_deadline_cost_estimated"]
                # the abandoned 3rd request is sent again as the 4th: same messages
                self.assertEqual(event["prompt_chars"], _sent_chars(api.calls[2]))
                self.assertEqual(event["prompt_tokens_estimated"],
                                 -(-event["prompt_chars"] // pgg_game.DEADLINE_CHARS_PER_TOKEN))
                # the one measure, with the run's answer_format
                self.assertEqual([c.args[2] for c in measure.call_args_list], [fmt])
                lengths[fmt] = event["prompt_chars"]
                release.set()
        self.assertEqual(len(set(lengths.values())), 3, lengths)


if __name__ == "__main__":
    unittest.main()
