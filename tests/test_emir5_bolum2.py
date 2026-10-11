"""Mock tests of EMIR 5 Bölüm 2 files and the remaining M2 tests (task #93). No network,
no ../.env, no write into a run directory.

K1 frames/abstract_v4.json = abstract_v3 + "The following describes you:" on its own
   line before the card in the system message; every other text the model sees is
   abstract_v3's; no "experiment" / "participant"; kind abstract.
K3 cards/main_cards_v1.json: 12 cards; minimal = v3 (= v2), value = v2 byte for byte;
   factual = the D2 C1 court-time sentence after the v3 card head; no forbidden root.
Config configs/main.json (stage 1) and the stage 0a / 0b configs: K2 models and
   providers, locks, placeholders for G / budget / answer format, prereg_approved false.
Calibration configs/cost_calibration_minipilot.json (the mini-pilot's token
   distribution) chosen by a config's "cost_calibration"; the default calibration is
   unchanged.
M2 rest: the punishment step (condition P) cut off and resumed with abstract_v4, serial
   and with workers=4 / parallel_units=3: every request byte for byte the uninterrupted
   run's, nothing answered asked again, the valid rows the uninterrupted run's.
"""

import contextlib
import hashlib
import io
import json
import os
import re
import signal
import sys
import tempfile
import threading
import time
import unittest
import zlib
from collections import Counter
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_pgg_game import CARD_A, CARD_B, ROOT, _payload  # noqa: E402  (dummy key first)
from test_pgg_guards import CostAPI  # noqa: E402
from test_pgg_k3_k5 import _request  # noqa: E402
from test_pgg_resume import ResumeBase, _killer, _rows  # noqa: E402
from test_pgg_resume_rounds import _comparable  # noqa: E402

import cerceve_linter  # noqa: E402
import llm_client  # noqa: E402
import pgg_cost  # noqa: E402
import pgg_cost_calibrate  # noqa: E402
import pgg_frames  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Engine, GameParams, RunStopped  # noqa: E402

V3 = ROOT / "frames" / "abstract_v3.json"
V4 = ROOT / "frames" / "abstract_v4.json"
CARDS = ROOT / "cards" / "main_cards_v1.json"
MAIN = ROOT / "configs" / "main.json"
S0A = {"example_object": ROOT / "configs" / "main_s0a_example.json",
       "json_schema_strict": ROOT / "configs" / "main_s0a_schema.json"}
S0B = ROOT / "configs" / "main_s0b.json"
MINIPILOT = ROOT / "configs" / "minipilot.json"
CAL = ROOT / "configs" / "cost_calibration_minipilot.json"
RUNS_DIR = Path(json.loads(MINIPILOT.read_text(encoding="utf-8"))["runs_dir"])
MP_DIR = RUNS_DIR / "minipilot_20261008"
SLUGS = {"deepseek": "deepseek/deepseek-v4.1-flash", "mistral": "mistralai/mistral-large-4-0",
         "gpt": "openai/gpt-6-luna"}
PREFIX = "The following describes you:\n"
# workspace/kart_linter.py ROOTS (17), copied: the workspace is not part of the repository
KART_LINTER_ROOTS = ["contribut", "cooperat", "reciproc", "shar", "common good", "public good",
                     "collective", "generos", "fair", "trust", "group", "project", "invest",
                     "give", "pool", "team", "selfless"]
IDENTITY_ROOTS = ["saudi", "american", "arab", "western", "individualis", "collectivis",
                  "stereotyp"]
# prereg_minipilot.md §5.1 E2a dictionaries with spelling variants
E2A = ["public good", "commons", "fehr", "gächter", "gachter", "gaechter", "herrmann", "ostrom",
       "experiment", "nash", "subgame", "sub game", "backward induction", "backwards induction",
       "equilibri"]
N_DAYS = {"Boston": "444", "Copenhagen": "485", "Athens": "1,711", "Riyadh": "575"}


def _sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# K1 abstract_v4
# --------------------------------------------------------------------------

