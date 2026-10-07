"""Mock tests of A4 (provider mismatch, require_parameters) and A5 (code version).

(a) A4: a response of a pinned model from another provider is no decision: it
is logged ("provider_mismatch": true, content, cost), billed, re-requested and
counted on the row, per model, per segment and in total; the attempt limit
(llm_client max_retries = 4) ends in stop_reason "provider_mismatch_limit";
pinned models send provider.require_parameters true, unpinned ones no
provider object. (b) A5: git checkout clean / dirty, a copied code directory
with a valid / missing / broken CODE_VERSION.json, the refusal of a real run
and of --resume on dirty or unversioned code (a dry run only warns), and a
git_commit change on --resume written to the summary. No network, no ../.env;
the git repositories are made in a temporary directory.
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_llm_client_logging import MESSAGES, SCHEMA, LoggingTestBase  # noqa: E402
from test_pgg_game import CARD_A, _payload  # noqa: E402
from test_pgg_guards import CostAPI, _response  # noqa: E402
from test_pgg_resume import GEMINI, ResumeBase, _rows, _tree  # noqa: E402

import llm_client  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Engine, GameParams, RunAborted, RunStopped  # noqa: E402

PINNED = {"m1": {"slug": "prov-a/fp8", "name": "Prov A", "quantizations": ["fp8"]}}
M1 = {"m1": "v/m1"}


def _raw(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines()]


# --------------------------------------------------------------------------
# (a) A4 in llm_client
# --------------------------------------------------------------------------

class MismatchInClient(LoggingTestBase):
    def replies(self, *providers):
        out = [_response(_payload({"action": i}), model="m", cost=0.01 * (i + 1), provider=p)
               for i, p in enumerate(providers)]
        self.create.side_effect = out

    def call_valid(self, **kw):
        counts, seen = {}, []
        out = llm_client.call_llm_valid("m", MESSAGES, schema=SCHEMA, session_id="s",
                                        is_valid=lambda c: True, counts=counts,
                                        on_response=seen.append, return_parse_fail=True, **kw)
        return out, counts, seen

    def test_mismatch_is_logged_billed_and_re_requested(self):
        self.replies("Prov B", "prov-a")             # same_provider: case / punctuation
        out, counts, seen = self.call_valid(expected_provider="Prov A")
        self.assertEqual(out, ({"action": 1}, 0, 0))  # the second response is the decision
        self.assertEqual(self.create.call_count, 2)
        self.assertEqual(counts["n_provider_mismatch"], 1)
        self.assertEqual((counts["n_parse_fail"], counts["n_provider_error"]), (0, 0))
        bad, ok = self.records()
        self.assertEqual((bad["error_kind"], bad["provider_mismatch"], bad["retrying"]),
                         ("provider_mismatch", True, True))
        self.assertEqual((bad["provider"], bad["expected_provider"]), ("Prov B", "Prov A"))
        self.assertEqual(bad["response_raw"], _payload({"action": 0}))   # its content
        self.assertEqual(bad["usage"]["cost"], 0.01)                     # and its cost
        self.assertNotIn("response_parsed", bad)
        self.assertEqual(ok["response_parsed"], {"action": 1})
        self.assertNotIn("provider_mismatch", ok)
        # both responses reach on_response (billed); only the first is flagged
        self.assertEqual([i.get("provider_mismatch", False) for i in seen], [True, False])
        self.assertEqual([i["usage"]["cost"] for i in seen], [0.01, 0.02])

    def test_no_provider_name_is_a_mismatch_no_expected_provider_is_none(self):
        # task #68 (K4): without a provider name the response is no decision either
        self.replies(None, "Prov A")
        out, counts, seen = self.call_valid(expected_provider="Prov A")
        self.assertEqual(out, ({"action": 1}, 0, 0))
        self.assertEqual(self.create.call_count, 2)
        self.assertEqual((counts["n_provider_mismatch"], counts["n_provider_missing"]), (1, 1))
        bad, ok = self.records()
        self.assertEqual((bad["error_kind"], bad["provider_mismatch"], bad["provider_missing"],
                          bad["provider"], bad["retrying"]),
                         ("provider_mismatch", True, True, None, True))
        self.assertIn("without a provider name", bad["error"])
        self.assertEqual(bad["usage"]["cost"], 0.01)                     # billed
        self.assertNotIn("provider_missing", ok)
        self.assertEqual([(i.get("provider_mismatch", False), i.get("provider_missing", False))
                          for i in seen], [(True, True), (False, False)])
        # another name: a mismatch, not a missing name
        self.replies("Prov B", "Prov A")
        _, counts, _ = self.call_valid(expected_provider="Prov A")
        self.assertEqual((counts["n_provider_mismatch"], counts["n_provider_missing"]), (1, 0))
        # no expected provider: nothing is checked
        for name in ("Prov B", None):
            self.replies(name)
            out, counts, _ = self.call_valid()
            self.assertEqual((out[0], counts["n_provider_mismatch"],
                              counts["n_provider_missing"]), ({"action": 0}, 0, 0))

    def test_attempt_limit_carries_the_last_error_kind(self):
        self.replies(*["Prov B"] * 4)
        counts = {}
        with self.assertRaises(RuntimeError) as cm:
            llm_client.call_llm_valid("m", MESSAGES, schema=SCHEMA, session_id="s",
                                      is_valid=lambda c: True, counts=counts,
                                      expected_provider="Prov A")
        self.assertEqual(cm.exception.last_error_kind, "provider_mismatch")
        self.assertEqual(self.create.call_count, 4)                 # max_retries
        self.assertEqual(counts["n_provider_mismatch"], 4)
        final = self.records()[-1]
        self.assertEqual((final["error_kind"], final["expected_provider"]),
                         ("provider_mismatch", "Prov A"))
        self.assertNotIn("retrying", final)

    def test_same_provider_copies_agree(self):
        for a, b in (("Google AI Studio", "google-ai-studio"), ("Google", "Google AI Studio"),
                     ("DeepInfra", "deepinfra"), ("OpenAI", "Open AI"), ("x", "y")):
            self.assertEqual(pgg_game.same_provider(a, b), llm_client.same_provider(a, b))


# --------------------------------------------------------------------------
# (a) A4 in the engine
# --------------------------------------------------------------------------

class MismatchInEngine(ResumeBase):
    def cfg1(self, **kw):
        base = dict(models=dict(M1), cards=[CARD_A], arms=("group",), params=GameParams(rounds=1),
                    providers=PINNED, budget_usd=None, invalid_rate_cap=None)
        base.update(kw)
        return self.rcfg(**base)

    def use_api(self, provider_fn, cost=0.001):
        api = CostAPI(cost=cost, provider_fn=provider_fn)
        self.use(api)                        # self.api = api
        return api

    def test_mismatch_is_re_requested_and_counted(self):
        # the 3rd response (agent 3, round 1) comes from another provider
        api = self.use_api(lambda k: "Prov B" if len(self.api.calls) == 3 else "Prov A")
        engine = Engine(self.cfg1())
        engine.run()
        self.assertEqual(len(api.calls), 5)                       # 4 decisions + 1 re-request
        rows = _rows(self.results)
        self.assertEqual(len(rows), 4)
        self.assertEqual([r["n_provider_mismatch"] for r in rows], [0, 0, 1, 0])
        self.assertEqual({r["provider"] for r in rows}, {"Prov A"})
        summary = self.summary_now()
        self.assertIsNone(summary["stop_reason"])
        stats = summary["per_model"]["v/m1"]
        self.assertEqual((stats["n_provider_mismatch"], stats["n_responses"], stats["n_accepted"]),
                         (1, 5, 4))
        self.assertEqual(stats["providers"], {"Prov A": 4, "Prov B": 1})
        self.assertAlmostEqual(stats["cost_usd"], 5 * 0.001, places=12)   # the mismatch is billed
        self.assertEqual((stats["n_invalid"], stats["n_parse_fail"]), (0, 0))  # not in the cap
        self.assertEqual(summary["n_provider_mismatch"], 1)
        self.assertEqual(summary["segments"][-1]["n_provider_mismatch"], 1)
        self.assertEqual(summary["segments"][-1]["per_model"]["v/m1"]["n_provider_mismatch"], 1)
        self.assertIn("§8.2 item 5", summary["provider_mismatch_rule"])
        bad = [r for r in _raw(self.raw) if r.get("provider_mismatch")]
        self.assertEqual(len(bad), 1)
        self.assertEqual((bad[0]["call"]["agent_id"], bad[0]["provider"], bad[0]["usage"]["cost"]),
                         (3, "Prov B", 0.001))
        self.assertIn('"contribution"', bad[0]["response_raw"])
        self.assertEqual([e["reason"] for e in self.raw_events("pgg_run_stopped")], [])
        # a resume plan rebuilds the count and the cost from the raw log
        plan = Engine(self.cfg1(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual(plan.prior_stats["m1"]["n_provider_mismatch"], 1)
        self.assertAlmostEqual(plan.prior_cost_usd, 5 * 0.001, places=12)
        self.assertEqual(plan.segments[0]["n_provider_mismatch"], 1)

    def test_mismatch_cost_counts_in_the_budget(self):
        # without the mismatch's 0.001 the 4 decisions (0.004) would all be sent
        api = self.use_api(lambda k: "Prov B" if len(self.api.calls) == 3 else "Prov A")
        with self.assertRaisesRegex(RunStopped, "budget"):
            Engine(self.cfg1(budget_usd=0.0035)).run()
        self.assertEqual(len(api.calls), 4)
        self.assertEqual(self.summary_now()["stop_reason"], "budget")

    def test_attempt_limit_stops_with_provider_mismatch_limit(self):
        api = self.use_api(lambda k: "Prov B")
        with self.assertRaises(RunAborted) as cm:
            Engine(self.cfg1()).run()
        self.assertEqual(cm.exception.reason, "provider_mismatch_limit")
        self.assertIn("attempt limit reached", str(cm.exception))
        self.assertEqual(len(api.calls), 4)              # llm_client max_retries
        summary = self.summary_now()
        self.assertEqual(summary["stop_reason"], "provider_mismatch_limit")
        self.assertEqual(summary["per_model"]["v/m1"]["n_provider_mismatch"], 4)
        self.assertAlmostEqual(summary["total_cost_usd"], 4 * 0.001, places=12)
        aborted = self.raw_events("pgg_run_aborted")
        self.assertEqual((aborted[0]["reason"], aborted[0]["n_provider_mismatch"]),
                         ("provider_mismatch_limit", 4))
        self.assertEqual([e["reason"] for e in self.raw_events("pgg_run_stopped")],
                         ["provider_mismatch_limit"])
        self.assertFalse(self.results.read_text())       # no row

    def test_limit_with_another_last_error_is_run_aborted(self):
        # 3 mismatches, then broken JSON: the limit is the same, the reason the old one
        api = self.use_api(lambda k: "Prov B" if len(self.api.calls) < 4 else "Prov A")
        api.content_fn = lambda k, c: c if len(api.calls) < 4 else "not json"
        with self.assertRaises(RunAborted) as cm:
            Engine(self.cfg1()).run()
        self.assertEqual(cm.exception.reason, "run_aborted")
        self.assertEqual(self.summary_now()["stop_reason"], "run_aborted")
        self.assertEqual(self.summary_now()["per_model"]["v/m1"]["n_provider_mismatch"], 3)

    def test_require_parameters_only_for_pinned_models(self):
        api = self.use_api(lambda k: "Prov A")
        Engine(self.cfg1()).run()
        for kwargs in api.calls:
            routing = kwargs["extra_body"]["provider"]
            self.assertIs(routing["require_parameters"], True)
            self.assertIs(routing["allow_fallbacks"], False)
            self.assertEqual((routing["only"], routing["order"]), (["prov-a/fp8"], ["prov-a/fp8"]))
        summary = self.summary_now()
        self.assertIs(summary["providers"]["m1"]["require_parameters"], True)
        # "config" stays as the earlier code wrote it (its runs resume); the policy is
        # in the segment entry and the start event
        self.assertNotIn("require_parameters", summary["config"]["providers"]["m1"])
        self.assertEqual(summary["segments"][-1]["provider_policy"], pgg_game.PROVIDER_POLICY)
        self.assertEqual(self.raw_events("pgg_run_start")[0]["provider_policy"],
                         pgg_game.PROVIDER_POLICY)
        # not pinned: no provider object at all
        shutil.rmtree(self.run_dir)
        api = self.use_api(lambda k: "Prov A")
        Engine(self.cfg1(providers=None)).run()
        self.assertTrue(api.calls)
        self.assertTrue(all("provider" not in c["extra_body"] for c in api.calls))


# --------------------------------------------------------------------------
# (b) A5: code version
# --------------------------------------------------------------------------

def _git(cwd, *args):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t",
                           "-c", "commit.gpgsign=false", *args],
                          capture_output=True, text=True, check=True, env=env).stdout.strip()


class CodeVersionBase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.repo = self.tmp / "repo"
        (self.repo / "tests").mkdir(parents=True)
        for name in pgg_game.CODE_FILES:
            (self.repo / name).write_text(f"# {name}\n")
        (self.repo / "tests" / "test_x.py").write_text("# test\n")
        (self.repo / "notes.md").write_text("notes\n")
        _git(self.repo, "init", "-q")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "c1")
        self.sha = _git(self.repo, "rev-parse", "HEAD")

    def copy(self, name="_kod") -> Path:
        """The tracked files, without .git (as git archive unpacks them)."""
        dst = self.tmp / name
        shutil.copytree(self.repo, dst, ignore=shutil.ignore_patterns(".git"))
        return dst


class GitCheckout(CodeVersionBase):
    def test_clean_checkout(self):
        cv = pgg_game._read_code_version(self.repo)
        self.assertEqual((cv["source"], cv["git_commit"], cv["git_dirty"]), ("git", self.sha, False))
        self.assertEqual(set(cv["files_sha256"]), set(pgg_game.CODE_FILES))
        self.assertIsNone(pgg_game.code_version_problem(cv))

    def test_dirty_tracked_py_file(self):
        (self.repo / "tests" / "test_x.py").write_text("# changed\n")
        cv = pgg_game._read_code_version(self.repo)
        self.assertEqual((cv["git_commit"], cv["git_dirty"]), (self.sha, True))
        self.assertEqual(cv["dirty_files"], ["tests/test_x.py"])
        self.assertRegex(pgg_game.code_version_problem(cv), "dirty.*tests/test_x.py")

    def test_staged_change_is_dirty_too(self):
        (self.repo / "pgg_cost.py").write_text("# changed\n")
        _git(self.repo, "add", "pgg_cost.py")
        self.assertTrue(pgg_game._read_code_version(self.repo)["git_dirty"])

    def test_untracked_files_and_other_tracked_files_do_not_count(self):
        (self.repo / "new_module.py").write_text("# untracked\n")
        (self.repo / "notes.md").write_text("edited notes\n")
        cv = pgg_game._read_code_version(self.repo)
        self.assertEqual(cv["git_dirty"], False)
        self.assertIsNone(pgg_game.code_version_problem(cv))

    def test_stamp_is_refused_inside_a_checkout(self):
        with self.assertRaisesRegex(ValueError, "is a git checkout"):
            pgg_game.write_code_version(self.repo, repo_dir=self.repo)


class CopiedCode(CodeVersionBase):
    def test_no_stamp_means_unknown(self):
        dst = self.copy()
        cv = pgg_game._read_code_version(dst)
        self.assertEqual((cv["source"], cv["git_commit"], cv["git_dirty"]), (None, None, None))
        self.assertRegex(pgg_game.code_version_problem(cv), "unknown.*--write-code-version")

    def test_valid_stamp(self):
        dst = self.copy()
        path = pgg_game.write_code_version(dst, self.sha, repo_dir=self.repo)
        stamp = json.loads(path.read_text())
        self.assertEqual(path, dst / pgg_game.CODE_VERSION_FILE)
        self.assertEqual(stamp["git_commit"], self.sha)
        self.assertEqual(set(stamp["files_sha256"]),
                         set(pgg_game.CODE_FILES) | {"tests/test_x.py"})   # tracked .py only
        cv = pgg_game._read_code_version(dst)
        self.assertEqual((cv["source"], cv["git_commit"], cv["git_dirty"], cv["n_files_verified"]),
                         ("stamp", self.sha, False, len(pgg_game.CODE_FILES) + 1))
        self.assertIsNone(pgg_game.code_version_problem(cv))
        # written again with the same content: kept as it is
        before = path.read_bytes()
        self.assertEqual(pgg_game.write_code_version(dst, "HEAD", repo_dir=self.repo), path)
        self.assertEqual(path.read_bytes(), before)

    def test_broken_stamps(self):
        dst = self.copy()
        path = pgg_game.write_code_version(dst, self.sha, repo_dir=self.repo)
        good = path.read_text()
        cases = {
            "changed file": (lambda: (dst / "llm_client.py").write_text("# edited\n"),
                             "llm_client.py: sha256 differs"),
            "missing file": (lambda: (dst / "tests" / "test_x.py").unlink(),
                             "tests/test_x.py: listed in CODE_VERSION.json, missing"),
            "not JSON": (lambda: path.write_text("{"), "cannot be read"),
            "no commit": (lambda: path.write_text(json.dumps(
                {**json.loads(good), "git_commit": None})), "40-digit"),
            "CODE_FILES not covered": (lambda: path.write_text(json.dumps(
                {**json.loads(good), "files_sha256": {"tests/test_x.py":
                                                      json.loads(good)["files_sha256"]
                                                      ["tests/test_x.py"]}})), "does not cover"),
            "path outside": (lambda: path.write_text(json.dumps(
                {**json.loads(good), "files_sha256": {**json.loads(good)["files_sha256"],
                                                      "../x.py": "0" * 64}})), "not inside"),
        }
        for name, (break_it, message) in cases.items():
            with self.subTest(name):
                shutil.rmtree(dst)
                dst = self.copy()
                path.write_text(good)
                break_it()
                cv = pgg_game._read_code_version(dst)
                self.assertEqual((cv["source"], cv["git_dirty"]), ("stamp", True))
                self.assertIn(message, " ".join(cv["stamp_problems"]))
                self.assertRegex(pgg_game.code_version_problem(cv), "does not match the code")

    def test_stamp_is_not_written_for_a_different_copy(self):
        dst = self.copy()
        (dst / "pgg_game.py").write_text("# not the commit\n")
        with self.assertRaisesRegex(ValueError, "pgg_game.py differs.*not written"):
            pgg_game.write_code_version(dst, self.sha, repo_dir=self.repo)
        self.assertFalse((dst / pgg_game.CODE_VERSION_FILE).exists())
        with self.assertRaisesRegex(ValueError, "not a commit"):
            pgg_game.write_code_version(self.copy("_kod2"), "nope", repo_dir=self.repo)

    def test_stamp_of_another_commit_is_not_overwritten(self):
        dst = self.copy()
        pgg_game.write_code_version(dst, self.sha, repo_dir=self.repo)
        (self.repo / "tests" / "test_x.py").write_text("# v2\n")
        _git(self.repo, "commit", "-q", "-am", "c2")
        (dst / "tests" / "test_x.py").write_text("# v2\n")
        with self.assertRaisesRegex(ValueError, "exists with another commit"):
            pgg_game.write_code_version(dst, "HEAD", repo_dir=self.repo)

    def test_cli_writes_the_stamp(self):
        dst = self.copy()
        with mock.patch.object(pgg_game, "PROJECT_DIR", self.repo), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            code = pgg_game.main(["--write-code-version", str(dst), "--code-commit", self.sha])
        self.assertEqual(code, 0)
        self.assertIn(f"commit {self.sha}, {len(pgg_game.CODE_FILES) + 1} .py dosyası",
                      out.getvalue())
        self.assertTrue((dst / pgg_game.CODE_VERSION_FILE).is_file())
        with mock.patch.object(pgg_game, "PROJECT_DIR", self.repo), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            code = pgg_game.main(["--write-code-version", str(self.tmp / "missing")])
        self.assertEqual(code, 1)
        self.assertIn("HATA", err.getvalue())


CLEAN = {"git_commit": "a" * 40, "git_dirty": False, "source": "git", "code_dir": "/x",
         "files_sha256": {}}
DIRTY = {**CLEAN, "git_dirty": True, "dirty_files": ["pgg_game.py"]}
UNKNOWN = {"git_commit": None, "git_dirty": None, "source": None, "code_dir": "/x",
           "files_sha256": {}}


class RunRefusesUnverifiedCode(ResumeBase):
    def setUp(self):
        super().setUp()
        self.use(CostAPI())

    def checked(self, cv):
        """The real check (EngineTestBase turns it off) with code_version() = cv."""
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(pgg_game, "_REQUIRE_VERIFIED_CODE", True))
        stack.enter_context(mock.patch.object(pgg_game, "code_version", return_value=dict(cv)))
        return stack

    def test_dirty_or_unknown_code_does_not_start(self):
        for cv, message in ((DIRTY, "code is dirty"), (UNKNOWN, "code version is unknown")):
            with self.subTest(message), self.checked(cv):
                engine = Engine(self.rcfg())
                with self.assertRaisesRegex(ValueError, f"not started, no call made: .*{message}"):
                    engine.run()
                self.assertEqual(self.api.calls, [])
                self.assertFalse(self.run_dir.exists())          # nothing written, no lock

    def test_clean_code_runs_and_is_recorded(self):
        with self.checked(CLEAN):
            Engine(self.rcfg()).run()
        summary = self.summary_now()
        self.assertEqual(summary["segments"][-1]["code_version"]["git_commit"], "a" * 40)
        self.assertEqual(self.raw_events("pgg_run_start")[0]["code_version"]["git_commit"], "a" * 40)

    def test_resume_on_dirty_code_does_not_start(self):
        with self.checked(CLEAN):
            self.interrupted_run()
        before = _tree(self.run_dir)
        engine, api = self.resume()
        with self.checked(DIRTY), self.assertRaisesRegex(ValueError, "not resumed, no call made"):
            engine.run(resume=True)
        self.assertEqual(api.calls, [])
        self.assertEqual(_tree(self.run_dir), before)

    def test_cli_real_run_refused_before_llm_client_is_used(self):
        cards = self.tmp / "cards.json"
        cards.write_text(json.dumps([{"card_id": "a", "style": "s", "text": "short fake card"}]))
        argv = ["--run", "c1", "--cards", str(cards), "--models", "gpt", "--arms", "isolated",
                "--isolated-reps", "1", "--runs-dir", str(self.tmp / "runs")]
        with self.checked(DIRTY), mock.patch.object(pgg_game, "_llm") as llm, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(pgg_game.main(argv), 1)
        llm.assert_not_called()
        self.assertIn("HATA: kod sürümü: the code is dirty", err.getvalue())
        self.assertEqual(self.api.calls, [])
        self.assertFalse((self.tmp / "runs" / "c1").exists())

    def test_dry_runs_only_warn(self):
        with self.checked(DIRTY), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(pgg_game.main(["--dry-run"]), 0)
        self.assertIn("UYARI: kod sürümü", out.getvalue())
        self.assertIn("BAŞLAMAZ", out.getvalue())
        with self.checked(CLEAN), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(pgg_game.main(["--dry-run"]), 0)
        self.assertIn(f"Kod sürümü: {'a' * 40} (kaynak: git deposu; temiz)", out.getvalue())
        # --resume --dry-run: the plan is printed, with the warning
        with self.checked(CLEAN):
            self.interrupted_run(at=14, models=dict(GEMINI), budget_usd=None, invalid_rate_cap=None)
        cards = self.tmp / "cards.json"
        cards.write_text(json.dumps([{"card_id": c.card_id, "style": c.style, "text": c.text}
                                     for c in self.rcfg().cards]))
        argv = ["--resume", "--dry-run", "--run", "r1", "--cards", str(cards), "--models", "gemini",
                "--runs-dir", str(self.tmp / "runs"), "--rounds", "2", "--groups-per-cell", "1",
                "--isolated-reps", "1"]
        before = _tree(self.run_dir)
        with self.checked(DIRTY), contextlib.redirect_stdout(io.StringIO()) as out:
            code = pgg_game.main(argv)
        text = out.getvalue()
        self.assertIn("SÜRDÜRME PLANI", text)
        self.assertIn("UYARI: kod sürümü", text)
        self.assertIn("Config tutarlı", text)
        self.assertEqual(code, 0, text)
        self.assertEqual(_tree(self.run_dir), before)


class CommitChangeOnResume(ResumeBase):
    def with_commit(self, commit):
        cv = {**CLEAN, "git_commit": commit}
        return mock.patch.object(pgg_game, "code_version", return_value=cv)

    def test_other_commit_is_written_to_the_summary(self):
        a, b = "a" * 40, "b" * 40
        with self.with_commit(a):
            self.interrupted_run()
        with self.with_commit(b):
            engine, _ = self.resume()
            engine.run(resume=True)
        summary = self.summary_now()
        self.assertEqual(summary["units"]["n_remaining"], 0)
        change = {"now": b, "earlier": {"0": a}, "differs_from_segments": [0]}
        self.assertEqual(summary["segments"][-1]["code_change"], change)
        self.assertIsNone(summary["segments"][0].get("code_change"))
        self.assertEqual(summary["code_changes"], [{"segment": 1, **change}])
        self.assertEqual(self.raw_events("pgg_run_resume")[0]["code_change"], change)
        self.assertEqual([s["code_version"]["git_commit"] for s in summary["segments"]], [a, b])

    def test_same_commit_is_no_change_and_dry_run_reports_a_change(self):
        a = "a" * 40
        with self.with_commit(a):
            self.interrupted_run()
            plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
            self.assertIsNone(plan.code_change)
            engine, _ = self.resume()
            engine.run(resume=True)
        summary = self.summary_now()
        self.assertIsNone(summary["segments"][-1]["code_change"])
        self.assertEqual(summary["code_changes"], [])
        # a later segment with another commit: both earlier segments are listed
        with self.with_commit("c" * 40):
            engine = Engine(self.rcfg(), llm=pgg_game.OfflineLLM())
            plan = engine.resume_plan()
            text = pgg_game.resume_report(engine, plan)
        self.assertEqual(plan.code_change["differs_from_segments"], [0, 1])
        self.assertIn("Kod commit'i önceki segment(ler)den farklı", text)

    def test_segments_without_a_recorded_commit_count_as_different(self):
        with mock.patch.object(pgg_game, "code_version", return_value=dict(UNKNOWN)):
            self.interrupted_run()                      # e.g. a copy run by the earlier code
        with self.with_commit("a" * 40):
            engine, _ = self.resume()
            engine.run(resume=True)
        change = self.summary_now()["segments"][-1]["code_change"]
        self.assertEqual(change["earlier"], {"0": None})
        self.assertEqual(change["differs_from_segments"], [0])


if __name__ == "__main__":
    unittest.main()
