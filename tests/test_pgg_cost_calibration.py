"""Tests of the pilot v2 cost calibration (task B4): pgg_cost_calibrate.py and pgg_cost.py.

No network, no ../.env. The reproduction test needs only the committed
calibration JSON and fixed expected values, so it never skips; one extra test
re-derives the JSON from the real run directory and is skipped without it.
"""

import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_pgg_game import ROOT  # noqa: E402  (sets the dummy key before importing llm_client)
from test_pgg_guards import PILOT_CARDS_V2, PILOT_CONFIG  # noqa: E402

import pgg_cost  # noqa: E402
import pgg_cost_calibrate  # noqa: E402
import pgg_game  # noqa: E402

CALIBRATION_FILE = ROOT / "configs" / "cost_calibration_pilot_v2.json"
MINIPILOT_CONFIG = ROOT / "configs" / "minipilot.json"
MISTRAL = "mistralai/mistral-large-4-0"

# Billed total of pilot v2: runs/pilot_v2_20261005/pilot_v2_20261005_summary.json
# "total_cost_usd" (= sum of usage.cost in its raw log), per model "cost_usd".
ACTUAL_TOTAL_USD = 0.6364072616
ACTUAL_PER_MODEL_USD = {"deepseek": 0.5173644616, "gpt": 0.0680905, "gemini": 0.0509523}
TOLERANCE = 0.10

PILOT_V2_DIR = (Path(json.loads(PILOT_CONFIG.read_text(encoding="utf-8"))["runs_dir"])
                / "pilot_v2_20261005")


def _dry_run(*argv) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = pgg_game.main(["--dry-run", *argv])
    assert code == 0, code
    return buf.getvalue()


class PilotV2Reproduction(unittest.TestCase):
    def test_calibration_is_of_pilot_v2(self):
        cal = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
        self.assertEqual(cal["source"]["run"], "pilot_v2_20261005")
        self.assertAlmostEqual(cal["actual_total_cost_usd"], ACTUAL_TOTAL_USD, places=9)
        self.assertAlmostEqual(cal["recomputed_total_cost_usd"], ACTUAL_TOTAL_USD, places=9)
        self.assertEqual(cal["source"]["n_valid_rows"], 1620)

    def test_dry_run_of_pilot_config_within_ten_percent(self):
        text = _dry_run("--config", str(PILOT_CONFIG), "--cards", str(PILOT_CARDS_V2))
        self.assertEqual(text.count("540 çağrı (contribute_N=480, isolated=60)"), 3)
        total = re.search(r"^TOPLAM .*?1620 çağrı\s+~([0-9.]+) USD \(tahmin\)", text, re.M)
        self.assertIsNotNone(total, text)
        estimated = float(total.group(1))
        self.assertLessEqual(abs(estimated / ACTUAL_TOTAL_USD - 1), TOLERANCE,
                             f"estimated {estimated} vs actual {ACTUAL_TOTAL_USD}")
        self.assertIn("p95 üst sınır", text)
        self.assertIn("calibration: billed usage.cost_details", text)   # price source

    def test_estimate_per_model_within_ten_percent(self):
        est = pgg_cost.estimate(pgg_cost.PILOT_V2_MODELS, pgg_cost.call_counts(n_cells=6))
        self.assertEqual(est["unpriced"], [])
        for key, actual in ACTUAL_PER_MODEL_USD.items():
            m = est["per_model"][key]
            self.assertLessEqual(abs(m["cost_usd"] / actual - 1), TOLERANCE, key)
            self.assertIs(m["estimate"], False)
            self.assertEqual(m["extrapolated_kinds"], [])
            self.assertGreater(m["p95_upper_usd"], m["cost_usd"])
            self.assertAlmostEqual(m["cost_usd"], m["base_cost_usd"] + m["paid_invalid_usd"])
        self.assertLessEqual(abs(est["total_cost_usd"] / ACTUAL_TOTAL_USD - 1), TOLERANCE)
        self.assertGreater(est["total_p95_upper_usd"], est["total_cost_usd"])

    def test_paid_invalid_share_is_needed(self):
        # valid calls alone miss the billed total by more than the tolerance
        est = pgg_cost.estimate(pgg_cost.PILOT_V2_MODELS, pgg_cost.call_counts(n_cells=6))
        base = sum(m["base_cost_usd"] for m in est["per_model"].values())
        self.assertGreater(abs(base / ACTUAL_TOTAL_USD - 1), TOLERANCE)


