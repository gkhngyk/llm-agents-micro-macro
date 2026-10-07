"""Mock tests of task #67 (EMIR 2, K1 + K2 + config). No network, no ../.env, no game call.

(a) K1 frame lock: frame_files entries {"path", "sha256"}; a file with another
sha256 stops the run (RunConfig / Engine, the CLI's real run) and the dry run;
relative paths are the code directory's. (b) K1 story linter: a frame of kind
"story" with a forbidden root of cerceve_linter (in its texts or in the rendered
prompts) stops the run and the dry run; abstract frames are not linted. (c) K1
dirty code: frames/*.json, configs/*.json and cards/*.json count like *.py
(git checkout and CODE_VERSION.json stamp). (d) K2: the sign sentence of q2 in
abstract_v3 and story_A, answer key 28 / -6; a "+3" (or U+2212 "-3") answer of a
rule-comprehension call is parsed, decisions are parsed as before. (e) rule-
comprehension rows are told apart by step "comprehension". (f) the run name
template "minipilot_{run_date}": resolved at the start of a new run, recorded in
the summary; --resume needs the resolved name.
"""

import hashlib
import json
import re
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_frames import STORY, V2, V3, FrameBase, _comp_reply, _main  # noqa: E402
from test_minipilot import MINIPILOT_CONFIG, MINIPILOT_PROVIDERS  # noqa: E402
from test_pgg_a4_a5 import CodeVersionBase, _git  # noqa: E402
from test_pgg_game import CARD_A, ROOT, FakeAPI, _payload  # noqa: E402
from test_pgg_guards import CostAPI, GuardTestBase  # noqa: E402

import cerceve_linter  # noqa: E402
import llm_client  # noqa: E402
import pgg_frames  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Engine, FrameError, GameParams  # noqa: E402

STORY_A = ROOT / "frames" / "story_A.json"
CARDS_V3 = ROOT / "cards" / "pilot_cards_v3.json"
# EMIR 3 3b (task #73); task #67's sentence was the K2 one below
NEW_SENTENCE = "Give the change as a whole number (it can be positive, zero or negative)."
K2_SENTENCE = "Give the change as a whole number with its sign, for example +3 or -3."


def _sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _story_variant(tmp: Path, edit, name="story_x.json") -> Path:
    """story_A with an edit (raw dict -> None), written to tmp."""
    raw = json.loads(STORY_A.read_text(encoding="utf-8"))
    edit(raw)
    path = tmp / name
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# (a) sha256 lock of the frame files
# --------------------------------------------------------------------------

