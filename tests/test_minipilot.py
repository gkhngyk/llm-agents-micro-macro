"""Mock tests of the mini-pilot model set and configs/minipilot.json (B1, B3).

No network, no ../.env: the OpenRouter client is a mock (EngineTestBase).
"""

import contextlib
import hashlib
import io
import json
import os
import re
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
# Settings prereg_minipilot.md decides (EMIR 2 Part 1, filled in task #67).
PREREG_SETTINGS = ("run", "cards", "cities", "conditions", "arms", "groups_per_cell",
                   "isolated_reps", "isolated_points", "isolated_frame", "rationale",
                   "seed_namespace", "max_invalid", "invalid_rate_cap",
                   "stop_on_length", "check_snapshot", "workers", "parallel_units", "frames")
# The values of task #67 (Part 1; the TBD fields from prereg_minipilot.md's settings table).
DECIDED = {
    "run": "minipilot_{run_date}", "cards": "cards/pilot_cards_v3.json",
    "cities": ["Boston", "Riyadh"], "conditions": ["N"], "arms": ["group", "isolated"],
    "groups_per_cell": 2, "isolated_reps": 2, "isolated_points": [0, 5, 10, 15, 20],
    "isolated_frame": "fixed_round", "rationale": True, "seed_namespace": "pgg-minipilot",
    "max_invalid": 3, "invalid_rate_cap": 0.05, "stop_on_length": True, "check_snapshot": True,
    "workers": 4, "parallel_units": 3,
    # EMIR 3 Part 1 (task #73): Mistral plays abstract_v3 only (its E3 suitability
    # is measured in the main frame); the frame comparison is within DeepSeek and GPT
    "frames": {"abstract_v3": ["deepseek", "mistral", "gpt"],
               "story": ["deepseek", "gpt"]},
}
FRAME_FILES = {"abstract_v3": "frames/abstract_v3.json", "story": "frames/story_A.json"}


def _raw():
    return json.loads(MINIPILOT_CONFIG.read_text(encoding="utf-8"))


