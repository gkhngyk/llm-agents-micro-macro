#!/usr/bin/env python3
"""Start, watch and stop a long run of pgg_game.py outside any tool session (task #80).

    runctl.py start  --config CONFIG --run RUN --runs-dir DIR [--resume] [...] [-- ARGS]
    runctl.py status --runs-dir DIR --run RUN      (or --run-dir DIR/RUN) [--json]
    runctl.py stop   --runs-dir DIR --run RUN      [--via-file] [--wait S]

start: runs `python pgg_game.py --config ... --run ... --runs-dir ...
--heartbeat-interval S [--resume] [ARGS]` in the code directory as a
detached process: a new session (setsid, so no terminal and no process group
of the caller: closing the terminal or ending the caller's session does not
signal it), SIGHUP ignored (as nohup), stdin /dev/null, stdout and stderr
appended to <runs-dir>/<run>/console.log. The launch is recorded in
<runs-dir>/<run>/launcher.jsonl (pid, argv, code dir, console log; never the
environment). With --caffeinate, `caffeinate -is -w PID` keeps the Mac awake
while the run lives. start then waits (--wait) until the run's own
status.json names the new pid, or the process has ended (the console log's
tail is printed).

status: reads files only (status.json, launcher.jsonl, console.log and the
mtime of the raw log): it never signals or calls anything and writes nothing.
The run process writes status.json itself (pgg_game.py, heartbeat every
--heartbeat-interval seconds). Exit code: 0 running (fresh heartbeat), 3
ended, 4 heartbeat stale (the process may be gone: see the console log; go on
with start --resume), 2 no status.json yet or unreadable.

stop: SIGTERM to the pid of status.json, after checking that <run>.lock holds
the same pid (else a reused pid could be hit; --force skips the check). The
run ends as on SIGINT / SIGTERM: stop_reason "interrupted", summary written,
calls in flight let end. Where the caller may not signal the process (orc's
sandbox: PermissionError) or with --via-file, it writes stop_request.json
({pid, segment}) instead; the run's heartbeat thread reads it within about a
second and sends SIGTERM to itself. --wait S waits until status.json says
"ended".

Only the standard library; pgg_game and llm_client are not imported.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent.parent      # repository / code copy
STATUS_FILE = "status.json"                            # = pgg_game.STATUS_FILE
STOP_REQUEST_FILE = "stop_request.json"                # = pgg_game.STOP_REQUEST_FILE
LAUNCHER_LOG = "launcher.jsonl"
CONSOLE_LOG = "console.log"
DEFAULT_HEARTBEAT_S = 30.0                             # = pgg_game.DEFAULT_HEARTBEAT_S

EXIT_RUNNING, EXIT_NO_STATUS, EXIT_ENDED, EXIT_STALE = 0, 2, 3, 4


def _iso(ts: float | None) -> str:
    return "-" if ts is None else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _last_jsonl(path: Path) -> dict | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            return rec
    return None


def _tail(path: Path, n: int = 30) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except OSError:
        return []


def _write_atomic(path: Path, obj: dict) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def run_dir_of(args) -> Path:
    if args.run_dir:
        return Path(args.run_dir)
    if not (args.runs_dir and args.run):
        raise SystemExit("HATA: --run-dir ya da --runs-dir ile --run gerekli")
    return Path(args.runs_dir) / args.run


# --------------------------------------------------------------------------
# status (files only)
# --------------------------------------------------------------------------

def read_state(run_dir: Path, now: float | None = None, stale_after: float | None = None) -> dict:
    """What the files say about the run; reads files and their mtimes only."""
    now = time.time() if now is None else now
    status = _read_json(run_dir / STATUS_FILE)
    launch = _last_jsonl(run_dir / LAUNCHER_LOG)
    out = {"run_dir": str(run_dir), "status": status if isinstance(status, dict) else None,
           "launch": launch, "now": now}
    if out["status"] is None:
        out["verdict"] = "no_status"
        out["exit_code"] = EXIT_NO_STATUS
        return out
    st = out["status"]
    interval = st.get("heartbeat_interval_s") or DEFAULT_HEARTBEAT_S
    limit = stale_after if stale_after is not None else 3 * interval + 15
    age = now - st["heartbeat_ts"] if isinstance(st.get("heartbeat_ts"), (int, float)) else None
    out.update(heartbeat_age_s=age, stale_after_s=limit)
    raw = (st.get("files") or {}).get("raw_log")
    if raw:
        try:
            out["raw_log_age_s"] = now - Path(raw).stat().st_mtime
        except OSError:
            out["raw_log_age_s"] = None
    # a launch after the status file's segment started whose process has not
    # written status.json (yet): refused before its checks, or still starting
    if launch and launch.get("pid") != st.get("pid") and \
            (launch.get("ts") or 0) > (st.get("started_ts") or 0):
        out["newer_launch_without_status"] = True
    if st.get("state") == "ended":
        out["verdict"], out["exit_code"] = "ended", EXIT_ENDED
    elif age is None or age > limit:
        out["verdict"], out["exit_code"] = "stale", EXIT_STALE
    else:
        out["verdict"], out["exit_code"] = "running", EXIT_RUNNING
    return out


def format_state(s: dict) -> str:
    lines = [f"Koşu dizini: {s['run_dir']}"]
    launch = s.get("launch")
    if s["verdict"] == "no_status":
        lines.append("status.json yok ya da okunamadı: koşu süreci henüz durum yazmadı "
                     "(başlamadı, denetimlerde reddedildi ya da hâlâ açılıyor).")
    else:
        st = s["status"]
        verdict = {"running": "ÇALIŞIYOR", "ended": "BİTTİ",
                   "stale": "HEARTBEAT BAYAT (süreç ölmüş olabilir)"}[s["verdict"]]
        lines.append(f"Durum: {verdict} — state={st.get('state')}, run={st.get('run')}, "
                     f"segment={st.get('segment')}, pid={st.get('pid')}, host={st.get('host')}")
        age = s.get("heartbeat_age_s")
        lines.append(f"Heartbeat: {_iso(st.get('heartbeat_ts'))} ("
                     + ("?" if age is None else f"{age:.0f} sn önce")
                     + f"; aralık {st.get('heartbeat_interval_s')} sn, bayat sınırı "
                     f"{s['stale_after_s']:.0f} sn; {st.get('n_heartbeats')} heartbeat)")
        lines.append(f"Segment başı: {_iso(st.get('started_ts'))}"
                     + (f"; bitiş: {_iso(st.get('ended_ts'))}" if st.get("ended_ts") else ""))
        u = st.get("units") or {}
        lines.append(f"Birimler: {u.get('n_complete')}/{u.get('n_units')} tamam "
                     f"(kaynak: {u.get('source')}"
                     + (f"; bu segmentte {u['n_completed_this_segment']}"
                        if u.get("n_completed_this_segment") is not None else "")
                     + (f"; bu segmentte {u['n_complete_this_segment']}"
                        if u.get("n_complete_this_segment") is not None else "") + ")")
        c = st.get("cost_usd") or {}
        if c:
            per = ", ".join(f"{m.split('/')[-1]} {v:.4f}" for m, v in (c.get("per_model") or {}).items())
            lines.append(f"Maliyet: toplam {c.get('total', 0):.4f} USD (bu segment "
                         f"{c.get('segment', 0):.4f}; bütçe {st.get('budget_usd')}); {per}")
        lines.append(f"stop_reason: {st.get('stop_reason')}"
                     + (f"; sinyal {st['signal']}" if st.get("signal") else "")
                     + (f"; durdurulan modeller {st['stopped_models']}"
                        if st.get("stopped_models") else "")
                     + (f"; sonuç (outcome) {st['outcome']}" if st.get("outcome") else "")
                     + (f"; hata {st['error']}" if st.get("error") else ""))
        if s.get("raw_log_age_s") is not None:
            lines.append(f"Ham log son yazım: {s['raw_log_age_s']:.0f} sn önce")
    if launch:
        lines.append(f"Son başlatma (launcher.jsonl): {_iso(launch.get('ts'))}, pid "
                     f"{launch.get('pid')}, konsol {launch.get('console_log')}")
    if s.get("newer_launch_without_status") or (s["verdict"] in ("no_status", "stale") and launch):
        lines.append("UYARI: son başlatılan süreç status.json yazmadı ya da susmuş; konsol "
                     "logunun sonu:")
        lines += ["  | " + x for x in _tail(Path(s["run_dir"]) / CONSOLE_LOG, 15)]
    return "\n".join(lines)


def cmd_status(args) -> int:
    s = read_state(run_dir_of(args), stale_after=args.stale_after)
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=2))
    else:
        print(format_state(s))
    return s["exit_code"]


# --------------------------------------------------------------------------
# start
# --------------------------------------------------------------------------

def _resolve(path: str, base: Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else base / p


def build_command(args, code_dir: Path) -> list[str]:
    entry = _resolve(args.entry, code_dir) if args.entry else code_dir / "pgg_game.py"
    cmd = [args.python, "-u", str(entry), "--config", str(_resolve(args.config, code_dir)),
           "--run", args.run, "--runs-dir", str(args.runs_dir),
           "--heartbeat-interval", f"{args.heartbeat_interval:g}"]
    if args.resume:
        cmd.append("--resume")
    extra = list(args.extra or [])
    if extra[:1] == ["--"]:
        extra = extra[1:]
    return cmd + extra


def start_problems(args, code_dir: Path, run_dir: Path) -> list[str]:
    problems = []
    entry = _resolve(args.entry, code_dir) if args.entry else code_dir / "pgg_game.py"
    if not entry.is_file():
        problems.append(f"çalıştırılacak dosya yok: {entry}")
    if not _resolve(args.config, code_dir).is_file():
        problems.append(f"config yok: {_resolve(args.config, code_dir)}")
    runs = Path(args.runs_dir)
    if not runs.is_absolute() or not runs.is_dir():
        problems.append(f"--runs-dir mutlak ve var olan bir dizin olmalı: {runs}")
    if "{" in args.run or "/" in args.run:
        problems.append(f"--run açık bir ad olmalı (şablon ya da yol değil): {args.run}")
    if args.resume and not run_dir.is_dir():
        problems.append(f"--resume: koşu dizini yok: {run_dir}")
    # the key: present or not, its value is never read here
    if "OPENROUTER_API_KEY" not in os.environ and not (code_dir.parent / ".env").is_file():
        problems.append("OPENROUTER_API_KEY ortamda yok ve kod dizininin bir üstünde .env yok "
                        f"({code_dir.parent / '.env'})")
    s = read_state(run_dir) if run_dir.is_dir() else None
    if s and s["verdict"] == "running":
        problems.append(f"koşu çalışıyor görünüyor (pid {s['status'].get('pid')}, heartbeat "
                        f"{s['heartbeat_age_s']:.0f} sn önce); önce durdurun ya da bekleyin")
    return problems


def _spawn(cmd, *, cwd, log) -> subprocess.Popen:
    """A process in its own session, SIGHUP ignored, no stdin; output to log."""
    previous = signal.signal(signal.SIGHUP, signal.SIG_IGN)   # inherited through exec (nohup)
    try:
        return subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True,
                                close_fds=True, env={**os.environ, "PYTHONUNBUFFERED": "1"})
    finally:
        signal.signal(signal.SIGHUP, previous)


def cmd_start(args) -> int:
    code_dir = Path(args.code_dir).resolve() if args.code_dir else CODE_DIR
    run_dir = Path(args.runs_dir) / args.run
    problems = start_problems(args, code_dir, run_dir)
    if problems:
        for p in problems:
            print(f"HATA: {p}", file=sys.stderr)
        print("başlatılmadı", file=sys.stderr)
        return 1
    cmd = build_command(args, code_dir)
    run_dir.mkdir(exist_ok=True)
    console = run_dir / CONSOLE_LOG
    now = time.time()
    with open(console, "a", encoding="utf-8") as log:
        log.write(f"===== runctl start {_iso(now)}: {' '.join(cmd)} (cwd {code_dir})\n")
        log.flush()
        proc = _spawn(cmd, cwd=code_dir, log=log)
    caffeinate_pid = None
    if args.caffeinate:
        with open(os.devnull, "w") as null:
            caffeinate_pid = _spawn(["caffeinate", "-is", "-w", str(proc.pid)],
                                    cwd=code_dir, log=null).pid
    record = {"ts": now, "at": _iso(now), "event": "start", "pid": proc.pid,
              "host": socket.gethostname(), "argv": cmd, "cwd": str(code_dir),
              "python": args.python, "console_log": str(console), "resume": args.resume,
              "heartbeat_interval_s": args.heartbeat_interval, "caffeinate_pid": caffeinate_pid}
    with open(run_dir / LAUNCHER_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"başlatıldı: pid {proc.pid} (ayrı oturum), konsol {console}")
    deadline = time.monotonic() + args.wait
    while time.monotonic() < deadline:
        code = proc.poll()
        if code is not None:
            print(f"SÜREÇ BİTTİ (çıkış kodu {code}); konsol logunun sonu:", file=sys.stderr)
            for line in _tail(console, 40):
                print("  | " + line, file=sys.stderr)
            return 1
        st = _read_json(run_dir / STATUS_FILE)
        if isinstance(st, dict) and st.get("pid") == proc.pid:
            print(format_state(read_state(run_dir)))
            return 0
        time.sleep(0.5)
    print(f"UYARI: {args.wait:g} sn içinde status.json bu pid'i göstermedi; süreç yaşıyor "
          f"olabilir. İzleyin: runctl.py status --run-dir {run_dir}", file=sys.stderr)
    return 5


# --------------------------------------------------------------------------
# stop
# --------------------------------------------------------------------------

def _wait_ended(run_dir: Path, wait_s: float) -> dict | None:
    deadline = time.monotonic() + wait_s
    while True:
        st = _read_json(run_dir / STATUS_FILE)
        if isinstance(st, dict) and st.get("state") == "ended":
            return st
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.5)


def write_stop_request(run_dir: Path, st: dict) -> Path:
    path = run_dir / STOP_REQUEST_FILE
    _write_atomic(path, {"pid": st.get("pid"), "segment": st.get("segment"),
                         "requested_at": _iso(time.time()), "by": "runctl"})
    return path


def cmd_stop(args) -> int:
    run_dir = run_dir_of(args)
    st = _read_json(run_dir / STATUS_FILE)
    if not isinstance(st, dict):
        print(f"HATA: {run_dir / STATUS_FILE} yok ya da okunamadı; durdurulacak süreç bilinmiyor",
              file=sys.stderr)
        return EXIT_NO_STATUS
    if st.get("state") == "ended":
        print(f"koşu zaten bitmiş: stop_reason={st.get('stop_reason')}, "
              f"outcome={st.get('outcome')}")
        return 0
    pid = st.get("pid")
    if not isinstance(pid, int) or pid <= 0:
        print(f"HATA: status.json'da geçerli pid yok: {pid!r}", file=sys.stderr)
        return 1
    lock = _read_json(run_dir / f"{st.get('run')}.lock")
    if not args.force and (not isinstance(lock, dict) or lock.get("pid") != pid):
        print(f"HATA: kilit dosyası pid'i ({(lock or {}).get('pid')}) status.json pid'i ({pid}) "
              "ile aynı değil ya da kilit yok: süreç zaten bitmiş olabilir; sinyal "
              "gönderilmedi (--force ile yine de gönderilir)", file=sys.stderr)
        return 1
    how = None
    if not args.via_file:
        try:
            os.kill(pid, signal.SIGTERM)
            how = f"SIGTERM gönderildi (pid {pid})"
        except ProcessLookupError:
            print(f"HATA: pid {pid} yaşamıyor; status.json bitmemiş görünüyor (süreç ölmüş "
                  "olabilir, --resume ile sürdürülebilir)", file=sys.stderr)
            return 1
        except PermissionError:
            how = None                     # e.g. orc's sandbox: ask the process itself
    if how is None:
        path = write_stop_request(run_dir, st)
        how = (f"durdurma isteği yazıldı: {path} (pid {pid}); koşu süreci ~1 sn içinde kendine "
               "SIGTERM gönderir")
    print(how)
    if args.wait:
        end = _wait_ended(run_dir, args.wait)
        if end is None:
            print(f"UYARI: {args.wait:g} sn içinde state=ended olmadı (uçuştaki çağrılar "
                  "bekleniyor olabilir)", file=sys.stderr)
            return EXIT_STALE
        print(f"bitti: stop_reason={end.get('stop_reason')}, sinyal={end.get('signal')}, "
              f"outcome={end.get('outcome')}")
    return 0


# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)

    def where(p):
        p.add_argument("--run-dir", help="<runs-dir>/<run>")
        p.add_argument("--runs-dir")
        p.add_argument("--run")

    p = sub.add_parser("start", help="start pgg_game.py as a detached process")
    p.add_argument("--config", required=True, help="relative paths: relative to the code dir")
    p.add_argument("--run", required=True, help="resolved run name (no {run_date} template)")
    p.add_argument("--runs-dir", required=True, help="absolute, existing")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--code-dir", help=f"directory of pgg_game.py (default {CODE_DIR})")
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--entry", help="script run instead of <code-dir>/pgg_game.py (tests)")
    p.add_argument("--heartbeat-interval", type=float, default=DEFAULT_HEARTBEAT_S)
    p.add_argument("--caffeinate", action="store_true",
                   help="keep the Mac awake while the run lives (caffeinate -is -w PID)")
    p.add_argument("--wait", type=float, default=60.0,
                   help="seconds to wait for the run's first status.json")
    p.add_argument("extra", nargs=argparse.REMAINDER, help="-- further pgg_game.py options")
    p.set_defaults(fn=cmd_start)

    p = sub.add_parser("status", help="read status.json (files only)")
    where(p)
    p.add_argument("--json", action="store_true")
    p.add_argument("--stale-after", type=float,
                   help="heartbeat age (s) above which the run is reported stale "
                        "(default 3 x interval + 15)")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("stop", help="SIGTERM (or stop_request.json) to the running run")
    where(p)
    p.add_argument("--via-file", action="store_true",
                   help="only write stop_request.json (no signal)")
    p.add_argument("--force", action="store_true", help="skip the lock-file pid check")
    p.add_argument("--wait", type=float, default=0.0,
                   help="seconds to wait for state ended")
    p.set_defaults(fn=cmd_stop)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
