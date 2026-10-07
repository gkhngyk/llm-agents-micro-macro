"""Tests of the M1 Mistral calibration overlay and the gate decision (task #71, EMIR 2 M2a).

No network, no ../.env, no write into a run directory. The synthetic tests
build a tiny M1 run and a tiny pilot run in a temporary directory; the
reproduction test re-derives the committed overlay from the real run
directories and is skipped without them.
"""

import contextlib
import hashlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_pgg_game import ROOT  # noqa: E402  (sets the dummy key before importing llm_client)
from test_pgg_guards import PILOT_CONFIG  # noqa: E402

import pgg_cost  # noqa: E402
import pgg_cost_calibrate  # noqa: E402
import pgg_frames  # noqa: E402
import pgg_game  # noqa: E402

MISTRAL = "mistralai/mistral-large-4-0"
BASE_FILE = ROOT / "configs" / "cost_calibration_pilot_v2.json"
M1_FILE = ROOT / "configs" / "cost_calibration_minipilot_m1.json"
# abstract_v3 as M1 ran it (before task #73's q2 sentence)
M1_FRAME_SHA256 = "9bdc919a0eebe1991e69212e9144e6ef49622da0f20cd9886bd94ded312bf163"
MINIPILOT_CONFIG = ROOT / "configs" / "minipilot.json"
RUNS_DIR = Path(json.loads(PILOT_CONFIG.read_text(encoding="utf-8"))["runs_dir"])
M1_DIR = RUNS_DIR / "tesisat_olcum_20261007"
PILOT_V2_DIR = RUNS_DIR / "pilot_v2_20261005"
GATE = 4.5

