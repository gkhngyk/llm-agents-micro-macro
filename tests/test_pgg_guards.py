"""Mock tests of the run guards and the pilot configuration (no network, no ../.env)."""

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_pgg_game import (  # noqa: E402  (sets the dummy key before importing llm_client)
    CARD_A, CARD_B, ROOT, EngineTestBase, FakeAPI, _payload)

import llm_client  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Engine, GameParams, ModelStopped, RunAborted, RunStopped  # noqa: E402

PILOT_CONFIG = ROOT / "configs" / "pilot.json"
PILOT_CARDS = ROOT / "cards" / "pilot_cards.json"            # first pilot, kept unchanged
PILOT_CARDS_V2 = ROOT / "cards" / "pilot_cards_v2.json"      # pilot v2 (configs/pilot.json)
# Pinned providers of pilot v2 (endpoints list checked 2026-10-05): model key ->
# (slug, provider name the responses carry, quantizations).
PILOT_V2_PROVIDERS = {"deepseek": ("deepinfra/fp8", "DeepInfra", ["fp8"]),
                      "gpt": ("openai", "OpenAI", None),
                      "gemini": ("google-vertex", "Google", None)}


def _response(content, *, model, cost=None, finish_reason="stop", reasoning_tokens=5,
              provider=None, usage=None):
    if usage is None:
        usage = {"prompt_tokens": 100, "completion_tokens": 20,
                 "completion_tokens_details": {"reasoning_tokens": reasoning_tokens}}
        if cost is not None:
            usage["cost"] = cost
    message = SimpleNamespace(content=content, reasoning=None)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    resp = SimpleNamespace(model=model, choices=[choice],
                           usage=SimpleNamespace(model_dump=lambda: dict(usage)))
    if provider is not None:
        resp.provider = provider           # top-level provider name, as OpenRouter returns it
    return resp


class CostAPI(FakeAPI):
    """FakeAPI whose responses carry usage.cost, the requested model and a finish_reason.

    content_fn(kwargs, default) may replace the content; finish_fn / model_fn /
    provider_fn / usage_fn may replace finish_reason / the returned model /
    the provider name / the whole usage dict.
    """

    def __init__(self, cost=0.0001, content_fn=None, finish_fn=None, model_fn=None,
                 provider_fn=None, usage_fn=None):
        super().__init__()
        self.cost = cost
        self.content_fn = content_fn
        self.finish_fn = finish_fn
        self.model_fn = model_fn
        self.provider_fn = provider_fn
        self.usage_fn = usage_fn

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        content = self.default_reply(*self.parse(kwargs))
        if self.content_fn:
            content = self.content_fn(kwargs, content)
        finish = self.finish_fn(kwargs) if self.finish_fn else "stop"
        model = self.model_fn(kwargs) if self.model_fn else kwargs["model"]
        provider = self.provider_fn(kwargs) if self.provider_fn else None
        usage = self.usage_fn(kwargs) if self.usage_fn else None
        return _response(content, model=model, cost=self.cost, finish_reason=finish,
                         provider=provider, usage=usage)


class GuardTestBase(EngineTestBase):
    def use(self, api):
        self.api = api
        self.create.side_effect = api

    def events(self, name):
        return [e for e in self.raw_log() if e.get("event") == name]

    def summary(self, run="t1"):
        return json.loads((self.tmp / "results" / f"{run}_summary.json").read_text())