class FrameLock(FrameBase):
    def locked(self, story_sha=None, v3_sha=None, **kw):
        return self.fcfg(frame_files={
            "abstract_v3": {"path": str(V3), "sha256": v3_sha or _sha(V3)},
            "story": {"path": str(self.story), "sha256": story_sha or _sha(self.story)}}, **kw)

    def test_locked_files_run(self):
        self.use(CostAPI())
        Engine(self.locked()).run()
        rows = self.rows()
        self.assertEqual({(r["frame"], r["frame_sha256"]) for r in rows},
                         {("abstract_v3", _sha(V3)), ("story", _sha(self.story))})

    def test_changed_file_refuses_the_run_before_any_call(self):
        self.use(CostAPI())
        cfg = self.locked()
        # the story file changes after it was locked (one byte)
        self.story.write_bytes(self.story.read_bytes() + b"\n")
        with self.assertRaisesRegex(FrameError, r"frame 'story': sha256 of .* but frame_files "
                                                r"locks .*no run starts"):
            Engine(cfg)
        with self.assertRaisesRegex(FrameError, "frame 'abstract_v3'.*frame_files locks"):
            Engine(self.locked(v3_sha="0" * 64))
        self.create.assert_not_called()
        self.assertFalse((self.tmp / "runs" / "fr").exists())

    def test_entry_forms(self):
        spec = pgg_game.frame_file_spec
        self.assertEqual(spec("s", None), (None, None))
        self.assertEqual(spec("s", "/a/b.json"), ("/a/b.json", None))
        self.assertEqual(spec("s", {"path": "x.json", "sha256": "a" * 64}), ("x.json", "a" * 64))
        self.assertEqual(spec("s", {"path": "x.json"}), ("x.json", None))
        for bad in ({"path": 3}, {"file": "x"}, {"path": "x", "sha256": "abc"},
                    {"path": "x", "sha256": "A" * 64}, {"path": "x", "sha": "a" * 64}, 7):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                spec("s", bad)
        with self.assertRaisesRegex(ValueError, r"frame_files\[story\]"):
            Engine(self.fcfg(frame_files={"story": {"path": str(self.story), "sha256": "x"}}))
        # relative paths are the code directory's (not the working directory's)
        self.assertEqual(pgg_game.resolve_frame_path("x", "frames/abstract_v3.json"), V3)
        self.assertEqual(pgg_game.resolve_frame_path("abstract_v3", None), V3)
        self.assertEqual(pgg_game.resolve_frame_path("x", str(self.story)), self.story)

    def committed_with(self, **frame_files) -> Path:
        raw = json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8"))
        for label, sha in frame_files.items():
            raw["frame_files"][label]["sha256"] = sha
        path = self.tmp / "mp.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        return path

    def test_dry_run_fails_on_a_changed_file(self):
        for label in ("story", "abstract_v3"):
            with self.subTest(label):
                code, out, err = _main("--dry-run", "--config",
                                       str(self.committed_with(**{label: "f" * 64})))
                self.assertEqual(code, 1)
                self.assertIn(f"HATA: çerçeve: frame '{label}': sha256 of", err)
                self.assertIn("frame_files locks " + "f" * 64, err)
                self.assertNotIn("TOPLAM", out)
        self.create.assert_not_called()

    def test_real_run_fails_on_a_changed_file(self):
        self.use(CostAPI())
        raw = json.loads(self.committed_with(story="f" * 64).read_text())
        raw.update(prereg_approved=True, run="lock_mock", runs_dir=str(self.tmp / "runs"))
        path = self.tmp / "mp_approved.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        code, _, err = _main("--config", str(path))
        self.assertEqual(code, 1)
        self.assertIn("frame_files locks", err)
        self.create.assert_not_called()
        self.assertFalse((self.tmp / "runs" / "lock_mock").exists())


# --------------------------------------------------------------------------
# (b) forbidden roots in story frames at the run start
# --------------------------------------------------------------------------

