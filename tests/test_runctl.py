"""Mock tests of status.json, its heartbeat and scripts/runctl.py (task #80).

(a) the run process writes status.json itself: at the start, by heartbeat
while it runs, and at the end (state, units, cost, stop_reason, outcome);
(b) SIGTERM and stop_request.json end the run with stop_reason "interrupted";
(c) runctl.py status reads files only and reports running / stale / ended;
(d) end to end: runctl.py start runs a stand-in run process
(tests/fake_long_run.py: the real CLI with a fake, slow API) detached in its
own session; it goes on after start has returned; runctl.py stop ends it with
SIGTERM (or the request file) and status.json says "interrupted".
No network, no ../.env.
"""

import ast
import contextlib
import hashlib
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_pgg_game import CARD_A, CARD_B, ROOT  # noqa: E402
from test_pgg_guards import CostAPI  # noqa: E402
from test_pgg_resume import ResumeBase  # noqa: E402

import pgg_game  # noqa: E402
from pgg_game import Engine, RunStopped  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
import runctl  # noqa: E402

RUNCTL = ROOT / "scripts" / "runctl.py"
MODELS_SLUGS = ("v/m1", "v/m2")                   # test_pgg_resume.MODELS2
FAKE_RUN = ROOT / "tests" / "fake_long_run.py"


def _wait(seconds: float) -> None:
    """A real pause (time.sleep is mocked in the engine tests)."""
    threading.Event().wait(seconds)


def _tree(path: Path) -> dict:
    return {str(p.relative_to(path)): (hashlib.sha256(p.read_bytes()).hexdigest(),
                                       p.stat().st_mtime_ns)
            for p in sorted(path.rglob("*")) if p.is_file()}


# --------------------------------------------------------------------------
# (a) + (b) in process
# --------------------------------------------------------------------------

