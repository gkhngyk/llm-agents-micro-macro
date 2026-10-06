"""Mock tests of the mini-pilot model set and configs/minipilot.json (B1, B3).

No network, no ../.env: the OpenRouter client is a mock (EngineTestBase).
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_pgg_game import ROOT  # noqa: E402  (sets the dummy key before importing llm_client)
from test_pgg_guards import PILOT_CARDS_V2, PILOT_CONFIG, CostAPI, GuardTestBase  # noqa: E402

import llm_client  # noqa: E402
import pgg_cost  # noqa: E402
import pgg_game  # noqa: E402

MINIPILOT_CONFIG = ROOT / "configs" / "minipilot.json"
MISTRAL = "mistralai/mistral-large-4-0"
# Pinned providers of the mini-pilot (endpoints lists checked 2026-10-06):
# model key -> (slug, OpenRouter model, provider name the responses carry, quantizations).
MINIPILOT_PROVIDERS = {
    "deepseek": ("deepinfra/fp8", "deepseek/deepseek-v4.1-flash", "DeepInfra", ["fp8"]),
    "mistral": ("mistral", MISTRAL, "Mistral", None),
    "gpt": ("openai", "openai/gpt-6-luna", "OpenAI", None),
}
# Settings prereg_minipilot.md decides; the config leaves them open.
PREREG_SETTINGS = ("run", "cards", "cities", "conditions", "arms", "groups_per_cell",
                   "isolated_reps", "isolated_points", "isolated_frame", "rationale",
                   "seed_namespace", "max_invalid", "invalid_rate_cap",
                   "stop_on_length", "check_snapshot", "workers", "parallel_units", "frames")
# budget_usd (6) and expected_cost_gate_usd (4.5) are fixed by goal C5 (task #61);
# the story file is chosen with the story draft
NESTED_PREREG = ("frame_files.story",)


def _raw():
    return json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8"))


class MiniPilotConfig(unittest.TestCase):
    def test_models_and_providers(self):
        raw = _raw()
        models = pgg_game.resolve_models(raw["models"], pgg_cost.KNOWN_MODELS)
        self.assertEqual(models, llm_client.MODELS)
        self.assertEqual(models, {"deepseek": "deepseek/deepseek-v4.1-flash", "mistral": MISTRAL,
                                  "gpt": "openai/gpt-6-luna"})
        self.assertNotIn("google/gemini-2.5-flash-lite", raw["models"])
        self.assertEqual(set(raw["providers"]), set(MINIPILOT_PROVIDERS))
        for key, (slug, model, name, quant) in MINIPILOT_PROVIDERS.items():
            spec = raw["providers"][key]
            self.assertEqual(models[key], model)
            self.assertEqual((spec["slug"], spec["name"], spec.get("quantizations")),
                             (slug, name, quant))
            pgg_game.check_provider_spec(key, spec)
            routing = pgg_game.provider_routing(spec)
            self.assertEqual((routing["order"], routing["only"]), ([slug], [slug]))
            self.assertIs(routing["allow_fallbacks"], False)
            self.assertIs(routing["require_parameters"], True)
        # deepseek exactly as in pilot v2
        pilot = json.loads(PILOT_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(raw["providers"]["deepseek"], pilot["providers"]["deepseek"])

    def test_fixed_settings(self):
        raw = _raw()
        self.assertIs(raw["prereg_approved"], False)
        self.assertEqual(raw["max_tokens"], 16000)
        self.assertEqual((raw["request_deadline_s"], raw["stall_timeout_s"]), (900, 1800))
        self.assertEqual((raw["budget_usd"], raw["expected_cost_gate_usd"]), (6, 4.5))
        self.assertIs(raw["comprehension"], True)
        self.assertEqual(raw["isolated_round_no"], 5)
        self.assertNotIn("temperature", raw)
        self.assertNotIn("reasoning_effort", raw)
        self.assertEqual(raw["runs_dir"], json.loads(PILOT_CONFIG.read_text())["runs_dir"])

    def test_prereg_settings_are_open_placeholders(self):
        raw = _raw()
        for key in PREREG_SETTINGS:
            self.assertTrue(pgg_game.is_placeholder(raw[key]), key)
            self.assertTrue(raw[key].startswith("<TBD_PREREG"), key)
        self.assertEqual(sorted(pgg_game.open_choices(raw)),
                         sorted(PREREG_SETTINGS + NESTED_PREREG))
        self.assertIsNotNone(pgg_game.prereg_problem(raw))

    def test_prereg_lock_rule(self):
        self.assertIsNone(pgg_game.prereg_problem({}))          # no field: not gated
        self.assertIsNone(pgg_game.prereg_problem({"prereg_approved": True}))
        for value in (False, None, "true", 1, "<TBD_PREREG>"):
            self.assertIn("not true", pgg_game.prereg_problem({"prereg_approved": value}))
        self.assertFalse(any("prereg" in a.dest for a in pgg_game.build_parser()._actions))

    def test_pilot_v2_config_is_not_gated_and_still_resolves(self):
        pilot = json.loads(PILOT_CONFIG.read_text(encoding="utf-8"))
        self.assertNotIn("prereg_approved", pilot)
        self.assertIsNone(pgg_game.prereg_problem(pilot))
        self.assertEqual(pgg_game.resolve_models(pilot["models"], pgg_cost.KNOWN_MODELS),
                         llm_client.MODELS_PILOT_V2)
        self.assertEqual(pgg_game.resolve_models(pilot["models"], llm_client.MODELS_KNOWN),
                         llm_client.MODELS_PILOT_V2)

    def test_mistral_cost_is_a_marked_estimate(self):
        self.assertEqual(pgg_cost.PRICES_USD_PER_M[MISTRAL], (0.68, 2.09))
        self.assertEqual(pgg_cost.price(MISTRAL)[:2], (0.68, 2.09))
        entry = pgg_cost.CALIBRATION["models"][MISTRAL]
        self.assertIs(entry["estimate"], True)
        self.assertEqual(entry["kinds"]["isolated"]["reasoning_tokens"]["mean"], 0)  # task #59
        counts = pgg_cost.call_counts(n_cells=6)
        est = pgg_cost.estimate(pgg_cost.PILOT_MODELS, counts)
        self.assertEqual(est["unpriced"], [])
        self.assertIs(est["per_model"]["mistral"]["estimate"], True)
        self.assertIs(est["per_model"]["deepseek"]["estimate"], False)
        self.assertEqual(est["total_calls"], 1620)
        self.assertAlmostEqual(est["total_cost_usd"],
                               sum(m["cost_usd"] for m in est["per_model"].values()))
        text = pgg_cost.format_report(est)
        self.assertNotIn("maliyet tahmini yok", text)
        self.assertIn("mistral: pilot verisi yok", text)
        self.assertIn("endpoints list price", text)
        # the max_tokens ceiling: listed price, calibrated mean prompt tokens
        prompt = {k: entry["kinds"][k]["prompt_tokens"]["mean"] for k in ("contribute_N", "isolated")}
        ceiling = pgg_cost.ceiling({"mistral": MISTRAL}, counts, 16000)
        self.assertAlmostEqual(ceiling["mistral"],
                               (480 * (prompt["contribute_N"] * 0.68 + 16000 * 2.09)
                                + 60 * (prompt["isolated"] * 0.68 + 16000 * 2.09)) / 1e6)


class MiniPilotRuns(GuardTestBase):
    def filled_config(self, **overrides) -> Path:
        """The committed config with test values for every placeholder."""
        cards = self.tmp / "cards.json"
        cards.write_text(json.dumps([
            {"card_id": "x_minimal", "style": "minimal", "city": "X", "text": "Fake card X."},
            {"card_id": "y_minimal", "style": "minimal", "city": "Y", "text": "Fake card Y."},
        ]), encoding="utf-8")
        (self.tmp / "runs").mkdir(exist_ok=True)
        raw = _raw()
        raw.update({
            "prereg_approved": True, "run": "mini_mock", "cards": str(cards),
            "cities": ["X", "Y"], "conditions": ["N"], "arms": ["group", "isolated"],
            "groups_per_cell": 1, "isolated_reps": 1, "isolated_points": [0, 10, 20],
            "isolated_frame": "fixed_round", "rationale": True, "seed_namespace": "pgg-test",
            "frames": {"abstract_v3": ["deepseek", "mistral", "gpt"]}, "frame_files": None,
            "max_invalid": 3, "budget_usd": 1.0, "invalid_rate_cap": 0.5,
            "stop_on_length": True, "check_snapshot": True, "workers": 1,
            "parallel_units": 1, "runs_dir": str(self.tmp / "runs"),
            "params": {"rounds": 2}, "isolated_round_no": 2,
        })
        raw.update(overrides)
        path = self.tmp / "minipilot_filled.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        return path

    def main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = pgg_game.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_mock_run_sends_the_pinned_requests(self):
        names = {model: name for _, model, name, _ in MINIPILOT_PROVIDERS.values()}
        self.use(CostAPI(cost=0.0001, provider_fn=lambda k: names[k["model"]]))
        code, out, err = self.main("--config", str(self.filled_config()))
        self.assertEqual(code, 0, err)
        # per model: 2 cards x 1 group x 4 agents x 2 rounds + 2 cards x 3 values,
        # plus rule comprehension: 2 cards x 4 agents + 2 schedules
        self.assertEqual(len(self.api.calls), 3 * 32)
        mistral = [k for k in self.api.calls if k["model"] == MISTRAL]
        self.assertEqual(len(mistral), 32)
        for kwargs in self.api.calls:
            slug, _, _, quant = next(v for v in MINIPILOT_PROVIDERS.values()
                                     if v[1] == kwargs["model"])
            expected = {"order": [slug], "only": [slug], "allow_fallbacks": False,
                        "require_parameters": True}
            if quant:
                expected["quantizations"] = quant
            self.assertEqual(kwargs["extra_body"]["provider"], expected)
            self.assertEqual(kwargs["max_tokens"], 16000)
            self.assertNotIn("temperature", kwargs)                 # B3: not sent
            self.assertNotIn("reasoning", kwargs["extra_body"])      # B3: not sent
            self.assertNotIn("reasoning_effort", kwargs)
            self.assertEqual(kwargs["response_format"], {"type": "json_object"})
        self.assertEqual(mistral[0]["extra_body"]["provider"],
                         {"order": ["mistral"], "only": ["mistral"], "allow_fallbacks": False,
                          "require_parameters": True})
        run_dir = self.tmp / "runs" / "mini_mock"
        rows = [json.loads(x) for x in (run_dir / "mini_mock.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 96)
        self.assertEqual({r["frame"] for r in rows}, {"abstract_v3"})
        self.assertEqual({r["model"] for r in rows}, set(llm_client.MODELS.values()))
        self.assertEqual({(r["temperature"], r["reasoning_effort"]) for r in rows},
                         {("default", "default")})
        self.assertEqual({r["provider"] for r in rows if r["model"] == MISTRAL}, {"Mistral"})
        records = [json.loads(x) for x in (run_dir / "raw_calls.jsonl").read_text().splitlines()]
        calls = [r for r in records if r.get("model") == MISTRAL and "response_raw" in r]
        self.assertEqual(len(calls), 32)
        self.assertEqual({(r["temperature"], r["reasoning_effort"]) for r in calls},
                         {("default", "default")})

    def test_unapproved_prereg_refuses_a_real_run(self):
        self.use(CostAPI())
        # the committed config: refused by the lock before anything else
        code, _, err = self.main("--config", str(MINIPILOT_CONFIG))
        self.assertEqual(code, 1)
        self.assertIn("prereg_approved is false", err)
        self.assertIn("çağrı yapılmadı", err)
        # every placeholder filled, but not approved; also with --resume
        for value in (False, "true", None):
            path = self.filled_config(prereg_approved=value)
            for extra in ((), ("--resume",)):
                code, _, err = self.main("--config", str(path), *extra)
                self.assertEqual(code, 1)
                self.assertIn("not true", err)
        self.create.assert_not_called()
        self.assertFalse((self.tmp / "runs" / "mini_mock").exists())

    def test_approved_but_placeholder_left_refuses(self):
        self.use(CostAPI())
        path = self.filled_config(seed_namespace="<TBD_PREREG: seed namespace>")
        code, _, err = self.main("--config", str(path))
        self.assertEqual(code, 1)
        self.assertIn("seed_namespace", err)
        self.create.assert_not_called()
        self.assertFalse((self.tmp / "runs" / "mini_mock").exists())

    def test_dry_run_of_the_committed_config(self):
        code, out, err = self.main("--dry-run", "--config", str(MINIPILOT_CONFIG))
        self.assertEqual(code, 0, err)
        self.create.assert_not_called()
        self.assertIn("ÇAĞRI SAYISI HESAPLANAMADI", out)
        for key in ("conditions", "arms", "groups_per_cell", "isolated_reps", "isolated_points",
                    "cards", "cities"):
            self.assertIn(key, out.splitlines()[1])
        self.assertIn(f"mistral={MISTRAL}", out)
        self.assertIn("ÖN KAYIT ONAYI YOK", out)
        self.assertIn("SEÇİLMEMİŞ (gerçek koşu başlamaz)", out)
        self.assertIn("reasoning_effort=gönderilmez", out)
        self.assertIn("max_tokens=16000", out)
        self.assertIn("request_deadline_s=900", out)
        self.assertIn("stall_timeout_s=1800", out)

    def test_dry_run_counts_once_the_design_is_given(self):
        # CLI values on top of the placeholders (cards file: cities filter it)
        code, out, err = self.main(
            "--dry-run", "--config", str(MINIPILOT_CONFIG), "--cards", str(PILOT_CARDS_V2),
            "--cities", "Boston,Riyadh", "--conditions", "N", "--arms", "group,isolated",
            "--groups-per-cell", "2", "--isolated-reps", "2", "--points", "0,5,10,15,20",
            "--frames", "abstract_v3=deepseek,mistral,gpt", "--isolated-frame", "fixed_round")
        self.assertEqual(code, 0, err)
        # + rule comprehension: 6 cells x 2 groups x 4 agents + 6 x 2 schedules
        self.assertEqual(out.count("600 çağrı (contribute_N=480, isolated=60, comprehension=60)"), 3)
        self.assertIn("1800 çağrı", out)
        self.assertNotIn("maliyet tahmini yok", out)
        self.assertNotIn("HARİÇ", out)
        self.assertIn("mistral: pilot verisi yok", out)
        self.assertNotIn("HESAPLANAMADI", out)
        self.assertNotIn("ÖRNEK (tahmin)", out)
        # a placeholder cards file does not block when --cells is given
        code, out, _ = self.main(
            "--dry-run", "--config", str(MINIPILOT_CONFIG), "--cells", "2", "--conditions", "N",
            "--arms", "group", "--groups-per-cell", "1", "--isolated-reps", "1", "--points", "0",
            "--frames", "abstract_v3=deepseek,mistral,gpt")
        self.assertEqual(code, 0)
        self.assertEqual(out.count("88 çağrı"), 3)              # 2 cells x 1 group x 4 x (10 + 1)
        self.create.assert_not_called()

    def test_dry_run_subprocess_needs_no_key(self):
        env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
        proc = subprocess.run(
            [sys.executable, str(ROOT / "pgg_game.py"), "--dry-run", "--config",
             str(MINIPILOT_CONFIG)],
            capture_output=True, text=True, env=env, cwd=self.tmp, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ÇAĞRI SAYISI HESAPLANAMADI", proc.stdout)

    def test_pilot_v2_dry_run_unchanged(self):
        code, out, err = self.main("--dry-run", "--config", str(PILOT_CONFIG),
                                   "--cards", str(PILOT_CARDS_V2))
        self.assertEqual(code, 0, err)
        self.assertEqual(out.count("540 çağrı (contribute_N=480, isolated=60)"), 3)
        self.assertIn("gemini", out)
        self.assertIn("~0.6364 USD (tahmin)", out)
        self.assertNotIn("ÖN KAYIT", out)
        self.assertNotIn("HARİÇ", out)


if __name__ == "__main__":
    unittest.main()
