"""Mock tests of the plumbing before the pilot re-run (no network, no ../.env).

(a) persistent output directory, (b) max_tokens / timeout, (c) provider
pinning, (d) provider errors, (e) run order, (f) earnings labels, (g) isolated
frame.
"""

import contextlib
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_pgg_game import CARD_A, CARD_B, ROOT, FakeAPI, _payload  # noqa: E402
from test_pgg_guards import PILOT_CONFIG, CostAPI, GuardTestBase, _response  # noqa: E402

import llm_client  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Card, Engine, GameParams  # noqa: E402

CARDS6 = [Card(f"city{i}", "s", f"Fake card {i}: placeholder text.") for i in range(6)]
MODELS3 = {"m1": "v/m1", "m2": "v/m2", "m3": "v/m3"}
PINNED = {"m1": {"slug": "prov-a/fp8", "name": "Prov A", "quantizations": ["fp8"]}}


def _cards_file(tmp: Path) -> Path:
    path = tmp / "cards.json"
    path.write_text(json.dumps([{"card_id": "a", "style": "s", "text": "short fake card"}]))
    return path


def _lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


# --------------------------------------------------------------------------
# (a) persistent output directory
# --------------------------------------------------------------------------

class RunsDir(GuardTestBase):
    def runs_cfg(self, **kw):
        base = dict(results_dir=None, runs_dir=self.tmp / "runs")
        base.update(kw)
        return self.cfg(**base)

    def test_outputs_go_to_runs_dir_with_line_counts_in_summary(self):
        (self.tmp / "runs").mkdir()
        before = llm_client.LOG_PATH
        engine = Engine(self.runs_cfg(params=GameParams(rounds=2), arms=("group", "isolated")))
        path = engine.run()
        run_dir = self.tmp / "runs" / "t1"
        self.assertEqual(path, run_dir / "t1.jsonl")
        raw = run_dir / "raw_calls.jsonl"
        summary = json.loads((run_dir / "t1_summary.json").read_text())
        self.assertEqual(summary["files"]["results"], {"path": str(path), "lines": 8 + 5})
        self.assertEqual(summary["files"]["raw_log"]["path"], str(raw))
        self.assertEqual(summary["files"]["raw_log"]["lines"], _lines(raw))
        self.assertTrue(summary["files"]["raw_log"]["redirected_for_run"])
        self.assertEqual(summary["files"]["summary"]["path"], str(run_dir / "t1_summary.json"))
        events = [json.loads(x).get("event") for x in raw.read_text().splitlines()]
        self.assertEqual(events[0], "pgg_run_start")
        self.assertEqual(events[-1], "pgg_run_end")
        self.assertEqual(events.count(None), 13)          # one record per call
        self.assertEqual(llm_client.LOG_PATH, before)     # restored after the run
        self.assertFalse(self.log_path.exists())          # nothing went to the old log
        self.assertEqual(engine.files, summary["files"])

    def test_missing_relative_or_in_worktree_dir_fails_before_any_call(self):
        with self.assertRaisesRegex(ValueError, "does not exist"):
            Engine(self.runs_cfg())                       # tmp/runs not created
        with self.assertRaisesRegex(ValueError, "absolute"):
            Engine(self.runs_cfg(runs_dir=Path("runs")))
        with self.assertRaisesRegex(ValueError, "absolute"):
            Engine(self.cfg(results_dir=Path("results")))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            Engine(self.cfg(runs_dir=self.tmp))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            Engine(self.cfg(results_dir=None))
        # a git worktree (.git is a file): nothing inside it is accepted
        repo = self.tmp / "repo"
        (repo / "runs").mkdir(parents=True)
        (repo / ".git").write_text("gitdir: elsewhere\n")
        with mock.patch.object(pgg_game, "PROJECT_DIR", repo):
            with self.assertRaisesRegex(ValueError, "inside the git worktree"):
                Engine(self.runs_cfg(runs_dir=repo / "runs"))
            with self.assertRaisesRegex(ValueError, "inside the git worktree"):
                Engine(self.cfg(results_dir=repo / "results"))
        # a main checkout (.git is a directory): its results/ is persistent
        (repo / ".git").unlink()
        (repo / ".git").mkdir()
        with mock.patch.object(pgg_game, "PROJECT_DIR", repo):
            Engine(self.runs_cfg(runs_dir=repo / "runs"))
        self.create.assert_not_called()

    def test_default_runs_dir_only_in_an_orc_worktree(self):
        project = self.tmp / "Proj"
        worktree = project / "worktrees" / "task-1"
        worktree.mkdir(parents=True)
        with mock.patch.object(pgg_game, "PROJECT_DIR", worktree):
            self.assertIsNone(pgg_game.default_runs_dir())      # no workspace next to it
            (project / "workspace").mkdir()
            self.assertEqual(pgg_game.default_runs_dir(), project.resolve() / "workspace" / "runs")
        with mock.patch.object(pgg_game, "PROJECT_DIR", self.tmp / "plain"):
            self.assertIsNone(pgg_game.default_runs_dir())

    def cli(self, *argv, env=None):
        err = io.StringIO()
        environ = {k: v for k, v in os.environ.items() if k != pgg_game.RUNS_DIR_ENV}
        environ.update(env or {})
        with mock.patch.dict(os.environ, environ, clear=True), \
                contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()) as out:
            code = pgg_game.main(["--cards", str(_cards_file(self.tmp)), "--models", "gemini",
                                  "--arms", "isolated", "--isolated-reps", "1", *argv])
        return code, err.getvalue(), out.getvalue()

    def test_cli_without_a_known_runs_dir_does_not_start(self):
        with mock.patch.object(pgg_game, "default_runs_dir", return_value=None):
            code, err, _ = self.cli("--run", "r1")
        self.assertEqual(code, 1)
        self.assertIn("--runs-dir", err)
        # default known but not created: also no start
        with mock.patch.object(pgg_game, "default_runs_dir", return_value=self.tmp / "nope"):
            code, err, _ = self.cli("--run", "r1")
        self.assertEqual(code, 1)
        self.assertIn("does not exist", err)
        code, err, _ = self.cli("--run", "r1", "--runs-dir", "relative/runs")
        self.assertEqual(code, 1)
        self.assertIn("absolute", err)
        self.create.assert_not_called()

    def test_cli_runs_dir_sources_and_printed_line_counts(self):
        env_dir, cli_dir = self.tmp / "env_runs", self.tmp / "cli_runs"
        env_dir.mkdir()
        cli_dir.mkdir()
        code, _, out = self.cli("--run", "r1", env={pgg_game.RUNS_DIR_ENV: str(env_dir)})
        self.assertEqual(code, 0)
        self.assertEqual(_lines(env_dir / "r1" / "r1.jsonl"), 5)
        self.assertIn(f"dosya (results): {env_dir / 'r1' / 'r1.jsonl'} — 5 satır", out)
        self.assertIn("dosya (raw_log)", out)
        code, _, _ = self.cli("--run", "r2", "--runs-dir", str(cli_dir),
                              env={pgg_game.RUNS_DIR_ENV: str(env_dir)})
        self.assertEqual(code, 0)
        self.assertTrue((cli_dir / "r2" / "r2_summary.json").exists())
        self.assertFalse((env_dir / "r2").exists())
        config = self.tmp / "cfg.json"
        config.write_text(json.dumps({"runs_dir": str(cli_dir)}))
        code, _, _ = self.cli("--run", "r3", "--config", str(config),
                              env={pgg_game.RUNS_DIR_ENV: str(env_dir)})
        self.assertEqual(code, 0)
        self.assertTrue((cli_dir / "r3" / "raw_calls.jsonl").exists())

    def test_set_log_path_returns_the_previous_path(self):
        before = llm_client.LOG_PATH
        previous = llm_client.set_log_path(self.tmp / "x.jsonl")
        self.addCleanup(llm_client.set_log_path, previous)
        self.assertEqual(previous, before)
        llm_client._append_log({"a": 1})
        self.assertEqual(_lines(self.tmp / "x.jsonl"), 1)