class StoryLinter(FrameBase):
    def story_cfg(self, path, **kw):
        return self.fcfg(frame_files={"story": str(path)}, **kw)

    def test_committed_story_a_is_clean(self):
        f = pgg_frames.load_frame(STORY_A)
        self.assertEqual((f.name, f.kind), ("story_A_jar", "story"))
        self.assertEqual(pgg_game.story_frame_problems(f, GameParams()), [])
        self.story_cfg(STORY_A).validate()                     # passes the run-start check
        # the whole linter of the workspace (every round, position, value, card):
        # no root outside the card segment
        res = cerceve_linter.lint_rendered(ROOT, STORY_A, CARDS_V3)
        self.assertEqual([(k, s) for (k, s), a in res["agg"].items()
                          if a["hits"] and s != "kart"], [])
        self.assertGreater(res["n_prompts"], 1000)

    def test_forbidden_root_refuses_the_run_and_the_dry_run(self):
        self.use(CostAPI())
        cases = {
            "rules text": (lambda r: r["rules"].append({"text": "- It is a game."}),
                           r"rules\[\d+\]\.text: game \(game\)"),
            "player label": (lambda r: r.update(player_label="Player {player_no}"),
                             r"player_label: player \(Player\)"),
            "hyphenated": (lambda r: r["rules"].append({"text": "- No free-riding."}),
                           r"free rid \(free-riding\)"),
            "q2 text": (lambda r: r["comprehension"]["questions"][1].update(
                text=r["comprehension"]["questions"][1]["text"] + " Mind the payoff."),
                r"comprehension\.questions\[1\]\.text: payoff"),
            # a field name of the schema the model sees
            "decision key": (lambda r: r["response"].update(decision_key="tokens_in"),
                             r"rendered contribute N round 1 schema: token \(tokens_in\)"),
            "punishment only (P)": (lambda r: r.update(punish=r["punish"] + " Punish them."),
                                    r"rendered punish: punish \(Punish\)"),
        }
        for name, (edit, pattern) in cases.items():
            with self.subTest(name):
                path = _story_variant(self.tmp, edit)
                with self.assertRaisesRegex(FrameError, "story frame 'story'.*forbidden roots") as cm:
                    Engine(self.story_cfg(path))
                self.assertRegex(str(cm.exception), pattern)
                # the dry run fails the same way
                raw = json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8"))
                raw["frame_files"]["story"] = {"path": str(path), "sha256": _sha(path)}
                conf = self.tmp / "mp.json"
                conf.write_text(json.dumps(raw), encoding="utf-8")
                code, out, err = _main("--dry-run", "--config", str(conf))
                self.assertEqual(code, 1)
                self.assertIn("forbidden roots", err)
                self.assertNotIn("TOPLAM", out)
        self.create.assert_not_called()
        self.assertFalse((self.tmp / "runs" / "fr").exists())

    def test_abstract_frames_are_not_linted(self):
        v3 = pgg_frames.load_frame(V3)
        self.assertEqual(v3.kind, "abstract")
        # abstract_v2 has no field: frozen legacy file (task #73), kind None
        v2 = pgg_frames.load_frame(V2)
        self.assertEqual((v2.kind, v2.legacy, v2.lint_exempt), (None, True, False))
        # abstract_v3 says game / player / contribute on purpose ...
        problems = pgg_game.story_frame_problems(v3, GameParams())
        for root in ("game", "player", "contribut", "group project", "public good"):
            self.assertTrue([p for p in problems if f": {root} (" in p], root)
        # ... and runs (with the story fixture, kind abstract since task #73)
        self.fcfg().validate()
        # the same text as a story frame is refused: the kind decides
        raw = json.loads(V3.read_text(encoding="utf-8"))
        raw["kind"] = "story"
        path = self.tmp / "v3_as_story.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaisesRegex(FrameError, "story frame 'abstract_v3'"):
            Engine(self.fcfg(frame_files={"abstract_v3": str(path), "story": str(self.story)}))

    def test_kind_must_be_known(self):
        raw = json.loads(STORY_A.read_text(encoding="utf-8"))
        raw["kind"] = "fable"
        with self.assertRaisesRegex(pgg_frames.FrameError, r"kind: must be one of \('abstract', "
                                                           r"'story'\)"):
            pgg_frames.validate_frame(raw, "t")


# --------------------------------------------------------------------------
# (c) dirty code: frames/*.json, configs/*.json, cards/*.json
# --------------------------------------------------------------------------