class StatusFile(ResumeBase):
    def status(self):
        return json.loads((self.run_dir / "status.json").read_text())

    def test_heartbeat_while_running_and_final_status(self):
        seen = []
        api = CostAPI(cost=0.001)

        def content_fn(kwargs, content):
            if len(api.calls) in (12, 30):
                _wait(0.25)                # several heartbeats of 0.02 s go by
                seen.append(self.status())
            return content
        api.content_fn = content_fn
        self.use(api)
        engine = Engine(self.rcfg())
        engine.heartbeat_s = 0.02
        engine.run()
        first, second = seen
        for st in seen:
            self.assertEqual(st["state"], "running")
            self.assertEqual(st["pid"], os.getpid())
            self.assertEqual((st["run"], st["segment"]), ("r1", 0))
            self.assertIsNone(st["stop_reason"])
            self.assertEqual(st["units"]["n_units"], 8)
            self.assertEqual(st["units"]["source"], "heartbeat")
        self.assertGreater(second["heartbeat_ts"], first["heartbeat_ts"])
        self.assertGreater(second["n_heartbeats"], first["n_heartbeats"])
        self.assertGreaterEqual(first["n_heartbeats"], 3)
        # calls 1-11 are answered, unit 0 (8 calls) is complete
        self.assertEqual(first["units"]["n_complete"], 1)
        self.assertAlmostEqual(first["cost_usd"]["total"], 0.011)
        self.assertGreater(second["units"]["n_complete"], first["units"]["n_complete"])

        end = self.status()
        summary = self.summary_now()
        self.assertEqual((end["state"], end["outcome"]), ("ended", "completed"))
        self.assertIsNone(end["stop_reason"])
        self.assertIsNone(end["error"])
        self.assertEqual(end["units"]["source"], "summary")
        self.assertEqual(end["units"]["n_complete"], 8)
        self.assertEqual(end["units"]["n_remaining"], 0)
        self.assertAlmostEqual(end["cost_usd"]["total"], summary["total_cost_usd"])
        self.assertAlmostEqual(end["cost_usd"]["total"], 0.001 * len(api.calls))
        self.assertEqual(list(end["cost_usd"]["per_model"]), list(MODELS_SLUGS))
        self.assertGreaterEqual(end["ended_ts"], end["started_ts"])
        self.assertEqual(summary["files"]["status"]["path"], str(self.run_dir / "status.json"))
        self.assertFalse(list(self.run_dir.glob(".status.json.*")))      # no temp file left
        # the heartbeat thread has ended with the run
        self.assertFalse([t for t in threading.enumerate() if t.name == "heartbeat-r1"])

    def test_sigterm_leaves_interrupted(self):
        self.interrupted_run()
        st = self.status()
        self.assertEqual((st["state"], st["stop_reason"], st["signal"], st["outcome"]),
                         ("ended", "interrupted", "SIGTERM", "stopped"))
        self.assertEqual(self.summary_now()["stop_reason"], "interrupted")
        self.assertEqual(st["units"]["n_complete"], 2)
        self.assertIsNone(st["error"])

    def test_stop_request_file_stops_as_sigterm(self):
        api = CostAPI()
        engine = None
        before = signal.getsignal(signal.SIGTERM)

        def content_fn(kwargs, content):
            if len(api.calls) == 10:
                (self.run_dir / "stop_request.json").write_text(json.dumps(
                    {"pid": os.getpid(), "segment": 0, "requested_at": "now", "by": "test"}))
                for _ in range(500):       # the heartbeat thread reads it within ~1 s
                    if engine._interrupted is not None:
                        break
                    _wait(0.01)
            return content
        api.content_fn = content_fn
        self.use(api)
        engine = Engine(self.rcfg())
        engine.heartbeat_s = 0.05
        with self.assertRaisesRegex(RunStopped, "interrupted"):
            engine.run()
        self.assertEqual(len(api.calls), 10)          # no call after the request
        st = self.status()
        self.assertEqual((st["state"], st["stop_reason"], st["signal"], st["outcome"]),
                         ("ended", "interrupted", "SIGTERM", "stopped"))
        self.assertEqual(st["stop_request"]["by"], "test")
        self.assertEqual(len(self.raw_events("pgg_stop_request")), 1)
        stopped = self.raw_events("pgg_run_stopped")
        self.assertEqual([(r["reason"], r["signal"], r["stop_request"]["pid"]) for r in stopped],
                         [("interrupted", "SIGTERM", os.getpid())])
        self.assertEqual(signal.getsignal(signal.SIGTERM), before)       # handler restored

    def test_stop_request_of_another_process_is_ignored(self):
        api = CostAPI()

        def content_fn(kwargs, content):
            if len(api.calls) == 3:
                (self.run_dir / "stop_request.json").write_text(json.dumps(
                    {"pid": os.getpid() + 100000, "segment": 0}))
                _wait(0.2)
            return content
        api.content_fn = content_fn
        self.use(api)
        engine = Engine(self.rcfg())
        engine.heartbeat_s = 0.05
        engine.run()
        st = self.status()
        self.assertEqual((st["outcome"], st["stop_reason"], st["stop_request"]),
                         ("completed", None, None))
        self.assertEqual(self.raw_events("pgg_stop_request"), [])

    def test_refused_resume_does_not_touch_status(self):
        self.interrupted_run()
        before = (self.run_dir / "status.json").read_bytes()
        engine, api = self.resume(groups_per_cell=2)              # another design
        with self.assertRaisesRegex(ValueError, "not resumed"):
            engine.run(resume=True)
        self.assertEqual(api.calls, [])
        self.assertEqual((self.run_dir / "status.json").read_bytes(), before)

    def test_resumed_segment_counts_earlier_units(self):
        self.interrupted_run()
        engine, _ = self.resume()
        engine.run(resume=True)
        st = self.status()
        self.assertEqual((st["segment"], st["resume"], st["outcome"]), (1, True, "completed"))
        self.assertEqual(st["units"]["n_complete"], 8)
        self.assertEqual(st["units"]["n_complete_this_segment"], 6)


# --------------------------------------------------------------------------
# (c) runctl.py status: files only
# --------------------------------------------------------------------------