class CalibrationFile(unittest.TestCase):
    def setUp(self):
        self.text = CALIBRATION_FILE.read_text(encoding="utf-8")
        self.cal = json.loads(self.text)

    def test_no_account_id_or_text(self):
        for needle in ("sk-or", "user_id", "org_id", "session_id", "pgg-pilot_v2",
                       "rationale", "messages", "Boston", "Riyadh"):
            self.assertNotIn(needle, self.text)
        self.assertNotRegex(self.text, r"gen-[A-Za-z0-9]{6,}")      # generation ids

    def test_models_kinds_and_flags(self):
        models = self.cal["models"]
        self.assertEqual(set(models), set(pgg_cost.KNOWN_MODELS.values()))
        for slug, m in models.items():
            self.assertIs(m["estimate"], slug == MISTRAL, slug)
            self.assertEqual(set(m["kinds"]), {"contribute_N", "isolated"})
            for kind, k in m["kinds"].items():
                for field in ("prompt_tokens", "completion_tokens"):
                    self.assertGreaterEqual(k[field]["p95"], k[field]["mean"], (slug, kind))
        for slug in pgg_cost.PILOT_V2_MODELS.values():
            m = models[slug]
            self.assertEqual((m["kinds"]["contribute_N"]["n"], m["kinds"]["isolated"]["n"]),
                             (480, 60))
            self.assertEqual(m["paid"]["n_valid"], 540)
            self.assertIn("cost_usd", m["kinds"]["isolated"])
            self.assertTrue(m["price_usd_per_m"]["source"].startswith("calibration"))

    def test_mistral_assumptions(self):
        m = self.cal["models"][MISTRAL]
        self.assertEqual((m["price_usd_per_m"]["input"], m["price_usd_per_m"]["output"]),
                         (0.68, 2.09))
        self.assertEqual(m["b2_measurement"]["reasoning_tokens"], 0)
        self.assertIs(m["b2_measurement"]["reasoning_tokens_field"], True)
        self.assertIs(m["paid"]["estimate"], True)
        self.assertGreaterEqual(len(m["assumptions"]), 4)
        measured = [self.cal["models"][s] for s in pgg_cost.PILOT_V2_MODELS.values()]
        for kind, k in m["kinds"].items():
            self.assertEqual(k["reasoning_tokens"]["mean"], 0)
            self.assertNotIn("cost_usd", k)
            means = [x["kinds"][kind]["prompt_tokens"]["mean"] for x in measured]
            self.assertAlmostEqual(k["prompt_tokens"]["mean"], sum(means) / 3, places=4)
            # p95 upper bound also covers reasoning: largest completion p95 measured
            self.assertEqual(k["completion_tokens"]["p95"],
                             max(x["kinds"][kind]["completion_tokens"]["p95"] for x in measured))

    @unittest.skipUnless((PILOT_V2_DIR / "pilot_v2_20261005.jsonl").is_file(),
                         "pilot v2 run directory not on this machine")
    def test_file_matches_the_run_directory(self):
        before = {p.name: (p.stat().st_size, p.stat().st_mtime_ns)
                  for p in PILOT_V2_DIR.iterdir()}
        self.assertEqual(pgg_cost_calibrate.calibrate(PILOT_V2_DIR), self.cal)
        after = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in PILOT_V2_DIR.iterdir()}
        self.assertEqual(after, before)                              # read only