class AbstractV4(unittest.TestCase):
    def setUp(self):
        self.v3, self.v4 = pgg_frames.load_frame(V3), pgg_frames.load_frame(V4)
        self.params = GameParams()
        self.cards = pgg_game.load_cards(CARDS, None)

    def test_file_differs_from_v3_only_in_the_system_line_and_metadata(self):
        a, b = _json(V3), _json(V4)
        self.assertEqual(sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k)),
                         ["_notes", "description", "name", "system"])
        self.assertEqual((a["system"], b["system"]), ("{card}", PREFIX + "{card}"))
        self.assertEqual((b["name"], b["kind"]), ("abstract_v4", "abstract"))
        # line by line: only the lines of these four keys differ
        la, lb = V3.read_text().split("\n"), V4.read_text().split("\n")
        self.assertEqual(len(la), len(lb))
        self.assertEqual([i for i, (x, y) in enumerate(zip(la, lb)) if x != y], [1, 3, 4, 6])

    def _all_prompts(self, f, card):
        p = self.params
        cs = pgg_game.contribution_schema(p, True, prompt_frame=f)
        hist = []
        for r in (1, 2):
            c = [3 * r, 10, 15, 20 - r]
            rec = pgg_game.RoundRecord(r, c, pgg_game.project_payoffs(p, c),
                                       final_earnings=pgg_game.project_payoffs(p, c))
            rec.punishment = [[0, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 1], [0, 0, 0, 0]]
            rec.final_earnings, rec.cost_paid, rec.received = pgg_game.apply_punishment(
                p, rec.round_earnings, rec.punishment)
            hist.append(rec)
        out = []
        for cond in ("N", "P"):
            for rnd in (1, 3):
                out.append((pgg_game.contribution_messages(p, cond, card, hist[:rnd - 1], 1, rnd,
                                                           prompt_frame=f), cs))
            out.append((f.comprehension_messages(p, card, cond), f.comprehension_schema(True)))
        out.append((pgg_game.punishment_messages(p, card, hist[:1], 0, 2, [6, 12, 0, 20],
                                                 pgg_game.project_payoffs(p, [6, 12, 0, 20])[0],
                                                 prompt_frame=f),
                    pgg_game.punishment_schema(p, [2, 3, 4], True, prompt_frame=f)))
        for x in pgg_game.ISOLATED_POINTS:
            out.append((pgg_game.isolated_messages(p, card, x, "fixed_round", 5, prompt_frame=f),
                        cs))
        return out

    def test_every_prompt_is_v3s_but_the_system_message(self):
        n = 0
        for fmt in llm_client.ANSWER_FORMATS:
            for card in self.cards:
                for (m3, s3), (m4, s4) in zip(self._all_prompts(self.v3, card),
                                              self._all_prompts(self.v4, card)):
                    a3, rf3 = llm_client.answer_request(m3, s3, fmt)
                    a4, rf4 = llm_client.answer_request(m4, s4, fmt)
                    self.assertEqual(a3[0], {"role": "system", "content": card.text})
                    self.assertEqual(a4[0], {"role": "system", "content": PREFIX + card.text})
                    self.assertEqual((a3[1:], rf3), (a4[1:], rf4))
                    sent = json.dumps([a4, rf4], ensure_ascii=False).lower()
                    self.assertNotIn("experiment", sent)
                    self.assertNotIn("participant", sent)
                    n += 1
        self.assertEqual(n, 3 * 12 * 12)

    def test_same_answer_key_isolated_wording_and_audit(self):
        self.assertEqual(self.v4.comprehension_key(self.params), {"q1": 28, "q2": -6})
        self.assertEqual(list(self.v4.isolated_frames), ["fixed_round"])
        audit = pgg_game.frame_audit("abstract_v4", self.v4, self.params, with_frames=True)
        self.assertEqual((audit["kind"], audit["lint"]), ("abstract", "exempt"))
        # the added line has no forbidden root of the frame linter either
        self.assertEqual(cerceve_linter.find_hits(PREFIX), [])


# --------------------------------------------------------------------------
# K3 cards
# --------------------------------------------------------------------------

