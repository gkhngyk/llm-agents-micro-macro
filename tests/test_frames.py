"""Mock tests of task #61: frame files (C1), story-arm plumbing (C2), rule comprehension (C4)
and the cost gate / hard cap (C5). No network, no ../.env, no game call.

(a) frames/abstract_v2.json renders the prompts of c0b91f5 character for
character (frozen copy, and the prompts in the pilot v2 raw log where that
directory exists); (b) abstract_v3 differs only in the system message and the
isolated question; (c) frame files are validated (unknown / missing
placeholders, numbers in the text, ...) and a run with an invalid one does not
start; (d) cells are card x model x frame: a model outside a frame never plays
it, the frame is in unit labels, session ids, seeds and the run order; rows
carry the frame and its sha256, and --resume refuses a changed frame file;
(e) rule comprehension: a wrong answer is a valid row, only an answer outside
the schema is invalid; (f) the expected-cost gate (4.5 USD) and the hard cap
(6 USD); per-frame dry run with scaled prompt tokens.
"""

import contextlib
import io
import json
import re
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_pgg_game import CARD_A, CARD_B, ROOT, FakeAPI, _payload  # noqa: E402
from test_pgg_guards import PILOT_CARDS_V2, PILOT_CONFIG, CostAPI, GuardTestBase  # noqa: E402
from test_pgg_resume import _killer, _rows, _tree  # noqa: E402

import legacy_prompts_c0b91f5 as legacy  # noqa: E402
import llm_client  # noqa: E402
import pgg_cost  # noqa: E402
import pgg_frames  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Card, Engine, GameParams, RoundRecord, RunStopped  # noqa: E402

FRAMES = ROOT / "frames"
V2 = FRAMES / "abstract_v2.json"
V3 = FRAMES / "abstract_v3.json"
STORY = ROOT / "tests" / "fixtures" / "story_fixture.json"
MINIPILOT_CONFIG = ROOT / "configs" / "minipilot.json"
MODELS3 = {"deepseek": "deepseek/deepseek-v4.1-flash", "mistral": "mistralai/mistral-large-4-0",
           "gpt": "openai/gpt-6-luna"}
SYSTEM_SENTENCE = "You are a participant in a decision-making experiment. "
PILOT_V2_DIR = (Path(json.loads(PILOT_CONFIG.read_text(encoding="utf-8"))["runs_dir"])
                / "pilot_v2_20261005")

PARAM_SETS = [GameParams(), GameParams(group_size=3, rounds=5, endowment=10, mpcr=0.5),
              GameParams(group_size=5, rounds=7, endowment=30, mpcr=0.3, punish_cost=2,
                         punish_impact=4, max_punish=6)]
CARDS = [CARD_A, Card("x", "y", "Where you grew up, people {braces} stay literal: 7 days."),
         Card("long", "value", "A 21-year-old student.\nSecond line, with 'quotes' and \"more\".")]


def _history(p: GameParams, condition: str, n_rounds: int) -> list:
    """A history with varied numbers (fractions in the earnings, punishments under P)."""
    out = []
    for r in range(1, n_rounds + 1):
        c = [(3 * r + 7 * j) % (p.endowment + 1) for j in range(p.group_size)]
        rec = RoundRecord(r, c, pgg_game.project_payoffs(p, c),
                          final_earnings=pgg_game.project_payoffs(p, c))
        if condition == "P":
            rec.punishment = [[(i + j + r) % 3 if i != j else 0 for j in range(p.group_size)]
                              for i in range(p.group_size)]
            rec.final_earnings, rec.cost_paid, rec.received = pgg_game.apply_punishment(
                p, rec.round_earnings, rec.punishment)
        out.append(rec)
    return out