class MiniPilotEstimate(unittest.TestCase):
    def test_placeholder_config_prints_example_at_pilot_v2_volume(self):
        # the committed config is filled since task #67; the placeholder state before it
        raw = json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8"))
        for k in ("run", "cards", "cities", "conditions", "arms", "groups_per_cell",
                  "isolated_reps", "isolated_points", "isolated_frame", "frames"):
            raw[k] = f"<TBD_PREREG: {k}>"
        raw["frame_files"] = {"story": "<TBD_PREREG: story frame file>"}
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "minipilot_placeholder.json"
            cfg_path.write_text(json.dumps(raw), encoding="utf-8")
            text = _dry_run("--config", str(cfg_path))
        self.assertIn("ÇAĞRI SAYISI HESAPLANAMADI", text)
        self.assertIn("ÖRNEK (tahmin)", text)
        self.assertEqual(text.count("540 çağrı (contribute_N=480, isolated=60)"), 3)
        self.assertEqual(text.count("KURU ÇALIŞTIRMA"), 1)
        self.assertIn("mistral: pilot verisi yok", text)
        self.assertNotIn("gemini", text)
        line = next(x for x in text.splitlines() if x.startswith("TOPLAM"))
        self.assertIn("1620 çağrı", line)
        self.assertIn("p95 üst sınır", line)

    def test_punishment_kinds_are_extrapolated_and_marked(self):
        counts = pgg_cost.call_counts(n_cells=6, conditions=("N", "P"))
        est = pgg_cost.estimate(pgg_cost.PILOT_MODELS, counts)
        for m in est["per_model"].values():
            self.assertEqual(m["extrapolated_kinds"], ["contribute_P", "punish_P"])
        p, c, extrapolated = pgg_cost.kind_tokens(MISTRAL, "punish_P")
        n_p, n_c, _ = pgg_cost.kind_tokens(MISTRAL, "contribute_N")
        self.assertTrue(extrapolated)
        self.assertAlmostEqual(p, n_p * 1590 / 1120)
        self.assertAlmostEqual(c, n_c * 80 / 60)
        self.assertIn("pilot v2'de yoktu", pgg_cost.format_report(est))

    def test_uncalibrated_model_is_unpriced(self):
        est = pgg_cost.estimate({"x": "vendor/unknown"}, pgg_cost.call_counts(n_cells=1))
        self.assertEqual(est["unpriced"], ["x"])
        self.assertIn("HARİÇ", pgg_cost.format_report(est))


def _usage(prompt, completion, reasoning, cost, prompt_share=0.25):
    return {"prompt_tokens": prompt, "completion_tokens": completion,
            "completion_tokens_details": {"reasoning_tokens": reasoning},
            "prompt_tokens_details": {"cached_tokens": 0}, "cost": cost,
            "cost_details": {"upstream_inference_prompt_cost": cost * prompt_share,
                             "upstream_inference_completions_cost": cost * (1 - prompt_share)}}


