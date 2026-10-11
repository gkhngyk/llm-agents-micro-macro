"""Mock tests of EMIR 6 C3 + Soru 1-2 (task #96). No network, no ../.env, no real run directory.

C3 stage 0a redesigned: per format and model 6 cards x 1 group of a 3-round game
(params.rounds = 3 only in the 0a configs) + isolated X = 10 x 2 + rule
comprehension; invalid_rate_cap off, max_invalid 8. In stage 0a
(pgg_game.FORMAT_TEST_STAGES) a call without a valid answer (RunAborted) stops
only its model ("format_failed" when its answers were invalid / unparseable),
the other models go on, the model stays stopped on --resume, and the summary's
"format_test" holds the counts the selection rule reads.
Soru 1 per-model groups: config "groups_per_cell_by_model" overrides
groups_per_cell for the models it names (units, planned calls, dry run, config
record: a resume with other groups is refused).
Soru 2 budgets in the configs; prompt_scales renders the calibration reference
with the calibration's 10-round game.
"""

import contextlib
import hashlib
import io
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_pgg_game import CARD_A, CARD_B, _payload  # noqa: E402
from test_pgg_guards import CostAPI, GuardTestBase  # noqa: E402
from test_pgg_resume import ResumeBase, _rows  # noqa: E402

import pgg_cost  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Engine, GameParams, RunAborted, RunConfig  # noqa: E402

ROOT = Path(pgg_game.__file__).resolve().parent
CONFIGS = ROOT / "configs"
MAIN = CONFIGS / "main.json"
S0A = {"example_object": CONFIGS / "main_s0a_example.json",
       "json_schema_strict": CONFIGS / "main_s0a_schema.json"}
S0B = CONFIGS / "main_s0b.json"
FRAME_SHA = "c00db315d9c3141b78b04de5ece650e4b922db907cb90ae124666c439633a9f4"
CARDS_SHA = "bb2be483d1cb860df43d46675a0b798acc240f5d022ee36a5e5d272a12d7f1dc"
PROVIDER_NAMES = {"deepseek/deepseek-v4.1-flash": "DeepInfra",
                  "mistralai/mistral-large-4-0": "Mistral", "openai/gpt-6-luna": "OpenAI"}
MISTRAL = "mistralai/mistral-large-4-0"


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _cli(argv):
    with contextlib.redirect_stdout(io.StringIO()) as out, \
            contextlib.redirect_stderr(io.StringIO()) as err:
        code = pgg_game.main(argv)
    return code, out.getvalue(), err.getvalue()


def _user(kwargs) -> str:
    return kwargs["messages"][-1]["content"]


def _stage_reply(kwargs, content):
    """Valid answers for every call of the abstract_v4 stage configs (any answer format)."""
    user = _user(kwargs)
    if "RULE CHECK" in user:
        return _payload({"q1": 28, "q2": -6, "rationale": "r"})
    if "QUESTION" in user:
        return _payload({"contribution": 5, "rationale": "r"})
    return _payload({"contribution": 7, "rationale": "r"})


class StageAPI(CostAPI):
    """CostAPI whose content comes from content_fn only (FakeAPI's default reply reads the
    schema text, which the answer formats A and B do not send)."""

    def default_reply(self, kind, agent, rnd, others):
        return _payload({})


def _stage_settings(path, tmp, **over):
    args = pgg_game.build_parser().parse_args(["--config", str(path)])
    s = pgg_game.settings_from_args(args)
    s.update(over)
    models = pgg_game.resolve_models(s["models"], pgg_cost.KNOWN_MODELS)
    return s, models


# --------------------------------------------------------------------------
# C3: the 0a configs and their 3-round design
# --------------------------------------------------------------------------