def _main(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = pgg_game.main(list(argv))
    return code, out.getvalue(), err.getvalue()


# --------------------------------------------------------------------------
# (a) abstract_v2 == the prompts of c0b91f5, character for character
# --------------------------------------------------------------------------

class AbstractV2Equality(unittest.TestCase):
    def test_every_prompt_equals_the_frozen_code(self):
        v2 = pgg_frames.load_frame(V2)
        n = 0
        for p in PARAM_SETS:
            for card in CARDS:
                self.assertEqual(pgg_game.system_message(card), legacy.system_message(card))
                for cond in ("N", "P"):
                    for single in (False, True):
                        self.assertEqual(pgg_game.rules_text(p, cond, single_round=single),
                                         legacy.rules_text(p, cond, single_round=single))
                    for k in range(p.rounds):
                        hist = _history(p, cond, k)
                        for me in range(p.group_size):
                            self.assertEqual(
                                pgg_game.contribution_messages(p, cond, card, hist, me, k + 1),
                                legacy.contribution_messages(p, cond, card, hist, me, k + 1))
                            self.assertEqual(v2.contribution_messages(p, cond, card, hist, me, k + 1),
                                             legacy.contribution_messages(p, cond, card, hist, me, k + 1))
                            n += 2
                            if cond == "P":
                                c = [(5 * me + k) % (p.endowment + 1)] * p.group_size
                                e = pgg_game.project_payoffs(p, c)[me] + 0.4
                                self.assertEqual(
                                    pgg_game.punishment_messages(p, card, hist, me, k + 1, c, e),
                                    legacy.punishment_messages(p, card, hist, me, k + 1, c, e))
                                n += 1
                for frame in ("one_shot", "repeated"):
                    for x in range(0, p.endowment + 1, 5):
                        self.assertEqual(pgg_game.isolated_messages(p, card, x, frame),
                                         legacy.isolated_messages(p, card, x, frame))
                        n += 1
        self.assertGreater(n, 1000)

    def test_schemas_and_number_format_unchanged(self):
        p = GameParams()
        self.assertEqual(pgg_game.contribution_schema(p, True), {
            "type": "object", "required": ["contribution"], "properties": {
                "contribution": {"type": "integer", "minimum": 0, "maximum": 20},
                "rationale": {"type": "string",
                              "description": "One or two sentences on why you chose this."}}})
        self.assertEqual(pgg_game.punishment_schema(p, [2, 3, 4], False)["properties"]
                         ["punishments"]["description"],
                         "Punishment points per other player, keyed by player number.")
        for x in (12.0, 24.4, 0.4, 1.6000000000000001, 7.123456):
            self.assertEqual(pgg_game._num(x), legacy._num(x))
        for cs in ([0, 0, 0, 0], [20, 13, 7, 1], [3, 3, 3]):
            self.assertEqual(pgg_frames._project_share(p, cs), pgg_game.project_share(p, cs))

    def test_default_frame_is_abstract_v2_with_its_sha256(self):
        f = pgg_game.default_frame()
        self.assertEqual((f.name, Path(f.path)), ("abstract_v2", V2))
        self.assertEqual(f.sha256, pgg_frames.hashlib.sha256(V2.read_bytes()).hexdigest())
        self.assertFalse(f.has_comprehension)
        self.assertEqual(f.isolated_frames, ("one_shot", "repeated"))

    def test_schema_suffix_equals_llm_client(self):
        msgs = [{"role": "user", "content": "x"}]
        aug = llm_client.augment_with_schema(msgs, {"a": 1})
        self.assertEqual(aug[-1]["content"], "x" + pgg_game.SCHEMA_PROMPT_SUFFIX + '{"a": 1}')

    def test_pilot_config_records_are_unchanged(self):
        """configs/pilot.json: no frame in the config record, ids and seeds as before."""
        settings = pgg_game.settings_from_args(pgg_game.build_parser().parse_args(
            ["--config", str(PILOT_CONFIG), "--cards", str(PILOT_CARDS_V2)]))
        cfg = pgg_game.run_config("pilot_v2_x", settings, dict(llm_client.MODELS_PILOT_V2),
                                  {"results_dir": Path("/nonexistent/abs/dir")})
        self.assertIsNone(cfg.frames)
        engine = Engine.__new__(Engine)              # no validate (the dir does not exist)
        engine.cfg, engine.llm = cfg, pgg_game.OfflineLLM()
        engine.frames = cfg.load_frames()
        engine.max_tokens = 16000
        rec = engine.config_record()
        self.assertNotIn("frame_setup", rec)
        self.assertNotIn("expected_cost_gate_usd", rec)
        specs = engine.unit_specs()
        self.assertTrue(all(s.frame == "abstract_v2" for s in specs))
        self.assertTrue(all(s.label.count("|") == 5 for s in specs))
        self.assertTrue(all(s.session_id.endswith(("-000", "-001")) for s in specs))


@unittest.skipUnless((PILOT_V2_DIR / "raw_calls.jsonl").is_file(),
                     "pilot_v2_20261005 run directory not on this machine")
class PilotV2RawLogEquality(unittest.TestCase):
    """Every prompt sent in pilot v2 is rendered again, character for character."""

    def test_every_logged_prompt_is_reproduced(self):
        p = GameParams()
        cards = {(c.card_id, c.style): c
                 for c in pgg_game.load_cards(PILOT_CARDS_V2, ["Boston", "Riyadh"])}
        contrib: dict = {}
        for line in (PILOT_V2_DIR / "pilot_v2_20261005.jsonl").read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue                       # a cut-off line
            if r.get("step") == "contribute":
                contrib.setdefault((r["session_id"], r.get("segment", 0), r["round"]),
                                   {})[r["agent_id"]] = r["contribution"]

        def history(sid, seg, rnd):
            out = []
            for rr in range(1, rnd):
                segs = [s for (x, s, y), v in contrib.items()
                        if x == sid and y == rr and s <= seg and len(v) == 4]
                if not segs:
                    return None
                c = [contrib[(sid, max(segs), rr)][a] for a in range(1, 5)]
                out.append(RoundRecord(rr, c, pgg_game.project_payoffs(p, c),
                                       final_earnings=pgg_game.project_payoffs(p, c)))
            return out

        seg, n, missing = 0, 0, 0
        for line in (PILOT_V2_DIR / "raw_calls.jsonl").read_text().splitlines():
            rec = json.loads(line)
            if rec.get("event") in ("pgg_run_start", "pgg_run_resume"):
                seg = rec.get("segment", 0)
            if rec.get("event") or "messages" not in rec:
                continue
            call = rec.get("call") or pgg_game._call_from_messages(rec["messages"])
            parts = rec["session_id"].split("-")
            card = cards[(parts[3], parts[4])]
            if call["step"] == "isolated":
                want = pgg_game.isolated_messages(p, card, call["others_mean"], "repeated")
            else:
                hist = history(rec["session_id"], call.get("segment", seg), call["round"])
                if hist is None:
                    missing += 1
                    continue
                want = pgg_game.contribution_messages(p, "N", card, hist, call["agent_id"] - 1,
                                                      call["round"])
            self.assertEqual(rec["messages"], want, rec["session_id"])
            n += 1
        self.assertGreater(n, 1800)
        self.assertEqual(missing, 0)


# --------------------------------------------------------------------------
# (b) abstract_v3: only the system message and the isolated question differ
# --------------------------------------------------------------------------

class AbstractV3(unittest.TestCase):
    def setUp(self):
        self.v2, self.v3 = pgg_frames.load_frame(V2), pgg_frames.load_frame(V3)

    def test_system_message_is_the_card_alone(self):
        for card in CARDS:
            msg = self.v3.system_message(card)
            self.assertEqual(msg, {"role": "system", "content": card.text})
            self.assertNotIn("participant", msg["content"])
            self.assertNotIn("decision-making experiment", msg["content"])
            self.assertIn(SYSTEM_SENTENCE, self.v2.system_message(card)["content"])

    def test_rules_history_round_and_punishment_are_the_v2_texts(self):
        for p in PARAM_SETS:
            for cond in ("N", "P"):
                self.assertEqual(self.v3.rules_text(p, cond), self.v2.rules_text(p, cond))
                for k in (0, 1, p.rounds - 1):
                    hist = _history(p, cond, k)
                    a = self.v3.contribution_messages(p, cond, CARD_A, hist, 1, k + 1)
                    b = self.v2.contribution_messages(p, cond, CARD_A, hist, 1, k + 1)
                    self.assertEqual(a[1], b[1])
                    self.assertNotEqual(a[0], b[0])
            hist = _history(p, "P", 2)
            self.assertEqual(self.v3.punishment_messages(p, CARD_A, hist, 0, 3, [1] * p.group_size,
                                                         20.5, 20)[1],
                             self.v2.punishment_messages(p, CARD_A, hist, 0, 3, [1] * p.group_size,
                                                         20.5, 20)[1])
        self.assertEqual(self.v3.data["response"], self.v2.data["response"])

    def test_isolated_question_names_a_fixed_round(self):
        p = GameParams()
        user = self.v3.isolated_messages(p, CARD_A, 15, "fixed_round", 5)[1]["content"]
        self.assertIn("This is round 5 of 10.", user)
        self.assertNotIn("neither the first nor the last", user)
        self.assertIn("In the previous round the other 3 players of your group contributed, "
                      "on average, 15 points each.", user)
        repeated = self.v2.isolated_messages(p, CARD_A, 15, "repeated")[1]["content"]
        self.assertIn("neither the first nor the last", repeated)
        # the only difference: the first sentence of the question
        self.assertEqual(user.replace("This is round 5 of 10.", "X"),
                         repeated.replace("Consider a round of this 10-round game that is "
                                          "neither the first nor the last round.", "X"))
        self.assertIn("This is round 7 of 9.",
                      self.v3.isolated_messages(GameParams(rounds=9), CARD_A, 0, "fixed_round",
                                                7)[1]["content"])
        self.assertEqual(self.v3.isolated_frames, ("fixed_round",))
        with self.assertRaises(ValueError):
            self.v3.isolated_messages(p, CARD_A, 5, "repeated")
        with self.assertRaises(ValueError):
            self.v3.isolated_messages(p, CARD_A, 5, "fixed_round")      # no round number

    def test_comprehension_questions_and_key(self):
        p = GameParams()
        self.assertEqual(self.v3.comprehension_key(p), {"q1": 28, "q2": -6})
        user = self.v3.comprehension_messages(p, CARD_A)[1]["content"]
        self.assertTrue(user.startswith(self.v3.rules_text(p, "N") + "\n\nRULE CHECK\n"))
        self.assertIn("1. Suppose that in a round you contribute 8 points and the other 3 "
                      "players contribute 4, 12 and 16 points. What are your total earnings in "
                      "that round?", user)
        self.assertIn("2. Suppose that the contributions of the other players stay the same. "
                      "If you contribute 10 more points", user)
        self.assertNotIn("HISTORY", user)
        self.assertNotIn("ROUND", user)
        # the key follows the parameters (never written in the file)
        self.assertEqual(self.v3.comprehension_key(GameParams(endowment=30, mpcr=0.5)),
                         {"q1": 42, "q2": -5})
        with self.assertRaisesRegex(ValueError, "not a whole number"):
            self.v3.comprehension_key(GameParams(mpcr=0.35))
        with self.assertRaisesRegex(ValueError, "others"):
            self.v3.comprehension_key(GameParams(group_size=3))
        schema = self.v3.comprehension_schema(True)
        self.assertEqual(schema["required"], ["q1", "q2"])
        self.assertEqual(schema["properties"]["q1"]["type"], "integer")
        self.assertNotIn("q1", self.v3.comprehension_schema(False)["properties"].keys() - {"q1"})


# --------------------------------------------------------------------------
# (c) frame file validation
# --------------------------------------------------------------------------

class FrameValidation(unittest.TestCase):
    def broken(self, edit) -> str:
        raw = json.loads(V3.read_text())
        edit(raw)
        with self.assertRaises(pgg_frames.FrameError) as cm:
            pgg_frames.validate_frame(raw, "test")
        return str(cm.exception)

    def test_committed_frames_and_fixture_are_valid(self):
        for path in (V2, V3, STORY):
            pgg_frames.load_frame(path)

    def test_unknown_placeholder(self):
        msg = self.broken(lambda r: r.update(contribute=r["contribute"] + " {payoff}"))
        self.assertIn("contribute: unknown placeholder(s) ['payoff']", msg)
        msg = self.broken(lambda r: r.update(system="{card} {n}"))
        self.assertIn("system: unknown placeholder(s) ['n']", msg)

    def test_missing_placeholder(self):
        msg = self.broken(lambda r: r.update(system="Just text."))
        self.assertIn("system: missing placeholder {card}", msg)
        msg = self.broken(lambda r: r["isolated"]["fixed_round"].update(
            question="QUESTION\nThe others gave {others_mean}. How many of {endowment}?"))
        self.assertIn("isolated.fixed_round.question: missing placeholder {round_no}", msg)
        msg = self.broken(lambda r: r["comprehension"].update(prompt="1. {q1}"))
        self.assertIn("comprehension.prompt: missing placeholder {q2}", msg)
        msg = self.broken(lambda r: r.update(rules=[x for x in r["rules"] if "P" not in
                                                    x.get("when", [])]))
        self.assertIn("{max_punish}", msg)

    def test_numbers_must_come_from_the_parameters(self):
        msg = self.broken(lambda r: r["rules"].append({"text": "- You get 20 points."}))
        self.assertIn("numbers written in the text ['20']", msg)
        msg = self.broken(lambda r: r["rules"].append({"text": "- Factor 1.6, share 0,4."}))
        self.assertIn("'1.6'", msg)
        self.assertIn("'0,4'", msg)
        # a lone 0 and a "1. " enumeration at a line start are allowed
        pgg_frames.validate_frame(json.loads(V3.read_text()))
        self.assertEqual(pgg_frames.literal_digits("from 0 to {endowment}\n1. {q1}\n2. x"), [])

    def test_syntax_sections_and_keys(self):
        self.assertIn("bad braces", self.broken(lambda r: r.update(system="{card")))
        self.assertIn("plain name", self.broken(lambda r: r.update(system="{card:>10}")))
        self.assertIn("plain name", self.broken(lambda r: r.update(system="{} {card}")))
        self.assertIn("punish: missing", self.broken(lambda r: r.pop("punish")))
        self.assertIn("history.round_P: missing", self.broken(lambda r: r["history"].pop("round_P")))
        self.assertIn("story: unknown key", self.broken(lambda r: r.update(story="x")))
        self.assertIn("unknown isolated frame", self.broken(
            lambda r: r["isolated"].update(twice=r["isolated"]["fixed_round"])))
        self.assertIn("schema: must be 1", self.broken(lambda r: r.update(schema=2)))
        self.assertIn("unique id", self.broken(
            lambda r: r["comprehension"]["questions"][1].update(id="q1")))
        self.assertIn("own_change takes", self.broken(
            lambda r: r["comprehension"]["questions"][1]["answer"].update(delta=0)))
        self.assertIn("reserved", self.broken(
            lambda r: r["response"].update(decision_key="rationale")))

    def test_invalid_frame_stops_the_run_before_any_call(self):
        raw = json.loads(V3.read_text())
        raw["contribute"] += " {unknown_thing}"
        with self.subTest("RunConfig / Engine"):
            tmp = Path(self.enterContext(_tmpdir()))
            bad = tmp / "bad.json"
            bad.write_text(json.dumps(raw))
            cfg = pgg_game.RunConfig(run="x", cards=[CARD_A], models={"m1": "v/m1"},
                                     results_dir=tmp / "out", frames={"abstract_v3": ["m1"]},
                                     frame_files={"abstract_v3": str(bad)},
                                     isolated_frame="fixed_round")
            with self.assertRaisesRegex(pgg_frames.FrameError, "unknown_thing"):
                cfg.validate()
            self.assertFalse((tmp / "out").exists())


class _tmpdir:
    def __enter__(self):
        import tempfile
        self._t = tempfile.TemporaryDirectory()
        return self._t.name

    def __exit__(self, *exc):
        self._t.cleanup()


# --------------------------------------------------------------------------
# (d) cells card x model x frame, rows, resume
# --------------------------------------------------------------------------

class FrameBase(GuardTestBase):
    def setUp(self):
        super().setUp()
        (self.tmp / "runs").mkdir()
        self.story = self.tmp / "story.json"
        shutil.copyfile(STORY, self.story)

    def fcfg(self, **kw):
        base = dict(run="fr", results_dir=None, runs_dir=self.tmp / "runs",
                    cards=[CARD_A, CARD_B], models={"deepseek": "v/ds", "mistral": "v/mi",
                                                    "gpt": "v/gpt"},
                    frames={"abstract_v3": ["deepseek", "mistral", "gpt"],
                            "story": ["deepseek", "mistral"]},
                    frame_files={"story": str(self.story)}, isolated_frame="fixed_round",
                    arms=("group", "isolated"), params=GameParams(rounds=2), groups_per_cell=1,
                    isolated_reps=1, isolated_points=(0, 10), budget_usd=1.0,
                    comprehension=True, isolated_round_no=2)
        base.update(kw)
        return self.cfg(**base)

    def rows(self, run="fr"):
        return _rows(self.tmp / "runs" / run / f"{run}.jsonl")


class ModelFrameCells(FrameBase):
    def test_gpt_never_plays_the_story(self):
        self.use(CostAPI())
        engine = Engine(self.fcfg())
        specs = engine.unit_specs()
        # 2 cards x (3 + 2) model-frame pairs x (1 group + 1 schedule)
        self.assertEqual(len(specs), 20)
        pairs = {(s.model_key, s.frame) for s in specs}
        self.assertEqual(pairs, {("deepseek", "abstract_v3"), ("mistral", "abstract_v3"),
                                 ("gpt", "abstract_v3"), ("deepseek", "story"),
                                 ("mistral", "story")})
        self.assertTrue(all(s.label.endswith("|" + s.frame) for s in specs))
        self.assertTrue(all(s.session_id.endswith("-" + s.frame) for s in specs))
        # round-robin: every block of len(cards) units has every card
        for i in range(0, len(specs), 2):
            self.assertEqual({s.card.card_id for s in specs[i:i + 2]}, {"cityA", "cityB"})
        engine.run()
        rows = self.rows()
        self.assertFalse([r for r in rows if r["model_key"] == "gpt" and r["frame"] == "story"])
        self.assertTrue([r for r in rows if r["model_key"] == "gpt"])
        story_calls = [c for c in self.api.calls if "[fixture" in c["messages"][-1]["content"]]
        self.assertTrue(story_calls)
        self.assertNotIn("v/gpt", {c["model"] for c in story_calls})
        # every row: frame, frame_id, frame_sha256
        sha = {"abstract_v3": pgg_frames.load_frame(V3).sha256,
               "story": pgg_frames.load_frame(self.story).sha256}
        for r in rows:
            self.assertEqual(r["frame_sha256"], sha[r["frame"]])
            self.assertEqual(r["frame_id"], {"abstract_v3": "abstract_v3",
                                             "story": "story_fixture"}[r["frame"]])
        # story prompts come from the story file, abstract ones from abstract_v3
        for c in self.api.calls:
            system = c["messages"][0]["content"]
            self.assertTrue(system.startswith("[fixture system] ") or system in
                            (CARD_A.text, CARD_B.text), system)
        # the story's decision key is its own
        story_rows = [r for r in rows if r["frame"] == "story" and r["step"] != "comprehension"]
        self.assertTrue(all(isinstance(r["contribution"], int) for r in story_rows))
        summary = json.loads((self.tmp / "runs" / "fr" / "fr_summary.json").read_text())
        self.assertEqual(summary["frames"]["story"]["models"], ["deepseek", "mistral"])
        self.assertEqual(summary["config"]["frame_setup"]["frames"]["story"]["sha256"],
                         sha["story"])
        self.assertEqual(summary["invalid_limit_per_model"], None)

    def test_calibration_script_reads_rows_with_frames(self):
        import pgg_cost_calibrate
        self.use(CostAPI())
        Engine(self.fcfg()).run()
        rows = self.rows()
        for r in rows:
            self.assertEqual(pgg_cost_calibrate.unit_key(r), r["unit"])
        self.assertEqual({pgg_cost_calibrate.call_kind(r) for r in rows},
                         {"contribute_N", "isolated", "comprehension"})

    def test_frame_is_in_seeds_and_order(self):
        engine = Engine(self.fcfg())
        seeds = {}
        self.use(CostAPI())
        engine.run()
        for r in self.rows():
            seeds.setdefault((r["model_key"], r["card_id"], r["step"], r["round"],
                              r["agent_id"], r.get("others_mean")), set()).add(r["seed"])
        both = [v for k, v in seeds.items() if k[0] != "gpt"]
        self.assertTrue(both and all(len(v) == 2 for v in both))     # one seed per frame
        self.assertEqual(engine.seed_for("deepseek", "story", "cityA"),
                         llm_client.stable_seed("pgg", "fr", "deepseek", "story", "cityA"))

    def test_frames_config_errors(self):
        with self.assertRaisesRegex(ValueError, "not among the run's models"):
            Engine(self.fcfg(frames={"abstract_v3": ["deepseek", "mistral", "gpt", "claude"]}))
        with self.assertRaisesRegex(ValueError, "models in no frame: \\['gpt'\\]"):
            Engine(self.fcfg(frames={"abstract_v3": ["deepseek", "mistral"]}, frame_files=None))
        with self.assertRaisesRegex(ValueError, "no isolated question 'repeated'"):
            Engine(self.fcfg(isolated_frame="repeated"))
        # task #73: abstract_v2 (frozen, no "kind") is only the default of a config
        # without frames; named under frames it is refused for its missing kind ...
        with self.assertRaisesRegex(ValueError, "frame 'abstract_v2' .* has no \"kind\""):
            Engine(self.fcfg(frames={"abstract_v2": ["deepseek", "mistral", "gpt"]},
                             frame_files=None, isolated_frame="repeated"))
        # ... and a copy with kind abstract has no comprehension questions
        v2 = json.loads(V2.read_text())
        v2["kind"] = "abstract"
        (self.tmp / "v2_kind.json").write_text(json.dumps(v2))
        with self.assertRaisesRegex(ValueError, "no comprehension questions"):
            Engine(self.fcfg(frames={"abstract_v2": ["deepseek", "mistral", "gpt"]},
                             frame_files={"abstract_v2": str(self.tmp / "v2_kind.json")},
                             isolated_frame="repeated"))
        with self.assertRaisesRegex(ValueError, "placeholder"):
            Engine(self.fcfg(frame_files={"story": "<TBD_PREREG: story file>"}))
        with self.assertRaisesRegex(ValueError, "frame_files needs frames"):
            Engine(self.fcfg(frames=None, frame_files={"story": str(self.story)},
                             comprehension=False, isolated_frame="one_shot"))
        with self.assertRaisesRegex(ValueError, "isolated_round_no"):
            Engine(self.fcfg(isolated_round_no=1))
        # model slugs work as well as keys
        self.assertEqual(pgg_game.resolve_frames({"story": ["v/ds", "mistral"]},
                                                 {"deepseek": "v/ds", "mistral": "v/mi"}),
                         {"story": ["deepseek", "mistral"]})

    def test_isolated_round_no_reaches_the_prompt_and_the_row(self):
        self.use(CostAPI())
        Engine(self.fcfg(isolated_round_no=7, params=GameParams(rounds=8),
                         arms=("isolated",))).run()
        iso = [c for c in self.api.calls if FakeAPI.parse(c)[0] == "isolated"]
        self.assertTrue(iso)
        for c in iso:
            user = c["messages"][-1]["content"]
            self.assertTrue("This is round 7 of 8." in user or "Sitting 7 of 8." in user, user)
        rows = [r for r in self.rows() if r["step"] == "isolated"]
        self.assertEqual({(r["isolated_frame"], r["isolated_round_no"]) for r in rows},
                         {("fixed_round", 7)})


class FrameResume(FrameBase):
    def interrupted(self, at=30):
        api = CostAPI()
        api.content_fn = _killer(api, at)
        self.use(api)
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            Engine(self.fcfg()).run()

    def test_resume_with_the_same_frames_goes_on(self):
        self.interrupted()
        self.use(CostAPI())
        engine = Engine(self.fcfg())
        plan = engine.resume_plan()
        self.assertEqual(plan.problems, [])
        self.assertTrue(any("frame sha256 of the rows" in c for c in plan.config_checked))
        engine.run(resume=True)
        summary = json.loads((self.tmp / "runs" / "fr" / "fr_summary.json").read_text())
        self.assertEqual(summary["units"]["n_complete"], 20)

    def test_changed_frame_file_is_refused(self):
        self.interrupted()
        raw = json.loads(self.story.read_text())
        raw["description"] += " (edited)"
        self.story.write_text(json.dumps(raw))
        before = _tree(self.tmp / "runs" / "fr")
        self.use(CostAPI())
        engine = Engine(self.fcfg())
        problems = "\n".join(engine.resume_plan().problems)
        self.assertIn("frame 'story': rows have frame 'story' with sha256", problems)
        self.assertIn("config frame_setup", problems)
        with self.assertRaisesRegex(ValueError, "not resumed, no call made.*sha256"):
            engine.run(resume=True)
        self.assertEqual(self.api.calls, [])             # no call of the resumed segment
        self.assertEqual(_tree(self.tmp / "runs" / "fr"), before)

    def test_changed_default_frame_is_refused_for_a_run_without_frames(self):
        """A run without "frames" (as pilot v2) has rows with abstract_v2's sha256."""
        cfg = dict(frames=None, frame_files=None, comprehension=False, isolated_frame="repeated",
                   models={"m1": "v/m1"})
        api = CostAPI()
        api.content_fn = _killer(api, 6)
        self.use(api)
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            Engine(self.fcfg(**cfg)).run()
        rows = self.rows()
        self.assertEqual({(r["frame"], r["frame_sha256"]) for r in rows},
                         {("abstract_v2", pgg_game.default_frame().sha256)})
        raw = json.loads(V2.read_text())
        raw["description"] += " (edited)"
        raw["kind"] = "abstract"      # task #73: an edited copy is no longer the legacy file
        edited = self.tmp / "abstract_v2.json"
        edited.write_text(json.dumps(raw))
        with mock.patch.object(pgg_game, "default_frame",
                               lambda: pgg_frames.load_frame(edited)):
            engine = Engine(self.fcfg(**cfg))
            self.assertIn("a frame file must not change within a run",
                          "\n".join(engine.resume_plan().problems))
            with self.assertRaisesRegex(ValueError, "not resumed"):
                engine.run(resume=True)


# --------------------------------------------------------------------------
# (e) rule comprehension
# --------------------------------------------------------------------------

def _comp_reply(replies):
    """content_fn: the rule-comprehension calls get replies[0], replies[1], ... in order."""
    queue = list(replies)

    def fn(kwargs, content):
        if FakeAPI.parse(kwargs)[0] == "comprehension" and queue:
            return queue.pop(0)
        return content
    return fn


class Comprehension(FrameBase):
    def one(self, **kw):
        return self.fcfg(models={"deepseek": "v/ds"}, frames={"abstract_v3": ["deepseek"]},
                         frame_files=None, cards=[CARD_A], **kw)

    def test_wrong_answer_is_valid_schema_violation_is_re_requested(self):
        replies = [
            _payload({"q1": 30, "q2": -6, "rationale": "r"}),     # agent 1: q1 wrong, valid
            _payload({"q1": "28", "q2": -6}),                     # agent 2: string -> invalid
            _payload({"q1": 28, "q2": -6}),                       #   re-request: correct
            _payload({"q1": 28.0, "q2": 6}),                      # agent 3: float -> invalid
            _payload({"q1": 28}),                                 #   missing q2 -> invalid
            _payload({"q1": 28, "q2": 6}),                        #   valid, q2 wrong
            _payload({"q1": 1, "q2": 1}),                         # agent 4: both wrong, valid
            _payload({"q1": 28, "q2": -6}),                       # schedule: correct
        ]
        self.use(CostAPI(content_fn=_comp_reply(replies)))
        Engine(self.one()).run()
        rows = self.rows()
        comp = [r for r in rows if r["step"] == "comprehension"]
        self.assertEqual(len(comp), 5)                            # 4 agents + 1 schedule
        g = {r["agent_id"]: r for r in comp if r["arm"] == "group"}
        self.assertEqual([(g[a]["comp_q1_answer"], g[a]["comp_q2_answer"]) for a in (1, 2, 3, 4)],
                         [(30, -6), (28, -6), (28, 6), (1, 1)])
        self.assertEqual([(g[a]["comp_q1_correct"], g[a]["comp_q2_correct"]) for a in (1, 2, 3, 4)],
                         [(False, True), (True, True), (True, False), (False, False)])
        self.assertEqual([g[a]["n_invalid"] for a in (1, 2, 3, 4)], [0, 1, 2, 0])
        self.assertEqual({(r["comp_q1_key"], r["comp_q2_key"]) for r in comp}, {(28, -6)})
        self.assertTrue(all(r["round"] == 1 for r in g.values()))
        iso = [r for r in comp if r["arm"] == "isolated"]
        self.assertEqual((iso[0]["round"], iso[0]["comp_n_correct"]), (None, 2))
        # wrong answers stop nothing: the game and the schedule are complete
        self.assertEqual(len([r for r in rows if r["step"] == "contribute"]), 8)
        self.assertEqual(len([r for r in rows if r["step"] == "isolated"]), 2)
        summary = json.loads((self.tmp / "runs" / "fr" / "fr_summary.json").read_text())
        c = summary["comprehension"]["per_model_frame"]["deepseek"]["abstract_v3"]
        self.assertEqual((c["n"], c["n_q1_correct"], c["n_q2_correct"], c["n_all_correct"]),
                         (5, 3, 3, 2))
        self.assertAlmostEqual(c["q1_correct_rate"], 0.6)
        self.assertAlmostEqual(c["all_correct_rate"], 0.4)
        self.assertEqual(summary["comprehension"]["answer_keys"], {"abstract_v3": {"q1": 28, "q2": -6}})
        # task #73: rule-comprehension invalids are counted apart, outside the cap
        self.assertEqual(summary["per_model"]["v/ds"]["n_invalid"], 0)
        self.assertEqual(summary["per_model"]["v/ds"]["n_comp_invalid"], 3)
        self.assertEqual((c["n_invalid"], c["n_missing"]), (3, 0))

    def test_asked_once_per_agent_before_round_one_not_in_the_game_context(self):
        self.use(CostAPI())
        Engine(self.one(arms=("group",))).run()
        kinds = [FakeAPI.parse(c)[0] for c in self.api.calls]
        self.assertEqual(kinds, ["comprehension"] * 4 + ["contribute"] * 8)
        for c in self.api.calls[:4]:
            user = c["messages"][-1]["content"]
            self.assertIn("RULE CHECK", user)
            self.assertNotIn("HISTORY", user)
        for c in self.api.calls[4:]:
            self.assertNotIn("RULE CHECK", c["messages"][-1]["content"])

    def test_resume_after_round_one_does_not_ask_again(self):
        api = CostAPI()
        api.content_fn = _killer(api, 10)                 # in round 2 (4 comp + 4 + 2)
        self.use(api)
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            Engine(self.one(arms=("group",))).run()
        self.use(CostAPI())
        engine = Engine(self.one(arms=("group",)))
        engine.run(resume=True)
        self.assertEqual([FakeAPI.parse(c)[0] for c in self.api.calls], ["contribute"] * 4)
        valid = engine.valid_rows()
        self.assertEqual(len([r for r in valid if r["step"] == "comprehension"]), 4)
        self.assertEqual(len(valid), 12)

    def test_off_by_default_and_counted_in_the_plan(self):
        self.use(CostAPI())
        Engine(self.one(comprehension=False)).run()
        self.assertNotIn("comprehension", [FakeAPI.parse(c)[0] for c in self.api.calls])
        cfg = self.one()
        self.assertEqual(cfg.planned_calls_per_model("deepseek"), 8 + 2 + 4 + 1)


# --------------------------------------------------------------------------
# (f) cost gate 4.5 USD, hard cap 6 USD, per-frame dry run
# --------------------------------------------------------------------------

class CostGateAndCap(FrameBase):
    def known(self, **kw):
        return self.fcfg(models=dict(MODELS3), **kw)

    def test_gate_stops_a_run_before_any_call(self):
        engine = Engine(self.known(expected_cost_gate_usd=0.0001))
        est = engine.design_estimate()
        self.assertGreater(est["total_cost_usd"], 0.0001)
        with self.assertRaisesRegex(ValueError, "expected_cost_gate_usd=0.0001.*not started"):
            engine.run()
        self.create.assert_not_called()
        self.assertFalse((self.tmp / "runs" / "fr").exists())
        # below the gate: runs
        self.use(CostAPI())
        Engine(self.known(expected_cost_gate_usd=4.5)).run()
        self.assertTrue(self.api.calls)

    def test_gate_needs_priced_models(self):
        with self.assertRaisesRegex(ValueError, "cannot be checked"):
            Engine(self.fcfg(expected_cost_gate_usd=4.5)).run()
        self.create.assert_not_called()

    def test_hard_cap_ten_dollars(self):
        # EMIR 3 Part 2 (task #73): the hard cap is 10 USD (was 6), the gate 4.5 USD
        raw = json.loads(MINIPILOT_CONFIG.read_text())
        self.assertEqual(raw["budget_usd"], 10)
        self.assertEqual(raw["expected_cost_gate_usd"], 4.5)
        self.use(CostAPI(cost=1.0))
        engine = Engine(self.known(budget_usd=raw["budget_usd"]))
        with self.assertRaisesRegex(RunStopped, "budget"):
            engine.run()
        self.assertEqual(len(self.api.calls), 10)              # 10 x 1 USD, then no new call
        self.assertAlmostEqual(engine.total_cost, 10.0)
        self.assertEqual(engine.stop_reason, "budget")

    def test_prompt_scales(self):
        p, cards = GameParams(), pgg_game.load_cards(PILOT_CARDS_V2, ["Boston", "Riyadh"])
        v2 = pgg_game.default_frame()
        s2 = pgg_game.prompt_scales(v2, p, cards, isolated_frame="repeated")
        self.assertEqual(s2, {"contribute_N": 1.0, "contribute_P": 1.0, "punish_P": 1.0,
                              "isolated": 1.0})
        v3 = pgg_frames.load_frame(V3)
        s3 = pgg_game.prompt_scales(v3, p, cards, isolated_frame="fixed_round")
        self.assertLess(s3["contribute_N"], 1.0)
        self.assertGreater(s3["contribute_N"], 0.9)
        self.assertLess(s3["isolated"], 1.0)
        self.assertIn("comprehension", s3)
        # the scale is the character ratio of the whole request
        chars = pgg_game.mean_prompt_chars
        self.assertAlmostEqual(
            s3["comprehension"],
            chars(v3, "comprehension", p, cards) / chars(v2, "contribute_N", p, cards))
        # abstract_v2 as a frame gives the numbers of the unscaled estimate
        counts = pgg_cost.call_counts(n_cells=6)
        est = pgg_game.design_estimate(
            models=llm_client.MODELS_PILOT_V2, frame_models={"abstract_v2": list(
                llm_client.MODELS_PILOT_V2)}, frames={"abstract_v2": v2}, n_cells=6, params=p,
            conditions=("N",), arms=("group", "isolated"), groups_per_cell=2, isolated_reps=2,
            n_points=5, isolated_frame="repeated", cards=cards)
        self.assertAlmostEqual(est["total_cost_usd"], pgg_cost.estimate(
            llm_client.MODELS_PILOT_V2, counts)["total_cost_usd"], places=12)

    def test_comprehension_calls_are_counted_and_mistral_is_a_lower_bound(self):
        counts = pgg_cost.call_counts(n_cells=6, comprehension=True)
        self.assertEqual(counts["comprehension"], 6 * 2 * 4 + 6 * 2)
        self.assertNotIn("comprehension", pgg_cost.call_counts(n_cells=6))
        # pilot v2's Mistral entry ("estimate": true, no reasoning): a lower bound
        with mock.patch.object(pgg_cost, "CALIBRATION", pgg_cost.load_calibration(overlays=())):
            m = pgg_cost.model_cost(MODELS3["mistral"], counts, {"comprehension": 0.5})
            self.assertIs(m["lower_bound"], True)
            self.assertIn("comprehension", m["extrapolated_kinds"])
            self.assertEqual(m["scaled_kinds"], {"comprehension": 0.5})
            text = pgg_cost.format_report(pgg_cost.estimate(MODELS3, counts))
            self.assertIn("(tahmin, ALT SINIR;", text)
        self.assertIs(pgg_cost.model_cost(MODELS3["deepseek"], counts)["lower_bound"], False)
        # task #71: the M1 overlay measured Mistral's reasoning, no longer a lower bound
        m = pgg_cost.model_cost(MODELS3["mistral"], counts, {"comprehension": 0.5})
        self.assertIs(m["lower_bound"], False)
        self.assertIn("comprehension", m["extrapolated_kinds"])
        text = pgg_cost.format_report(pgg_cost.estimate(MODELS3, counts))
        self.assertNotIn("ALT SINIR", text)
        self.assertIn("mistral: kalibrasyon M1 tesisat ölçümü tesisat_olcum_20261007", text)

    def dry(self, *extra):
        return _main("--dry-run", "--config", str(MINIPILOT_CONFIG), "--cards",
                     str(PILOT_CARDS_V2), "--cities", "Boston,Riyadh", "--conditions", "N",
                     "--arms", "group,isolated", "--groups-per-cell", "2", "--isolated-reps",
                     "2", "--points", "0,5,10,15,20", "--isolated-frame", "fixed_round", *extra)

    def test_dry_run_one_line_per_frame_and_model(self):
        cfg_path = self.tmp / "mp.json"
        raw = json.loads(MINIPILOT_CONFIG.read_text())
        raw["frame_files"] = {"story": str(self.story)}
        raw.pop("cards_sha256")        # other cards (v2) on purpose: not the locked file
        cfg_path.write_text(json.dumps(raw))
        code, out, err = _main(
            "--dry-run", "--config", str(cfg_path), "--cards", str(PILOT_CARDS_V2),
            "--cities", "Boston,Riyadh", "--conditions", "N", "--arms", "group,isolated",
            "--groups-per-cell", "2", "--isolated-reps", "2", "--points", "0,5,10,15,20",
            "--isolated-frame", "fixed_round",
            "--frames", "abstract_v3=deepseek,mistral,gpt;story=deepseek,mistral")
        self.assertEqual(code, 0, err)
        lines = [x for x in out.splitlines()
                 if re.match(r"^(abstract_v3|story)\s+(deepseek|mistral|gpt)\s", x)]
        self.assertEqual(len(lines), 5)
        self.assertFalse([x for x in lines if x.startswith("story") and " gpt " in x])
        for x in lines:
            self.assertIn("600 çağrı (contribute_N=480, isolated=60, comprehension=60)", x)
        self.assertFalse([x for x in lines if "ALT SINIR" in x])   # Mistral from M1 (task #71)
        self.assertEqual(out.count("mistral: kalibrasyon M1 tesisat ölçümü tesisat_olcum_20261007"), 1)
        self.assertIn("3000 çağrı", out)
        self.assertIn("istem ölçeği (karakter oranı, tahmin): contribute_N x", out)
        self.assertIn("Beklenti kapısı expected_cost_gate_usd=4.5 USD:", out)
        self.assertIn("Sert tavan budget_usd=10 USD", out)
        self.assertIn("Kartlar: ", out)
        self.assertIn("KİLİTSİZ (cards_sha256 yok)", out)
        total = float(re.search(r"^TOPLAM .*?~([0-9.]+) USD \(tahmin", out, re.M).group(1))
        self.assertEqual("GEÇER" in out, total <= 4.5)
        self.create.assert_not_called()

    def test_dry_run_gate_exceeded_is_reported(self):
        cfg_path = self.tmp / "mp.json"
        raw = json.loads(MINIPILOT_CONFIG.read_text())
        raw["expected_cost_gate_usd"] = 0.01
        cfg_path.write_text(json.dumps(raw))
        code, out, err = _main("--dry-run", "--config", str(cfg_path), "--cells", "6",
                               "--conditions", "N", "--arms", "group", "--groups-per-cell", "2",
                               "--isolated-reps", "1", "--points", "0",
                               "--frames", "abstract_v3=deepseek,mistral,gpt")
        self.assertEqual(code, 0, err)
        self.assertIn("AŞILIYOR — gerçek koşu BAŞLAMAZ", out)

    def test_dry_run_with_a_story_file_not_chosen(self):
        # the committed config locks story_A (task #67); a placeholder story file is
        # the state before the user chose a draft
        cfg_path = self.tmp / "mp_unchosen.json"
        raw = json.loads(MINIPILOT_CONFIG.read_text())
        raw["frame_files"]["story"] = "<TBD_PREREG: story frame file chosen by the user>"
        raw.pop("cards_sha256")        # other cards (v2) on purpose: not the locked file
        cfg_path.write_text(json.dumps(raw))
        code, out, err = _main("--dry-run", "--config", str(cfg_path), "--cards",
                               str(PILOT_CARDS_V2), "--cities", "Boston,Riyadh",
                               "--frames", "abstract_v3=deepseek,mistral,gpt;story=deepseek")
        self.assertEqual(code, 0, err)
        self.assertIn("istem ölçeği yok: çerçeve dosyası seçilmedi", out)

    def test_dry_run_invalid_frame_file(self):
        bad = self.tmp / "bad.json"
        raw = json.loads(STORY.read_text())
        raw["system"] = "no card here"
        bad.write_text(json.dumps(raw))
        cfg_path = self.tmp / "mp.json"
        conf = json.loads(MINIPILOT_CONFIG.read_text())
        conf["frame_files"] = {"story": str(bad)}
        cfg_path.write_text(json.dumps(conf))
        code, out, err = _main("--dry-run", "--config", str(cfg_path), "--cells", "2",
                               "--conditions", "N", "--arms", "group", "--groups-per-cell", "1",
                               "--isolated-reps", "1", "--points", "0",
                               "--frames", "abstract_v3=gpt;story=deepseek,mistral")
        self.assertEqual(code, 1)
        self.assertIn("system: missing placeholder {card}", err)


if __name__ == "__main__":
    unittest.main()