class MainCards(unittest.TestCase):
    def setUp(self):
        self.raw = CARDS.read_bytes()
        self.cards = json.loads(self.raw)
        self.v2 = _json(ROOT / "cards" / "pilot_cards_v2.json")
        self.v3 = _json(ROOT / "cards" / "pilot_cards_v3.json")

    @staticmethod
    def find(cards, city, style):
        return next(c for c in cards if c["city"] == city and c["style"] == style)

    def test_grid_fields_and_format(self):
        self.assertEqual([(c["city"], c["style"]) for c in self.cards],
                         [(ci, st) for ci in ("Boston", "Copenhagen", "Athens", "Riyadh")
                          for st in ("minimal", "value", "factual")])
        for c in self.cards:
            self.assertEqual(list(c), ["card_id", "city", "style", "text"])
            self.assertEqual(c["card_id"], f"{c['city'].lower()}_{c['style']}")
        self.assertEqual(self.raw, (json.dumps(self.cards, indent=2, ensure_ascii=False)
                                    + "\n").encode("utf-8"))
        self.assertEqual(len(pgg_game.load_cards(CARDS, None)), 12)

    def test_minimal_and_value_are_byte_identical(self):
        enc = lambda c: json.dumps(c, indent=2, ensure_ascii=False).encode("utf-8")
        for c in self.cards:
            if c["style"] == "factual":
                continue
            sources = (self.v3, self.v2) if c["style"] == "minimal" else (self.v2,)
            for src in sources:
                o = self.find(src, c["city"], c["style"])
                self.assertEqual(c["text"].encode("utf-8"), o["text"].encode("utf-8"))
                self.assertEqual(enc(c), enc(o))

    def test_factual_is_the_d2_c1_sentence_after_the_v3_head(self):
        for city, n in N_DAYS.items():
            head = self.find(self.v3, city, "factual")["text"].split(". ", 1)[0] + "."
            self.assertEqual(head, self.find(self.v3, city, "minimal")["text"])
            self.assertEqual(self.find(self.cards, city, "factual")["text"],
                             f"{head} In your country, a lawsuit over an unpaid bill takes about "
                             f"{n} days.")

    def test_no_forbidden_root(self):
        for c in self.cards:
            low = cerceve_linter._norm(c["text"])
            self.assertEqual(cerceve_linter.find_hits(c["text"]), [], c["card_id"])
            for root in KART_LINTER_ROOTS + IDENTITY_ROOTS + E2A:
                self.assertNotIn(root, low, (c["card_id"], root))

    def test_locked_in_every_main_config(self):
        for path in (MAIN, S0B, *S0A.values()):
            raw = _json(path)
            self.assertEqual((raw["cards"], raw["cards_sha256"]),
                             ("cards/main_cards_v1.json", _sha(CARDS)))
            self.assertEqual(pgg_game.check_cards_lock(CARDS, raw["cards_sha256"]), _sha(CARDS))


# --------------------------------------------------------------------------
# configs/main.json and the stage configs
# --------------------------------------------------------------------------