# --------------------------------------------------------------------------
# (b) max_tokens and timeout
# --------------------------------------------------------------------------

class TokensAndTimeout(GuardTestBase):
    def test_pilot_config_values(self):
        raw = json.loads(PILOT_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(raw["max_tokens"], 16000)
        self.assertGreaterEqual(raw["request_timeout_s"], 300)
        self.assertGreaterEqual(llm_client.DEFAULT_TIMEOUT_S, 300)
        self.assertEqual(llm_client.DEFAULT_MAX_TOKENS, 16000)

    def test_timeout_and_max_tokens_are_sent_and_recorded(self):
        rows = self.run_engine(params=GameParams(rounds=1), max_tokens=16000,
                               request_timeout_s=321)
        for kwargs in self.api.calls:
            self.assertEqual((kwargs["max_tokens"], kwargs["timeout"]), (16000, 321))
        self.assertEqual({r["max_tokens"] for r in rows}, {16000})
        summary = self.summary()
        self.assertEqual((summary["max_tokens"], summary["request_timeout_s"]), (16000, 321))

    def test_default_timeout_is_the_clients(self):
        self.run_engine(params=GameParams(rounds=1))
        self.assertEqual({c["timeout"] for c in self.api.calls}, {llm_client.DEFAULT_TIMEOUT_S})

    def test_cli_timeout_option(self):
        code = None
        with contextlib.redirect_stdout(io.StringIO()):
            code = pgg_game.main(["--run", "c1", "--cards", str(_cards_file(self.tmp)),
                                  "--models", "gpt", "--arms", "isolated", "--isolated-reps", "1",
                                  "--request-timeout", "450", "--max-tokens", "16000",
                                  "--results-dir", str(self.tmp / "res")])
        self.assertEqual(code, 0)
        self.assertEqual({(c["timeout"], c["max_tokens"]) for c in self.api.calls}, {(450, 16000)})

    def test_dry_run_with_new_max_tokens_shows_ceiling(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(pgg_game.main(["--dry-run", "--config", str(PILOT_CONFIG),
                                            "--cards", str(ROOT / "cards" / "pilot_cards.json")]), 0)
        text = buf.getvalue()
        self.assertIn("1620 çağrı", text)
        self.assertIn("max_tokens=16000", text)
        self.assertIn("Tavan (her çağrı max_tokens=16000", text)
        self.create.assert_not_called()


# --------------------------------------------------------------------------
# (c) provider pinning
# --------------------------------------------------------------------------

class ProviderPinning(GuardTestBase):
    def test_routing_is_sent_and_provider_logged_on_every_row(self):
        self.use(CostAPI(provider_fn=lambda k: "Prov A"))
        rows = self.run_engine(params=GameParams(rounds=1), providers=PINNED,
                               models={"m1": "v/m1"})
        for kwargs in self.api.calls:
            self.assertEqual(kwargs["extra_body"]["provider"], {
                "order": ["prov-a/fp8"], "only": ["prov-a/fp8"], "allow_fallbacks": False,
                "require_parameters": True, "quantizations": ["fp8"]})
            self.assertEqual(kwargs["extra_headers"]["X-OpenRouter-Metadata"], "enabled")
        self.assertEqual({r["provider"] for r in rows}, {"Prov A"})
        self.assertEqual({r["provider_quantization"] for r in rows}, {None})
        calls = [r for r in self.raw_log() if "response_raw" in r]
        self.assertEqual({r["provider"] for r in calls}, {"Prov A"})
        s = self.summary()
        self.assertEqual(s["providers"]["m1"]["only"], ["prov-a/fp8"])
        self.assertEqual(s["per_model"]["v/m1"]["providers"], {"Prov A": 4})

    def test_no_quantizations_key_when_not_given(self):
        self.assertEqual(pgg_game.provider_routing({"slug": "openai", "name": "OpenAI"}),
                         {"order": ["openai"], "only": ["openai"], "allow_fallbacks": False,
                          "require_parameters": True})

    def test_unpinned_models_send_no_provider(self):
        self.run_engine(params=GameParams(rounds=1))
        self.assertTrue(all("provider" not in c["extra_body"] for c in self.api.calls))

    def test_name_match_ignores_case_and_punctuation_and_unknown_is_counted(self):
        self.assertTrue(pgg_game.same_provider("Google AI Studio", "google-ai-studio"))
        self.assertFalse(pgg_game.same_provider("Google", "Google AI Studio"))
        # task #68: only an unpinned model's response without a name is accepted
        # and counted as n_provider_unknown (a pinned one is re-requested, below)
        self.use(CostAPI(provider_fn=lambda k: None))
        Engine(self.cfg(params=GameParams(rounds=1))).run()
        self.assertEqual(self.summary()["per_model"]["vendor/model-1"]["n_provider_unknown"], 4)
        self.assertEqual(len(self.api.calls), 4)

    def test_missing_provider_name_is_re_requested_and_summed(self):
        # task #68 (K4; pilot v2 counted these as n_provider_unknown and kept
        # them): a pinned model's response without a provider name is no
        # decision; it is re-requested and counted as a mismatch, with its own
        # sub-count n_provider_missing; the run does not stop and every row
        # names the pinned provider
        pinned = PINNED | {"m2": {"slug": "prov-b", "name": "Prov B"}}
        names = {"v/m1": "Prov A", "v/m2": "Prov B"}
        self.use(CostAPI(provider_fn=lambda k: None if len(self.api.calls) % 3 == 0
                         else names[k["model"]]))
        rows = self.run_engine(params=GameParams(rounds=3), providers=pinned,
                               models={"m1": "v/m1", "m2": "v/m2"})
        self.assertEqual(len(rows), 24)
        self.assertEqual(len(self.api.calls), 35)            # first T = 24 + T // 3
        s = self.summary()
        self.assertIsNone(s["stop_reason"])
        self.assertEqual(self.events("pgg_run_stopped"), [])
        per = {m: v["n_provider_missing"] for m, v in s["per_model"].items()}
        self.assertEqual(sum(per.values()), 11)              # every 3rd of 35 calls
        self.assertTrue(all(v > 0 for v in per.values()))
        self.assertEqual((s["n_provider_missing"], s["n_provider_mismatch"],
                          s["n_provider_unknown"]), (11, 11, 0))
        self.assertTrue(all(r["provider"] is not None for r in rows))
        self.assertEqual(sum(r["n_provider_missing"] for r in rows), 11)
        self.assertEqual(sum(r["n_provider_mismatch"] for r in rows), 11)
        for m, v in s["per_model"].items():
            self.assertEqual(v["providers"].get("None"), per[m])
            self.assertEqual(v["n_provider_mismatch"], per[m])
        missing = [r for r in self.raw_log() if r.get("provider_missing")]
        self.assertEqual(len(missing), 11)
        self.assertTrue(all(r["provider_mismatch"] and r["error_kind"] == "provider_mismatch"
                            and r["provider"] is None and r["retrying"] for r in missing))

    def test_unpinned_models_count_provider_unknown(self):
        # task #68: n_provider_unknown stays only for unpinned models (no check)
        self.use(CostAPI(provider_fn=lambda k: None))
        rows = self.run_engine(params=GameParams(rounds=1))
        self.assertEqual(self.summary()["n_provider_unknown"], 4)
        self.assertEqual(self.summary()["n_provider_missing"], 0)
        self.assertEqual(len(rows), 4)
        self.assertEqual(len(self.api.calls), 4)             # not re-requested

    def test_placeholder_or_incomplete_providers_do_not_start(self):
        for bad in ({"m1": {"slug": "<SEÇİLECEK>", "name": "X"}},
                    {"m1": {"slug": "x", "name": "X", "quantizations": ["<SEÇİLECEK: fp8>"]}},
                    {"m1": {"slug": "x"}},
                    {"m1": {"slug": "x", "name": "X", "quantizations": ["fp7"]}},
                    {"m1": {"slug": "x", "name": "X", "typo": 1}},
                    {"m2": {"slug": "x", "name": "X"}}):
            with self.assertRaises(ValueError, msg=bad):
                Engine(self.cfg(providers=bad))
        with self.assertRaisesRegex(ValueError, "none for"):
            Engine(self.cfg(providers=PINNED, models={"m1": "v/m1", "m2": "v/m2"}))
        self.create.assert_not_called()

    def test_cli_placeholder_in_providers_does_not_start(self):
        config = self.tmp / "cfg.json"
        config.write_text(json.dumps({"providers": {"gemini": {"slug": "<SEÇİLECEK>",
                                                               "name": "<SEÇİLECEK>"}}}))
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = pgg_game.main(["--run", "p", "--config", str(config), "--cards",
                                  str(_cards_file(self.tmp)), "--models", "gemini",
                                  "--runs-dir", str(self.tmp)])
        self.assertEqual(code, 1)
        self.assertIn("providers.gemini.slug", err.getvalue())
        self.create.assert_not_called()

    def test_cli_providers_by_slug_are_sent(self):
        config = self.tmp / "cfg.json"
        config.write_text(json.dumps({"providers": {"google/gemini-2.5-flash-lite": {
            "slug": "google-ai-studio", "name": "Google AI Studio"}}}))
        self.use(CostAPI(provider_fn=lambda k: "Google AI Studio"))
        with contextlib.redirect_stdout(io.StringIO()):
            code = pgg_game.main(["--run", "p", "--config", str(config), "--cards",
                                  str(_cards_file(self.tmp)), "--models", "gemini", "--arms",
                                  "isolated", "--isolated-reps", "1", "--runs-dir", str(self.tmp)])
        self.assertEqual(code, 0)
        self.assertEqual({c["extra_body"]["provider"]["only"][0] for c in self.api.calls},
                         {"google-ai-studio"})


class ProviderInfoFromResponse(unittest.TestCase):
    def completion(self, **extra):
        from openai.types.chat import ChatCompletion
        return ChatCompletion.model_validate({
            "id": "x", "object": "chat.completion", "created": 1, "model": "m",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": "{}"}}], **extra})

    def test_metadata_selected_endpoint_then_top_level_field(self):
        meta = {"endpoints": {"total": 2, "available": [
            {"provider": "Other", "model": "m", "selected": False},
            {"provider": "DeepInfra", "model": "m", "selected": True, "quantization": "fp8"}]}}
        self.assertEqual(llm_client._provider_info(self.completion(openrouter_metadata=meta)),
                         ("DeepInfra", "fp8"))
        self.assertEqual(llm_client._provider_info(self.completion(provider="Novita")),
                         ("Novita", None))
        self.assertEqual(llm_client._provider_info(self.completion()), (None, None))
        self.assertEqual(llm_client._provider_info(mock.Mock()), (None, None))


# --------------------------------------------------------------------------
# (d) provider errors
# --------------------------------------------------------------------------

ZERO = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": 0}


class ProviderErrors(GuardTestBase):
    def test_client_classifies_error_and_zero_token_responses(self):
        self.create.side_effect = [
            _response("not json", model="m", finish_reason="error", cost=0),
            _response("", model="m", usage=dict(ZERO)),
            _response('{"x": 1}', model="m", cost=0.1)]
        counts = {}
        out = llm_client.call_llm_valid(
            "m", [{"role": "user", "content": "hi"}], schema={"type": "object"},
            session_id="s", is_valid=lambda c: c.get("x") == 1, return_parse_fail=True,
            counts=counts)
        self.assertEqual(out, ({"x": 1}, 0, 0))                 # n_parse_fail stays 0
        self.assertEqual(counts, {"n_invalid": 0, "n_parse_fail": 0, "n_provider_error": 2,
                                  "n_transport": 0, "n_deadline": 0, "n_provider_mismatch": 0,
                                  "n_provider_missing": 0})
        kinds = [r.get("error_kind") for r in self.raw_log()]
        self.assertEqual(kinds, ["provider", "provider", None])

    def test_classification_edges(self):
        is_err = llm_client._is_provider_error
        self.assertTrue(is_err(_response("{}", model="m", finish_reason="error", cost=0.5)))
        self.assertTrue(is_err(_response("{}", model="m", usage={"prompt_tokens": 0,
                                                                 "completion_tokens": 0})))
        self.assertFalse(is_err(_response("{}", model="m", usage=dict(ZERO, cost=0.01))))
        self.assertFalse(is_err(_response("{}", model="m", usage={"prompt_tokens": 5,
                                                                  "completion_tokens": 0,
                                                                  "cost": 0})))
        self.assertFalse(is_err(_response("{}", model="m", cost=0)))   # 100 + 20 tokens
        self.assertFalse(is_err(mock.Mock()))

    def test_exhausted_call_carries_the_provider_error_count(self):
        self.create.side_effect = [_response("x", model="m", finish_reason="error")] * 2
        with self.assertRaises(RuntimeError) as cm:
            llm_client.call_llm("m", [{"role": "user", "content": "hi"}],
                                schema={"type": "object"}, session_id="s", max_retries=2)
        self.assertEqual((cm.exception.n_provider_error, cm.exception.n_parse_fail), (2, 0))
        self.assertEqual(self.raw_log()[-1]["error_kind"], "provider")
        # through call_llm_valid the counts dict holds them too
        self.create.side_effect = [_response("x", model="m", finish_reason="error")] * 4
        counts = {}
        with self.assertRaises(RuntimeError):
            llm_client.call_llm_valid("m", [{"role": "user", "content": "hi"}],
                                      schema={"type": "object"}, session_id="s",
                                      is_valid=lambda c: True, counts=counts)
        self.assertEqual(counts, {"n_invalid": 0, "n_parse_fail": 0, "n_provider_error": 4,
                                  "n_transport": 0, "n_deadline": 0, "n_provider_mismatch": 0,
                                  "n_provider_missing": 0})

    def test_engine_counts_them_apart_and_not_in_the_invalid_cap(self):
        n = []

        def finish(kwargs):
            n.append(1)
            return "error" if len(n) % 2 else "stop"          # every second response

        self.use(CostAPI(finish_fn=finish))
        engine = Engine(self.cfg(arms=("isolated",), isolated_reps=4, invalid_rate_cap=0.05))
        self.assertEqual(engine.invalid_limit, 1)
        path = engine.run()
        rows = [json.loads(x) for x in path.read_text().splitlines()]
        self.assertEqual(len(rows), 20)                       # the model was not stopped
        self.assertEqual(engine.stopped_models, {})
        self.assertEqual({r["n_provider_error"] for r in rows}, {1})
        self.assertEqual({(r["n_parse_fail"], r["n_invalid"]) for r in rows}, {(0, 0)})
        s = self.summary()
        self.assertEqual(s["n_provider_error"], 20)
        m = s["per_model"]["vendor/model-1"]
        self.assertEqual((m["n_provider_error"], m["n_parse_fail"], m["n_invalid"]), (20, 0, 0))
        self.assertEqual(m["finish_reasons"], {"error": 20, "stop": 20})


# --------------------------------------------------------------------------
# (e) run order
# --------------------------------------------------------------------------

class RunOrder(GuardTestBase):
    def order(self, **kw):
        base = dict(cards=CARDS6, models=MODELS3, arms=("group", "isolated"), groups_per_cell=2,
                    isolated_reps=2)
        base.update(kw)
        return [label for _, label, _ in Engine(self.cfg(**base)).units()]

    def test_same_seed_same_order_and_crc32_not_hash(self):
        a, b = self.order(), self.order()
        self.assertEqual(a, b)
        self.assertEqual(len(a), 6 * 3 * 4)
        self.assertEqual(len(set(a)), len(a))
        self.assertNotEqual(a, self.order(run="other"))       # the run name is in the seed key
        self.assertNotEqual(a, self.order(seed_namespace="ns2"))
        engine = Engine(self.cfg(cards=CARDS6, models=MODELS3))
        self.assertEqual(engine._order_key("card", 0, "city1", "s")[0],
                         llm_client.stable_seed("pgg", "t1", "order", "card", 0, "city1", "s"))

    def test_blocks_cover_every_card_and_passes_every_cell(self):
        labels = self.order()
        cards = {c.card_id for c in CARDS6}
        for start in range(0, len(labels), 6):                # every block of len(cards) units
            self.assertEqual({x.split("|")[1] for x in labels[start:start + 6]}, cards)
        cells = {(m, c) for m in MODELS3 for c in cards}
        for start in range(0, len(labels), 18):               # every pass: every cell once
            got = [(x.split("|")[0], x.split("|")[1]) for x in labels[start:start + 18]]
            self.assertEqual(sorted(got), sorted(cells))
        first_pass = labels[:18]
        self.assertTrue(all(x.endswith("|group|0") for x in first_pass))
        self.assertTrue(all(x.endswith("|isolated|0") for x in labels[18:36]))

    def test_first_calls_cover_all_cards(self):
        self.run_engine(cards=CARDS6, params=GameParams(rounds=1), groups_per_cell=2)
        first = self.api.calls[:4 * 6]
        texts = {c["messages"][0]["content"] for c in first}
        self.assertEqual(len(texts), 6)
        for card in CARDS6:
            self.assertTrue(any(card.text in t for t in texts))

    def test_order_is_logged_at_start_and_in_the_summary(self):
        self.run_engine(cards=[CARD_A, CARD_B], params=GameParams(rounds=1),
                        models={"m1": "v/m1", "m2": "v/m2"})
        start = self.events("pgg_run_start")
        self.assertEqual(len(start), 1)
        self.assertEqual(start[0]["unit_order"], self.summary()["unit_order"])
        self.assertEqual(len(start[0]["unit_order"]), 4)
        self.assertEqual(self.raw_log()[0]["event"], "pgg_run_start")   # before the first call


# --------------------------------------------------------------------------
# (f) earnings labels
# --------------------------------------------------------------------------

class EarningsLabels(GuardTestBase):
    def test_rules_text_labels(self):
        text = pgg_game.rules_text(GameParams(), "N")
        self.assertIn("Your earnings from the project in a round are therefore:\n"
                      "  0.4 x (sum of all 4 players' contributions)\n", text)
        self.assertIn("- Your total earnings in a round are the points you kept plus your "
                      "earnings from the project:\n"
                      "  20 - (your contribution) + 0.4 x (sum of all 4 players' contributions)",
                      text)

    def test_history_numbers_match_the_rows(self):
        rows = self.run_engine(params=GameParams(rounds=3))
        prompts = {FakeAPI.parse(c)[1:3]: c["messages"][-1]["content"] for c in self.api.calls}
        for rnd in (1, 2):
            group = {r["agent_id"]: r for r in rows if r["round"] == rnd}
            total = sum(r["contribution"] for r in group.values())
            for agent, r in group.items():
                share = pgg_game._num(0.4 * total)
                own_total = pgg_game._num(20 - r["contribution"] + 0.4 * total)
                self.assertAlmostEqual(r["payoff"], 20 - r["contribution"] + 0.4 * total)
                line = (f"  Your earnings from the project: {share}. "
                        f"Your total earnings this round: {own_total}.")
                self.assertIn(f"Round {rnd}\n", prompts[(agent, 3)])
                self.assertIn(line, prompts[(agent, 3)])
        # round 1 of the fake: contributions 4, 7, 10, 13 -> total 34, share 13.6
        self.assertIn("Your earnings from the project: 13.6. Your total earnings this round: 29.6.",
                      prompts[(1, 2)])
        self.assertEqual(pgg_game.project_share(GameParams(), [4, 7, 10, 13]), 13.6)

    def test_punishment_prompt_labels(self):
        rows = self.run_engine(conditions=("P",), params=GameParams(rounds=1))
        punish = [c for c in self.api.calls if FakeAPI.parse(c)[0] == "punish"]
        user = punish[0]["messages"][-1]["content"]
        contrib = [r for r in rows if r["step"] == "contribute"]
        total = sum(r["contribution"] for r in contrib)
        me = [r for r in contrib if r["agent_id"] == 1][0]
        self.assertIn(f"Your earnings from the project this round: {pgg_game._num(0.4 * total)}. "
                      f"Your total earnings this round (before punishment): "
                      f"{pgg_game._num(me['payoff_before_punishment'])}.", user)
        self.assertIn("Your total cost may not exceed your total earnings this round", user)


# --------------------------------------------------------------------------
# (g) isolated frame
# --------------------------------------------------------------------------

class IsolatedFrame(GuardTestBase):
    def test_one_shot_keeps_the_old_question(self):
        rows = self.run_engine(arms=("isolated",))
        user = self.api.calls[0]["messages"][-1]["content"]
        self.assertIn("Consider one round. Suppose the other 3 players of your group each "
                      "contribute, on average, 0 points. There is no history and no other round.",
                      user)
        self.assertIn("this question is about one round", user)
        self.assertEqual({r["isolated_frame"] for r in rows}, {"one_shot"})

    def test_repeated_frame(self):
        rows = self.run_engine(arms=("isolated",), isolated_frame="repeated")
        self.assertEqual([r["contribution"] for r in rows], [0, 2, 5, 7, 10])  # parse still works
        for x, c in zip((0, 5, 10, 15, 20), self.api.calls):
            user = c["messages"][-1]["content"]
            self.assertIn("The same 4 players stay together for all 10 rounds.", user)
            self.assertIn("Consider a round of this 10-round game that is neither the first nor "
                          "the last round. In the previous round the other 3 players of your "
                          f"group contributed, on average, {x} points each.", user)
            self.assertIn("in this round?", user)
            self.assertNotIn("There is no history", user)
            self.assertNotIn("HISTORY", user)
        self.assertEqual({r["isolated_frame"] for r in rows}, {"repeated"})
        self.assertEqual(self.summary()["isolated_frame"], "repeated")

    def test_placeholder_or_unknown_frame_does_not_start(self):
        for bad in ("<SEÇİLECEK: one_shot | repeated>", "twice"):
            with self.assertRaises(ValueError):
                Engine(self.cfg(arms=("isolated",), isolated_frame=bad))
        with self.assertRaises(ValueError):
            pgg_game.isolated_messages(GameParams(), CARD_A, 5, "twice")
        self.create.assert_not_called()

    def test_cli_frame_option_and_config_placeholder(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code = pgg_game.main(["--run", "g1", "--cards", str(_cards_file(self.tmp)),
                                  "--models", "gpt", "--arms", "isolated", "--isolated-reps", "1",
                                  "--isolated-frame", "repeated", "--runs-dir", str(self.tmp)])
        self.assertEqual(code, 0)
        self.assertIn("previous round", self.api.calls[0]["messages"][-1]["content"])
        config = self.tmp / "cfg.json"
        config.write_text(json.dumps({"isolated_frame": "<SEÇİLECEK: one_shot | repeated>"}))
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = pgg_game.main(["--run", "g2", "--config", str(config), "--cards",
                                  str(_cards_file(self.tmp)), "--models", "gpt",
                                  "--runs-dir", str(self.tmp)])
        self.assertEqual(code, 1)
        self.assertIn("isolated_frame", err.getvalue())
        self.assertEqual(len(self.api.calls), 5)              # only the first run's calls


if __name__ == "__main__":
    unittest.main()


# --------------------------------------------------------------------------
# (h) card length on every row
# --------------------------------------------------------------------------

class CardLength(GuardTestBase):
    def test_card_length_function(self):
        self.assertEqual(pgg_game.card_length(Card("a", "s", "You are a 21-year-old student.")),
                         {"card_n_words": 5, "card_n_chars": 30})
        self.assertEqual(pgg_game.card_length(Card("a", "s", "  two\n words ")),
                         {"card_n_words": 2, "card_n_chars": 13})

    def test_every_row_has_its_cards_length(self):
        short = Card("short", "minimal", "You are a student.")
        long_ = Card("long", "factual", "You are a student. The city has a long history.")
        rows = self.run_engine(cards=[short, long_], arms=("group", "isolated"),
                               params=GameParams(rounds=1))
        self.assertEqual(len(rows), 2 * (4 + 5))
        by_card = {c.card_id: c for c in (short, long_)}
        for r in rows:
            card = by_card[r["card_id"]]
            self.assertEqual((r["card_n_words"], r["card_n_chars"]),
                             (len(card.text.split()), len(card.text)), r["arm"])
        self.assertEqual({(r["card_id"], r["card_n_words"]) for r in rows},
                         {("short", 4), ("long", 10)})