# workspace/gorev_tesisat_olcum.md (task #70), section 1.1 and 1.2
M1_REPORT = {"n": {"contribute_N": 12, "isolated": 6},
             "completion_mean": {"contribute_N": 2511.166667, "isolated": 2851.5},
             "prompt_mean": {"contribute_N": 387.0, "isolated": 377.0},
             "cost_usd_sum": 0.10343395, "elapsed_s_max": 173.757,
             "n_reasoning_gt_completion": 11}


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class OverlayFile(unittest.TestCase):
    def setUp(self):
        self.text = M1_FILE.read_text(encoding="utf-8")
        self.cal = json.loads(self.text)
        self.entry = self.cal["models"][MISTRAL]

    def test_no_account_id_or_text(self):
        for needle in ("sk-or", "user_id", "org_id", "session_id", "rationale\"", "messages",
                       "Boston", "Riyadh", "boston", "riyadh", "pgg-tesisat"):
            self.assertNotIn(needle, self.text)
        self.assertNotRegex(self.text, r"gen-[A-Za-z0-9]{6,}")

    def test_only_mistral_and_its_source(self):
        self.assertEqual(list(self.cal["models"]), [MISTRAL])
        self.assertEqual(self.cal["overlay_of"], BASE_FILE.name)
        self.assertEqual(self.cal["source"]["run"], "tesisat_olcum_20261007")
        self.assertEqual(self.cal["source"]["n_mistral_rows"], 18)
        # M1 ran abstract_v3 before task #73 changed its q2 text (rule comprehension,
        # not measured in M1): the source keeps M1's sha256; calibrate_mistral_m1
        # re-renders every M1 prompt with today's file (test_file_matches_...)
        self.assertEqual(self.cal["source"]["frame_sha256"], M1_FRAME_SHA256)
        self.assertNotEqual(_sha(ROOT / "frames" / "abstract_v3.json"), M1_FRAME_SHA256)
        # the pilot v2 calibration (task #60) is the file the overlay was made on, unchanged
        self.assertEqual(self.cal["source"]["base_sha256"], _sha(BASE_FILE))

    def test_measured_numbers_are_the_m1_report(self):
        m = self.entry["measured"]
        for kind in ("contribute_N", "isolated"):
            self.assertEqual(m[kind]["n"], M1_REPORT["n"][kind])
            self.assertAlmostEqual(m[kind]["completion_tokens"]["mean"],
                                   M1_REPORT["completion_mean"][kind], places=5)
            self.assertAlmostEqual(m[kind]["prompt_tokens"]["mean"], M1_REPORT["prompt_mean"][kind])
        self.assertAlmostEqual(m["cost_usd_sum"], M1_REPORT["cost_usd_sum"], places=9)
        self.assertAlmostEqual(m["elapsed_s_max"], M1_REPORT["elapsed_s_max"], places=3)
        self.assertEqual(m["n_reasoning_gt_completion"], M1_REPORT["n_reasoning_gt_completion"])
        self.assertEqual(m["n_invalid"], 0)
        self.assertEqual((self.entry["price_usd_per_m"]["input"],
                          self.entry["price_usd_per_m"]["output"]), (0.68, 2.09))

    def test_later_rounds_rule_and_labels(self):
        later = self.entry["later_rounds"]
        self.assertEqual(later["rule"], "pilot_v2_max")
        self.assertEqual(later["ratio_run"], "pilot_v2_20261005")
        self.assertIn("(tahmin)", later["text"])
        self.assertTrue(all("(tahmin)" in a for a in self.entry["assumptions"][:4]))
        self.assertIn("(tahmin)", self.entry["report_note"])
        for kind, k in self.entry["kinds"].items():
            used = {s: max(later["ratios"][key][kind][s] for key in ("deepseek", "gpt"))
                    for s in ("mean", "p95")}
            self.assertEqual(k["completion_ratio_used"], used)
            measured = self.entry["measured"][kind]["completion_tokens"]
            for s in ("mean", "p95"):
                self.assertAlmostEqual(k["completion_tokens"][s], measured[s] * used[s], places=4)
                self.assertGreaterEqual(k["completion_tokens"]["p95"], k["completion_tokens"]["mean"])
                self.assertGreaterEqual(k["prompt_tokens"]["p95"], k["prompt_tokens"]["mean"])
        # pilot v2's reasoning models think less after round 1: the ratio is below 1
        self.assertLess(self.entry["kinds"]["contribute_N"]["completion_ratio_used"]["mean"], 1)
        # paid-but-invalid: the pooled pilot v2 share, as before (tahmin)
        base = json.loads(BASE_FILE.read_text(encoding="utf-8"))["models"][MISTRAL]["paid"]
        self.assertEqual(self.entry["paid"]["paid_invalid_cost_ratio"],
                         base["paid_invalid_cost_ratio"])
        self.assertIs(self.entry["paid"]["estimate"], True)

    @unittest.skipUnless((M1_DIR / "results.jsonl").is_file()
                         and (PILOT_V2_DIR / "pilot_v2_20261005.jsonl").is_file(),
                         "M1 or pilot v2 run directory not on this machine")
    def test_file_matches_the_run_directories(self):
        before = {d: {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in d.iterdir()}
                  for d in (M1_DIR, PILOT_V2_DIR)}
        self.assertEqual(pgg_cost_calibrate.calibrate_mistral_m1(M1_DIR, PILOT_V2_DIR), self.cal)
        after = {d: {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in d.iterdir()}
                 for d in (M1_DIR, PILOT_V2_DIR)}
        self.assertEqual(after, before)                              # read only