class MainConfigs(unittest.TestCase):
    def setUp(self):
        self.main = _json(MAIN)
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_stage1_design(self):
        m = self.main
        self.assertIs(m["prereg_approved"], False)
        self.assertEqual((m["run"], m["seed_namespace"]), ("main_s1_{run_date}", "pgg-main-s1"))
        self.assertEqual(m["models"], list(SLUGS.values()))
        self.assertEqual(m["providers"], {
            "deepseek": {"slug": "deepinfra/fp8", "name": "DeepInfra", "quantizations": ["fp8"]},
            "mistral": {"slug": "mistral", "name": "Mistral"},
            "gpt": {"slug": "openai", "name": "OpenAI"}})
        self.assertNotIn("reasoning_effort", m)
        self.assertNotIn("temperature", m)
        self.assertEqual((m["max_tokens"], m["check_snapshot"]), (16000, True))
        self.assertEqual((m["conditions"], m["arms"]), (["N"], ["group", "isolated"]))
        self.assertEqual(m["cities"], ["Boston", "Copenhagen", "Athens", "Riyadh"])
        self.assertEqual((m["isolated_points"], m["isolated_reps"], m["isolated_frame"],
                          m["isolated_round_no"]), ([0, 5, 10, 15, 20], 4, "fixed_round", 5))
        self.assertIs(m["comprehension"], True)
        self.assertEqual(m["frames"], {"abstract_v4": ["deepseek", "mistral", "gpt"]})
        self.assertEqual(m["frame_files"], {"abstract_v4": {"path": "frames/abstract_v4.json",
                                                            "sha256": _sha(V4)}})
        self.assertEqual(m["cost_calibration"], {"path": "configs/cost_calibration_minipilot.json",
                                                 "sha256": _sha(CAL)})
        # task #96 (EMIR 6 Soru 1-2): G 16 / 10 / 16 and the budgets are the user's
        # decisions now; only answer_format (stage 0a) is still a placeholder
        self.assertEqual((m["groups_per_cell"], m["groups_per_cell_by_model"]),
                         (10, {"deepseek": 16, "mistral": 10, "gpt": 16}))
        self.assertEqual((m["budget_usd"], m["model_budget_usd"], m["expected_cost_gate_usd"]),
                         (91, {"deepseek": 22, "mistral": 68, "gpt": 3}, 52))
        self.assertTrue(pgg_game.is_placeholder(m["answer_format"]))
        self.assertIn("TBD", m["answer_format"])
        self.assertEqual(pgg_game.open_choices(m), ["answer_format"])
        self.assertIsNotNone(pgg_game.prereg_problem(m))

    def test_stage_configs(self):
        names = {MAIN: ("main_s1_{run_date}", "pgg-main-s1")}
        for fmt, path in S0A.items():
            a = _json(path)
            self.assertIs(a["prereg_approved"], False)
            self.assertEqual(a["answer_format"], fmt)
            # task #96 (EMIR 6 C3): + 1 group of a 3-round game per card
            self.assertEqual((a["cities"], a["arms"], a["isolated_points"], a["isolated_reps"],
                              a["comprehension"], a["groups_per_cell"], a["params"]),
                             (["Boston", "Riyadh"], ["group", "isolated"], [10], 2, True, 1,
                              {"rounds": 3}))
            names[path] = (a["run"], a["seed_namespace"])
        b = _json(S0B)
        self.assertIs(b["prereg_approved"], False)
        self.assertEqual((b["groups_per_cell"], b["isolated_reps"], b["isolated_points"],
                          b["arms"], b["comprehension"]),
                         (1, 1, [0, 5, 10, 15, 20], ["group", "isolated"], True))
        self.assertTrue(pgg_game.is_placeholder(b["answer_format"]))
        names[S0B] = (b["run"], b["seed_namespace"])
        # every stage has its own run name and seed namespace
        self.assertEqual(len({r for r, _ in names.values()}), 4)
        self.assertEqual(len({s for _, s in names.values()}), 4)
        # the rest is stage 1's
        same = ("models", "providers", "frames", "frame_files", "cards", "cards_sha256",
                "max_tokens", "check_snapshot", "isolated_frame", "isolated_round_no",
                "cost_calibration", "rationale", "runs_dir", "reasoning_cap_rule",
                "snapshot_version_models", "invalid_rate_cap", "max_invalid")
        # task #96 (EMIR 6 C3): 0a has its own round of the isolated question (2 of 3),
        # no invalid-rate cap and max_invalid 8
        s0a_own = ("isolated_round_no", "invalid_rate_cap", "max_invalid")
        for path in (S0B, *S0A.values()):
            raw = _json(path)
            keys = [k for k in same if path == S0B or k not in s0a_own]
            self.assertEqual({k: raw[k] for k in keys}, {k: self.main[k] for k in keys}, path)

    def dry(self, path, *extra) -> str:
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            code = pgg_game.main(["--dry-run", "--config", str(path), *extra])
        self.assertEqual(code, 0, err.getvalue())
        return out.getvalue()

    def total(self, text):
        return float(re.search(r"^TOPLAM .*?(\d+) çağrı +~([0-9.]+) USD", text, re.M).group(2))

    def test_dry_runs(self):
        text = self.dry(MAIN)            # task #96: G 16 / 10 / 16 (tests/test_emir6_c3.py)
        self.assertRegex(text, r"(?m)^TOPLAM .*? 23040 çağrı")
        totals = {}
        for g in (6, 10, 16):
            text = self.dry(MAIN, "--groups-per-cell", str(g))
            calls = int(re.search(r"^TOPLAM .*?(\d+) çağrı", text, re.M).group(1))
            # 12 cards x (G x 4 x 10 + G x 4 comprehension + 4 x 5 isolated + 4) x 3 models
            self.assertEqual(calls, 3 * 12 * (g * 44 + 24))
            totals[g] = self.total(text)
            self.assertIn("Üzerine yazılan: configs/cost_calibration_minipilot.json", text)
            self.assertIn("kilitli, beklenenle aynı", text)
            self.assertIn("ÖN KAYIT ONAYI YOK", text)
            self.assertIn("SEÇİLMEMİŞ (gerçek koşu başlamaz): answer_format", text)
        self.assertLess(totals[6], totals[10])
        self.assertLess(totals[10], totals[16])
        for path in S0A.values():
            text = self.dry(path)
            self.assertIn("360 çağrı", text)             # task #96: 3-round group + isolated
            self.assertIn("GEÇER", text)
        text = self.dry(S0B)
        self.assertIn("1800 çağrı", text)
        self.assertIn("GEÇER", text)

    def test_calibration_file_lock(self):
        raw = dict(self.main, cost_calibration={"path": str(CAL), "sha256": "0" * 64})
        path = self.tmp / "m.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(pgg_game.main(["--dry-run", "--config", str(path),
                                            "--groups-per-cell", "10"]), 1)
        self.assertIn("cost_calibration: sha256", err.getvalue())
        with self.assertRaisesRegex(ValueError, "cannot be read"):
            pgg_game.cost_calibration_files("configs/nope.json")
        self.assertEqual(pgg_game.cost_calibration_files(None), ())

    def test_run_config_validates(self):
        # stage 1 with G = 10 and a chosen format builds a valid RunConfig (no call)
        s = dict(self.main, groups_per_cell=10, answer_format="example_object", budget_usd=85,
                 groups_per_cell_by_model=None,
                 model_budget_usd={"deepseek": 14, "mistral": 68, "gpt": 2},
                 expected_cost_gate_usd=49, runs_dir=str(self.tmp))
        s["cards"] = str(ROOT / s["cards"])
        s["params"] = GameParams()
        models = pgg_game.resolve_models(s["models"], pgg_cost.KNOWN_MODELS)
        cfg = pgg_game.run_config("main_s1_20261010", s, models, {"runs_dir": self.tmp})
        engine = Engine(cfg, llm=pgg_game.OfflineLLM())
        self.assertEqual(cfg.planned_calls_per_model(), 12 * (10 * 44 + 24))
        est = engine.design_estimate()
        self.assertIsNone(engine.cost_gate_problem())
        self.assertLess(est["total_cost_usd"], 49)
        # the default calibration is back after the estimate
        self.assertEqual(pgg_cost.CALIBRATION["overlays"][-1]["file"],
                         "cost_calibration_minipilot_m1.json")