def placeholder_config(tmp: Path) -> Path:
    """The committed config with the design settings open again ("<TBD_PREREG: ...>"),
    as it was before task #67: for the tests of the placeholder paths of the dry run."""
    raw = _raw()
    for key in PREREG_SETTINGS:
        raw[key] = f"<TBD_PREREG: {key}>"
    raw["frame_files"] = {"story": "<TBD_PREREG: story frame file>"}
    raw.pop("cards_sha256")            # task #73's cards lock did not exist then
    raw["prereg_approved"] = False     # nor the approval (task #75)
    path = Path(tmp) / "minipilot_placeholders.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def committed_copy(tmp: Path, **overrides) -> Path:
    """A copy of the committed config with only `overrides` changed and runs_dir always
    in `tmp`: since the approval (task #75) a real run of the committed config itself
    would start and write to the real runs_dir, so tests run copies."""
    raw = _raw()
    (Path(tmp) / "runs").mkdir(exist_ok=True)
    raw["runs_dir"] = str(Path(tmp) / "runs")
    raw.update(overrides)
    path = Path(tmp) / "minipilot_copy.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


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
        self.assertIs(raw["prereg_approved"], True)        # approved 2026-10-07 (task #75)
        self.assertEqual(raw["max_tokens"], 16000)
        self.assertEqual((raw["request_deadline_s"], raw["stall_timeout_s"]), (900, 1800))
        self.assertEqual((raw["budget_usd"], raw["expected_cost_gate_usd"]), (10, 4.5))
        self.assertIs(raw["comprehension"], True)
        self.assertEqual(raw["isolated_round_no"], 5)
        self.assertNotIn("temperature", raw)
        self.assertNotIn("reasoning_effort", raw)
        self.assertEqual(raw["runs_dir"], json.loads(PILOT_CONFIG.read_text())["runs_dir"])

    def test_prereg_settings_are_the_part_one_decisions(self):
        raw = _raw()
        for key, value in DECIDED.items():
            self.assertEqual(raw[key], value, key)
        self.assertEqual(pgg_game.open_choices(raw), [])           # no TBD_PREREG left
        self.assertNotIn("TBD", json.dumps({k: v for k, v in raw.items() if k != "_notes"}))
        # ... and approved by the user (prereg_minipilot.md, 2026-10-07, EMIR 3; task #75)
        self.assertIs(raw["prereg_approved"], True)
        self.assertIsNone(pgg_game.prereg_problem(raw))
        # every frame file is locked with the sha256 of the committed file
        self.assertEqual(set(raw["frame_files"]), set(FRAME_FILES))
        for label, rel in FRAME_FILES.items():
            entry = raw["frame_files"][label]
            self.assertEqual(entry["path"], rel)
            self.assertEqual(entry["sha256"],
                             hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), label)
        self.assertEqual(pgg_game.load_frame_file("story", raw["frame_files"]["story"]).kind,
                         "story")
        self.assertEqual(
            pgg_game.load_frame_file("abstract_v3", raw["frame_files"]["abstract_v3"]).kind,
            "abstract")
        # the cards: v3 as checked before the copy (a4f50d0f...a9aa), 6 cards of 2 cities,
        # locked by cards_sha256 (task #73, EMIR 3 3e)
        sha = hashlib.sha256((ROOT / raw["cards"]).read_bytes()).hexdigest()
        self.assertTrue(sha.startswith("a4f50d0f") and sha.endswith("a9aa"), sha)
        self.assertEqual(raw["cards_sha256"], sha)
        self.assertEqual(pgg_game.check_cards_lock(ROOT / raw["cards"], raw["cards_sha256"]), sha)
        # Mistral's reasoning_capped rule (task #73, EMIR 3 3a); the others the default
        self.assertEqual(raw["reasoning_cap_rule"], {"mistral": "max_reasoning_completion"})
        cards = pgg_game.load_cards(ROOT / raw["cards"], raw["cities"])
        self.assertEqual(sorted((c.card_id, c.style) for c in cards),
                         sorted((f"{city}_{style}", style) for city in ("boston", "riyadh")
                                for style in ("minimal", "value", "factual")))
        # the story frame of the workspace that was not chosen (draft B) is not in the repo
        self.assertFalse(list((ROOT / "frames").glob("*story_B*")))

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
        # task #71: the M1 overlay replaces pilot v2's "estimate": true entry
        base = pgg_cost.load_calibration(overlays=())["models"][MISTRAL]
        self.assertIs(base["estimate"], True)
        self.assertEqual(base["kinds"]["isolated"]["reasoning_tokens"]["mean"], 0)  # task #59
        entry = pgg_cost.CALIBRATION["models"][MISTRAL]
        self.assertIs(entry["estimate"], False)
        self.assertGreater(entry["measured"]["isolated"]["reasoning_tokens"]["mean"], 1000)
        self.assertTrue(entry["assumptions"])
        self.assertIn("(tahmin)", entry["later_rounds"]["text"])
        counts = pgg_cost.call_counts(n_cells=6)
        est = pgg_cost.estimate(pgg_cost.PILOT_MODELS, counts)
        self.assertEqual(est["unpriced"], [])
        self.assertIs(est["per_model"]["mistral"]["estimate"], False)
        self.assertIs(est["per_model"]["mistral"]["lower_bound"], False)
        self.assertIs(est["per_model"]["deepseek"]["estimate"], False)
        self.assertEqual(est["total_calls"], 1620)
        self.assertAlmostEqual(est["total_cost_usd"],
                               sum(m["cost_usd"] for m in est["per_model"].values()))
        text = pgg_cost.format_report(est)
        self.assertNotIn("maliyet tahmini yok", text)
        self.assertIn("mistral: kalibrasyon M1 tesisat ölçümü tesisat_olcum_20261007", text)
        self.assertIn("tesisat_olcum_20261007 (M1)", text)          # price source
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
            "cards_sha256": hashlib.sha256(cards.read_bytes()).hexdigest(),
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
        # the committed config with the approval taken back: refused by the lock before
        # anything else (the committed config itself is approved since task #75)
        code, _, err = self.main("--config", str(committed_copy(self.tmp, prereg_approved=False)))
        self.assertEqual(code, 1)
        self.assertIn("prereg_approved is false", err)
        self.assertIn("çağrı yapılmadı", err)
        self.assertEqual(list((self.tmp / "runs").iterdir()), [])
        # every placeholder filled, but not approved; also with --resume
        for value in (False, "true", None):
            path = self.filled_config(prereg_approved=value)
            for extra in ((), ("--resume",)):
                code, _, err = self.main("--config", str(path), *extra)
                self.assertEqual(code, 1)
                self.assertIn("not true", err)
        self.create.assert_not_called()
        self.assertFalse((self.tmp / "runs" / "mini_mock").exists())

    def test_approved_committed_config_passes_the_lock(self):
        # task #75: the committed config is approved, so the lock lets a real run start.
        # Shown on a copy (mock client, runs_dir in tmp, a small design); the approval,
        # frames, frame and cards locks, providers and budgets are the committed ones.
        class AnyFrameAPI(CostAPI):
            # story_A names no "Player n" / "ROUND n": any valid answer will do here
            @staticmethod
            def parse(kwargs):
                kind, agent, rnd, others = CostAPI.parse(kwargs)
                return kind, agent or 1, rnd or 1, 10 if others is None else others

        names = {model: name for _, model, name, _ in MINIPILOT_PROVIDERS.values()}
        self.use(AnyFrameAPI(cost=0.0001, provider_fn=lambda k: names[k["model"]]))
        raw = _raw()
        self.assertIs(raw["prereg_approved"], True)
        path = committed_copy(
            self.tmp, run="mini_open", cities=["Boston"], groups_per_cell=1, isolated_reps=1,
            isolated_points=[0], params={"rounds": 2}, isolated_round_no=2, workers=1,
            parallel_units=1)
        copy = json.loads(path.read_text(encoding="utf-8"))
        for key in ("prereg_approved", "frames", "frame_files", "cards", "cards_sha256",
                    "providers", "budget_usd", "model_budget_usd", "expected_cost_gate_usd"):
            self.assertEqual(copy[key], raw[key], key)
        code, _, err = self.main("--config", str(path))
        self.assertEqual(code, 0, err)
        self.assertNotIn("prereg_approved", err)
        self.assertTrue(self.api.calls)
        self.assertEqual({k["model"] for k in self.api.calls}, set(names))
        run_dir = self.tmp / "runs" / "mini_open"
        rows = [json.loads(x) for x in (run_dir / "mini_open.jsonl").read_text().splitlines()]
        self.assertEqual({(r["frame"], r["model"]) for r in rows},
                         {("abstract_v3", m) for m in names}
                         | {("story", m) for m in names if m != MISTRAL})

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
        self.assertNotIn("HESAPLANAMADI", out)
        self.assertNotIn("SEÇİLMEMİŞ", out)
        # 6 cards x 3 models x 2 frames; per cell: 2 groups x 4 agents x 10 rounds,
        # 2 x 5 isolated values, comprehension 2 x 4 + 2
        lines = [x for x in out.splitlines()
                 if re.match(r"^(abstract_v3|story)\s+(deepseek|mistral|gpt)\s", x)]
        # EMIR 3 Part 1 (task #73): Mistral's story arm is out, its abstract_v3 arm in
        self.assertEqual(len(lines), 5)
        self.assertFalse([x for x in lines if re.match(r"^story\s+mistral\s", x)])
        self.assertTrue([x for x in lines if re.match(r"^abstract_v3\s+mistral\s", x)])
        for x in lines:
            self.assertIn("600 çağrı (contribute_N=480, isolated=60, comprehension=60)", x)
        self.assertIn("3000 çağrı", out)
        self.assertIn("p95 üst sınır", next(x for x in out.splitlines() if x.startswith("TOPLAM")))
        self.assertIn("Beklenti kapısı expected_cost_gate_usd=4.5 USD: GEÇER", out)
        self.assertIn(f"mistral   {MISTRAL}", out)
        for label, rel in FRAME_FILES.items():
            sha = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
            self.assertIn(f"Çerçeve {label}: {ROOT / rel} (kind "
                          + ("story; linter: GEÇTİ (kind story; yasaklı kök yok)" if label == "story"
                             else "abstract; linter: MUAF (kind \"abstract\" declared in the file")
                          , out)
            self.assertIn(f"sha256 {sha} — kilitli, beklenenle aynı", out)
        cards_sha = hashlib.sha256((ROOT / "cards" / "pilot_cards_v3.json").read_bytes()).hexdigest()
        self.assertIn(f"Kartlar: {ROOT / 'cards' / 'pilot_cards_v3.json'}, sha256 {cards_sha} — "
                      "kilitli, beklenenle aynı", out)
        self.assertIn("Run adı: şablon minipilot_{run_date} — yeni gerçek koşuda koşu günüyle "
                      f"çözülür (bugün: minipilot_{pgg_game.run_date()})", out)
        self.assertIn("Ön kayıt: onaylı (prereg_approved=true)", out)      # task #75
        self.assertNotIn("ÖN KAYIT ONAYI YOK", out)
        self.assertIn("reasoning_effort=gönderilmez", out)
        self.assertIn("max_tokens=16000", out)
        self.assertIn("request_deadline_s=900", out)
        self.assertIn("stall_timeout_s=1800", out)
        self.assertIn("seed_namespace=pgg-minipilot, parallel_units=3, workers=4", out)

    def test_dry_run_of_the_placeholder_config(self):
        code, out, err = self.main("--dry-run", "--config", str(placeholder_config(self.tmp)))
        self.assertEqual(code, 0, err)
        self.create.assert_not_called()
        self.assertIn("ÇAĞRI SAYISI HESAPLANAMADI", out)
        for key in ("conditions", "arms", "groups_per_cell", "isolated_reps", "isolated_points",
                    "cards", "cities"):
            self.assertIn(key, out.splitlines()[1])
        self.assertIn(f"mistral={MISTRAL}", out)
        self.assertIn("ÖN KAYIT ONAYI YOK", out)
        self.assertIn("SEÇİLMEMİŞ (gerçek koşu başlamaz)", out)

    def test_dry_run_counts_once_the_design_is_given(self):
        # CLI values on top of the placeholders (cards file: cities filter it)
        code, out, err = self.main(
            "--dry-run", "--config", str(placeholder_config(self.tmp)), "--cards",
            str(PILOT_CARDS_V2),
            "--cities", "Boston,Riyadh", "--conditions", "N", "--arms", "group,isolated",
            "--groups-per-cell", "2", "--isolated-reps", "2", "--points", "0,5,10,15,20",
            "--frames", "abstract_v3=deepseek,mistral,gpt", "--isolated-frame", "fixed_round")
        self.assertEqual(code, 0, err)
        # + rule comprehension: 6 cells x 2 groups x 4 agents + 6 x 2 schedules
        self.assertEqual(out.count("600 çağrı (contribute_N=480, isolated=60, comprehension=60)"), 3)
        self.assertIn("1800 çağrı", out)
        self.assertNotIn("maliyet tahmini yok", out)
        self.assertNotIn("HARİÇ", out)
        self.assertIn("mistral: kalibrasyon M1 tesisat ölçümü tesisat_olcum_20261007", out)
        self.assertNotIn("HESAPLANAMADI", out)
        self.assertNotIn("ÖRNEK (tahmin)", out)
        # a placeholder cards file does not block when --cells is given
        code, out, _ = self.main(
            "--dry-run", "--config", str(placeholder_config(self.tmp)), "--cells", "2",
            "--conditions", "N",
            "--arms", "group", "--groups-per-cell", "1", "--isolated-reps", "1", "--points", "0",
            "--frames", "abstract_v3=deepseek,mistral,gpt")
        self.assertEqual(code, 0)
        # one line per frame x model (the per-model lines of task #68 name the frames)
        self.assertEqual(out.count("88 çağrı (contribute_N"), 3)  # 2 cells x 1 group x 4 x (10 + 1)
        self.create.assert_not_called()

    def test_dry_run_subprocess_needs_no_key(self):
        env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
        proc = subprocess.run(
            [sys.executable, str(ROOT / "pgg_game.py"), "--dry-run", "--config",
             str(MINIPILOT_CONFIG)],
            capture_output=True, text=True, env=env, cwd=self.tmp, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # the config's relative cards / frame paths are the repository's, not the cwd's
        self.assertIn("3000 çağrı", proc.stdout)
        self.assertIn(f"Çerçeve story: {ROOT / 'frames' / 'story_A.json'} (kind story", proc.stdout)

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