class Stage0aConfigs(GuardTestBase):
    def test_config_values(self):
        main = _json(MAIN)
        for fmt, path in S0A.items():
            with self.subTest(fmt):
                a = _json(path)
                self.assertIs(a["prereg_approved"], True)    # task #99
                self.assertEqual((a["stage"], a["answer_format"]), ("0a", fmt))
                self.assertEqual(a["params"], {"rounds": 3})
                self.assertEqual((a["cities"], a["arms"], a["groups_per_cell"], a["isolated_reps"],
                                  a["isolated_points"], a["isolated_round_no"], a["comprehension"]),
                                 (["Boston", "Riyadh"], ["group", "isolated"], 1, 2, [10], 2, True))
                self.assertIsNone(a["invalid_rate_cap"])
                self.assertEqual(a["max_invalid"], 8)
                self.assertEqual((a["budget_usd"], a["model_budget_usd"],
                                  a["expected_cost_gate_usd"]),
                                 (1.6, {"deepseek": 0.3, "mistral": 1.3, "gpt": 0.1}, 1.0))
                self.assertNotIn("groups_per_cell_by_model", a)
                self.assertEqual(a["frame_files"]["abstract_v4"]["sha256"], FRAME_SHA)
                self.assertEqual(a["cards_sha256"], CARDS_SHA)
                self.assertNotIn("Design the engine runs as it is", a["_notes"])
                self.assertNotIn("until then a placeholder", a["_notes"])
        # the default game (10 rounds) is unchanged; stages 0b and 1 play it
        self.assertEqual(GameParams().rounds, 10)
        self.assertNotIn("params", main)
        self.assertNotIn("params", _json(S0B))

    def test_run_config_counts(self):
        for fmt, path in S0A.items():
            with self.subTest(fmt):
                s, models = _stage_settings(path, self.tmp)
                self.assertEqual(s["params"], GameParams(rounds=3))
                cfg = pgg_game.run_config("main_s0a_x_20261011", s, models,
                                          {"runs_dir": self.tmp})
                engine = Engine(cfg, llm=pgg_game.OfflineLLM())
                for key in models:
                    # 6 cards x (4 agents x 3 rounds + 4 comprehension + 2 x (1 + 1))
                    self.assertEqual(cfg.planned_calls_per_model(key), 6 * 20)
                    self.assertEqual(cfg.planned_calls_per_model(key, comprehension=False), 6 * 14)
                    self.assertIsNone(cfg.invalid_limit(key))           # cap off
                specs = engine.unit_specs()
                self.assertEqual(len(specs), 3 * 6 * 3)                # 1 group + 2 schedules
                self.assertEqual(sum(1 for s_ in specs if s_.arm == "group"), 18)
                self.assertIsNone(engine.cost_gate_problem())
                est = engine.design_estimate()
                self.assertEqual(est["total_calls"], 360)
                self.assertLess(est["total_cost_usd"] * 1.1, cfg.expected_cost_gate_usd + 1e-9)
                self.assertLessEqual(est["total_p95_upper_usd"], cfg.budget_usd)
                for key, m in est["per_model"].items():
                    self.assertLessEqual(m["p95_upper_usd"], cfg.model_budget_usd[key], key)

    def test_round_5_of_10_does_not_fit_a_3_round_game(self):
        s, models = _stage_settings(S0A["example_object"], self.tmp, isolated_round_no=5)
        with self.assertRaisesRegex(ValueError, r"isolated_round_no must be an integer in 2\.\.3"):
            Engine(pgg_game.run_config("x", s, models, {"runs_dir": self.tmp}),
                   llm=pgg_game.OfflineLLM())

    def test_rendered_prompts_say_round_k_of_3(self):
        s, models = _stage_settings(S0A["example_object"], self.tmp)
        cfg = pgg_game.run_config("x", s, models, {"runs_dir": self.tmp})
        f = cfg.load_frames()["abstract_v4"]
        p, card = cfg.params, cfg.cards[0]
        history = []
        for r in range(1, 4):
            user = pgg_game.contribution_messages(p, "N", card, history, 0, r,
                                                  prompt_frame=f)[-1]["content"]
            self.assertIn(f"ROUND {r} of 3. You are Player 1. All players decide", user)
            self.assertIn("The same 4 players stay together for all 3 rounds.", user)
            c = [7, 7, 7, 7]
            history.append(pgg_game.RoundRecord(r, c, pgg_game.project_payoffs(p, c),
                                                final_earnings=pgg_game.project_payoffs(p, c)))
        iso = pgg_game.isolated_messages(p, card, 10, "fixed_round", 2,
                                         prompt_frame=f)[-1]["content"]
        self.assertIn("This is round 2 of 3. In the previous round the other 3 players", iso)


