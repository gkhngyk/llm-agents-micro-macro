"""Mock tests of task #68 (EMIR 2 K3, K4, K5, items 15 and 17). No network, no ../.env.

(a) K3a: model_budget_usd stops one model alone (the others go on), with the
reason and the moment in the summary, and counts the earlier segments on
--resume; (b) K3b: an attempt past its deadline without usage is priced as
prompt + max_tokens (listed prices), counts in the budget and the model's cap,
is flagged on its row, and is taken back when the late response arrives;
(c) K3c: the dry run prints mean and p95 per model and in total, the gate
goes by the mean; (d) K4: a pinned model's response without a provider name
is re-requested and counted (n_provider_mismatch, n_provider_missing), up to
the attempt limit; (e) item 15: model_version (the serving endpoint's dated
model) on every row, and check_snapshot on it for snapshot_version_models,
also across segments; (f) K5: a run cut off and resumed sends byte for byte
the requests of an uninterrupted run, for abstract_v3 and frames/story_A.json
with rule comprehension on, in the group and the isolated arm; (g) item 17:
the plumbing choices of #61 / #62 stay as they are in both frames.
"""

import contextlib
import io
import json
import re
import threading
import zlib
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_llm_client_logging import MESSAGES, SCHEMA, LoggingTestBase  # noqa: E402
from test_pgg_deadline import _until  # noqa: E402
from test_pgg_game import CARD_A, ROOT, FakeAPI, _payload  # noqa: E402
from test_pgg_guards import CostAPI  # noqa: E402
from test_pgg_resume import GEMINI, ResumeBase, _killer, _rows  # noqa: E402
from test_pgg_resume_rounds import _comparable  # noqa: E402

import openai  # noqa: E402

import llm_client  # noqa: E402
import pgg_cost  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Card, Engine, GameParams, RunAborted, RunStopped  # noqa: E402

MINIPILOT = ROOT / "configs" / "minipilot.json"
MISTRAL = {"mistral": "mistralai/mistral-large-4-0"}
DATED = "mistralai/mistral-large-4-0-20261006"