class StatusCommand(unittest.TestCase):
    def setUp(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.run_dir = Path(tmp.name) / "r1"
        self.run_dir.mkdir()

    def write_status(self, **kw):
        st = {"schema": 1, "run": "r1", "segment": 2, "pid": 4242, "host": "h",
              "started_ts": 1000.0, "state": "running", "heartbeat_ts": 1100.0,
              "heartbeat_interval_s": 30.0, "n_heartbeats": 4,
              "units": {"n_units": 120, "n_complete": 37, "n_complete_before_segment": 30,
                        "n_completed_this_segment": 7, "source": "heartbeat"},
              "cost_usd": {"total": 1.2345, "segment": 0.2, "per_model": {"v/m1": 1.2345}},
              "budget_usd": 10, "stopped_models": {}, "stop_reason": None, "signal": None,
              "files": {"raw_log": str(self.run_dir / "raw_calls.jsonl")}}
        st.update(kw)
        (self.run_dir / "status.json").write_text(json.dumps(st))
        return st

    def main(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = runctl.main(["status", "--run-dir", str(self.run_dir), *extra])
        return code, out.getvalue()

    def test_verdicts(self):
        self.write_status()
        self.assertEqual(runctl.read_state(self.run_dir, now=1110.0)["verdict"], "running")
        self.assertEqual(runctl.read_state(self.run_dir, now=1110.0)["exit_code"], 0)
        # stale after 3 x 30 + 15 = 105 s without a heartbeat
        s = runctl.read_state(self.run_dir, now=1100.0 + 106)
        self.assertEqual((s["verdict"], s["exit_code"]), ("stale", 4))
        self.assertEqual(runctl.read_state(self.run_dir, now=1100.0 + 104)["verdict"], "running")
        self.write_status(state="ended", stop_reason="interrupted", outcome="stopped")
        s = runctl.read_state(self.run_dir, now=99999.0)
        self.assertEqual((s["verdict"], s["exit_code"]), ("ended", 3))
        (self.run_dir / "status.json").unlink()
        s = runctl.read_state(self.run_dir)
        self.assertEqual((s["verdict"], s["exit_code"]), ("no_status", 2))

    def test_output_and_nothing_written(self):
        self.write_status(heartbeat_ts=time.time())
        (self.run_dir / "raw_calls.jsonl").write_text("{}\n")
        before = _tree(self.run_dir)
        code, out = self.main()
        self.assertEqual(code, 0)
        self.assertIn("ÇALIŞIYOR", out)
        self.assertIn("pid=4242", out)
        self.assertIn("Birimler: 37/120 tamam", out)
        self.assertIn("toplam 1.2345 USD", out)
        code, out = self.main("--json")
        self.assertEqual(json.loads(out)["status"]["units"]["n_complete"], 37)
        self.assertEqual(_tree(self.run_dir), before)

    def test_launch_without_status_shows_console_tail(self):
        (self.run_dir / "launcher.jsonl").write_text(json.dumps(
            {"ts": 5.0, "pid": 77, "console_log": "c"}) + "\n")
        (self.run_dir / "console.log").write_text("HATA: prereg_approved is false\n")
        code, out = self.main()
        self.assertEqual(code, 2)
        self.assertIn("status.json yok", out)
        self.assertIn("pid 77", out)
        self.assertIn("HATA: prereg_approved is false", out)

    def test_runctl_imports_only_the_standard_library(self):
        tree = ast.parse(RUNCTL.read_text(encoding="utf-8"))
        names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)
                 for a in n.names}
        names |= {n.module.split(".")[0] for n in ast.walk(tree)
                  if isinstance(n, ast.ImportFrom) and n.module}
        self.assertEqual(names - {"__future__"}, {"argparse", "json", "os", "shutil", "signal",
                                                  "socket", "subprocess", "sys", "time",
                                                  "pathlib"})
        self.assertEqual((runctl.STATUS_FILE, runctl.STOP_REQUEST_FILE,
                          runctl.DEFAULT_HEARTBEAT_S),
                         (pgg_game.STATUS_FILE, pgg_game.STOP_REQUEST_FILE,
                          pgg_game.DEFAULT_HEARTBEAT_S))


# --------------------------------------------------------------------------
# (d) end to end: a detached stand-in run process
# --------------------------------------------------------------------------