class Stage0aRuns(GuardTestBase):
    def run_stage(self, path, content_fn=_stage_reply, run="s0a", **over):
        s, models = _stage_settings(path, self.tmp, **over)
        (self.tmp / "runs").mkdir(exist_ok=True)
        cfg = pgg_game.run_config(run, s, models, {"runs_dir": self.tmp / "runs"})
        api = StageAPI(content_fn=content_fn, provider_fn=lambda k: PROVIDER_NAMES[k["model"]])
        self.use(api)
        engine = Engine(cfg)
        path = engine.run()
        summary = json.loads((self.tmp / "runs" / run / f"{run}_summary.json").read_text())
        return engine, api, _rows(path), summary

    def test_full_stage_runs_with_every_prompt_of_3_rounds(self):
        for fmt, path in S0A.items():
            with self.subTest(fmt):
                engine, api, rows, summary = self.run_stage(path, run=f"s0a_{fmt}")
                self.assertEqual(len(api.calls), 360)
                self.assertEqual(len(rows), 360)
                self.assertEqual({r["answer_format"] for r in rows}, {fmt})
                rounds = {int(m.group(1)) for k in api.calls
                          for m in [re.search(r"ROUND (\d+) of 3\.", _user(k))] if m}
                self.assertEqual(rounds, {1, 2, 3})
                self.assertFalse(any("of 10" in _user(k) for k in api.calls))
                self.assertTrue(all("This is round 2 of 3." in _user(k) for k in api.calls
                                    if "QUESTION" in _user(k)))
                ft = summary["format_test"]
                self.assertEqual((ft["answer_format"], ft["max_invalid"], ft["invalid_rate_cap"]),
                                 (fmt, 8, None))
                self.assertEqual(set(ft["models"]), {"deepseek", "mistral", "gpt"})
                for m in ft["models"].values():
                    self.assertEqual((m["n_responses"], m["n_invalid_parse"],
                                      m["invalid_parse_rate"], m["run_aborted"],
                                      m["format_failed"], m["n_units"], m["n_units_complete"]),
                                     (120, 0, 0.0, False, False, 18, 18))
                self.assertEqual(summary["stopped_models"], {})
                self.assertIsNone(summary["invalid_limit_per_model"])

    def test_a_failed_format_stops_only_that_model(self):
        def mistral_invalid(kwargs, content):
            content = _stage_reply(kwargs, content)
            if kwargs["model"] == MISTRAL and "ROUND" in _user(kwargs):
                return _payload({"contribution": 25, "rationale": "r"})     # outside 0..20
            return content
        engine, api, rows, summary = self.run_stage(S0A["example_object"], mistral_invalid)
        self.assertIsNone(engine.aborted)
        self.assertIsNone(summary["stop_reason"])
        self.assertEqual(summary["stopped_models"], {"mistral": "format_failed"})
        stop = summary["model_stops"]["mistral"]
        self.assertEqual((stop["reason"], stop["failure"], stop["abort_reason"],
                          stop["failed_call_n_invalid"]),
                         ("format_failed", "max_invalid", "run_aborted", 9))
        by_model = {}
        for r in rows:
            by_model[r["model_key"]] = by_model.get(r["model_key"], 0) + 1
        self.assertEqual((by_model["deepseek"], by_model["gpt"]), (120, 120))
        self.assertLess(by_model.get("mistral", 0), 120)
        ft = summary["format_test"]["models"]
        self.assertEqual((ft["mistral"]["run_aborted"], ft["mistral"]["format_failed"],
                          ft["mistral"]["failure"]), (True, True, "max_invalid"))
        self.assertGreaterEqual(ft["mistral"]["n_invalid"], 9)     # the failed call's 9
        self.assertGreater(ft["mistral"]["invalid_parse_rate"], 0.02)
        self.assertEqual(ft["mistral"]["invalid_parse_rate"],
                         ft["mistral"]["n_invalid_parse"] / ft["mistral"]["n_responses"])
        for key in ("deepseek", "gpt"):
            self.assertEqual((ft[key]["run_aborted"], ft[key]["format_failed"],
                              ft[key]["invalid_parse_rate"], ft[key]["n_units_complete"]),
                             (False, False, 0.0, 18))
        raw = [json.loads(x) for x in
               (self.tmp / "runs" / "s0a" / "raw_calls.jsonl").read_text().splitlines()]
        ev = [e for e in raw if e.get("event") == "pgg_run_aborted"]
        self.assertTrue(ev and all(e["model_only"] and e["failure"] == "max_invalid"
                                   and e["n_invalid"] == 9 for e in ev))
        # the failed call: 1 request + 8 re-requests, all invalid
        stopped = [e for e in raw if e.get("event") == "pgg_model_stopped"
                   and e["reason"] == "format_failed"]
        self.assertEqual(len(stopped), 1)