# --------------------------------------------------------------------------
# calibration from the mini-pilot
# --------------------------------------------------------------------------

class MinipilotCalibration(unittest.TestCase):
    def setUp(self):
        self.text = CAL.read_text(encoding="utf-8")
        self.cal = json.loads(self.text)

    def test_overlay_structure_and_no_ids(self):
        self.assertEqual(self.cal["overlay_of"], "cost_calibration_pilot_v2.json")
        self.assertEqual(self.cal["source"]["run"], "minipilot_20261008")
        self.assertEqual(self.cal["source"]["frame_sha256"], _sha(V3))
        self.assertEqual(set(self.cal["models"]), set(SLUGS.values()))
        self.assertAlmostEqual(self.cal["actual_total_cost_usd"], 4.0842744204, places=8)
        self.assertAlmostEqual(self.cal["recomputed_total_cost_usd"],
                               self.cal["actual_total_cost_usd"], places=6)
        body = json.dumps({k: v for k, v in self.cal.items() if k != "_notes"})
        for word in ("account", "user_id", "key_id", "gen-", "sk-or", "session_id",
                     "You are a", "rationale\":", "pgg-minipilot-"):
            self.assertNotIn(word, body)
        n_rows = {"deepseek": (48, 432, 60, 60), "mistral": (32, 280, 30, 38),
                  "gpt": (48, 432, 60, 60)}
        for slug, m in self.cal["models"].items():
            got = tuple(m["measured"][k]["n"] for k in
                        ("group_round_1", "group_rounds_2_10", "isolated", "comprehension"))
            self.assertEqual(got, n_rows[m["key"]])
            self.assertIs(m["estimate"], False)
        mistral = self.cal["models"][SLUGS["mistral"]]
        self.assertIsNone(mistral["measured_story"])
        self.assertEqual(mistral["paid"]["n_valid_rows"], 380)
        self.assertIn("Mistral eksik veri: 380/600", mistral["report_note"])

    def test_contribute_is_the_round_weighted_mix(self):
        for m in self.cal["models"].values():
            r1, rl = m["measured"]["group_round_1"], m["measured"]["group_rounds_2_10"]
            k = m["kinds"]["contribute_N"]
            for stat in ("mean", "p95"):
                self.assertAlmostEqual(k["completion_tokens"][stat],
                                       0.1 * r1["completion_tokens"][stat]
                                       + 0.9 * rl["completion_tokens"][stat], places=5)
                self.assertAlmostEqual(k["prompt_tokens_abstract_v3"][stat],
                                       0.1 * r1["prompt_tokens"][stat]
                                       + 0.9 * rl["prompt_tokens"][stat], places=5)
            for kind, kk in m["kinds"].items():
                for stat in ("mean", "p95"):
                    self.assertAlmostEqual(kk["prompt_tokens"][stat] * kk["prompt_scale_abstract_v3"],
                                           kk["prompt_tokens_abstract_v3"][stat], places=3)
            self.assertEqual(m["kinds"]["comprehension"]["completion_tokens"],
                             m["measured"]["comprehension"]["completion_tokens"])

    def test_measured_comprehension_is_not_extrapolated(self):
        with pgg_cost.extra_overlays([CAL]):
            for slug in SLUGS.values():
                self.assertFalse(pgg_cost.kind_tokens(slug, "comprehension")[2])
            note = pgg_cost.source_note()
        self.assertTrue(pgg_cost.kind_tokens(SLUGS["gpt"], "comprehension")[2])   # default
        self.assertIn("cost_calibration_minipilot.json (koşu minipilot_20261008", note)
        self.assertEqual(pgg_cost.source_note(), pgg_cost.SOURCE_NOTE)

    def test_default_calibration_and_minipilot_estimate_unchanged(self):
        before = json.dumps(pgg_cost.CALIBRATION, sort_keys=True)
        with pgg_cost.extra_overlays([CAL]):
            self.assertNotEqual(json.dumps(pgg_cost.CALIBRATION, sort_keys=True), before)
        self.assertEqual(json.dumps(pgg_cost.CALIBRATION, sort_keys=True), before)
        with self.assertRaises(RuntimeError):
            with pgg_cost.extra_overlays([CAL]):
                raise RuntimeError("x")
        self.assertEqual(json.dumps(pgg_cost.CALIBRATION, sort_keys=True), before)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(pgg_game.main(["--dry-run", "--config", str(MINIPILOT)]), 0)
        self.assertIn("~4.0440 USD (tahmin); p95 üst sınır ~9.4348 USD", out.getvalue())
        with self.assertRaisesRegex(ValueError, "not found"):
            with pgg_cost.extra_overlays([ROOT / "configs" / "nope.json"]):
                pass
        # no extra overlay: the calibration in use (even a patched one) is kept
        patched = {"patched": True}
        with mock.patch.object(pgg_cost, "CALIBRATION", patched):
            with pgg_cost.extra_overlays(()) as cal:
                self.assertIs(cal, patched)
                self.assertIs(pgg_cost.CALIBRATION, patched)

    def test_calibrated_scope_reproduces_the_abstract_arm(self):
        # the abstract_v3 arm of the mini-pilot priced from the overlay = its billed cost
        params = GameParams()
        mp = _json(MINIPILOT)
        cards = pgg_game.load_cards(ROOT / mp["cards"], mp["cities"])
        frame = pgg_frames.load_frame(V3)
        sc = pgg_game.prompt_scales(frame, params, cards, isolated_frame="fixed_round",
                                    isolated_round_no=5)
        with pgg_cost.extra_overlays([CAL]):
            for slug, m in self.cal["models"].items():
                meas = m["measured"]
                if m["key"] == "mistral":
                    continue            # its rounds 2-10 are not 9 x round 1 (cut-off group)
                counts = {"contribute_N": meas["group_round_1"]["n"]
                          + meas["group_rounds_2_10"]["n"],
                          "isolated": meas["isolated"]["n"],
                          "comprehension": meas["comprehension"]["n"]}
                got = pgg_cost.model_cost(slug, counts, sc)["base_cost_usd"]
                billed = sum(v["cost_usd_sum"] for v in meas.values())
                self.assertAlmostEqual(got / billed, 1.0, places=3, msg=m["key"])

    @unittest.skipUnless((MP_DIR / "raw_calls.jsonl").is_file(), "mini-pilot run directory absent")
    def test_file_is_reproduced_read_only_from_the_run(self):
        before = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in MP_DIR.iterdir()}
        self.assertEqual(pgg_cost_calibrate.calibrate_minipilot(MP_DIR), self.cal)
        after = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in MP_DIR.iterdir()}
        self.assertEqual(after, before)

    def test_raw_log_reader_keeps_model_and_cost_only(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "raw_calls.jsonl"
            recs = [{"model": "a", "usage": {"cost": 0.5}, "response_raw": {"user": "acct-1"}},
                    {"model": "a", "usage": {"cost": 0.25}, "messages": ["x"]},
                    {"model": "b", "usage": None},
                    {"event": "pgg_run_start", "model": "a"}]
            path.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
            self.assertEqual(pgg_cost_calibrate.raw_paid_by_model(path), ({"a": 0.75}, 3))


# --------------------------------------------------------------------------
# M2: condition P (punishment step) cut off and resumed, abstract_v4
# --------------------------------------------------------------------------

class PAPI(CostAPI):
    """CostAPI that reads every answer format's prompt (kind from the question text)
    and answers contribution and punishment as a function of the whole prompt."""

    @staticmethod
    def parse(kwargs):
        user = kwargs["messages"][-1]["content"]
        if "RULE CHECK" in user:
            kind = "comprehension"
        elif "punishment step" in user:
            kind = "punish"
        elif "QUESTION" in user:
            kind = "isolated"
        else:
            kind = "contribute"
        agent = re.search(r"You are Player (\d)", user)
        rnd = re.search(r"ROUND (\d+) of", user)
        others = re.search(r"on average, (\d+) points", user)
        return (kind, int(agent.group(1)) if agent else None,
                int(rnd.group(1)) if rnd else None, int(others.group(1)) if others else None)


def _p_reply(kwargs, content):
    kind, agent, _, _ = PAPI.parse(kwargs)
    h = zlib.crc32(kwargs["messages"][-1]["content"].encode())
    if kind == "contribute":
        return _payload({"contribution": h % 21, "rationale": "r"})
    if kind == "punish":
        targets = [str(t) for t in range(1, 5) if t != agent]
        return _payload({"punishments": {t: (h >> i) & 1 for i, t in enumerate(targets)},
                         "rationale": "r"})
    return content


def _pkey(kwargs) -> tuple:
    return (kwargs["extra_body"]["session_id"], *PAPI.parse(kwargs))


class PunishmentCutResumeV4(ResumeBase):
    """Condition P with abstract_v4 (sha256-locked as in configs/main.json), comprehension
    on, rounds 3: a group game is 4 comprehension + 3 x (4 contribute + 4 punish) calls."""

    def pcfg(self, runs, **kw):
        locked = _json(MAIN)["frame_files"]["abstract_v4"]
        base = dict(run="p4", results_dir=None, runs_dir=runs, cards=[CARD_A],
                    models={"m1": "v/m1"}, frames={"abstract_v4": ["m1"]},
                    frame_files={"abstract_v4": locked}, conditions=("P",), arms=("group",),
                    comprehension=True, params=GameParams(rounds=3), groups_per_cell=1,
                    budget_usd=1.0, invalid_rate_cap=None)
        base.update(kw)
        return self.cfg(**base)

    def dir(self, name):
        d = self.tmp / f"{name}{len(list(self.tmp.iterdir()))}"
        d.mkdir()
        return d

    def uninterrupted(self, **kw):
        a = self.dir("A")
        api = PAPI(content_fn=_p_reply)
        self.use(api)
        Engine(self.pcfg(a, **kw)).run()
        return api, _rows(a / "p4" / "p4.jsonl")

    def check(self, api_a, rows_a, calls0, api1, engine, b, cut_call):
        """Every request is the uninterrupted run's; nothing answered asked again."""
        # (the four comprehension calls of a game share a key: their requests are equal)
        by_a = {_pkey(c): _request(c) for c in api_a.calls}
        for c in calls0 + api1.calls:
            self.assertEqual(_request(c), by_a[_pkey(c)], _pkey(c))
        answered0 = [c for c in calls0 if c is not cut_call]
        self.assertEqual(Counter(map(_request, answered0 + api1.calls)),
                         Counter(map(_request, api_a.calls)))
        valid = engine.valid_rows()
        self.assertEqual(_comparable(valid), _comparable(rows_a))
        summary = json.loads((b / "p4" / "p4_summary.json").read_text())
        self.assertEqual((summary["units"]["n_remaining"], summary["n_discarded"],
                          summary["n_reuse_invalid"]), (0, 0, 0))
        self.assertEqual(summary["n_answers_reused"], sum(r["reused"] for r in valid))
        self.assertEqual(summary["config"]["frame_setup"]["frames"]["abstract_v4"]["sha256"],
                         _sha(V4))
        punish = [r for r in valid if r["step"] == "punish"]
        self.assertEqual(len(punish), 4 * 3 * len(self.units))
        self.assertTrue(all(r["frame_id"] == "abstract_v4" for r in valid))
        return summary

    units = (0,)

    def serial_case(self, at, **kw):
        api_a, rows_a = self.uninterrupted(**kw)
        self.assertEqual(len(api_a.calls), 4 + 3 * 8)
        b = self.dir("B")
        api0 = PAPI()
        kill = _killer(api0, at)
        api0.content_fn = lambda k, c: kill(k, _p_reply(k, c))
        self.use(api0)
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            Engine(self.pcfg(b, **kw)).run()
        cut = api0.calls[at - 1]
        api1 = PAPI(content_fn=_p_reply)
        self.use(api1)
        engine = Engine(self.pcfg(b, **kw))
        engine.run(resume=True)
        self.assertEqual(len(api0.calls) + len(api1.calls), len(api_a.calls) + 1)
        return self.check(api_a, rows_a, api0.calls, api1, engine, b, cut), api0, api1

    def test_serial_cut_in_every_step(self):
        # call order: 4 comprehension, then per round 4 contribute + 4 punish
        for at, kind, rnd in ((3, "comprehension", None), (6, "contribute", 1),
                              (11, "punish", 1), (19, "punish", 2), (26, "punish", 3)):
            with self.subTest(at=at):
                summary, api0, _ = self.serial_case(at)
                self.assertEqual(PAPI.parse(api0.calls[at - 1])[0], kind)
                if rnd is not None:
                    self.assertEqual(PAPI.parse(api0.calls[at - 1])[2], rnd)

    def test_serial_punishment_cut_in_every_answer_format(self):
        for fmt in llm_client.ANSWER_FORMATS:
            with self.subTest(answer_format=fmt):
                summary, api0, api1 = self.serial_case(19, answer_format=fmt)
                if fmt != "schema_text":
                    self.assertEqual(summary["config"].get("answer_format"), fmt)
                if fmt == "json_schema_strict":
                    self.assertEqual(api1.calls[0]["response_format"]["type"], "json_schema")

    # -- workers=4, parallel_units=3: 2 cards x 2 groups = 4 group games (112 calls)

    def parallel_case(self, pred, k, answer_after=False, **kw):
        kw = dict(cards=[CARD_A, CARD_B], groups_per_cell=2, workers=4, parallel_units=3, **kw)
        self.units = (0, 1, 2, 3)
        api_a, rows_a = self.uninterrupted(**kw)
        self.assertEqual(len(api_a.calls), 4 * (4 + 3 * 8))
        b = self.dir("B")
        engine0 = Engine(self.pcfg(b, **kw))
        lock, counts, fired = threading.Lock(), Counter(), []

        def content_fn(kwargs, content):
            content = _p_reply(kwargs, content)
            kind, _, rnd, _ = PAPI.parse(kwargs)
            slot = (kwargs["extra_body"]["session_id"], kind, rnd)
            with lock:
                counts[slot] += 1
                fire = not fired and pred(slot) and counts[slot] == k
                if fire:
                    fired.append(kwargs)
            if fire:
                os.kill(os.getpid(), signal.SIGINT)
                deadline = time.monotonic() + 10
                while engine0._interrupted is None and time.monotonic() < deadline:
                    threading.Event().wait(0.005)
                if not answer_after:
                    return "not json"
            return content

        api0 = PAPI(content_fn=content_fn)
        self.use(api0)
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            engine0.run()
        self.assertEqual(len(fired), 1)
        self.assertLess(len(api0.calls), len(api_a.calls))
        api1 = PAPI(content_fn=_p_reply)
        self.use(api1)
        engine = Engine(self.pcfg(b, **kw))
        engine.run(resume=True)
        cut = None if answer_after else fired[0]
        return self.check(api_a, rows_a, api0.calls, api1, engine, b, cut), fired[0]

    def test_parallel_punishment_cut(self):
        for fmt in (None, "example_object"):
            with self.subTest(answer_format=fmt):
                summary, fired = self.parallel_case(
                    lambda s: s[1] == "punish" and s[2] == 2, 3, answer_format=fmt)
                self.assertEqual(PAPI.parse(fired)[0], "punish")
                self.assertGreaterEqual(summary["n_answers_reused"], 2)

    def test_parallel_contribution_cut_in_a_p_round(self):
        self.parallel_case(lambda s: s[1] == "contribute" and s[2] == 2, 4)

    def test_parallel_comprehension_cut(self):
        self.parallel_case(lambda s: s[1] == "comprehension", 3)

    def test_parallel_punishment_answer_arriving_after_the_signal(self):
        self.parallel_case(lambda s: s[1] == "punish" and s[2] == 3, 4, answer_after=True)


if __name__ == "__main__":
    unittest.main()