class LoadCalibration(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_overlay_replaces_mistral_only(self):
        base = json.loads(BASE_FILE.read_text(encoding="utf-8"))
        cal = pgg_cost.CALIBRATION
        self.assertEqual(cal["overlays"], [{"file": M1_FILE.name, "run": "tesisat_olcum_20261007",
                                            "models": [MISTRAL]}])
        self.assertEqual(cal["overlays_missing"], [])
        self.assertEqual(cal["models"][MISTRAL], json.loads(M1_FILE.read_text())["models"][MISTRAL])
        for slug in pgg_cost.PILOT_V2_MODELS.values():               # DeepSeek, GPT, Gemini
            self.assertEqual(cal["models"][slug], base["models"][slug])
        self.assertEqual(cal["source"], base["source"])
        self.assertIn(f"Üzerine yazılan: configs/{M1_FILE.name} (koşu tesisat_olcum_20261007",
                      pgg_cost.SOURCE_NOTE)
        self.assertIs(pgg_cost.load_calibration(overlays=())["models"][MISTRAL]["estimate"], True)

    def test_missing_overlay_is_listed(self):
        cal = pgg_cost.load_calibration(overlays=(self.tmp / "nope.json",))
        self.assertEqual(cal["overlays"], [])
        self.assertEqual(cal["overlays_missing"], ["nope.json"])
        self.assertIs(cal["models"][MISTRAL]["estimate"], True)

    def test_bad_overlays_are_errors(self):
        over = json.loads(M1_FILE.read_text(encoding="utf-8"))
        wrong_base = dict(over, overlay_of="other.json")
        (self.tmp / "a.json").write_text(json.dumps(wrong_base))
        with self.assertRaisesRegex(ValueError, "overlay of"):
            pgg_cost.load_calibration(overlays=(self.tmp / "a.json",))
        no_kind = json.loads(M1_FILE.read_text(encoding="utf-8"))
        del no_kind["models"][MISTRAL]["kinds"]["isolated"]
        (self.tmp / "b.json").write_text(json.dumps(no_kind))
        with self.assertRaisesRegex(ValueError, "lacks"):
            pgg_cost.load_calibration(overlays=(self.tmp / "b.json",))

    def test_pilot_v2_estimate_unchanged(self):
        # DeepSeek and GPT (and Gemini) priced as before: pilot v2 within ten percent
        est = pgg_cost.estimate(pgg_cost.PILOT_V2_MODELS, pgg_cost.call_counts(n_cells=6))
        self.assertLessEqual(abs(est["total_cost_usd"] / 0.6364072616 - 1), 0.10)


def _usage(prompt, completion, reasoning, cost, prompt_share=0.1):
    return {"prompt_tokens": prompt, "completion_tokens": completion,
            "completion_tokens_details": {"reasoning_tokens": reasoning},
            "cost": cost,
            "cost_details": {"upstream_inference_prompt_cost": cost * prompt_share,
                             "upstream_inference_completions_cost": cost * (1 - prompt_share)}}


class CalibrateSyntheticM1(unittest.TestCase):
    """calibrate_mistral_m1() on a made-up M1 run (3 Boston cards) and pilot run."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.m1, self.pilot = self.tmp / "m1", self.tmp / "pilot"
        self.m1.mkdir()
        self.pilot.mkdir()
        params = pgg_game.GameParams()
        frame = pgg_frames.load_frame(pgg_frames.frame_path("abstract_v3"))
        cards = pgg_game.load_cards(ROOT / "cards" / "pilot_cards_v3.json", ["Boston"])
        rows = []
        for i, card in enumerate(cards):
            base = {"model": MISTRAL, "model_key": "mistral", "ok": True, "n_invalid": 0,
                    "card_id": card.card_id, "style": card.style, "provider": "Mistral",
                    "model_version": "mistralai/mistral-large-4-0-x", "finish_reason": "stop"}
            msgs = pgg_game.contribution_messages(params, "N", card, [], 0, 1, prompt_frame=frame)
            rows.append({**base, "step": "contribute", "round": 1, "agent_id": 1,
                         "others_mean": None, "prompt_messages": msgs, "elapsed_s": 10.0 + i,
                         "reasoning_tokens": 900, "completion_tokens": 1000 + 100 * i,
                         "usage": _usage(400, 1000 + 100 * i, 900, 0.002)})
            msgs = pgg_game.isolated_messages(params, card, 10, "fixed_round", 5,
                                              prompt_frame=frame)
            rows.append({**base, "step": "isolated", "round": 5, "agent_id": 1,
                         "others_mean": 10, "prompt_messages": msgs, "elapsed_s": 50.0,
                         "reasoning_tokens": 2100, "completion_tokens": 2000,
                         "usage": _usage(380, 2000, 2100, 0.004)})
        rows.append({"model": "openai/gpt-6-luna", "model_key": "gpt", "ok": True})  # not Mistral
        self.summary = {
            "run": "m1_fake", "frame": "abstract_v3",
            "frame_sha256": _sha(pgg_frames.frame_path("abstract_v3")),
            "cards": "cards/pilot_cards_v3.json", "cities": ["Boston"],
            "isolated_frame": "fixed_round", "isolated_round_no": 5, "isolated_x": 10,
            "cost_by_model_usd": {"mistral": 0.018}, "n_attempts_sent": {"mistral": 6},
            "n_responses_billed": {"mistral": 6}}
        self.rows = rows
        self.write_m1()

        def prow(key, arm, rnd, others, completion, idx=0):
            return {"model": f"v/{key}", "model_key": key, "card_id": "c1", "style": "s",
                    "condition": "N", "arm": arm, "step": "contribute", "round": rnd,
                    "others_mean": others,
                    "session_id": f"pgg-fake-{key}-c1-s-N-{arm}-{idx:03d}",
                    "usage": {"completion_tokens": completion}}
        pilot_rows = []
        for key, (r1, r2, x10, x0) in {"deepseek": (1000, 200, 400, 400),
                                       "gpt": (100, 60, 100, 120)}.items():
            pilot_rows += [prow(key, "group", 1, None, r1), prow(key, "group", 2, None, r2),
                           prow(key, "isolated", 5, 10, x10), prow(key, "isolated", 5, 0, x0)]
        (self.pilot / "pilot_fake.jsonl").write_text("".join(json.dumps(r) + "\n" for r in pilot_rows))
        (self.pilot / "pilot_fake_summary.json").write_text(json.dumps(
            {"run": "pilot_fake", "superseded_units": []}))

    def write_m1(self):
        (self.m1 / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in self.rows))
        (self.m1 / "summary.json").write_text(json.dumps(self.summary))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_calibration(self):
        cal = pgg_cost_calibrate.calibrate_mistral_m1(self.m1, self.pilot)
        self.assertEqual(cal["source"]["run"], "m1_fake")
        self.assertEqual(cal["source"]["n_mistral_rows"], 6)
        e = cal["models"][MISTRAL]
        self.assertIs(e["estimate"], False)
        # ratios: deepseek (600 / 1000, 400 / 400), gpt (80 / 100, 110 / 100); the larger is used
        r = e["later_rounds"]["ratios"]
        self.assertAlmostEqual(r["deepseek"]["contribute_N"]["mean"], 0.6)
        self.assertAlmostEqual(r["gpt"]["contribute_N"]["mean"], 0.8)
        self.assertAlmostEqual(r["gpt"]["isolated"]["mean"], 1.1)
        c, i = e["kinds"]["contribute_N"], e["kinds"]["isolated"]
        self.assertAlmostEqual(c["completion_tokens"]["mean"], 1100 * 0.8, places=4)
        self.assertAlmostEqual(i["completion_tokens"]["mean"], 2000 * 1.1, places=4)
        # prompt: M1 tokens per character x abstract_v2 characters over all rounds
        m = e["measured"]["contribute_N"]
        self.assertAlmostEqual(m["prompt_tokens_per_char"], 400 / m["prompt_chars_mean"], places=6)
        self.assertAlmostEqual(c["prompt_tokens"]["mean"],
                               m["prompt_tokens_per_char"] * c["abstract_v2_prompt_chars_mean"],
                               places=2)
        self.assertGreater(c["abstract_v2_prompt_chars_mean"], m["prompt_chars_mean"])  # history
        self.assertEqual(e["measured"]["n_reasoning_gt_completion"], 3)    # the isolated rows
        self.assertEqual(e["measured"]["elapsed_s_max"], 50.0)
        self.assertAlmostEqual(e["price_usd_per_m"]["output"],
                               0.018 * 0.9 / (3300 + 6000) * 1e6, places=3)
        self.assertNotIn("Boston", json.dumps(cal))
        # the other rule: round 1 / X = 10 values unchanged
        r1 = pgg_cost_calibrate.calibrate_mistral_m1(self.m1, self.pilot, later_rounds="round1")
        k = r1["models"][MISTRAL]["kinds"]["contribute_N"]
        self.assertEqual(k["completion_ratio_used"], {"mean": 1.0, "p95": 1.0})
        self.assertAlmostEqual(k["completion_tokens"]["mean"], 1100, places=4)
        with self.assertRaises(ValueError):
            pgg_cost_calibrate.calibrate_mistral_m1(self.m1, self.pilot, later_rounds="other")

    def test_prompt_of_another_code_is_an_error(self):
        self.rows[0]["prompt_messages"][-1]["content"] += " changed"
        self.write_m1()
        with self.assertRaisesRegex(ValueError, "differs from this code"):
            pgg_cost_calibrate.calibrate_mistral_m1(self.m1, self.pilot)

    def test_cost_not_the_summary_is_an_error(self):
        self.summary["cost_by_model_usd"]["mistral"] = 0.5
        self.write_m1()
        with self.assertRaisesRegex(ValueError, "usage.cost"):
            pgg_cost_calibrate.calibrate_mistral_m1(self.m1, self.pilot)

    def test_cli_writes_outside_the_run_directories_only(self):
        with contextlib.redirect_stderr(io.StringIO()):
            code = pgg_cost_calibrate.main(["--m1-run-dir", str(self.m1), "--ratio-run-dir",
                                            str(self.pilot), "--out", str(self.m1 / "x.json")])
        self.assertEqual(code, 1)
        self.assertFalse((self.m1 / "x.json").exists())
        out = self.tmp / "m1.json"
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            code = pgg_cost_calibrate.main(["--m1-run-dir", str(self.m1), "--ratio-run-dir",
                                            str(self.pilot), "--out", str(out)])
        self.assertEqual(code, 0)
        self.assertIn("sonraki turlar: pilot_v2_max", buf.getvalue())
        self.assertEqual(json.loads(out.read_text())["source"]["run"], "m1_fake")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            pgg_cost_calibrate.main(["--m1-run-dir", str(self.m1)])    # needs --ratio-run-dir


class GateDecision(unittest.TestCase):
    """EMIR 3 Part 1-2 (task #73): gate 4.5 USD on the mean. Over it the run is not
    started and the overrun is reported; no arm is dropped (EMIR 2's fallback, which
    dropped Mistral's abstract_v3 arm first, is gone)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def dry(self, raw: dict) -> tuple[float, str]:
        path = self.tmp / "mp.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(pgg_game.main(["--dry-run", "--config", str(path)]), 0)
        text = out.getvalue()
        total = float(re.search(r"^TOPLAM .*?~([0-9.]+) USD \(tahmin", text, re.M).group(1))
        return total, text

    def test_committed_config_is_the_emir3_design_and_passes(self):
        raw = json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(raw["frames"], {"abstract_v3": ["deepseek", "mistral", "gpt"],
                                         "story": ["deepseek", "gpt"]})
        self.assertEqual(raw["expected_cost_gate_usd"], GATE)
        self.assertIs(raw["prereg_approved"], False)
        total, text = self.dry(raw)
        self.assertLessEqual(total, GATE)
        self.assertIn("Beklenti kapısı expected_cost_gate_usd=4.5 USD: GEÇER", text)
        # Mistral only in abstract_v3: its arm is there, its story arm is not
        self.assertRegex(text, r"(?m)^abstract_v3\s+mistral\s")
        self.assertNotRegex(text, r"(?m)^story\s+mistral\s")
        # no fallback text anywhere: EMIR 2's drop rule is gone from config and code
        for needle in ("pre-specified fallback", "abstract_v3 arm is dropped", "budget_usd = 6",
                       "mistral 3, deepseek 2", "story = deepseek, mistral"):
            self.assertNotIn(needle, raw["_notes"])
        self.assertIn("no arm is dropped", raw["_notes"])
        self.assertNotIn("fallback", Path(pgg_game.__file__).read_text(encoding="utf-8")
                         .split("def gate_problem", 1)[1].split("def model_budget_lines", 1)[0])

    def test_over_the_gate_is_reported_not_trimmed(self):
        raw = json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8"))
        total, text = self.dry(dict(raw, expected_cost_gate_usd=1.0))
        self.assertGreater(total, 1.0)
        self.assertIn("Beklenti kapısı expected_cost_gate_usd=1 USD: AŞILIYOR — gerçek koşu "
                      "BAŞLAMAZ", text)
        self.assertIn("no arm is dropped", text)
        # every arm of the design is still priced (nothing removed)
        self.assertEqual(len(re.findall(r"(?m)^(abstract_v3|story)\s+(deepseek|mistral|gpt)\s",
                                        text)), 5)
        self.assertIn("3000 çağrı", text)

    def test_gate_problem_follows_the_mean(self):
        rows = [{"frame": "f", "model": "m", "cost_usd": 4.4}]
        self.assertIsNone(pgg_game.gate_problem(
            {"unpriced": [], "total_cost_usd": 4.5, "rows": rows}, GATE))
        self.assertIn("above", pgg_game.gate_problem(
            {"unpriced": [], "total_cost_usd": 4.5001, "rows": rows}, GATE))

    def test_mistral_round1_values_would_be_over_the_gate(self):
        # sensitivity (report): with Mistral's round 1 / X = 10 values for every
        # round the EMIR 3 design is over the gate (it would not be run)
        entry = json.loads(M1_FILE.read_text(encoding="utf-8"))["models"][MISTRAL]
        alt = json.loads(json.dumps(entry))
        for kind, k in alt["kinds"].items():
            k["completion_tokens"] = dict(entry["measured"][kind]["completion_tokens"])
        cal = json.loads(json.dumps(pgg_cost.CALIBRATION))
        cal["models"][MISTRAL] = alt
        with mock.patch.object(pgg_cost, "CALIBRATION", cal):
            total, _ = self.dry(json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8")))
        self.assertGreater(total, GATE)


if __name__ == "__main__":
    unittest.main()