class FormatFailure(GuardTestBase):
    """Two models; m1's answers are never valid."""

    def cfg2(self, **kw):
        base = dict(cards=[CARD_A, CARD_B], models={"m1": "v/m1", "m2": "v/m2"},
                    arms=("group", "isolated"), params=GameParams(rounds=2), max_invalid=2,
                    stage="0a")
        base.update(kw)
        return self.cfg(**base)

    @staticmethod
    def bad_m1(reply):
        return lambda kwargs, content: reply if kwargs["model"] == "v/m1" else content

    def test_invalid_answers(self):
        self.use(CostAPI(content_fn=self.bad_m1(_payload({"contribution": 99}))))
        engine = Engine(self.cfg2())
        engine.run()
        s = self.summary()
        self.assertEqual(s["stopped_models"], {"m1": "format_failed"})
        m1 = s["format_test"]["models"]["m1"]
        self.assertEqual((m1["failure"], m1["n_invalid"], m1["n_responses"]),
                         ("max_invalid", 3, 3))
        self.assertEqual(m1["invalid_parse_rate"], 1.0)
        m2 = s["format_test"]["models"]["m2"]
        self.assertEqual((m2["n_units_complete"], m2["n_units"], m2["run_aborted"]), (4, 4, False))
        # the stats count the failed call's invalids like the raw log does
        self.assertEqual(s["per_model"]["v/m1"]["n_invalid"],
                         len([e for e in self.events("invalid_payload") if e["model"] == "v/m1"]))

    def test_unparseable_answers(self):
        self.use(CostAPI(content_fn=self.bad_m1("this is not json")))
        Engine(self.cfg2()).run()
        s = self.summary()
        self.assertEqual(s["stopped_models"], {"m1": "format_failed"})
        m1 = s["format_test"]["models"]["m1"]
        self.assertEqual((m1["failure"], m1["format_failed"], m1["n_invalid"]),
                         ("parse_fail", True, 0))
        self.assertGreater(m1["n_parse_fail"], 0)
        self.assertEqual(m1["n_invalid_parse"], m1["n_parse_fail"])

    def test_provider_mismatch_stops_the_model_but_is_no_format_failure(self):
        providers = {"m1": {"slug": "p1", "name": "P1"}, "m2": {"slug": "p2", "name": "P2"}}
        self.use(CostAPI(provider_fn=lambda k: "Other" if k["model"] == "v/m1" else "P2"))
        Engine(self.cfg2(providers=providers)).run()
        s = self.summary()
        self.assertEqual(s["stopped_models"], {"m1": "provider_mismatch_limit"})
        m1 = s["format_test"]["models"]["m1"]
        self.assertEqual((m1["run_aborted"], m1["format_failed"], m1["failure"]),
                         (True, False, None))
        self.assertEqual(s["format_test"]["models"]["m2"]["n_units_complete"], 4)

    def test_other_stages_still_stop_the_run(self):
        for stage in (None, "0b", "1"):
            with self.subTest(stage=stage):
                self.use(CostAPI(content_fn=self.bad_m1(_payload({"contribution": 99}))))
                with self.assertRaises(RunAborted) as cm:
                    Engine(self.cfg2(stage=stage, run=f"t_{stage}")).run()
                self.assertEqual((cm.exception.model_key, cm.exception.failure), ("m1", "max_invalid"))
                s = self.summary(f"t_{stage}")
                self.assertEqual(s["stop_reason"], "run_aborted")
                self.assertNotIn("format_test", s)