class EndToEnd(unittest.TestCase):
    def setUp(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.runs = self.tmp / "runs"
        self.runs.mkdir()
        cards = self.tmp / "cards.json"
        cards.write_text(json.dumps([{"card_id": c.card_id, "style": c.style, "text": c.text}
                                     for c in (CARD_A, CARD_B)]))
        self.config = self.tmp / "cfg.json"
        # 2 group games of 10 rounds + 2 schedules: 90 calls x 0.2 s
        self.config.write_text(json.dumps({
            "cards": str(cards), "models": ["gemini"], "params": {"rounds": 10},
            "groups_per_cell": 1, "isolated_reps": 1, "budget_usd": 5}))
        self.env = {**os.environ, "OPENROUTER_API_KEY": "test-dummy", "FAKE_DELAY_S": "0.2"}
        self.pids = []
        self.addCleanup(self.kill_leftovers)

    def kill_leftovers(self):
        for pid in self.pids:
            with contextlib.suppress(OSError):
                os.kill(pid, signal.SIGKILL)

    def runctl(self, *argv, env=None, timeout=60):
        return subprocess.run([sys.executable, str(RUNCTL), *argv], capture_output=True,
                              text=True, env=env or self.env, timeout=timeout)

    def start(self, run="r1", *extra, env=None, caffeinate=False):
        # task #90: caffeinate is on by default; off here unless a test asks for it
        p = self.runctl("start", "--config", str(self.config), "--run", run,
                        "--runs-dir", str(self.runs), "--entry", str(FAKE_RUN),
                        "--heartbeat-interval", "0.3", "--wait", "30",
                        *(() if caffeinate else ("--no-caffeinate",)), *extra, env=env)
        launch = runctl._last_jsonl(self.runs / run / "launcher.jsonl")
        if launch:
            self.pids.append(launch["pid"])
        return p, launch

    def status(self, run="r1"):
        return json.loads((self.runs / run / "status.json").read_text())

    def test_detached_run_heartbeats_after_start_returned_and_sigterm_stops_it(self):
        p, launch = self.start()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("ÇALIŞIYOR", p.stdout)
        pid = launch["pid"]
        self.assertNotIn("OPENROUTER_API_KEY", json.dumps(launch))         # no environment
        self.assertEqual(launch["argv"][2], str(FAKE_RUN))
        self.assertIn("--heartbeat-interval", launch["argv"])
        # start has returned; the run process goes on writing its heartbeat
        first = self.status()
        self.assertEqual(first["pid"], pid)
        _wait(1.5)
        second = self.status()
        self.assertEqual(second["state"], "running")
        self.assertGreater(second["n_heartbeats"], first["n_heartbeats"])
        self.assertGreater(second["heartbeat_ts"], first["heartbeat_ts"])
        with contextlib.suppress(PermissionError):
            self.assertEqual(os.getsid(pid), pid)          # its own session (setsid)
        s = self.runctl("status", "--runs-dir", str(self.runs), "--run", "r1")
        self.assertEqual(s.returncode, 0, s.stdout)
        # stop: SIGTERM to the pid of status.json (same pid in r1.lock)
        stop = self.runctl("stop", "--runs-dir", str(self.runs), "--run", "r1", "--wait", "30")
        self.assertEqual(stop.returncode, 0, stop.stdout + stop.stderr)
        self.assertIn(f"SIGTERM gönderildi (pid {pid})", stop.stdout)
        self.assertIn("stop_reason=interrupted", stop.stdout)
        end = self.status()
        self.assertEqual((end["state"], end["stop_reason"], end["signal"], end["outcome"]),
                         ("ended", "interrupted", "SIGTERM", "stopped"))
        self.assertIsNone(end["stop_request"])
        summary = json.loads((self.runs / "r1" / "r1_summary.json").read_text())
        self.assertEqual(summary["stop_reason"], "interrupted")
        self.assertLess(end["units"]["n_complete"], 4)
        for _ in range(100):                           # the lock goes with the process
            if not (self.runs / "r1" / "r1.lock").exists():
                break
            _wait(0.1)
        self.assertFalse((self.runs / "r1" / "r1.lock").exists())
        s = self.runctl("status", "--runs-dir", str(self.runs), "--run", "r1")
        self.assertEqual(s.returncode, 3, s.stdout)
        self.assertIn("BİTTİ", s.stdout)
        # a second stop finds it ended
        again = self.runctl("stop", "--runs-dir", str(self.runs), "--run", "r1")
        self.assertEqual(again.returncode, 0)
        self.assertIn("zaten bitmiş", again.stdout)

        # and it goes on with start --resume to the end
        p, launch = self.start("r1", "--resume")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for _ in range(600):
            st = self.status()
            if st["state"] == "ended":
                break
            _wait(0.1)
        self.assertEqual((st["segment"], st["outcome"], st["stop_reason"]), (1, "completed", None))
        self.assertEqual(st["units"]["n_complete"], st["units"]["n_units"])

    def stop_and_wait(self, run="r1"):
        stop = self.runctl("stop", "--runs-dir", str(self.runs), "--run", run, "--wait", "30")
        self.assertEqual(stop.returncode, 0, stop.stdout + stop.stderr)
        return self.status(run)

    @unittest.skipUnless(shutil.which("caffeinate"), "no caffeinate (not macOS)")
    def test_caffeinate_is_on_by_default_and_ends_with_the_run(self):
        p, launch = self.start(caffeinate=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual((launch["caffeinate"], launch["caffeinate_missing"]), (True, False))
        cpid = launch["caffeinate_pid"]
        self.assertIsInstance(cpid, int)
        self.pids.append(cpid)
        self.assertIn(f"caffeinate pid {cpid}", p.stdout)
        self.assertNotIn("caffeinate bulunamadı", p.stderr)
        self.assertEqual(self.stop_and_wait()["outcome"], "stopped")
        for _ in range(100):                   # caffeinate -w PID ends with the run
            try:
                os.kill(cpid, 0)
            except ProcessLookupError:
                break
            except PermissionError:            # not ours to signal: cannot be watched
                break
            _wait(0.1)
        else:
            self.fail("caffeinate did not end with the run")

    def test_no_caffeinate_and_missing_caffeinate(self):
        p, launch = self.start("r1")                     # --no-caffeinate
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual((launch["caffeinate"], launch["caffeinate_pid"],
                          launch["caffeinate_missing"]), (False, None, False))
        self.assertNotIn("caffeinate", p.stderr)
        self.stop_and_wait("r1")
        # default on, but no caffeinate on PATH: a warning, and the run starts
        p, launch = self.start("r2", caffeinate=True, env={**self.env, "PATH": "/nonexistent"})
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("UYARI: caffeinate bulunamadı", p.stderr)
        self.assertEqual((launch["caffeinate"], launch["caffeinate_pid"],
                          launch["caffeinate_missing"]), (True, None, True))
        self.assertEqual(self.stop_and_wait("r2")["outcome"], "stopped")

    def test_stop_via_request_file(self):
        p, launch = self.start()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        stop = self.runctl("stop", "--runs-dir", str(self.runs), "--run", "r1", "--via-file",
                           "--wait", "30")
        self.assertEqual(stop.returncode, 0, stop.stdout + stop.stderr)
        self.assertIn("durdurma isteği yazıldı", stop.stdout)
        end = self.status()
        self.assertEqual((end["stop_reason"], end["signal"], end["outcome"]),
                         ("interrupted", "SIGTERM", "stopped"))
        self.assertEqual(end["stop_request"]["pid"], launch["pid"])

    def test_start_reports_an_early_exit(self):
        cfg = json.loads(self.config.read_text())
        self.config.write_text(json.dumps({**cfg, "prereg_approved": False}))
        p, launch = self.start()
        self.assertEqual(p.returncode, 1)
        self.assertIn("SÜREÇ BİTTİ", p.stderr)
        self.assertIn("prereg_approved", p.stderr)              # the console log's tail
        self.assertFalse((self.runs / "r1" / "status.json").exists())
        s = self.runctl("status", "--runs-dir", str(self.runs), "--run", "r1")
        self.assertEqual(s.returncode, 2)
        self.assertIn("prereg_approved", s.stdout)

    def test_start_refusals_spawn_nothing(self):
        # a ../.env of the code directory counts as the key
        if not (ROOT.parent / ".env").is_file():
            env = {k: v for k, v in self.env.items() if k != "OPENROUTER_API_KEY"}
            p, launch = self.start("r1", env=env)
            self.assertEqual(p.returncode, 1)
            self.assertIn("OPENROUTER_API_KEY", p.stderr)
            self.assertIsNone(launch)
        p, launch = self.start("r1", "--resume")
        self.assertEqual(p.returncode, 1)
        self.assertIn("koşu dizini yok", p.stderr)
        self.assertIsNone(launch)
        p = self.runctl("start", "--config", str(self.config), "--run", "x_{run_date}",
                        "--runs-dir", str(self.runs), "--entry", str(FAKE_RUN))
        self.assertEqual(p.returncode, 1)
        self.assertIn("şablon", p.stderr)
        p = self.runctl("start", "--config", str(self.config), "--run", "r2",
                        "--runs-dir", "runs", "--entry", str(FAKE_RUN))
        self.assertEqual(p.returncode, 1)
        self.assertIn("mutlak", p.stderr)
        self.assertEqual(sorted(x.name for x in self.runs.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