def _raw(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def _metadata(provider, model) -> dict:
    """openrouter_metadata as tesisat_mistral_20261006 returned it (selected endpoint)."""
    return {"strategy": "direct", "endpoints": {"total": 1, "available": [
        {"provider": provider, "model": model, "selected": True}]}}


class VersionAPI(CostAPI):
    """CostAPI whose responses carry openrouter_metadata with version_fn(kwargs) (None: none)."""

    def __init__(self, version_fn, provider="Mistral", **kw):
        super().__init__(**kw)
        self.version_fn = version_fn
        self.provider = provider

    def __call__(self, **kwargs):
        resp = super().__call__(**kwargs)
        version = self.version_fn(kwargs)
        if version is not None:
            resp.openrouter_metadata = _metadata(self.provider, version)
        return resp


# --------------------------------------------------------------------------
# (a) K3a: per-model cap
# --------------------------------------------------------------------------

class ModelBudget(ResumeBase):
    def calls_of(self, api, slug):
        return sum(1 for c in api.calls if c["model"] == slug)

    def test_one_model_over_its_cap_stops_alone(self):
        # 2 models x (2 group games of 8 calls + 2 schedules of 5) = 26 calls each;
        # m1 may spend 0.0035 USD at 0.001 per call: its 5th call is not sent
        api = CostAPI(cost=0.001)
        self.use(api)
        engine = Engine(self.rcfg(model_budget_usd={"m1": 0.0035}))
        engine.run()                                     # no RunStopped: the run goes on
        self.assertEqual(self.calls_of(api, "v/m1"), 4)
        self.assertEqual(self.calls_of(api, "v/m2"), 26)
        summary = self.summary_now()
        self.assertIsNone(summary["stop_reason"])
        self.assertEqual(summary["stopped_models"], {"m1": "model_budget"})
        stop = summary["model_stops"]["m1"]
        self.assertEqual((stop["reason"], stop["segment"], stop["n_responses"],
                          stop["model_budget_usd"]), ("model_budget", 0, 4, 0.0035))
        self.assertAlmostEqual(stop["cost_usd"], 0.004, places=12)
        self.assertIsInstance(stop["ts"], float)
        self.assertEqual(summary["segments"][-1]["model_stops"]["m1"], stop)
        self.assertEqual(summary["model_budget_usd"], {"m1": 0.0035})
        self.assertEqual(summary["model_budget_status"]["m1"]["stopped"], True)
        self.assertAlmostEqual(summary["per_model"]["v/m1"]["cost_usd"], 0.004, places=12)
        self.assertAlmostEqual(summary["per_model"]["v/m2"]["cost_usd"], 0.026, places=12)
        # the other model's units are all complete; m1 has at most its first round
        rows = _rows(self.results)
        self.assertEqual(sum(r["model"] == "v/m2" for r in rows), 26)
        self.assertLessEqual(sum(r["model"] == "v/m1" for r in rows), 4)
        self.assertEqual(summary["units"]["n_remaining"], 4)          # m1's units
        events = self.raw_events("pgg_model_stopped")
        self.assertEqual([(e["model"], e["reason"], e["model_budget_usd"]) for e in events],
                         [("v/m1", "model_budget", 0.0035)])
        self.assertEqual(self.raw_events("pgg_run_stopped"), [])
        self.assertEqual(summary["config"]["model_budget_usd"], {"m1": 0.0035})

    def test_cap_counts_the_earlier_segments(self):
        # m1 may spend 0.00195 USD at 0.0001 per call: 20 of its 26 calls, over all segments
        caps = {"m1": 0.00195}
        _, api0 = self.interrupted_run(at=22, model_budget_usd=caps)
        n0 = self.calls_of(api0, "v/m1")
        self.assertTrue(0 < n0 < 20, n0)                  # not stopped in segment 0
        self.assertEqual(self.summary_now()["stopped_models"], {})
        billed0 = self.summary_now()["per_model"]["v/m1"]["n_responses"]   # the cut call
        engine, api1 = self.resume(model_budget_usd=caps)                # got no response
        engine.run(resume=True)
        self.assertEqual(billed0 + self.calls_of(api1, "v/m1"), 20)
        summary = self.summary_now()
        self.assertEqual(summary["per_model"]["v/m1"]["n_responses"], 20)
        stop = summary["model_stops"]["m1"]
        self.assertEqual((stop["reason"], stop["segment"], stop["n_responses"]),
                         ("model_budget", 1, 20))
        self.assertAlmostEqual(stop["cost_usd"], 0.002, places=12)
        self.assertNotIn("at_resume", stop)
        self.assertEqual(summary["segments"][0].get("model_stops"), {})
        # another segment: m1 is over its cap from the start, nothing of it is sent
        engine, api2 = self.resume(model_budget_usd=caps)
        plan = Engine(self.rcfg(model_budget_usd=caps), llm=pgg_game.OfflineLLM()).resume_plan()
        report = pgg_game.resume_report(engine, plan)
        self.assertIn("Model alt tavanları", report)
        self.assertIn("aşılmış, bu model koşulmaz", report)
        engine.run(resume=True)
        self.assertEqual(self.calls_of(api2, "v/m1"), 0)
        summary = self.summary_now()
        stop = summary["model_stops"]["m1"]
        self.assertEqual((stop["segment"], stop["at_resume"]), (2, True))
        self.assertEqual(summary["stopped_models"], {"m1": "model_budget"})

    def test_cap_settings_are_validated_and_in_the_config_record(self):
        for bad in ({"mx": 1}, {"m1": 0}, {"m1": -1}, {"m1": True}, {"m1": "1"}, {}, [1]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.rcfg(model_budget_usd=bad).validate()
        # a config without caps keeps the record of the earlier code (pilot v2 resumes)
        engine = Engine(self.rcfg(), llm=pgg_game.OfflineLLM())
        self.assertNotIn("model_budget_usd", engine.config_record())
        self.assertNotIn("snapshot_version_models", engine.config_record())
        # slugs or keys in a config
        self.assertEqual(pgg_game.resolve_model_keyed({"v/m1": 1, "m2": 2}, dict(self.rcfg().models),
                                                      "model_budget_usd"), {"m1": 1, "m2": 2})
        with self.assertRaisesRegex(ValueError, "not one of the run's models"):
            pgg_game.resolve_model_keyed({"nope": 1}, {"m1": "v/m1"}, "model_budget_usd")

    def test_committed_config_has_the_part_one_caps(self):
        raw = json.loads(MINIPILOT.read_text(encoding="utf-8"))
        self.assertEqual(raw["model_budget_usd"], {"mistral": 3, "deepseek": 2, "gpt": 0.5})
        self.assertEqual((raw["budget_usd"], raw["expected_cost_gate_usd"]), (6, 4.5))
        self.assertEqual(raw["snapshot_version_models"], ["mistral"])
        self.assertIs(raw["check_snapshot"], True)
        self.assertIs(raw["prereg_approved"], False)


# --------------------------------------------------------------------------
# (b) K3b: deadline without usage priced at max_tokens
# --------------------------------------------------------------------------

class DeadlineEstimate(ResumeBase):
    def cfg1(self, **kw):
        base = dict(models=dict(GEMINI), cards=[CARD_A], request_deadline_s=0.2,
                    stall_timeout_s=30)
        base.update(kw)
        return self.rcfg(**base)

    def hang_third(self, api):
        """create(): the 3rd call hangs until the returned event is set, then answers late."""
        release = threading.Event()
        n = [0]

        def create(**kw):
            n[0] += 1
            if n[0] == 3:
                release.wait(30)
                return api(**kw)              # its late response, billed at api.cost
            return api(**kw)

        self.create.side_effect = create
        self.addCleanup(_until, lambda: llm_client.abandoned_attempts_alive() == 0)
        self.addCleanup(release.set)
        return release

    def test_estimate_formula(self):
        engine = Engine(self.cfg1(max_tokens=16000), llm=pgg_game.OfflineLLM())
        est = engine.deadline_estimate("gemini", 3001)
        price_in, price_out = pgg_cost.PRICES_USD_PER_M["google/gemini-2.5-flash-lite"]
        self.assertEqual(est["prompt_tokens_estimated"], 1001)        # ceil(3001 / 3)
        self.assertAlmostEqual(est["estimated_cost_usd"],
                               (1001 * price_in + 16000 * price_out) / 1e6, places=15)
        self.assertEqual((est["max_tokens"], est["price_usd_per_m"]), (16000, [price_in, price_out]))
        mistral = Engine(self.cfg1(models=dict(MISTRAL), max_tokens=16000),
                         llm=pgg_game.OfflineLLM()).deadline_estimate("mistral", 3600)
        self.assertAlmostEqual(mistral["estimated_cost_usd"],
                               (1200 * 0.68 + 16000 * 2.09) / 1e6, places=15)

    def test_estimate_counts_in_the_model_cap(self):
        # without the estimate (~0.0064 USD) 13 calls at 0.0001 would stay below 0.005
        api = CostAPI(cost=0.0001)
        self.hang_third(api)
        Engine(self.cfg1(model_budget_usd={"gemini": 0.005})).run()
        summary = self.summary_now()
        self.assertEqual(summary["stopped_models"], {"gemini": "model_budget"})
        stats = summary["per_model"][GEMINI["gemini"]]
        self.assertEqual(stats["n_deadline_cost_estimated"], 1)
        self.assertGreater(stats["deadline_cost_estimated_usd"], 0.005)
        self.assertLess(len(api.calls), 13)

    def test_estimate_counts_in_the_hard_cap(self):
        api = CostAPI(cost=0.0001)
        self.hang_third(api)
        with self.assertRaisesRegex(RunStopped, "budget"):
            Engine(self.cfg1(budget_usd=0.005)).run()
        self.assertEqual(self.summary_now()["stop_reason"], "budget")

    def test_late_response_replaces_the_estimate(self):
        api = CostAPI(cost=0.0001)
        release = self.hang_third(api)
        engine = Engine(self.cfg1())
        engine.run()
        stats = engine.stats["gemini"]
        usd = self.raw_events("pgg_deadline_cost_estimated")[0]["estimated_cost_usd"]
        self.assertAlmostEqual(stats["cost_usd"], 13 * 0.0001 + usd, places=12)
        release.set()                                   # the abandoned call answers now
        self.assertTrue(_until(lambda: len(self.raw_events("pgg_deadline_estimate_replaced")) == 1))
        replaced = self.raw_events("pgg_deadline_estimate_replaced")[0]
        self.assertAlmostEqual(replaced["estimated_cost_usd"], usd, places=15)
        self.assertEqual(replaced["attempt"], 0)
        self.assertAlmostEqual(stats["cost_usd"], 14 * 0.0001, places=12)   # the real cost
        self.assertEqual((stats["n_deadline_cost_estimated"], stats["n_responses"]), (0, 14))
        self.assertAlmostEqual(stats["deadline_cost_estimated_usd"], 0.0, places=15)
        # the row keeps what was known when it was written
        hit = [r for r in _rows(self.results) if r["n_deadline"]]
        self.assertEqual((hit[0]["cost_estimated"], hit[0]["n_deadline_cost_estimated"]), (True, 1))
        # a resume plan rebuilds the same from the raw log
        plan = Engine(self.cfg1(), llm=pgg_game.OfflineLLM()).resume_plan()
        st = plan.prior_stats["gemini"]
        self.assertAlmostEqual(plan.prior_cost_usd, 14 * 0.0001, places=12)
        self.assertEqual((st["n_deadline_cost_estimated"], st["n_cost_unknown"]), (0, 1))
        # the summary was written before the late response: it still holds the
        # estimate, which the cost check knows (no "missing" cost is added)
        self.assertAlmostEqual(plan.cost_check["estimates_replaced_after_summary_usd"], usd,
                               places=15)
        self.assertEqual(plan.prior_extra_cost, 0.0)

    def test_late_response_before_the_deadline_hook_is_not_estimated(self):
        """The abandoned attempt's thread may answer before on_deadline runs: no estimate."""
        engine = Engine(self.cfg1(), llm=pgg_game.OfflineLLM())
        seen = {}

        def fake_call(model, messages, *, on_deadline, on_late_response, counts, meta, **kw):
            on_late_response({"usage": {"prompt_tokens": 1, "completion_tokens": 1, "cost": 0.002},
                              "attempt": 0, "provider": None})
            on_deadline({"usage": None, "cost_unknown": True, "late_response": False,
                         "n_bytes": 0, "attempt": 0})
            counts.update(n_deadline=1)
            meta.update(usage={"cost": 0.0001})
            seen["ok"] = True
            return {"contribution": 1}, 0, 0

        engine.llm = mock_llm = pgg_game.OfflineLLM()
        mock_llm.call_llm_valid = fake_call
        ans = engine._ask("gemini", [{"role": "user", "content": "x"}], {}, lambda c: True,
                          "s", {"step": "contribute", "round": 1, "agent_id": 1})
        self.assertTrue(seen["ok"])
        self.assertEqual(ans.n_deadline_cost_estimated, 0)
        st = engine.stats["gemini"]
        self.assertEqual((st["n_deadline_cost_estimated"], st["n_cost_unknown"]), (0, 1))
        self.assertAlmostEqual(st["cost_usd"], 0.002, places=12)


# --------------------------------------------------------------------------
# (c) K3c: dry run, mean and p95
# --------------------------------------------------------------------------

class DryRunP95(ResumeBase):
    def dry(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            code = pgg_game.main(["--dry-run", *argv])
        return code, out.getvalue(), err.getvalue()

    def test_committed_config_per_model_mean_and_p95(self):
        code, out, err = self.dry("--config", str(MINIPILOT))
        self.assertEqual(code, 0, err)
        raw = json.loads(MINIPILOT.read_text(encoding="utf-8"))
        s = pgg_game.settings_from_args(pgg_game.build_parser().parse_args(
            ["--config", str(MINIPILOT)]))
        models = pgg_game.resolve_models(raw["models"], pgg_cost.KNOWN_MODELS)
        frame_models = pgg_game.resolve_frames(raw["frames"], models)
        cards = pgg_game.load_cards(s["cards"], raw["cities"])
        est = pgg_game.design_estimate(
            models=models, frame_models=frame_models,
            frames=pgg_game.dry_run_frames(frame_models, raw["frame_files"], s["params"]),
            n_cells=len(cards), params=s["params"], conditions=("N",), arms=("group", "isolated"),
            groups_per_cell=2, isolated_reps=2, n_points=5, comprehension=True,
            isolated_frame="fixed_round", isolated_round_no=5, cards=cards)
        self.assertIn("Model başına (çerçeveleri toplamı; ortalama beklenti ve p95 üst sınır", out)
        for key in ("deepseek", "mistral", "gpt"):
            rows = [r for r in est["rows"] if r["model"] == key]
            mean = sum(r["cost_usd"] for r in rows)
            p95 = sum(r["p95_upper_usd"] for r in rows)
            self.assertAlmostEqual(est["per_model"][key]["cost_usd"], mean, places=12)
            self.assertAlmostEqual(est["per_model"][key]["p95_upper_usd"], p95, places=12)
            line = next(x for x in out.splitlines() if x.startswith(f"  {key} "))
            self.assertIn("1200 çağrı (abstract_v3, story)", line)
            self.assertIn(f"ortalama ~{mean:.4f} USD", line)
            self.assertIn(f"p95 üst sınır ~{p95:.4f} USD", line)
            self.assertIn(f"model_budget_usd={raw['model_budget_usd'][key]:g} USD", line)
        self.assertIn(f"~{est['total_cost_usd']:.4f} USD (tahmin); p95 üst sınır "
                      f"~{est['total_p95_upper_usd']:.4f} USD", out)
        # the gate goes by the mean: p95 above 4.5 USD, mean below it
        self.assertGreater(est["total_p95_upper_usd"], 4.5)
        self.assertLess(est["total_cost_usd"], 4.5)
        self.assertIn("Beklenti kapısı expected_cost_gate_usd=4.5 USD: GEÇER", out)
        self.assertIn("Kapı kararı toplam ORTALAMA beklentiye göre verilir; p95 bilgi amaçlıdır.", out)
        deepseek = next(x for x in out.splitlines() if x.startswith("  deepseek "))
        self.assertIn("ortalama altında, p95 AŞIYOR", deepseek)
        gpt = next(x for x in out.splitlines() if x.startswith("  gpt "))
        self.assertIn("ortalama altında, p95 altında", gpt)
        self.assertIn("model_budget_usd={'mistral': 3, 'deepseek': 2, 'gpt': 0.5}", out)
        self.create.assert_not_called()

    def test_gate_by_the_mean_when_it_is_above(self):
        tmp_cfg = self.tmp / "gate.json"
        raw = json.loads(MINIPILOT.read_text(encoding="utf-8"))
        raw["expected_cost_gate_usd"] = 1.0             # below the mean (~2.08)
        tmp_cfg.write_text(json.dumps(raw))           # its relative paths: the code directory
        code, out, _ = self.dry("--config", str(tmp_cfg))
        self.assertEqual(code, 0)
        self.assertIn("Beklenti kapısı expected_cost_gate_usd=1 USD: AŞILIYOR", out)


# --------------------------------------------------------------------------
# (d) K4: no provider name on a pinned model
# --------------------------------------------------------------------------

PINNED = {"m1": {"slug": "prov-a/fp8", "name": "Prov A", "quantizations": ["fp8"]}}


class MissingProviderInEngine(ResumeBase):
    def cfg1(self, **kw):
        base = dict(models={"m1": "v/m1"}, cards=[CARD_A], arms=("group",),
                    params=GameParams(rounds=1), providers=PINNED, budget_usd=None,
                    invalid_rate_cap=None)
        base.update(kw)
        return self.rcfg(**base)

    def test_missing_name_is_re_requested_counted_and_rebuilt(self):
        api = CostAPI(cost=0.001, provider_fn=lambda k: None if len(self.api.calls) == 2
                      else "Prov A")
        self.use(api)
        Engine(self.cfg1()).run()
        self.assertEqual(len(api.calls), 5)                 # 4 decisions + 1 re-request
        rows = _rows(self.results)
        self.assertEqual([r["n_provider_missing"] for r in rows], [0, 1, 0, 0])
        self.assertEqual([r["n_provider_mismatch"] for r in rows], [0, 1, 0, 0])
        self.assertEqual({r["provider"] for r in rows}, {"Prov A"})
        summary = self.summary_now()
        stats = summary["per_model"]["v/m1"]
        self.assertEqual((stats["n_provider_missing"], stats["n_provider_mismatch"],
                          stats["n_provider_unknown"], stats["n_responses"]), (1, 1, 0, 5))
        self.assertAlmostEqual(stats["cost_usd"], 0.005, places=12)        # billed
        self.assertEqual((summary["n_provider_missing"],
                          summary["segments"][-1]["n_provider_missing"]), (1, 1))
        self.assertIn("without a provider name", summary["provider_mismatch_rule"])
        plan = Engine(self.cfg1(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual((plan.prior_stats["m1"]["n_provider_missing"],
                          plan.prior_stats["m1"]["n_provider_mismatch"],
                          plan.prior_stats["m1"]["n_provider_unknown"]), (1, 1, 0))

    def test_attempt_limit_of_missing_names_stops(self):
        api = CostAPI(provider_fn=lambda k: None)
        self.use(api)
        with self.assertRaises(RunAborted) as cm:
            Engine(self.cfg1()).run()
        self.assertEqual(cm.exception.reason, "provider_mismatch_limit")
        self.assertIn("4 of them without a provider name", str(cm.exception))
        self.assertEqual(len(api.calls), 4)
        summary = self.summary_now()
        self.assertEqual(summary["stop_reason"], "provider_mismatch_limit")
        self.assertEqual(summary["per_model"]["v/m1"]["n_provider_missing"], 4)
        aborted = self.raw_events("pgg_run_aborted")[0]
        self.assertEqual((aborted["n_provider_mismatch"], aborted["n_provider_missing"]), (4, 4))


# --------------------------------------------------------------------------
# (e) item 15: model_version and check_snapshot on it
# --------------------------------------------------------------------------

class ModelVersionInClient(LoggingTestBase):
    def completion(self, version, provider="Mistral"):
        data = {"id": "g", "object": "chat.completion", "created": 0,
                "model": "mistralai/mistral-large-4-0",
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": '{"action": 1}'}}],
                "usage": {"prompt_tokens": 94, "completion_tokens": 7, "total_tokens": 101,
                          "cost": 0.00007855}}
        if version is not None:
            data["openrouter_metadata"] = _metadata(provider, version)
        return openai.types.chat.ChatCompletion.model_validate(data)

    def test_sdk_object_extra_field_is_read_and_logged(self):
        resp = self.completion(DATED)
        self.assertEqual(llm_client._model_version(resp), DATED)
        self.assertEqual(llm_client._provider_info(resp), ("Mistral", None))
        self.create.side_effect = [resp]
        meta, seen = {}, []
        llm_client.call_llm("m", MESSAGES, schema=SCHEMA, session_id="s", meta=meta,
                            on_response=seen.append)
        ok = self.records()[-1]
        self.assertEqual((ok["model_snapshot"], ok["model_version"]),
                         ("mistralai/mistral-large-4-0", DATED))
        self.assertEqual(meta["model_version"], DATED)
        self.assertEqual(seen[0]["model_version"], DATED)
        # no metadata: None
        self.create.side_effect = [self.completion(None)]
        meta = {}
        llm_client.call_llm("m", MESSAGES, schema=SCHEMA, session_id="s", meta=meta)
        self.assertIsNone(meta["model_version"])
        self.assertIsNone(self.records()[-1]["model_version"])

    def test_rejected_response_records_carry_it_too(self):
        self.create.side_effect = [self.completion("x/other-1", provider="Other"),
                                   self.completion(DATED)]
        llm_client.call_llm("m", MESSAGES, schema=SCHEMA, session_id="s",
                            expected_provider="Mistral")
        bad, ok = self.records()
        self.assertEqual((bad["provider_mismatch"], bad["model_version"]), (True, "x/other-1"))
        self.assertEqual(ok["model_version"], DATED)


class ModelVersionCheck(ResumeBase):
    def cfg1(self, **kw):
        base = dict(models=dict(MISTRAL), cards=[CARD_A], check_snapshot=True,
                    snapshot_version_models=("mistral",))
        base.update(kw)
        return self.rcfg(**base)

    def test_dated_version_on_every_row_and_compared(self):
        api = VersionAPI(lambda k: DATED)
        self.use(api)
        Engine(self.cfg1()).run()
        rows = _rows(self.results)
        self.assertEqual(len(rows), 13)
        self.assertEqual({(r["model_snapshot"], r["model_version"]) for r in rows},
                         {("mistralai/mistral-large-4-0", DATED)})
        self.assertTrue(all(r.get("model_version") == DATED for r in _raw(self.raw)
                            if "response_parsed" in r and r.get("event") is None))
        summary = self.summary_now()
        self.assertIsNone(summary["stop_reason"])
        self.assertEqual(summary["model_version_reference"], {"mistral": DATED})
        self.assertEqual(summary["snapshot_version_models"], ["mistral"])
        self.assertEqual(summary["per_model"][MISTRAL["mistral"]]["model_versions"], {DATED: 13})
        self.assertEqual(summary["config"]["snapshot_version_models"], ["mistral"])

    def test_version_change_stops_the_run(self):
        api = VersionAPI(lambda k: DATED if len(self.api.calls) < 6
                         else "mistralai/mistral-large-4-0-20261101")
        self.use(api)
        with self.assertRaisesRegex(RunStopped, "model_version_changed"):
            Engine(self.cfg1()).run()
        ev = self.raw_events("pgg_run_stopped")
        self.assertEqual(len(ev), 1)
        self.assertEqual((ev[0]["reason"], ev[0]["model_version"], ev[0]["expected_model_version"],
                          ev[0]["compared"]),
                         ("model_version_changed", "mistralai/mistral-large-4-0-20261101",
                          DATED, "model_version"))
        self.assertEqual(len(api.calls), 6)

    def test_version_of_another_model_is_a_snapshot_mismatch(self):
        self.use(VersionAPI(lambda k: "mistralai/mistral-medium-3-20261006"))
        with self.assertRaisesRegex(RunStopped, "model_snapshot_mismatch"):
            Engine(self.cfg1()).run()
        ev = self.raw_events("pgg_run_stopped")[0]
        self.assertEqual((ev["model_version"], ev["compared"]),
                         ("mistralai/mistral-medium-3-20261006", "model_version"))

    def test_without_the_setting_the_snapshot_rule_is_unchanged(self):
        # the response "model" is the undated slug: nothing to see without the setting
        self.use(VersionAPI(lambda k: DATED if len(self.api.calls) < 6 else "other/x-1"))
        Engine(self.cfg1(snapshot_version_models=())).run()
        summary = self.summary_now()
        self.assertIsNone(summary["stop_reason"])
        self.assertEqual(summary["model_version_reference"], {})
        rows = _rows(self.results)
        self.assertEqual({r["model_version"] for r in rows}, {DATED, "other/x-1"})  # still logged

    def test_missing_version_is_counted_not_stopped(self):
        self.use(VersionAPI(lambda k: None))
        Engine(self.cfg1()).run()
        summary = self.summary_now()
        self.assertIsNone(summary["stop_reason"])
        stats = summary["per_model"][MISTRAL["mistral"]]
        self.assertEqual((stats["n_model_version_unknown"], stats["model_versions"]),
                         (13, {"None": 13}))
        self.assertTrue(all(r["model_version"] is None for r in _rows(self.results)))

    def test_reference_goes_on_across_segments(self):
        api0 = VersionAPI(lambda k: DATED)
        api0.content_fn = _killer(api0, 6)
        self.use(api0)
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            Engine(self.cfg1()).run()
        plan = Engine(self.cfg1(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(plan.model_version_reference, {"mistral": DATED})
        engine = Engine(self.cfg1(), llm=pgg_game.OfflineLLM())
        self.assertIn(f"mistral {DATED}", pgg_game.resume_report(engine, plan))
        later = "mistralai/mistral-large-4-0-20261101"
        api1 = VersionAPI(lambda k: later)
        self.use(api1)
        with self.assertRaisesRegex(RunStopped, "model_version_changed"):
            Engine(self.cfg1()).run(resume=True)
        self.assertEqual(len(api1.calls), 1)               # the first response stops it
        ev = [e for e in self.raw_events("pgg_run_stopped") if e["reason"] == "model_version_changed"]
        self.assertEqual((ev[0]["model_version"], ev[0]["expected_model_version"]), (later, DATED))

    def test_setting_is_validated(self):
        with self.assertRaises(ValueError):
            self.cfg1(snapshot_version_models=("gpt",)).validate()
        with self.assertRaises(ValueError):
            self.cfg1(snapshot_version_models="mistral").validate()


# --------------------------------------------------------------------------
# (f) K5: cut off and resumed == uninterrupted, abstract_v3 and story_A, comprehension on
# --------------------------------------------------------------------------

class TwoFrameAPI(CostAPI):
    """CostAPI that reads the decision of abstract_v3 and story_A prompts alike."""

    @staticmethod
    def parse(kwargs):
        user = kwargs["messages"][-1]["content"]
        if '"q1": {"type": "integer"' in user:
            kind = "comprehension"
        elif "QUESTION" in user:
            kind = "isolated"
        else:
            kind = "contribute"
        agent = re.search(r"You are (?:Player|User) (\d)", user)
        rnd = re.search(r"(?:ROUND|DAY) (\d+) of", user)
        others = re.search(r"on average, (\d+) (?:points|credits)", user)
        return (kind, int(agent.group(1)) if agent else None,
                int(rnd.group(1)) if rnd else None, int(others.group(1)) if others else None)


def _prompt_reply(kwargs, content):
    """A decision that depends on the whole prompt (history included)."""
    if TwoFrameAPI.parse(kwargs)[0] != "contribute":
        return content
    user = kwargs["messages"][-1]["content"]
    return _payload({FakeAPI.decision_key(kwargs): zlib.crc32(user.encode()) % 21,
                     "rationale": "r"})


def _request(kwargs) -> str:
    """Everything sent for one call, as one string."""
    return json.dumps(kwargs, sort_keys=True, ensure_ascii=False, default=str)


def _requests_by_decision(calls) -> dict:
    """(session, kind, agent, round, others) -> the request of the LAST call for it."""
    return {(c["extra_body"]["session_id"], *TwoFrameAPI.parse(c)): _request(c) for c in calls}


class K5Config:
    """One model, one card, the committed (sha256-locked) frame, comprehension on:
    1 group game of 4 rounds (4 + 16 calls), then 1 schedule of 3 values (1 + 3)."""
    FRAMES = {"abstract_v3": "abstract_v3", "story_A": "story"}

    def kcfg(self, runs, frame, **kw):
        label = self.FRAMES[frame]
        locked = json.loads(MINIPILOT.read_text(encoding="utf-8"))["frame_files"][label]
        base = dict(run="k5", results_dir=None, runs_dir=runs, cards=[CARD_A],
                    models={"m1": "v/m1"}, frames={label: ["m1"]}, frame_files={label: locked},
                    isolated_frame="fixed_round", isolated_round_no=3, comprehension=True,
                    arms=("group", "isolated"), params=GameParams(rounds=4), groups_per_cell=1,
                    isolated_reps=1, isolated_points=(0, 10, 20), budget_usd=1.0,
                    invalid_rate_cap=None)
        base.update(kw)
        return self.cfg(**base)


class CutResumeSamePrompts(K5Config, ResumeBase):
    def dirs(self, *names):
        out = []
        for name in names:
            d = self.tmp / name
            d.mkdir()
            out.append(d)
        return out

    def check(self, frame, at, comprehension_again: dict):
        a, b = self.dirs(f"A{frame}{at}", f"B{frame}{at}")
        api_a = TwoFrameAPI(content_fn=_prompt_reply)
        self.use(api_a)
        Engine(self.kcfg(a, frame)).run()
        rows_a = _rows(a / "k5" / "k5.jsonl")
        # 1 group game: 4 comprehension + 4 x 4 contributions; 1 schedule: 1 + 3
        self.assertEqual(len(api_a.calls), 24)
        self.assertEqual(len(rows_a), 24)

        api0 = TwoFrameAPI()
        kill = _killer(api0, at)
        api0.content_fn = lambda k, c: kill(k, _prompt_reply(k, c))
        self.use(api0)
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            Engine(self.kcfg(b, frame)).run()
        api1 = TwoFrameAPI(content_fn=_prompt_reply)
        self.use(api1)
        engine = Engine(self.kcfg(b, frame))
        engine.run(resume=True)

        # byte for byte: the last request per decision, and every request sent at all
        both = api0.calls + api1.calls
        self.assertEqual(_requests_by_decision(both), _requests_by_decision(api_a.calls))
        self.assertEqual({_request(c) for c in both}, {_request(c) for c in api_a.calls})
        # rule comprehension asked again in segment 1 exactly where the cut lost it
        by_arm = {"group": 0, "isolated": 0}
        for c in api1.calls:
            if TwoFrameAPI.parse(c)[0] == "comprehension":
                arm = "isolated" if "isolated" in c["extra_body"]["session_id"] else "group"
                by_arm[arm] += 1
        self.assertEqual(by_arm, comprehension_again)
        # the valid rows equal the uninterrupted run's rows (seeds and frame included)
        valid = engine.valid_rows()
        self.assertEqual(_comparable(valid), _comparable(rows_a))
        self.assertEqual({r["frame_sha256"] for r in valid},
                         {json.loads(MINIPILOT.read_text(encoding="utf-8"))["frame_files"]
                          [self.FRAMES[frame]]["sha256"]})
        comp = [r for r in valid if r["step"] == "comprehension"]
        self.assertEqual(sorted((r["arm"], r["round"]) for r in comp),
                         [("group", 1)] * 4 + [("isolated", None)])

    def test_abstract_v3(self):
        # cut in round 1's comprehension (the unit starts again), in round 2 (goes
        # on from round 2, comprehension kept), in the schedule (run again whole)
        for at, again in ((3, {"group": 4, "isolated": 1}), (10, {"group": 0, "isolated": 1}),
                          (22, {"group": 0, "isolated": 1})):
            with self.subTest(at=at):
                self.check("abstract_v3", at, again)

    def test_story_A(self):
        for at, again in ((3, {"group": 4, "isolated": 1}), (10, {"group": 0, "isolated": 1}),
                          (22, {"group": 0, "isolated": 1})):
            with self.subTest(at=at):
                self.check("story_A", at, again)


# --------------------------------------------------------------------------
# (g) item 17: the open plumbing choices of #61 / #62 stay as they are
# --------------------------------------------------------------------------

class PlumbingChoicesKept(K5Config, ResumeBase):
    """prereg_minipilot.md §12 note (#63 §9.3), approved "as they are" (EMIR 2 item 17)."""

    def test_both_frames(self):
        files = json.loads(MINIPILOT.read_text(encoding="utf-8"))["frame_files"]
        card = Card("c", "s", "A 21-year-old student.")
        p = GameParams()
        for label, spec in files.items():
            with self.subTest(frame=label):
                f = pgg_game.load_frame_file(label, spec)
                # 1. the system message is the card alone
                self.assertEqual(f.data["system"], "{card}")
                for messages in (f.comprehension_messages(p, card, "N"),
                                 pgg_game.contribution_messages(p, "N", card, [], 0, 1,
                                                                prompt_frame=f)):
                    self.assertEqual(messages[0], {"role": "system", "content": card.text})
                # 4. q2: a change of 10 points (credits) of one's own, answer key -6
                q2 = [q for q in f.comprehension_questions() if q["id"] == "q2"][0]
                self.assertEqual(q2["answer"]["delta"], 10)
                self.assertIn("{delta} more", q2["text"])
                self.assertEqual(f.comprehension_key(p), {"q1": 28, "q2": -6})
                # 5. the schema's rationale description is the decisions' one
                schema = f.comprehension_schema(True)
                self.assertEqual(schema["properties"]["rationale"]["description"],
                                 "One or two sentences on why you chose this.")
                self.assertEqual(schema["properties"]["rationale"]["description"],
                                 f.response("rationale_description"))

    def test_once_per_schedule_and_rows_with_round_1(self):
        # 2. isolated: once per schedule; 3. group rows: round 1 (isolated: null)
        self.use(TwoFrameAPI())
        Engine(self.kcfg(self.tmp / "runs", "story_A", isolated_reps=2)).run()
        rows = _rows(self.tmp / "runs" / "k5" / "k5.jsonl")
        comp = [r for r in rows if r["step"] == "comprehension"]
        iso = [r for r in comp if r["arm"] == "isolated"]
        self.assertEqual(len(iso), 2)                          # 2 schedules, 1 each
        self.assertEqual(len({r["group_id"] for r in iso}), 2)
        self.assertTrue(all(r["round"] is None for r in iso))
        self.assertEqual(sorted((r["round"], r["agent_id"]) for r in comp if r["arm"] == "group"),
                         [(1, a) for a in range(1, 5)])


if __name__ == "__main__":
    import unittest
    unittest.main()