class FormatFailureResume(ResumeBase):
    def test_failed_model_stays_stopped_on_resume(self):
        bad = lambda k, c: _payload({"contribution": 99}) if k["model"] == "v/m1" else c  # noqa: E731
        kw = dict(stage="0a", invalid_rate_cap=None, max_invalid=1, budget_usd=None)
        # segment 0: m1 fails; then cut by SIGTERM in m2's last unit
        api0 = CostAPI(content_fn=bad)
        self.use(api0)
        Engine(self.rcfg(**kw)).run()
        s0 = self.summary_now()
        self.assertEqual(s0["stopped_models"], {"m1": "format_failed"})
        m1_units = [u for u in s0["unit_order"] if u.startswith("m1|")]
        self.assertEqual(s0["format_test"]["models"]["m1"]["n_units_complete"], 0)
        engine, api = self.resume(**kw)
        plan = engine.resume_plan()
        self.assertEqual(set(plan.format_failed), {"m1"})
        self.assertEqual(plan.format_failed["m1"]["failure"], "max_invalid")
        self.assertEqual(set(plan.remaining), set(m1_units))
        engine.run(resume=True)
        self.assertEqual(api.calls, [])                       # m1 is not asked again
        s1 = self.summary_now()
        self.assertEqual(s1["stopped_models"], {"m1": "format_failed"})
        stop = s1["segments"][-1]["model_stops"]["m1"]
        self.assertEqual((stop["reason"], stop["at_resume"], stop["failed_in_segment"]),
                         ("format_failed", True, 0))
        self.assertTrue(s1["format_test"]["models"]["m1"]["format_failed"])
        self.assertEqual(s1["format_test"]["models"]["m1"]["n_invalid"],
                         s0["format_test"]["models"]["m1"]["n_invalid"])


# --------------------------------------------------------------------------
# Soru 1: groups_per_cell_by_model
# --------------------------------------------------------------------------

class GroupsPerModel(ResumeBase):
    def test_units_and_planned_calls(self):
        cfg = self.rcfg(groups_per_cell_by_model={"m1": 3})
        engine = Engine(cfg, llm=pgg_game.OfflineLLM())
        specs = engine.unit_specs()
        groups = {}
        for s in specs:
            if s.arm == "group":
                groups[s.model_key] = groups.get(s.model_key, 0) + 1
        self.assertEqual(groups, {"m1": 2 * 3, "m2": 2 * 1})
        self.assertEqual(len(specs), 6 + 2 + 2 * 2)                 # + 1 schedule per cell
        self.assertEqual(cfg.groups_per_model(), {"m1": 3, "m2": 1})
        # 2 cards x (G x 4 agents x 2 rounds) + 2 cards x 5 points
        self.assertEqual(cfg.planned_calls_per_model("m1"), 2 * 3 * 8 + 10)
        self.assertEqual(cfg.planned_calls_per_model("m2"), 2 * 1 * 8 + 10)
        self.assertEqual(engine.config_record()["groups_per_cell_by_model"], {"m1": 3})
        # without it the record is the earlier one (earlier runs resume)
        self.assertNotIn("groups_per_cell_by_model",
                         Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).config_record())
        # every unit is in the order once; the m1-only passes come last
        self.assertEqual(len({s.label for s in specs}), len(specs))
        self.assertTrue(all(s.model_key == "m1" for s in specs[-4:]))

    def test_a_run_plays_every_group(self):
        self.use(CostAPI())
        Engine(self.rcfg(groups_per_cell_by_model={"m1": 2}, invalid_rate_cap=None)).run()
        rows = _rows(self.results)
        groups = {(r["model_key"], r["group_id"]) for r in rows if r["arm"] == "group"}
        self.assertEqual(sum(1 for m, _ in groups if m == "m1"), 4)
        self.assertEqual(sum(1 for m, _ in groups if m == "m2"), 2)
        s = self.summary_now()
        self.assertEqual(s["groups_per_cell"], {"m1": 2, "m2": 1})
        self.assertEqual(s["planned_calls_by_model"], {"m1": 2 * 2 * 8 + 10, "m2": 2 * 8 + 10})
        self.assertEqual(s["units"]["n_remaining"], 0)

    def test_validation(self):
        for value, msg in (({"m9": 2}, "not in the run"), ({"m1": 0}, "positive integer"),
                           ({"m1": 2.5}, "positive integer"), ({}, "non-empty")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, msg):
                    self.rcfg(groups_per_cell_by_model=value).validate()

    def test_resume_with_other_groups_is_refused(self):
        self.interrupted_run(at=5, groups_per_cell_by_model={"m1": 2})
        for other in (None, {"m1": 3}, {"m1": 2, "m2": 2}):
            with self.subTest(other=other):
                engine, api = self.resume(groups_per_cell_by_model=other)
                with self.assertRaisesRegex(ValueError, "config groups_per_cell_by_model"):
                    engine.run(resume=True)
                self.assertEqual(api.calls, [])
        engine, api = self.resume(groups_per_cell_by_model={"m1": 2})
        engine.run(resume=True)
        self.assertEqual(self.summary_now()["units"]["n_remaining"], 0)

    def test_settings_and_cli(self):
        args = pgg_game.build_parser().parse_args(
            ["--config", str(MAIN), "--groups-per-cell-by-model", "mistral=12"])
        self.assertEqual(pgg_game.settings_from_args(args)["groups_per_cell_by_model"],
                         {"mistral": 12})
        args = pgg_game.build_parser().parse_args(["--config", str(MAIN), "--groups-per-cell", "6"])
        s = pgg_game.settings_from_args(args)
        self.assertEqual(s["groups_per_cell"], 6)
        self.assertNotIn("groups_per_cell_by_model", s)
        models = pgg_game.resolve_models(_json(MAIN)["models"], pgg_cost.KNOWN_MODELS)
        self.assertEqual(pgg_game.resolve_model_keyed({MISTRAL: 4}, models, "g"), {"mistral": 4})
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            pgg_game.build_parser().parse_args(["--groups-per-cell-by-model", "mistral"])

    def test_count_blockers_see_a_placeholder(self):
        self.assertEqual(pgg_game.count_blockers({"groups_per_cell_by_model": {"gpt": "<G>"}}),
                         ["groups_per_cell_by_model.gpt"])