class CalibrateSyntheticRun(unittest.TestCase):
    """calibrate() on a tiny made-up run: every paid-call category once."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.run_dir = self.tmp / "fake_run"
        self.run_dir.mkdir()

        def row(arm, idx, segment, usage, rnd=1):
            r = {"model": "v/a", "model_key": "a", "card_id": "c1", "style": "s",
                 "condition": "N", "arm": arm, "step": "contribute", "round": rnd,
                 "session_id": f"pgg-fake-a-c1-s-N-{arm}-{idx:03d}", "usage": usage}
            if segment is not None:
                r["segment"] = segment
            return r

        valid = [row("group", 0, 1, _usage(100, 50, 40, 1.0)),
                 row("group", 0, 1, _usage(300, 150, 120, 2.0), rnd=2),
                 row("isolated", 0, None, _usage(80, 20, 0, 3.0))]
        superseded = [row("group", 0, None, _usage(100, 10, 0, 0.25))]
        rows = valid + superseded
        calls = [{"model": "v/a", "session_id": r["session_id"], "usage": r["usage"],
                  "finish_reason": "stop"} for r in rows]
        calls += [
            {"model": "v/a", "session_id": "x", "finish_reason": "error",
             "usage": _usage(0, 0, 0, 0.0)},                                  # provider error
            {"model": "v/a", "session_id": "x", "finish_reason": "stop",
             "usage": _usage(10, 10, 0, 0.5)},                                # paid, no row
            {"model": "v/a", "session_id": "x", "error": "timeout"},          # no usage
            {"event": "pgg_run_end", "run": "fake"},
        ]
        summary = {"run": "fake", "config": {"models": {"a": "v/a"}},
                   "providers": {"a": {"name": "P"}},
                   "superseded_units": [{"unit": "a|c1|s|N|group|0", "segment": 0, "n_rows": 1}],
                   "row_validity_rule": "rule", "planned_calls_per_model": 3,
                   "total_cost_usd": 6.75}
        (self.run_dir / "fake.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        (self.run_dir / "raw_calls.jsonl").write_text(
            "".join(json.dumps(c) + "\n" for c in calls))
        (self.run_dir / "fake_summary.json").write_text(json.dumps(summary))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_accounting(self):
        cal = pgg_cost_calibrate.calibrate(self.run_dir)
        self.assertAlmostEqual(cal["recomputed_total_cost_usd"], 6.75)
        m = cal["models"]["v/a"]
        paid = m["paid"]
        self.assertEqual((paid["n_paid_calls"], paid["n_valid"], paid["n_paid_invalid"],
                          paid["n_provider_error"], paid["n_superseded_rows"],
                          paid["n_paid_without_row"], paid["n_no_usage"]), (6, 3, 3, 1, 1, 1, 1))
        self.assertAlmostEqual(paid["valid_cost_usd"], 6.0)
        self.assertAlmostEqual(paid["paid_invalid_cost_usd"], 0.75)
        self.assertAlmostEqual(paid["superseded_cost_usd"], 0.25)
        self.assertAlmostEqual(paid["without_row_cost_usd"], 0.5)
        self.assertAlmostEqual(paid["paid_invalid_cost_ratio"], 0.125)
        self.assertAlmostEqual(paid["paid_invalid_call_rate"], 1.0)
        g = m["kinds"]["contribute_N"]
        self.assertEqual(g["n"], 2)
        self.assertEqual(g["prompt_tokens"], {"mean": 200, "p95": 290})    # 100 + 0.95 x 200
        self.assertEqual(g["reasoning_tokens"]["mean"], 80)
        self.assertEqual(g["visible_tokens"]["mean"], 20)
        self.assertEqual(m["kinds"]["isolated"]["cost_usd"], {"mean": 3.0, "p95": 3.0})
        # effective price = billed cost / tokens of the valid calls
        self.assertAlmostEqual(m["price_usd_per_m"]["input"], 6.0 * 0.25 / 480 * 1e6, places=3)
        self.assertAlmostEqual(m["price_usd_per_m"]["output"], 6.0 * 0.75 / 220 * 1e6, places=3)
        self.assertIs(cal["models"][MISTRAL]["estimate"], True)
        self.assertNotIn("pgg-fake", json.dumps(cal))

    def test_wrong_valid_count_is_an_error(self):
        summary = json.loads((self.run_dir / "fake_summary.json").read_text())
        summary["planned_calls_per_model"] = 4
        (self.run_dir / "fake_summary.json").write_text(json.dumps(summary))
        with self.assertRaises(ValueError):
            pgg_cost_calibrate.calibrate(self.run_dir)

    def test_refuses_to_write_into_the_run_directory(self):
        before = sorted(p.name for p in self.run_dir.iterdir())
        with contextlib.redirect_stderr(io.StringIO()):
            code = pgg_cost_calibrate.main(["--run-dir", str(self.run_dir),
                                            "--out", str(self.run_dir / "cal.json")])
        self.assertEqual(code, 1)
        self.assertEqual(sorted(p.name for p in self.run_dir.iterdir()), before)
        out = self.tmp / "cal.json"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(pgg_cost_calibrate.main(["--run-dir", str(self.run_dir),
                                                      "--out", str(out)]), 0)
        self.assertEqual(json.loads(out.read_text())["source"]["run"], "fake")


if __name__ == "__main__":
    unittest.main()