class DirtyDataFiles(CodeVersionBase):
    DATA = ("frames/f.json", "configs/c.json", "cards/k.json")
    OTHER = ("notes.json", "tests/fixtures/x.json", "frames/SCHEMA.md")

    def setUp(self):
        super().setUp()
        for name in self.DATA + self.OTHER:
            (self.repo / name).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / name).write_text("{}\n")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "c2")
        self.sha = _git(self.repo, "rev-parse", "HEAD")

    def test_clean(self):
        cv = pgg_game._read_code_version(self.repo)
        self.assertEqual((cv["git_commit"], cv["git_dirty"]), (self.sha, False))

    def test_changed_frame_config_or_card_file_is_dirty(self):
        for name in self.DATA:
            with self.subTest(name):
                (self.repo / name).write_text('{"changed": true}\n')
                cv = pgg_game._read_code_version(self.repo)
                self.assertEqual((cv["git_dirty"], cv["dirty_files"]), (True, [name]))
                self.assertRegex(pgg_game.code_version_problem(cv),
                                 f"dirty: tracked code / frame / config / card files.*{name}")
                _git(self.repo, "checkout", "-q", "--", name)
        self.assertFalse(pgg_game._read_code_version(self.repo)["git_dirty"])

    def test_other_files_and_untracked_ones_do_not_count(self):
        for name in self.OTHER:
            (self.repo / name).write_text('{"changed": true}\n')
        (self.repo / "frames" / "new_story.json").write_text("{}\n")      # untracked
        cv = pgg_game._read_code_version(self.repo)
        self.assertEqual(cv["git_dirty"], False)

    def test_stamp_covers_the_data_files(self):
        dst = self.copy()
        path = pgg_game.write_code_version(dst, self.sha, repo_dir=self.repo)
        files = json.loads(path.read_text())["files_sha256"]
        self.assertTrue(set(self.DATA) <= set(files))
        self.assertFalse(set(self.OTHER) & set(files))
        self.assertIsNone(pgg_game.code_version_problem(pgg_game._read_code_version(dst)))
        (dst / "configs" / "c.json").write_text('{"changed": true}\n')
        cv = pgg_game._read_code_version(dst)
        self.assertEqual((cv["source"], cv["git_dirty"]), ("stamp", True))
        self.assertIn("configs/c.json: sha256 differs", " ".join(cv["stamp_problems"]))

    def test_versioned_paths(self):
        yes = ("pgg_game.py", "tests/test_x.py", "frames/story_A.json", "configs/minipilot.json",
               "cards/pilot_cards_v3.json")
        no = ("notes.json", "frames/SCHEMA.md", "tests/fixtures/story_fixture.json", "data/x.json")
        self.assertTrue(all(pgg_game.is_versioned_file(n) for n in yes))
        self.assertFalse(any(pgg_game.is_versioned_file(n) for n in no))


# --------------------------------------------------------------------------
# (d) K2: the q2 sign sentence and signed answers
# --------------------------------------------------------------------------

class Q2Sentence(unittest.TestCase):
    def test_new_sentence_in_both_frames_and_key_unchanged(self):
        p = GameParams()
        texts = {
            "abstract_v3": "2. Suppose that the contributions of the other players stay the same. "
                           "If you contribute 10 more points to the group project, by how much do "
                           "your own total earnings in that round change? " + NEW_SENTENCE + "\n",
            "story_A_jar": "2. Suppose that the other users put the same amounts into the jar. If "
                           "you put 10 more credits into the jar, by how much does what you end "
                           "that day with change? " + NEW_SENTENCE + "\n",
        }
        for path in (V3, STORY_A):
            f = pgg_frames.load_frame(path)
            with self.subTest(f.name):
                self.assertEqual(f.comprehension_key(p), {"q1": 28, "q2": -6})   # prereg §6.3
                for cond in ("N", "P"):
                    user = f.comprehension_messages(p, CARD_A, cond)[1]["content"]
                    self.assertIn(texts[f.name], user)
                    self.assertEqual(user.count(NEW_SENTENCE), 1)
                    self.assertNotIn("negative number", user)
                    self.assertNotIn("if they go down", user)
                    self.assertNotIn("if it goes down", user)
                    self.assertNotIn(K2_SENTENCE, user)
                    self.assertNotIn("+3", user)
                    self.assertNotIn("for example", user)
                q2 = f.comprehension_questions()[1]
                self.assertEqual(q2["answer"], {"kind": "own_change", "delta": 10})
        # abstract_v2 (pilot v2) has no rule comprehension: nothing of it changed
        self.assertFalse(pgg_frames.load_frame(V2).has_comprehension)
        self.assertNotIn("comprehension", json.loads(V2.read_text()))

    def test_example_is_a_placeholder_with_its_own_checks(self):
        # no committed frame uses {example} since task #73; the mechanism keeps its
        # checks, tested on abstract_v3 with task #67's K2 sentence put back
        def k2():
            raw = json.loads(V3.read_text())
            q2 = raw["comprehension"]["questions"][1]
            q2["text"] = q2["text"].replace(
                NEW_SENTENCE, "Give the change as a whole number with its sign, for example "
                              "+{example} or -{example}.")
            q2["answer"]["example"] = 3
            return raw

        pgg_frames.validate_frame(k2(), "t")

        def broken(edit):
            raw = k2()
            edit(raw["comprehension"]["questions"][1])
            with self.assertRaises(pgg_frames.FrameError) as cm:
                pgg_frames.validate_frame(raw, "t")
            return str(cm.exception)

        self.assertIn("own_change takes", broken(lambda q: q["answer"].update(example=0)))
        self.assertIn("own_change takes", broken(lambda q: q["answer"].update(example="3")))
        self.assertIn("unknown placeholder(s) ['example']",
                      broken(lambda q: q["answer"].pop("example")))
        self.assertIn("missing placeholder {example}",
                      broken(lambda q: q.update(text=q["text"].replace("{example}", "x"))))
        self.assertIn("numbers written in the text ['3']",
                      broken(lambda q: q.update(text=q["text"].replace("+{example}", "+3"))))