class DryRunCounts(unittest.TestCase):
    def dry(self, *argv):
        code, out, err = _cli(["--dry-run", *argv])
        self.assertEqual(code, 0, err)
        return out

    def test_main_config_16_16_10(self):
        for fmt in ("example_object", "json_schema_strict"):
            with self.subTest(fmt):
                text = self.dry("--config", str(MAIN), "--answer-format", fmt)
                # 12 cards x (G x 4 x 10 + G x 4 comprehension + 4 x 5 isolated + 4)
                per = {k: 12 * (g * 44 + 24) for k, g in (("deepseek", 16), ("mistral", 10),
                                                          ("gpt", 16))}
                self.assertEqual(per, {"deepseek": 8736, "mistral": 5568, "gpt": 8736})
                total = int(re.search(r"^TOPLAM .*?(\d+) çağrı", text, re.M).group(1))
                self.assertEqual(total, sum(per.values()))
                for key, n in per.items():
                    g = 16 if key != "mistral" else 10
                    self.assertRegex(text, rf"abstract_v4 +{key} +\S+ +G={g} +{n} çağrı")
                self.assertIn("model başına deepseek 16, mistral 10, gpt 16 homojen grup", text)
                self.assertIn("Beklenti kapısı expected_cost_gate_usd=52 USD: GEÇER", text)
                self.assertIn("groups_per_cell_by_model={'deepseek': 16, 'mistral': 10, 'gpt': 16}",
                              text)
                self.assertNotIn("AŞIYOR", text)
        # --groups-per-cell alone: every model 10 (the numbers of task #95)
        text = self.dry("--config", str(MAIN), "--answer-format", "example_object",
                        "--groups-per-cell", "10")
        self.assertRegex(text, r"(?m)^TOPLAM .*? 16704 çağrı +~44\.4438 USD")

    def test_design_estimate_per_model(self):
        est = pgg_game.design_estimate(
            models={"gpt": "openai/gpt-6-luna", "mistral": MISTRAL},
            frame_models={pgg_game.DEFAULT_FRAME: ["gpt", "mistral"]}, frames={}, n_cells=2,
            params=GameParams(rounds=2), conditions=("N",), arms=("group",), groups_per_cell=1,
            isolated_reps=1, n_points=5, scale=False, groups_per_cell_by_model={"gpt": 3})
        calls = {r["model"]: (r["groups_per_cell"], r["calls"]) for r in est["rows"]}
        self.assertEqual(calls, {"gpt": (3, 2 * 3 * 8), "mistral": (1, 2 * 8)})
        self.assertEqual(est["total_calls"], 64)
        self.assertEqual(est["groups_per_model"], {"gpt": 3, "mistral": 1})


# --------------------------------------------------------------------------
# Soru 2: budgets; cost of a 3-round game
# --------------------------------------------------------------------------

