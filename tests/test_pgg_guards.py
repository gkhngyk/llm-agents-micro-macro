"""Mock tests of the run guards and the pilot configuration (no network, no ../.env)."""

import contextlib
import io
import json
import os
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
PILOT_CARDS = ROOT / "cards" / "pilot_cards.json"


def _response(content, *, model, cost=None, finish_reason="stop", reasoning_tokens=5):
    usage = {"prompt_tokens": 100, "completion_tokens": 20,
             "completion_tokens_details": {"reasoning_tokens": reasoning_tokens}}
    if cost is not None:
        usage["cost"] = cost
    message = SimpleNamespace(content=content, reasoning=None)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    return SimpleNamespace(model=model, choices=[choice],
                           usage=SimpleNamespace(model_dump=lambda: dict(usage)))


class CostAPI(FakeAPI):
    """FakeAPI whose responses carry usage.cost, the requested model and a finish_reason.

    content_fn(kwargs, default) may replace the content; finish_fn / model_fn
    may replace finish_reason / the returned model.
    """

    def __init__(self, cost=0.0001, content_fn=None, finish_fn=None, model_fn=None):
        super().__init__()
        self.cost = cost
        self.content_fn = content_fn
        self.finish_fn = finish_fn
        self.model_fn = model_fn

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        content = self.default_reply(*self.parse(kwargs))
        if self.content_fn:
            content = self.content_fn(kwargs, content)
        finish = self.finish_fn(kwargs) if self.finish_fn else "stop"
        model = self.model_fn(kwargs) if self.model_fn else kwargs["model"]
        return _response(content, model=model, cost=self.cost, finish_reason=finish)


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
                                            "--cards", str(PILOT_CARDS)]), 0)
        text = buf.getvalue()
        self.create.assert_not_called()
        self.assertEqual(text.count("540 çağrı (contribute_N=480, isolated=60)"), 3)
        self.assertIn("1620 çağrı", text)
        self.assertIn("~0.38 USD", text)
        self.assertIn("reasoning_effort=gönderilmez", text)
        self.assertIn("max_tokens=4000", text)
        self.assertIn("budget_usd=1.0", text)

    def test_pilot_config_end_to_end_with_mock_client(self):
        self.use(CostAPI(cost=0.0001))
        cwd = os.getcwd()
        os.chdir(ROOT)                      # the config's card path is relative
        self.addCleanup(os.chdir, cwd)
        with contextlib.redirect_stdout(io.StringIO()):
            code = pgg_game.main(["--config", str(PILOT_CONFIG), "--run", "pilot_mock",
                                  "--results-dir", str(self.tmp / "results")])
        self.assertEqual(code, 0)
        rows = [json.loads(x) for x in
                (self.tmp / "results" / "pilot_mock.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 1620)
        self.assertEqual(len(self.api.calls), 1620)
        for slug in llm_client.MODELS.values():
            mine = [r for r in rows if r["model"] == slug]
            self.assertEqual(len(mine), 540)
            self.assertEqual(sum(r["arm"] == "group" for r in mine), 480)
            self.assertEqual(sum(r["arm"] == "isolated" for r in mine), 60)
            self.assertEqual(len({r["group_id"] for r in mine if r["arm"] == "group"}), 12)
        self.assertEqual({r["card_id"].split("_")[0] for r in rows}, {"boston", "riyadh"})
        self.assertEqual({r["condition"] for r in rows}, {"N"})
        for kwargs in self.api.calls:     # reasoning_effort not sent, no temperature
            self.assertEqual(kwargs["max_tokens"], 4000)
            self.assertNotIn("reasoning", kwargs["extra_body"])
            self.assertNotIn("temperature", kwargs)
        self.assertEqual({r["reasoning_effort"] for r in rows}, {"default"})
        self.assertEqual({r["max_tokens"] for r in rows}, {4000})
        first = rows[0]
        self.assertTrue(first["session_id"].startswith("pgg-pilot_mock-"))
        args = (first["model_key"], first["card_id"], first["style"], "N", "group", 0,
                first["agent_id"], first["round"], "contribute")
        self.assertEqual(first["seed"], llm_client.stable_seed("pgg-pilot", "pilot_mock", *args))
        self.assertNotEqual(first["seed"], llm_client.stable_seed("pgg", "pilot_mock", *args))
        summary = self.summary("pilot_mock")
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
            return sorted(json.dumps({k: v for k, v in r.items() if k not in ("ts", "run")},
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