class SignedNumbers(unittest.TestCase):
    def test_parse(self):
        parse = llm_client._parse_json_strict
        self.assertEqual(parse('{"q1": 28, "q2": +3}', True), ({"q1": 28, "q2": 3}, True))
        self.assertEqual(parse('{"q1":+28,"q2":−6}', True), ({"q1": 28, "q2": -6}, True))
        self.assertEqual(parse('{"q2": [+1, +2]}', True), ({"q2": [1, 2]}, True))
        self.assertEqual(parse('{"q2": -6}', True), ({"q2": -6}, False))      # plain JSON
        # text inside strings is never touched
        raw = '{"q2": +3, "rationale": "it went: +3, [+4] or \\"x\\": +5 −6"}'
        self.assertEqual(parse(raw, True),
                         ({"q2": 3, "rationale": 'it went: +3, [+4] or "x": +5 −6'}, True))
        # prose around it, as the old fallback
        self.assertEqual(parse('Answer: {"q1": 28, "q2": +3}', True), ({"q1": 28, "q2": 3}, True))
        # off by default: decisions are parsed exactly as before
        for bad in ('{"q2": +3}', '{"contribution": +5}'):
            with self.assertRaises(json.JSONDecodeError):
                parse(bad)
        with self.assertRaises(json.JSONDecodeError):
            parse('{"q2": + 3}', True)                      # not a signed number