class Budgets(unittest.TestCase):
    def test_config_budgets(self):
        m = _json(MAIN)
        self.assertEqual((m["groups_per_cell"], m["groups_per_cell_by_model"]),
                         (10, {"deepseek": 16, "mistral": 10, "gpt": 16}))
        self.assertEqual((m["budget_usd"], m["model_budget_usd"], m["expected_cost_gate_usd"]),
                         (91, {"deepseek": 22, "mistral": 68, "gpt": 3}, 52))
        self.assertEqual(sorted(pgg_game.open_choices(m)), ["answer_format"])
        b = _json(S0B)
        self.assertEqual((b["budget_usd"], b["model_budget_usd"], b["expected_cost_gate_usd"]),
                         (10, {"deepseek": 2, "mistral": 8, "gpt": 0.5}, 5.5))
        for path in (MAIN, S0B, *S0A.values()):
            raw = _json(path)
            self.assertIs(raw["prereg_approved"], True, path)    # task #99
            self.assertNotIn("main_dryrun_tablosu.md", raw["_notes"], path)
            self.assertNotIn("placeholders until the user chooses", raw["_notes"], path)

    def test_budget_rule_holds_on_the_dry_runs(self):
        """sert >= toplam p95, alt >= model p95, kapı >= ortalama x 1,1 (A and B)."""
        for path in (MAIN, S0B, *S0A.values()):
            raw = _json(path)
            for fmt in ("example_object", "json_schema_strict"):
                with self.subTest(path=path.name, fmt=fmt):
                    args = pgg_game.build_parser().parse_args(
                        ["--config", str(path), "--answer-format", fmt])
                    s = pgg_game.settings_from_args(args)
                    models = pgg_game.resolve_models(s["models"], pgg_cost.KNOWN_MODELS)
                    with pgg_cost.extra_overlays(pgg_game.cost_calibration_files(
                            s["cost_calibration"])):
                        est = pgg_game.design_estimate(
                            models=models, frame_models=pgg_game.resolve_frames(s["frames"], models),
                            frames=pgg_game.dry_run_frames(s["frames"], s["frame_files"]),
                            n_cells=len(pgg_game.load_cards(s["cards"], s["cities"])),
                            params=s["params"], conditions=tuple(s["conditions"]),
                            arms=tuple(s["arms"]), groups_per_cell=s["groups_per_cell"],
                            groups_per_cell_by_model=s.get("groups_per_cell_by_model"),
                            isolated_reps=s["isolated_reps"], n_points=len(s["isolated_points"]),
                            comprehension=True, isolated_frame=s["isolated_frame"],
                            isolated_round_no=s["isolated_round_no"],
                            cards=pgg_game.load_cards(s["cards"], s["cities"]), answer_format=fmt)
                    self.assertGreaterEqual(raw["budget_usd"], est["total_p95_upper_usd"])
                    self.assertGreaterEqual(raw["expected_cost_gate_usd"],
                                            est["total_cost_usd"] * 1.1)
                    for key, m in est["per_model"].items():
                        self.assertGreaterEqual(raw["model_budget_usd"][key], m["p95_upper_usd"])

    def test_prompt_scales_of_3_rounds_use_the_10_round_reference(self):
        f = pgg_game.load_frame_file("abstract_v4", _json(MAIN)["frame_files"]["abstract_v4"])
        cards = pgg_game.load_cards(ROOT / "cards" / "main_cards_v1.json", ["Boston", "Riyadh"])
        ten = pgg_game.prompt_scales(f, GameParams(), cards, isolated_frame="fixed_round")
        three = pgg_game.prompt_scales(f, GameParams(rounds=3), cards,
                                       isolated_frame="fixed_round", isolated_round_no=2)
        self.assertLess(three["contribute_N"], 0.8 * ten["contribute_N"])   # shorter histories
        # the reference is the calibration's 10-round game whatever the params
        ref = pgg_game.mean_prompt_chars(pgg_game.default_frame(), "contribute_N", GameParams(),
                                         cards, isolated_frame="repeated")
        mine = pgg_game.mean_prompt_chars(f, "contribute_N", GameParams(rounds=3), cards,
                                          isolated_frame="fixed_round", isolated_round_no=2)
        self.assertAlmostEqual(three["contribute_N"], mine / ref)
        self.assertEqual(pgg_game.CALIBRATION_PARAMS, GameParams())

    def test_frame_and_cards_unchanged(self):
        def sha(p):
            return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
        self.assertEqual(sha("frames/abstract_v4.json"), FRAME_SHA)
        self.assertEqual(sha("cards/main_cards_v1.json"), CARDS_SHA)


if __name__ == "__main__":
    unittest.main()
