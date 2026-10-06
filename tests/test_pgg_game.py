"""Mock end-to-end tests of the public goods engine (no network, no ../.env)."""

import ast
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Dummy key and a no-op load_dotenv, so importing never reads ../.env.
os.environ["OPENROUTER_API_KEY"] = "test-dummy"
with mock.patch("dotenv.load_dotenv", lambda *a, **k: False):
    import llm_client

import pgg_cost
import pgg_game
from pgg_game import Card, Engine, GameParams, RunAborted, RunConfig

CARD_A = Card("cityA", "styleX", "Fake card A: a short placeholder description.")
CARD_B = Card("cityB", "styleY", "Fake card B: another short placeholder.")


def _response(content, model="snap-1", reasoning="thinking text", finish_reason="stop"):
    message = SimpleNamespace(content=content, reasoning=reasoning)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    usage = SimpleNamespace(model_dump=lambda: {"prompt_tokens": 10, "completion_tokens": 5})
    return SimpleNamespace(model=model, choices=[choice], usage=usage)


def _payload(obj):
    return json.dumps(obj)


class FakeAPI:
    """Stands in for the OpenRouter client's chat.completions.create.

    Works out which step a prompt is from its text and answers with
    default_reply unless `script` has queued replies for that exact decision:
    script[(kind, agent, round)] is a list of raw message contents.
    """

    def __init__(self, script=None):
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.calls = []

    @staticmethod
    def parse(kwargs):
        user = kwargs["messages"][-1]["content"]
        agent = re.search(r"You are Player (\d)", user)
        rnd = re.search(r"ROUND (\d+) of", user)
        if '"punishments"' in user:
            kind = "punish"
        elif "QUESTION" in user:
            kind = "isolated"
        else:
            kind = "contribute"
        others = re.search(r"on average, (\d+) points", user)
        return (kind, int(agent.group(1)) if agent else None,
                int(rnd.group(1)) if rnd else None, int(others.group(1)) if others else None)

    def default_reply(self, kind, agent, rnd, others):
        if kind == "contribute":
            return _payload({"contribution": (agent * 3 + rnd) % 21, "rationale": "because"})
        if kind == "isolated":
            return _payload({"contribution": others // 2, "rationale": "because"})
        # punish: player 1 punishes player 2 with 3 points, nobody else punishes
        targets = [str(t) for t in range(1, 5) if t != agent]
        return _payload({"punishments": {t: (3 if agent == 1 and t == "2" else 0) for t in targets}})

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        kind, agent, rnd, others = self.parse(kwargs)
        queue = self.script.get((kind, agent, rnd))
        content = queue.pop(0) if queue else self.default_reply(kind, agent, rnd, others)
        return _response(content)

    def kinds(self):
        return [self.parse(c)[0] for c in self.calls]


class EngineTestBase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.log_path = self.tmp / "logs" / "raw_calls.jsonl"
        for p in (
            mock.patch.object(llm_client, "LOG_PATH", self.log_path),
            mock.patch.object(llm_client, "_client"),
            mock.patch.object(llm_client.time, "sleep"),
            # A5's refusal of dirty / unversioned code has its own tests
            # (test_pgg_a4_a5.py); here the code may be uncommitted or a copy
            mock.patch.object(pgg_game, "_REQUIRE_VERIFIED_CODE", False),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.api = FakeAPI()
        self.create = llm_client._client.chat.completions.create
        self.create.side_effect = self.api

    def set_script(self, script):
        self.api.script = {k: list(v) for k, v in script.items()}

    def cfg(self, **kw):
        base = dict(run="t1", cards=[CARD_A], models={"m1": "vendor/model-1"},
                    arms=("group",), groups_per_cell=1, isolated_reps=1,
                    results_dir=self.tmp / "results")
        base.update(kw)
        return RunConfig(**base)

    def run_engine(self, **kw):
        path = Engine(self.cfg(**kw)).run()
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def raw_log(self):
        if not self.log_path.exists():
            return []
        return [json.loads(line) for line in self.log_path.read_text().splitlines()]


class GroupGameN(EngineTestBase):
    def test_one_group_ten_rounds_payoffs_and_fields(self):
        rows = self.run_engine()
        self.assertEqual(len(rows), 40)
        self.assertEqual(len(self.api.calls), 40)
        self.assertTrue(all(r["step"] == "contribute" and r["arm"] == "group"
                            and r["condition"] == "N" for r in rows))
        for rnd in range(1, 11):
            group = [r for r in rows if r["round"] == rnd]
            self.assertEqual(sorted(r["agent_id"] for r in group), [1, 2, 3, 4])
            contributions = {r["agent_id"]: r["contribution"] for r in group}
            total = sum(contributions.values())
            for r in group:
                expected = 20 - r["contribution"] + 0.4 * total
                self.assertAlmostEqual(r["payoff"], expected, places=6)
                self.assertAlmostEqual(r["payoff_before_punishment"], expected, places=6)
                self.assertEqual(r["group_total"], total)
                self.assertTrue(0 <= r["contribution"] <= 20)
        # the fake's rule (agent*3 + round) % 21 was recorded as given
        self.assertEqual([r["contribution"] for r in rows if r["agent_id"] == 2],
                         [(6 + k) % 21 for k in range(1, 11)])

    def test_every_row_has_all_fields(self):
        required = {"run", "condition", "arm", "model", "model_snapshot", "session_id",
                    "group_id", "agent_id", "round", "card_id", "style", "contribution",
                    "n_invalid", "n_parse_fail", "finish_reason", "usage", "reasoning",
                    "reasoning_effort", "max_tokens", "seed", "ts", "temperature"}
        rows = self.run_engine(params=GameParams(rounds=2))
        for r in rows:
            self.assertTrue(required <= set(r), required - set(r))
            self.assertEqual(r["run"], "t1")
            self.assertEqual(r["model"], "vendor/model-1")
            self.assertEqual(r["model_snapshot"], "snap-1")
            self.assertEqual(r["finish_reason"], "stop")
            self.assertEqual(r["usage"], {"prompt_tokens": 10, "completion_tokens": 5})
            self.assertEqual(r["reasoning"], "thinking text")
            self.assertEqual((r["card_id"], r["style"]), ("cityA", "styleX"))
            self.assertEqual((r["n_invalid"], r["n_parse_fail"]), (0, 0))
            self.assertEqual(r["temperature"], "default")
            self.assertEqual(r["reasoning_effort"], "default")
            self.assertEqual(r["rationale"], "because")

    def test_session_and_group_ids_are_deterministic(self):
        rows = self.run_engine(params=GameParams(rounds=1))
        self.assertEqual({r["session_id"] for r in rows}, {"pgg-t1-m1-cityA-styleX-N-group-000"})
        self.assertEqual({r["group_id"] for r in rows}, {"cityA-styleX-N-g00"})
        self.assertEqual(pgg_game.session_id_for("t1", "m1", "cityA", "styleX", "N", "group", 0),
                         "pgg-t1-m1-cityA-styleX-N-group-000")

    def test_prompt_history_has_only_earlier_rounds(self):
        self.run_engine(params=GameParams(rounds=3))
        by_key = {}
        for c in self.api.calls:
            kind, agent, rnd, _ = FakeAPI.parse(c)
            by_key[(agent, rnd)] = c["messages"][-1]["content"]
        self.assertIn("first round", by_key[(1, 1)])
        self.assertNotIn("Round 1\n", by_key[(1, 1)])
        third = by_key[(1, 3)]
        self.assertIn("Round 1\n", third)
        self.assertIn("Round 2\n", third)
        self.assertNotIn("Round 3\n", third)
        # own contribution of round 1 (agent 1: (3 + 1) % 21 = 4) is in the history
        self.assertIn("Player 1 (you): 4", third)
        self.assertIn("Your earnings from the project", third)

    def test_card_text_goes_to_system_message_for_all_four_agents(self):
        self.run_engine(params=GameParams(rounds=1))
        for c in self.api.calls:
            system, user = c["messages"][0], c["messages"][1]
            self.assertEqual(system["role"], "system")
            self.assertIn(CARD_A.text, system["content"])
            self.assertNotIn(CARD_A.text, user["content"])

    def test_no_temperature_and_configured_limits_sent_and_recorded(self):
        rows = self.run_engine(params=GameParams(rounds=1), max_tokens=1234,
                               reasoning_effort="low")
        for kwargs in self.api.calls:
            self.assertNotIn("temperature", kwargs)
            self.assertEqual(kwargs["max_tokens"], 1234)
            self.assertEqual(kwargs["extra_body"]["reasoning"], {"effort": "low"})
        self.assertEqual({r["max_tokens"] for r in rows}, {1234})
        self.assertEqual({r["reasoning_effort"] for r in rows}, {"low"})

    def test_defaults_use_client_default_max_tokens_and_send_no_reasoning(self):
        rows = self.run_engine(params=GameParams(rounds=1))
        for kwargs in self.api.calls:
            self.assertEqual(kwargs["max_tokens"], llm_client.DEFAULT_MAX_TOKENS)
            self.assertNotIn("reasoning", kwargs["extra_body"])
        self.assertEqual({r["max_tokens"] for r in rows}, {llm_client.DEFAULT_MAX_TOKENS})

    def test_per_model_reasoning_effort(self):
        rows = self.run_engine(params=GameParams(rounds=1), reasoning_effort={"m1": "high"},
                               models={"m1": "vendor/model-1", "m2": "vendor/model-2"})
        self.assertEqual({r["model_key"]: r["reasoning_effort"] for r in rows},
                         {"m1": "high", "m2": "default"})
        for kwargs in self.api.calls:
            has = "reasoning" in kwargs["extra_body"]
            self.assertEqual(has, kwargs["model"] == "vendor/model-1")

    def test_results_file_is_never_overwritten(self):
        self.run_engine(params=GameParams(rounds=1))
        with self.assertRaises(FileExistsError):
            self.run_engine(params=GameParams(rounds=1))

    def test_workers_do_not_change_the_rows(self):
        def stable(rows):
            return [{k: v for k, v in r.items() if k not in ("ts", "elapsed_s")} for r in rows]
        serial = stable(self.run_engine(params=GameParams(rounds=3)))
        parallel = stable(self.run_engine(run="t2", params=GameParams(rounds=3), workers=4))
        for r in parallel:
            r["run"] = "t1"
            r["session_id"] = r["session_id"].replace("-t2-", "-t1-")
            r.pop("seed")
        for r in serial:
            r.pop("seed")
        self.assertEqual(serial, parallel)


class IsolatedSchedule(EngineTestBase):
    def test_five_conditional_values_one_call_each(self):
        rows = self.run_engine(arms=("isolated",))
        self.assertEqual(len(rows), 5)
        self.assertEqual(len(self.api.calls), 5)
        self.assertEqual([r["others_mean"] for r in rows], [0, 5, 10, 15, 20])
        self.assertEqual([r["contribution"] for r in rows], [0, 2, 5, 7, 10])
        for r in rows:
            self.assertEqual((r["arm"], r["condition"], r["step"]), ("isolated", "N", "isolated"))
            self.assertIsNone(r["round"])
            self.assertEqual(r["group_id"], "cityA-styleX-N-iso00")
        for x, c in zip((0, 5, 10, 15, 20), self.api.calls):
            user = c["messages"][-1]["content"]
            self.assertIn(f"on average, {x} points", user)
            self.assertNotIn("HISTORY", user)
        self.assertEqual(len({r["seed"] for r in rows}), 5)

    def test_invalid_value_is_rerequested_on_its_own_row(self):
        # the value for others_mean=10 comes back as 25 first
        calls = []
        orig = self.api.default_reply

        def reply(kind, agent, rnd, others):
            calls.append(others)
            if others == 10 and calls.count(10) == 1:
                return _payload({"contribution": 25})
            return orig(kind, agent, rnd, others)

        self.api.default_reply = reply
        rows = self.run_engine(arms=("isolated",))
        self.assertEqual([r["n_invalid"] for r in rows], [0, 0, 1, 0, 0])
        self.assertEqual(len(self.api.calls), 6)


class InvalidPayloads(EngineTestBase):
    def test_invalid_values_are_rerequested_counted_and_never_coded(self):
        self.set_script({("contribute", 1, 1): [
            _payload({"contribution": 25}),        # out of range
            _payload({"contribution": "abc"}),     # wrong type
            "this is not json",                    # broken JSON
            _payload({"contribution": 7}),
        ]})
        rows = self.run_engine(params=GameParams(rounds=1))
        target = [r for r in rows if r["agent_id"] == 1][0]
        self.assertEqual(target["contribution"], 7)
        self.assertEqual(target["n_invalid"], 2)
        self.assertEqual(target["n_parse_fail"], 1)
        others = [r for r in rows if r["agent_id"] != 1]
        self.assertEqual([(r["n_invalid"], r["n_parse_fail"]) for r in others], [(0, 0)] * 3)
        for r in rows:
            self.assertIsInstance(r["contribution"], int)
            self.assertTrue(0 <= r["contribution"] <= 20)
        self.assertNotIn(25, [r["contribution"] for r in rows])
        invalid_events = [e for e in self.raw_log() if e.get("invalid")]
        self.assertEqual(len(invalid_events), 2)

    def test_non_integer_payloads_are_invalid(self):
        params = GameParams()
        for bad in ({"contribution": 12.0}, {"contribution": True}, {"contribution": -1},
                    {"contribution": 21}, {"contribution": "7"}, {"contribution": None},
                    {"other": 5}, [], "5"):
            self.assertFalse(pgg_game.is_valid_contribution(bad, params), bad)
        self.assertTrue(pgg_game.is_valid_contribution({"contribution": 0}, params))
        self.assertTrue(pgg_game.is_valid_contribution({"contribution": 20}, params))

    def test_retry_limit_stops_the_run_with_a_logged_error(self):
        self.set_script({("contribute", 2, 1): [_payload({"contribution": 25})] * 10})
        path = self.tmp / "results" / "t1.jsonl"
        with self.assertRaises(RunAborted):
            Engine(self.cfg(params=GameParams(rounds=1), max_invalid=1)).run()
        # agent 1: 1 call; agent 2: max_invalid + 1 = 2 calls, then the run stops
        self.assertEqual(len(self.api.calls), 3)
        self.assertEqual(path.read_text(), "")  # nothing was coded for the failed round
        events = [e for e in self.raw_log() if e.get("event") == "pgg_run_aborted"]
        self.assertEqual(len(events), 1)
        self.assertEqual((events[0]["agent_id"], events[0]["round"]), (2, 1))

    def test_cli_returns_error_code_on_abort(self):
        cards = self.tmp / "cards.json"
        cards.write_text(json.dumps([{"card_id": "a", "style": "s", "text": "short fake card"}]))
        self.api.default_reply = lambda *a: _payload({"contribution": 99})
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = pgg_game.main([
                "--run", "cli_abort", "--cards", str(cards), "--models", "deepseek",
                "--arms", "isolated", "--max-invalid", "0", "--results-dir", str(self.tmp / "r")])
        self.assertEqual(code, 1)
        self.assertIn("HATA", err.getvalue())


class PunishmentCondition(EngineTestBase):
    def test_punishment_step_is_separate_and_costs_one_to_three(self):
        rows = self.run_engine(conditions=("P",), params=GameParams(rounds=2))
        self.assertEqual(len(rows), 16)
        self.assertEqual(self.api.kinds(),
                         (["contribute"] * 4 + ["punish"] * 4) * 2)
        for rnd in (1, 2):
            contrib = {r["agent_id"]: r for r in rows
                       if r["round"] == rnd and r["step"] == "contribute"}
            punish = {r["agent_id"]: r for r in rows
                      if r["round"] == rnd and r["step"] == "punish"}
            total = sum(r["contribution"] for r in contrib.values())
            base = {i: 20 - contrib[i]["contribution"] + 0.4 * total for i in contrib}
            # player 1 gives 3 points to player 2: cost 3 for player 1, -9 for player 2
            self.assertEqual(punish[1]["punishments"], {"2": 3, "3": 0, "4": 0})
            self.assertEqual(punish[1]["punishment_cost_paid"], 3)
            self.assertEqual(punish[2]["punishment_points_received"], 3)
            self.assertAlmostEqual(punish[1]["payoff"], base[1] - 3, places=6)
            self.assertAlmostEqual(punish[2]["payoff"], base[2] - 9, places=6)
            self.assertAlmostEqual(punish[3]["payoff"], base[3], places=6)
            self.assertAlmostEqual(contrib[2]["payoff_before_punishment"], base[2], places=6)
            self.assertAlmostEqual(contrib[2]["payoff"], base[2] - 9, places=6)
            self.assertTrue(all(r["condition"] == "P" for r in rows))

    def test_punishment_prompt_and_history(self):
        self.run_engine(conditions=("P",), params=GameParams(rounds=2))
        punish_prompt = [c for c in self.api.calls if FakeAPI.parse(c)[0] == "punish"][0]
        user = punish_prompt["messages"][-1]["content"]
        self.assertIn("punishment step", user)
        self.assertIn("Contributions:", user)  # contributions are revealed before it
        round2 = [c for c in self.api.calls
                  if FakeAPI.parse(c)[:3] == ("contribute", 2, 2)][0]["messages"][-1]["content"]
        self.assertIn("Punishment points you received: 3 (points lost: 9)", round2)
        self.assertIn("Your earnings after punishment", round2)

    def test_invalid_punishments_are_rerequested(self):
        self.set_script({("punish", 3, 1): [
            _payload({"punishments": {"1": 11, "2": 0, "4": 0}}),   # more than 10
            _payload({"punishments": {"1": 0, "2": 0}}),            # missing target
            _payload({"punishments": {"1": 0, "2": 0, "4": 0, "9": 1}}),  # wrong key set
            _payload({"punishments": {"1": 0, "2": 0, "4": 2}}),
        ]})
        rows = self.run_engine(conditions=("P",), params=GameParams(rounds=1))
        row = [r for r in rows if r["step"] == "punish" and r["agent_id"] == 3][0]
        self.assertEqual((row["n_invalid"], row["punishment_cost_paid"]), (3, 2))
        self.assertEqual(row["punishments"], {"1": 0, "2": 0, "4": 2})

    def test_rule_functions(self):
        p = GameParams()
        zero = [[0] * 4 for _ in range(4)]
        points = [row[:] for row in zero]
        points[0][1] = 4
        points[2][1] = 1
        final, cost, received = pgg_game.apply_punishment(p, [20.0] * 4, points)
        self.assertEqual(cost, [4, 0, 1, 0])
        self.assertEqual(received, [0, 5, 0, 0])
        self.assertEqual(final, [16.0, 20.0 - 15, 19.0, 20.0])
        # budget: total cost may not exceed the round's earnings
        ok = {"punishments": {"2": 10, "3": 10, "4": 4}}
        self.assertTrue(pgg_game.is_valid_punishment(ok, p, [2, 3, 4], budget=24))
        self.assertFalse(pgg_game.is_valid_punishment(ok, p, [2, 3, 4], budget=23))
        self.assertEqual(pgg_game.punishment_budget(24.4), 24)

    def test_project_payoff_formula(self):
        p = GameParams()
        self.assertEqual(pgg_game.project_payoffs(p, [20, 20, 20, 20]), [32.0] * 4)
        self.assertEqual(pgg_game.project_payoffs(p, [0, 0, 0, 0]), [20.0] * 4)
        free_rider = pgg_game.project_payoffs(p, [0, 20, 20, 20])
        self.assertEqual(free_rider, [44.0, 24.0, 24.0, 24.0])


class SeedsAndSessions(EngineTestBase):
    def test_seed_is_stable_crc32_seed(self):
        rows1 = self.run_engine(params=GameParams(rounds=2))
        rows2 = self.run_engine(run="t1", params=GameParams(rounds=2),
                                results_dir=self.tmp / "other")
        self.assertEqual([r["seed"] for r in rows1], [r["seed"] for r in rows2])
        self.assertEqual(len({r["seed"] for r in rows1}), len(rows1))
        first = rows1[0]
        self.assertEqual(first["seed"], llm_client.stable_seed(
            "pgg", "t1", "m1", "cityA", "styleX", "N", "group", 0, 1, 1, "contribute"))
        self.assertEqual(llm_client.stable_seed("a", 1, "b"), llm_client.stable_seed("a", 1, "b"))

    def test_hash_builtin_is_not_used(self):
        for name in ("pgg_game.py", "pgg_cost.py"):
            tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
            calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Name) and n.func.id == "hash"]
            self.assertEqual(calls, [], name)


class PromptsAndCards(EngineTestBase):
    SCORE = re.compile(r"\d\s*/\s*\d|(?:score|rating|salience|skor|puan)\w*\W{0,3}\d", re.I)

    def test_no_numeric_disposition_score_in_any_prompt(self):
        self.run_engine(conditions=("N", "P"), arms=("group", "isolated"),
                        params=GameParams(rounds=2))
        kinds = set()
        for c in self.api.calls:
            kinds.add(FakeAPI.parse(c)[0])
            for m in c["messages"]:
                self.assertIsNone(self.SCORE.search(m["content"]), m["content"][:200])
        self.assertEqual(kinds, {"contribute", "punish", "isolated"})

    def test_card_guard(self):
        for bad in ("Cooperativeness 7/10.", "Fairness score: 7", "salience of 0.6",
                    "She rates 7 out of 10 on sharing."):
            with self.assertRaises(ValueError, msg=bad):
                pgg_game.check_card_text(bad)
        pgg_game.check_card_text("A 21-year-old student living in a large city.")

    def test_load_cards(self):
        path = self.tmp / "cards.json"
        path.write_text(json.dumps([
            {"card_id": "a", "style": "s1", "text": "text one"},
            {"card_id": "a", "style": "s2", "text": "text two"}]))
        self.assertEqual([c.style for c in pgg_game.load_cards(path)], ["s1", "s2"])
        path.write_text(json.dumps([{"card_id": "a", "style": "s1", "text": "x"},
                                    {"card_id": "a", "style": "s1", "text": "y"}]))
        with self.assertRaises(ValueError):
            pgg_game.load_cards(path)
        path.write_text(json.dumps([{"card_id": "a", "text": "x"}]))
        with self.assertRaises(ValueError):
            pgg_game.load_cards(path)

    def test_config_validation(self):
        with self.assertRaises(ValueError):
            self.cfg(reasoning_effort="bogus").validate()
        with self.assertRaises(ValueError):
            self.cfg(conditions=("X",)).validate()
        with self.assertRaises(ValueError):
            self.cfg(isolated_points=(0, 25)).validate()
        with self.assertRaises(ValueError):
            self.cfg(run="bad name/").validate()
        with self.assertRaises(ValueError):
            self.cfg(max_tokens=0).validate()

    def test_cli_real_run_with_mock_client(self):
        cards = self.tmp / "cards.json"
        cards.write_text(json.dumps([{"card_id": "a", "style": "s", "text": "short fake card"}]))
        out = self.tmp / "res"
        with contextlib.redirect_stdout(io.StringIO()):
            code = pgg_game.main([
                "--run", "cli1", "--cards", str(cards), "--models", "deepseek",
                "--arms", "isolated", "--isolated-reps", "1", "--results-dir", str(out),
                "--reasoning-effort", "low", "--max-tokens", "999"])
        self.assertEqual(code, 0)
        rows = [json.loads(x) for x in (out / "cli1.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 5)
        self.assertEqual({r["model"] for r in rows}, {"deepseek/deepseek-v4.1-flash"})
        self.assertEqual({(r["reasoning_effort"], r["max_tokens"]) for r in rows}, {("low", 999)})


class DryRun(EngineTestBase):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(pgg_game.main(["--dry-run", *argv]), 0)
        return buf.getvalue()

    def test_pilot_counts_without_any_api_call(self):
        text = self.run_cli()
        self.create.assert_not_called()
        self.assertEqual(self.api.calls, [])
        self.assertIn("1620", text)
        self.assertEqual(text.count("540 çağrı"), 3)
        self.assertIn("(tahmin)", text)
        self.assertIn("contribute_N=480", text)
        self.assertIn("isolated=60", text)
        self.assertIn("maliyet_analizi.md", text)

    def test_pilot_cost_matches_cost_analysis(self):
        counts = pgg_cost.call_counts(n_cells=6)
        self.assertEqual(counts, {"contribute_N": 480, "contribute_P": 0, "punish_P": 0,
                                  "isolated": 60})
        est = pgg_cost.estimate(pgg_cost.PILOT_V2_MODELS, counts)
        by_model = {k: m["cost_usd"] for k, m in est["per_model"].items()}
        # maliyet_analizi.md §4: pilot 0,18 / 0,13 / 0,07 = 0,38 USD
        self.assertAlmostEqual(by_model["deepseek"], 0.18, delta=0.01)
        self.assertAlmostEqual(by_model["gpt"], 0.13, delta=0.01)
        self.assertAlmostEqual(by_model["gemini"], 0.07, delta=0.005)
        self.assertAlmostEqual(est["total_cost_usd"], 0.38, delta=0.01)
        self.assertEqual(est["total_calls"], 1620)

    def test_counts_for_other_designs(self):
        both = pgg_cost.call_counts(n_cells=12, conditions=("N", "P"), groups_per_cell=5,
                                    isolated_reps=5)
        self.assertEqual(both["contribute_N"], 2400)   # 12 x 5 groups x 4 x 10 (maliyet §3)
        self.assertEqual(both["contribute_P"], 2400)
        self.assertEqual(both["punish_P"], 2400)
        self.assertEqual(both["isolated"], 300)
        only_group = pgg_cost.call_counts(n_cells=6, arms=("group",))
        self.assertEqual(only_group["isolated"], 0)

    def test_overrides_and_cards_file(self):
        text = self.run_cli("--models", "gemini", "--cells", "2", "--groups-per-cell", "1",
                            "--arms", "group", "--rounds", "5")
        self.assertIn("40 çağrı", text)  # 2 cells x 1 group x 4 x 5
        cards = self.tmp / "c.json"
        cards.write_text(json.dumps([
            {"card_id": f"c{i}", "style": "s", "text": f"card {i}"} for i in range(3)]))
        text = self.run_cli("--cards", str(cards), "--models", "gpt", "--arms", "isolated")
        self.assertIn("30 çağrı", text)  # 3 cells x 2 reps x 5 values

    def test_pilot_models_equal_llm_client_models(self):
        self.assertEqual(pgg_cost.PILOT_MODELS, llm_client.MODELS)
        self.assertEqual(pgg_cost.PILOT_V2_MODELS, llm_client.MODELS_PILOT_V2)
        self.assertEqual(pgg_cost.KNOWN_MODELS, llm_client.MODELS_KNOWN)
        self.assertEqual(set(pgg_cost.PRICES_USD_PER_M), set(llm_client.MODELS_KNOWN.values()))
        self.assertEqual(set(pgg_cost.REASONING_TOKENS), set(llm_client.MODELS_KNOWN.values()))

    def test_unknown_model_is_an_error(self):
        with self.assertRaises(ValueError):
            pgg_game.resolve_models(["nope"], pgg_cost.PILOT_MODELS)

    def test_dry_run_needs_no_key_and_does_not_import_llm_client(self):
        env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
        proc = subprocess.run(
            [sys.executable, str(ROOT / "pgg_game.py"), "--dry-run"],
            capture_output=True, text=True, env=env, cwd=self.tmp, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("1620", proc.stdout)


if __name__ == "__main__":
    unittest.main()