class SignedAnswersInARun(FrameBase):
    def one(self, **kw):
        return self.fcfg(models={"deepseek": "v/ds"}, frames={"abstract_v3": ["deepseek"]},
                         frame_files=None, cards=[CARD_A], **kw)

    def test_plus_answer_is_valid_and_wrong(self):
        replies = ['{"q1": 28, "q2": +3, "rationale": "up: +3"}',    # agent 1: +3, valid
                   '{"q1": 28, "q2": −6}',                       # agent 2: U+2212 -6
                   '{"q1": 28, "q2": "+3"}',                          # agent 3: string, invalid
                   _payload({"q1": 28, "q2": 3}),                     #   re-request
                   _payload({"q1": 28, "q2": -6}),                    # agent 4
                   '{"q1": 28, "q2": -6}']                            # schedule
        comp_reply = _comp_reply(replies)
        first_contribution = {"done": False}

        def content(kwargs, default):
            if FakeAPI.parse(kwargs)[0] == "contribute" and not first_contribution["done"]:
                first_contribution["done"] = True
                return '{"contribution": +5}'                  # a decision: still broken JSON
            return comp_reply(kwargs, default)

        self.use(CostAPI(content_fn=content))
        Engine(self.one()).run()
        rows = self.rows()
        comp = {(r["arm"], r["agent_id"]): r for r in rows if r["step"] == "comprehension"}
        got = [(comp[("group", a)]["comp_q2_answer"], comp[("group", a)]["comp_q2_correct"],
                comp[("group", a)]["n_parse_fail"], comp[("group", a)]["n_invalid"])
               for a in (1, 2, 3, 4)]
        self.assertEqual(got, [(3, False, 0, 0), (-6, True, 0, 0), (3, False, 0, 1),
                               (-6, True, 0, 0)])
        self.assertEqual(comp[("isolated", 1)]["comp_q2_answer"], -6)
        contrib = [r for r in rows if r["step"] == "contribute"]
        self.assertEqual(sum(r["n_parse_fail"] for r in contrib), 1)
        self.assertNotIn(5, [r["contribution"] for r in contrib if r["n_parse_fail"]])
        # the accepted "+3" response is logged as a degraded parse with its raw text
        records = [json.loads(x) for x in
                   (self.tmp / "runs" / "fr" / "raw_calls.jsonl").read_text().splitlines()]
        plus = [r for r in records if r.get("response_raw", "").startswith('{"q1": 28, "q2": +3')]
        self.assertEqual(len(plus), 1)
        self.assertIs(plus[0]["degraded"], True)
        self.assertEqual(plus[0]["response_parsed"]["q2"], 3)


# --------------------------------------------------------------------------
# (e) rule-comprehension rows: step "comprehension"
# --------------------------------------------------------------------------

class ComprehensionStep(FrameBase):
    def test_rows_are_told_apart_by_step(self):
        self.use(CostAPI())
        Engine(self.fcfg()).run()            # abstract_v3 x 3 models, story x 2, 2 cards
        rows = self.rows()
        comp = [r for r in rows if r["step"] == "comprehension"]
        # per cell (card x model x frame): 4 agents of 1 group + 1 isolated schedule
        self.assertEqual(len(comp), (2 * 3 + 2 * 2) * (4 + 1))
        self.assertEqual({r["step"] for r in rows}, {"comprehension", "contribute", "isolated"})
        # step "comprehension" <=> the row has the comprehension fields
        for r in rows:
            self.assertEqual("comp_n_correct" in r, r["step"] == "comprehension", r["step"])
        self.assertTrue(all("contribution" not in r or r["contribution"] is None for r in comp))
        self.assertEqual({(r["arm"], r["round"]) for r in comp}, {("group", 1), ("isolated", None)})
        self.assertEqual({r["frame"] for r in comp}, {"abstract_v3", "story"})
        # filtering by step leaves exactly the decisions
        decisions = [r for r in rows if r["step"] != "comprehension"]
        self.assertTrue(all(isinstance(r["contribution"], int) for r in decisions))


# --------------------------------------------------------------------------
# (f) run name template
# --------------------------------------------------------------------------