class PilotConfig(GuardTestBase):
    def test_pilot_cards_file(self):
        raw = json.loads(PILOT_CARDS.read_text(encoding="utf-8"))
        self.assertEqual(len(raw), 12)
        self.assertEqual({e["style"] for e in raw}, {"minimal", "value", "factual"})
        cards = pgg_game.load_cards(PILOT_CARDS, ["Boston", "Riyadh"])
        self.assertEqual([c.card_id for c in cards],
                         ["boston_minimal", "boston_value", "boston_factual",
                          "riyadh_minimal", "riyadh_value", "riyadh_factual"])
        by_id = {e["card_id"]: e["text"] for e in raw}
        self.assertTrue(all(c.text == by_id[c.card_id] for c in cards))  # texts untouched

    def test_pilot_cards_v2_file(self):
        raw = json.loads(PILOT_CARDS_V2.read_text(encoding="utf-8"))
        self.assertEqual(len(raw), 12)
        cards = pgg_game.load_cards(PILOT_CARDS_V2, ["Boston", "Riyadh"])
        self.assertEqual([c.card_id for c in cards],
                         ["boston_minimal", "boston_value", "boston_factual",
                          "riyadh_minimal", "riyadh_value", "riyadh_factual"])
        by_id = {e["card_id"]: e["text"] for e in raw}
        self.assertTrue(all(c.text == by_id[c.card_id] for c in cards))  # texts untouched
        self.assertTrue(all("21-year-old" in c.text for c in cards))
        # lengths as in kart_tasarimi_v2.md / #39 (words, characters)
        self.assertEqual({c.card_id: tuple(pgg_game.card_length(c).values()) for c in cards},
                         {"boston_minimal": (9, 58), "boston_value": (22, 142),
                          "boston_factual": (27, 151), "riyadh_minimal": (9, 58),
                          "riyadh_value": (21, 135), "riyadh_factual": (26, 144)})

    def test_pilot_v2_config_values(self):
        raw = json.loads(PILOT_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(pgg_game.open_choices(raw), [])           # nothing left to choose
        self.assertEqual(ROOT / raw["cards"], PILOT_CARDS_V2)
        self.assertEqual(raw["cities"], ["Boston", "Riyadh"])
        self.assertEqual(raw["conditions"], ["N"])
        self.assertEqual(raw["isolated_frame"], "repeated")
        self.assertEqual(raw["seed_namespace"], "pgg-pilot-v2")
        self.assertEqual((raw["max_tokens"], raw["request_timeout_s"]), (16000, 300))
        self.assertEqual((raw["budget_usd"], raw["invalid_rate_cap"]), (1.0, 0.05))
        self.assertNotIn("reasoning_effort", raw)
        self.assertNotIn("temperature", raw)
        self.assertEqual(raw["runs_dir"], "/Users/karbon/Desktop/Veri Bilimi/complexity-prj/orc/"
                                          "data/projects/PublicGoods/workspace/runs")
        for key, (slug, name, quant) in PILOT_V2_PROVIDERS.items():
            spec = raw["providers"][key]
            self.assertEqual((spec["slug"], spec["name"], spec.get("quantizations")),
                             (slug, name, quant))
            routing = pgg_game.provider_routing(spec)
            self.assertFalse(routing["allow_fallbacks"])
            self.assertEqual((routing["order"], routing["only"]), ([slug], [slug]))

    def test_city_filter_errors(self):
        path = self.tmp / "c.json"
        path.write_text(json.dumps([{"card_id": "a", "style": "s", "text": "t", "city": "X"}]))
        with self.assertRaises(ValueError):
            pgg_game.load_cards(path, ["Y"])
        path.write_text(json.dumps([{"card_id": "a", "style": "s", "text": "t"}]))
        with self.assertRaises(ValueError):
            pgg_game.load_cards(path, ["X"])
        self.assertEqual(len(pgg_game.load_cards(path)), 1)   # no filter: city not needed

    def test_pilot_dry_run_counts(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(pgg_game.main(["--dry-run", "--config", str(PILOT_CONFIG),
                                            "--cards", str(PILOT_CARDS_V2)]), 0)
        text = buf.getvalue()
        self.create.assert_not_called()
        self.assertEqual(text.count("540 çağrı (contribute_N=480, isolated=60)"), 3)
        self.assertIn("1620 çağrı", text)
        self.assertIn("~0.6364 USD", text)
        self.assertIn("reasoning_effort=gönderilmez", text)
        self.assertIn("max_tokens=16000", text)
        self.assertIn("request_timeout_s=300", text)
        self.assertIn("budget_usd=1.0", text)
        self.assertIn("isolated_frame=repeated", text)
        self.assertIn("seed_namespace=pgg-pilot-v2", text)
        self.assertNotIn("SEÇİLMEMİŞ", text)

    def test_dry_run_reports_whether_the_output_dir_exists(self):
        config = self.tmp / "cfg.json"
        for runs_dir, expected in ((self.tmp / "missing", "ÇIKTI DİZİNİ KULLANILAMIYOR"),
                                   (self.tmp, f"Çıktı dizini: {self.tmp} (mevcut)")):
            filled = json.loads(PILOT_CONFIG.read_text(encoding="utf-8"))
            filled["runs_dir"] = str(runs_dir)
            config.write_text(json.dumps(filled), encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(pgg_game.main(["--dry-run", "--config", str(config),
                                                "--cards", str(PILOT_CARDS_V2)]), 0)
            self.assertIn(expected, buf.getvalue())
        self.create.assert_not_called()

    def test_pilot_config_end_to_end_with_mock_client(self):
        # The committed config is complete; without an existing runs_dir a real
        # run refuses without a call. With one (a copy whose cards path is
        # absolute) it runs the 1620 calls of pilot v2.
        names = {slug: PILOT_V2_PROVIDERS[key][1]
                 for key, slug in llm_client.MODELS_PILOT_V2.items()}
        self.use(CostAPI(cost=0.0001, provider_fn=lambda k: names[k["model"]]))
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = pgg_game.main(["--config", str(PILOT_CONFIG), "--run", "pilot_mock",
                                  "--runs-dir", str(self.tmp / "no_such_dir")])
        self.assertEqual(code, 1)
        self.assertIn("does not exist", err.getvalue())
        self.create.assert_not_called()

        filled = json.loads(PILOT_CONFIG.read_text(encoding="utf-8"))
        filled["cards"] = str(PILOT_CARDS_V2)
        config = self.tmp / "pilot_filled.json"
        config.write_text(json.dumps(filled), encoding="utf-8")
        (self.tmp / "runs").mkdir()
        with contextlib.redirect_stdout(io.StringIO()):
            code = pgg_game.main(["--config", str(config), "--run", "pilot_mock",
                                  "--runs-dir", str(self.tmp / "runs")])
        self.assertEqual(code, 0)
        run_dir = self.tmp / "runs" / "pilot_mock"
        rows = [json.loads(x) for x in (run_dir / "pilot_mock.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 1620)
        self.assertEqual(len(self.api.calls), 1620)
        for slug in llm_client.MODELS_PILOT_V2.values():
            mine = [r for r in rows if r["model"] == slug]
            self.assertEqual(len(mine), 540)
            self.assertEqual(sum(r["arm"] == "group" for r in mine), 480)
            self.assertEqual(sum(r["arm"] == "isolated" for r in mine), 60)
            self.assertEqual(len({r["group_id"] for r in mine if r["arm"] == "group"}), 12)
            self.assertEqual({r["provider"] for r in mine}, {names[slug]})
        self.assertEqual({r["card_id"].split("_")[0] for r in rows}, {"boston", "riyadh"})
        self.assertEqual({r["condition"] for r in rows}, {"N"})
        texts = {e["card_id"]: e["text"] for e in json.loads(PILOT_CARDS_V2.read_text())}
        for r in rows:                    # card length on every row
            self.assertEqual((r["card_n_words"], r["card_n_chars"]),
                             (len(texts[r["card_id"]].split()), len(texts[r["card_id"]])))
        self.assertEqual({r["isolated_frame"] for r in rows if r["arm"] == "isolated"},
                         {"repeated"})
        slug_of = {slug: key for key, slug in llm_client.MODELS_PILOT_V2.items()}
        for kwargs in self.api.calls:     # reasoning_effort not sent, no temperature
            self.assertEqual(kwargs["max_tokens"], 16000)
            self.assertEqual(kwargs["timeout"], 300)
            self.assertNotIn("reasoning", kwargs["extra_body"])
            self.assertNotIn("temperature", kwargs)
            pslug, _, quant = PILOT_V2_PROVIDERS[slug_of[kwargs["model"]]]
            expected = {"order": [pslug], "only": [pslug], "allow_fallbacks": False,
                        "require_parameters": True}
            if quant:
                expected["quantizations"] = quant
            self.assertEqual(kwargs["extra_body"]["provider"], expected)
            user = kwargs["messages"][-1]["content"]
            if "Suppose" in user or "In the previous round the other" in user:
                self.assertIn("neither the first nor the last round", user)
        n_iso_prompts = sum("neither the first nor the last round" in c["messages"][-1]["content"]
                            for c in self.api.calls)
        self.assertEqual(n_iso_prompts, 3 * 60)
        self.assertEqual({r["reasoning_effort"] for r in rows}, {"default"})
        self.assertEqual({r["max_tokens"] for r in rows}, {16000})
        first = [r for r in rows if r["arm"] == "group" and r["group_id"].endswith("-g00")][0]
        self.assertTrue(first["session_id"].startswith("pgg-pilot_mock-"))
        args = (first["model_key"], first["card_id"], first["style"], "N", "group", 0,
                first["agent_id"], first["round"], "contribute")
        self.assertEqual(first["seed"], llm_client.stable_seed("pgg-pilot-v2", "pilot_mock", *args))
        self.assertNotEqual(first["seed"], llm_client.stable_seed("pgg-pilot", "pilot_mock", *args))
        summary = json.loads((run_dir / "pilot_mock_summary.json").read_text())
        self.assertEqual(summary["files"]["results"]["lines"], 1620)
        self.assertEqual(summary["n_provider_unknown"], 0)
        self.assertTrue((run_dir / "raw_calls.jsonl").exists())
        self.assertIsNone(summary["stop_reason"])
        self.assertEqual(summary["invalid_limit_per_model"], 27)   # 5 % of 540
        self.assertAlmostEqual(summary["total_cost_usd"], 1620 * 0.0001, places=9)
        self.assertEqual({m["n_responses"] for m in summary["per_model"].values()}, {540})


class Budget(GuardTestBase):
    def test_budget_stops_before_the_next_call(self):
        self.use(CostAPI(cost=0.01))
        with self.assertRaises(RunStopped):
            Engine(self.cfg(budget_usd=0.05)).run()
        self.assertEqual(len(self.api.calls), 5)     # 5 x 0.01 = 0.05: the 6th is not sent
        stop = self.events("pgg_run_stopped")
        self.assertEqual(len(stop), 1)
        self.assertEqual(stop[0]["reason"], "budget")
        self.assertAlmostEqual(stop[0]["total_cost_usd"], 0.05)
        self.assertEqual(self.summary()["stop_reason"], "budget")
        # round 1 (4 calls) was complete and written; round 2 was not
        rows = (self.tmp / "results" / "t1.jsonl").read_text().splitlines()
        self.assertEqual(len(rows), 4)

    def test_unparseable_and_invalid_responses_are_paid_for(self):
        seen = []

        def content(kwargs, default):
            seen.append(1)
            return {1: "not json", 2: _payload({"contribution": 25})}.get(len(seen), default)

        self.use(CostAPI(cost=0.01, content_fn=content))
        with self.assertRaises(RunStopped):
            Engine(self.cfg(budget_usd=0.035)).run()
        # bad, invalid, ok (agent 1), ok (agent 2) = 0.04 >= 0.035: nothing more
        self.assertEqual(len(self.api.calls), 4)
        self.assertEqual(self.summary()["per_model"]["vendor/model-1"]["n_responses"], 4)

    def test_missing_cost_is_priced_from_tokens(self):
        self.use(CostAPI(cost=None))
        Engine(self.cfg(params=GameParams(rounds=1),
                        models={"m1": "openai/gpt-6-luna"})).run()
        s = self.summary()["per_model"]["openai/gpt-6-luna"]
        self.assertEqual(s["n_cost_estimated"], 4)
        self.assertAlmostEqual(s["cost_usd"], 4 * (100 * 0.10 + 20 * 0.50) / 1e6)

    def test_budget_with_parallel_units_stops_all(self):
        self.use(CostAPI(cost=0.01))
        with self.assertRaises(RunStopped):
            Engine(self.cfg(budget_usd=0.2, cards=[CARD_A, CARD_B], groups_per_cell=3,
                            parallel_units=4, workers=4)).run()
        # at most the calls in flight when the cap was reached go over it
        self.assertLessEqual(len(self.api.calls), 20 + 16)
        self.assertGreaterEqual(len(self.api.calls), 20)


class InvalidRateCap(GuardTestBase):
    def test_cap_stops_only_that_model(self):
        counts = {}

        def content(kwargs, default):
            if kwargs["model"] != "vendor/model-1":
                return default
            key = kwargs["messages"][-1]["content"]
            counts[key] = counts.get(key, 0) + 1
            return _payload({"contribution": 25}) if counts[key] == 1 else default

        self.use(CostAPI(content_fn=content))
        engine = Engine(self.cfg(arms=("isolated",), isolated_reps=4, invalid_rate_cap=0.05,
                                 models={"m1": "vendor/model-1", "m2": "vendor/model-2"}))
        self.assertEqual(engine.invalid_limit, 1)    # 5 % of 20 planned calls
        path = engine.run()
        rows = [json.loads(x) for x in path.read_text().splitlines()]
        self.assertEqual(sum(r["model_key"] == "m2" for r in rows), 20)
        self.assertLess(sum(r["model_key"] == "m1" for r in rows), 20)
        self.assertEqual(engine.stopped_models, {"m1": "invalid_rate_cap"})
        ev = self.events("pgg_model_stopped")
        self.assertEqual(len(ev), 1)
        self.assertEqual((ev[0]["model"], ev[0]["n_invalid"], ev[0]["limit"]),
                         ("vendor/model-1", 2, 1))
        m1_calls = [c for c in self.api.calls if c["model"] == "vendor/model-1"]
        self.assertEqual(len(m1_calls), 4)           # 2 decisions x (invalid + valid), then none
        self.assertIsNone(self.summary()["stop_reason"])

    def test_cli_exit_code_2_when_a_model_was_stopped(self):
        cards = self.tmp / "cards.json"
        cards.write_text(json.dumps([{"card_id": "a", "style": "s", "text": "short fake card"}]))
        self.use(CostAPI(content_fn=lambda k, d: "not json" if len(self.api.calls) % 2 else d))
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = pgg_game.main(["--run", "cap", "--cards", str(cards), "--models", "gemini",
                                  "--arms", "isolated", "--invalid-rate-cap", "0.1",
                                  "--results-dir", str(self.tmp / "results")])
        self.assertEqual(code, 2)
        self.assertIn("invalid_rate_cap", err.getvalue())


class LengthAndSnapshot(GuardTestBase):
    def test_first_length_stops_the_run(self):
        self.use(CostAPI(finish_fn=lambda k: "length" if len(self.api.calls) == 3 else "stop"))
        with self.assertRaises(RunStopped):
            Engine(self.cfg(stop_on_length=True)).run()
        self.assertEqual(len(self.api.calls), 3)
        self.assertEqual(self.events("pgg_run_stopped")[0]["reason"], "finish_reason_length")
        self.assertEqual(self.summary()["per_model"]["vendor/model-1"]["n_length"], 1)

    def test_length_only_counted_when_guard_off(self):
        self.use(CostAPI(finish_fn=lambda k: "length"))
        Engine(self.cfg(params=GameParams(rounds=1))).run()
        self.assertEqual(self.summary()["per_model"]["vendor/model-1"]["finish_reasons"],
                         {"length": 4})

    def test_snapshot_mismatch_stops_and_suffix_is_allowed(self):
        self.use(CostAPI(model_fn=lambda k: k["model"] + "-20261001"))
        Engine(self.cfg(params=GameParams(rounds=1), check_snapshot=True)).run()
        self.use(CostAPI(model_fn=lambda k: "other/model"))
        with self.assertRaises(RunStopped):
            Engine(self.cfg(run="t2", check_snapshot=True)).run()
        ev = self.events("pgg_run_stopped")
        self.assertEqual((ev[0]["reason"], ev[0]["model_snapshot"]),
                         ("model_snapshot_mismatch", "other/model"))


class ParallelUnits(GuardTestBase):
    def test_parallel_units_write_the_same_rows(self):
        def stable(rows):
            return sorted(json.dumps({k: v for k, v in r.items()
                                      if k not in ("ts", "run", "elapsed_s")},
                                     sort_keys=True).replace("-t2-", "-t1-") for r in rows)

        kw = dict(cards=[CARD_A, CARD_B], arms=("group", "isolated"), groups_per_cell=2,
                  isolated_reps=2, params=GameParams(rounds=3), models={"m1": "v/m1", "m2": "v/m2"})
        serial = self.run_engine(**kw)
        parallel = self.run_engine(run="t2", parallel_units=5, workers=4, **kw)
        self.assertEqual(len(serial), 2 * 2 * (2 * 4 * 3 + 2 * 5))
        # seeds include the run name, so compare everything else
        for r in serial + parallel:
            r.pop("seed")
        self.assertEqual(stable(serial), stable(parallel))

    def test_run_aborted_stops_other_units(self):
        self.use(CostAPI(content_fn=lambda k, d: _payload({"contribution": 99})))
        with self.assertRaises(RunAborted):
            Engine(self.cfg(cards=[CARD_A, CARD_B], groups_per_cell=3, max_invalid=0,
                            parallel_units=3)).run()
        self.assertLessEqual(len(self.api.calls), 3)  # one in-flight call per unit at most
        self.assertEqual(self.summary()["stop_reason"], "run_aborted")


class ClientHooks(unittest.TestCase):
    def setUp(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for p in (mock.patch.object(llm_client, "LOG_PATH", Path(tmp.name) / "raw.jsonl"),
                  mock.patch.object(llm_client, "_client"),
                  mock.patch.object(llm_client.time, "sleep")):
            p.start()
            self.addCleanup(p.stop)
        self.create = llm_client._client.chat.completions.create

    def call(self, **kw):
        return llm_client.call_llm_valid(
            "m", [{"role": "user", "content": "hi"}], schema={"type": "object"},
            session_id="s", is_valid=lambda c: c.get("x") == 1, **kw)

    def test_before_call_can_stop_without_sending(self):
        class Halt(Exception):
            pass

        def halt():
            raise Halt()

        with self.assertRaises(Halt):
            self.call(before_call=halt)
        self.create.assert_not_called()

    def test_on_response_sees_every_arrived_response(self):
        self.create.side_effect = [
            _response("broken", model="m", cost=0.1, finish_reason="length"),
            ConnectionError("no response"),
            _response('{"x": 2}', model="m", cost=0.2),
            _response('{"x": 1}', model="m", cost=0.3),
        ]
        seen, before = [], []
        self.call(on_response=seen.append, before_call=lambda: before.append(1))
        self.assertEqual([i["usage"]["cost"] for i in seen], [0.1, 0.2, 0.3])
        self.assertEqual([i["finish_reason"] for i in seen], ["length", "stop", "stop"])
        self.assertEqual(len(before), 4)


if __name__ == "__main__":
    unittest.main()