class RunNameTemplate(GuardTestBase):
    def config(self, **overrides) -> Path:
        cards = self.tmp / "cards.json"
        cards.write_text(json.dumps([
            {"card_id": "x_minimal", "style": "minimal", "city": "X", "text": "Fake card X."}]),
            encoding="utf-8")
        (self.tmp / "runs").mkdir(exist_ok=True)
        raw = json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8"))
        raw.update({
            "prereg_approved": True, "cards": str(cards), "cities": ["X"],
            "cards_sha256": _sha(cards),
            "arms": ["group"], "groups_per_cell": 1, "isolated_reps": 1,
            "frames": {"abstract_v3": ["deepseek", "mistral", "gpt"]}, "frame_files": None,
            "budget_usd": 1.0, "invalid_rate_cap": 0.5, "workers": 1, "parallel_units": 1,
            "runs_dir": str(self.tmp / "runs"), "params": {"rounds": 2},
        })
        raw.update(overrides)
        path = self.tmp / "mp.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        return path

    def setUp(self):
        super().setUp()
        names = {model: name for _, model, name, _ in MINIPILOT_PROVIDERS.values()}
        self.use(CostAPI(provider_fn=lambda k: names[k["model"]]))
        p = mock.patch.object(pgg_game, "run_date", return_value="20990102")
        p.start()
        self.addCleanup(p.stop)

    def test_committed_config_has_the_template(self):
        raw = json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(raw["run"], "minipilot_{run_date}")
        self.assertEqual(pgg_game.resolve_run_name(raw["run"], "20261007"), "minipilot_20261007")
        self.assertTrue(re.fullmatch(pgg_game.run_template_pattern(raw["run"]),
                                     "minipilot_20261007"))
        self.assertFalse(re.fullmatch(pgg_game.run_template_pattern(raw["run"]),
                                      "minipilot_2026107"))
        with self.assertRaisesRegex(ValueError, "only {run_date}"):
            pgg_game.resolve_run_name("x_{day}")

    def test_new_run_resolves_it_and_records_it(self):
        code, out, err = _main("--config", str(self.config()))
        self.assertEqual(code, 0, err)
        run_dir = self.tmp / "runs" / "minipilot_20990102"
        summary = json.loads((run_dir / "minipilot_20990102_summary.json").read_text())
        self.assertEqual((summary["run"], summary["run_template"]),
                         ("minipilot_20990102", "minipilot_{run_date}"))
        self.assertEqual(summary["segments"][0]["run_template"], "minipilot_{run_date}")
        start = [json.loads(x) for x in (run_dir / "raw_calls.jsonl").read_text().splitlines()
                 if '"pgg_run_start"' in x]
        self.assertEqual(start[0]["run_template"], "minipilot_{run_date}")
        rows = [json.loads(x) for x in (run_dir / "minipilot_20990102.jsonl").read_text()
                .splitlines()]
        self.assertEqual({r["run"] for r in rows}, {"minipilot_20990102"})
        n_calls = len(self.api.calls)
        # --resume: the template is not resolved again (the run day may have passed)
        code, _, err = _main("--config", str(self.config()), "--resume")
        self.assertEqual(code, 1)
        self.assertIn("--resume needs the run name given explicitly (--run, e.g. "
                      "minipilot_YYYYMMDD)", err)
        code, _, err = _main("--config", str(self.config()), "--resume", "--dry-run")
        self.assertEqual(code, 1)
        self.assertIn("--resume needs the run name", err)
        code, _, err = _main("--config", str(self.config()), "--resume", "--run", "other_run")
        self.assertEqual(code, 1)
        self.assertIn("does not fit the config's run name template", err)
        self.assertEqual(len(self.api.calls), n_calls)
        # with the resolved name it resumes (nothing left) and keeps the template
        code, _, err = _main("--config", str(self.config()), "--resume", "--run",
                             "minipilot_20990102")
        self.assertEqual(code, 0, err)
        summary = json.loads((run_dir / "minipilot_20990102_summary.json").read_text())
        self.assertEqual((summary["segment"], summary["run_template"]),
                         (1, "minipilot_{run_date}"))
        self.assertIsNone(summary["segments"][1]["run_template"])
        self.assertEqual(len(self.api.calls), n_calls)

    def test_unapproved_committed_config_is_refused_before_the_name(self):
        # the committed config is approved since task #75: a copy with the approval
        # taken back (runs_dir in tmp, so a slip cannot write to the real one)
        raw = json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8"))
        raw.update(prereg_approved=False, runs_dir=str(self.tmp / "runs"))
        path = self.tmp / "mp_unapproved.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        code, _, err = _main("--config", str(path))
        self.assertEqual(code, 1)
        self.assertIn("prereg_approved is false", err)
        self.create.assert_not_called()
        self.assertFalse((self.tmp / "runs" / "minipilot_20990102").exists())


if __name__ == "__main__":
    unittest.main()
