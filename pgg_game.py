"""
Public goods game engine: repeated group game plus an isolated schedule arm.

Fixed frame (kararlar.md; notes/BACKGROUND.md §4, after Herrmann, Thöni &
Gächter 2008): groups of 4, 10 rounds, 20 points per round, MPCR 0.4,
contributions are integers 0..20,

    earnings_i = 20 - c_i + 0.4 * sum(c)

Conditions
  N  no punishment (the pilot uses only this one).
  P  punishment 1:3. After the contributions are revealed every player may
     assign 0..10 punishment points to each other player. A point costs the
     punisher 1 and the target 3. Contribution step and punishment step are
     separate calls. Coded and tested, not used by the pilot.

Arms
  group     homogeneous groups: 4 agents, same card + style, 10 rounds. A
            call is stateless: the whole history of the agent's own game goes
            into the prompt. Within a round the calls only see earlier
            rounds, so their order (or running them in parallel, --workers)
            cannot leak a decision.
  isolated  conditional contribution schedule without any group interaction:
            "if the others contributed on average 0 / 5 / 10 / 15 / 20, how
            much would you contribute?". Condition N only. isolated_frame
            "one_shot": one round, "There is no history and no other round";
            "repeated": a round (neither first nor last) of the 10-round game,
            given the others' mean of the previous round.

Design choices
  * Isolated schedule = ONE CALL PER VALUE (5 calls per cell and
    repetition), not one call with five answers. Reasons: (1) in one call the
    model sees all five conditions at once and tends to draw one internally
    consistent, monotone curve, i.e. each answer is anchored on the others,
    whereas the response function is what we want to measure; (2) an invalid
    value is re-requested alone and counted on its own row (n_invalid per
    value); (3) it is what the pilot scenario of maliyet_analizi.md prices
    (60 isolated calls per model = 6 cells x 2 repetitions x 5 values, 630
    input tokens each). Cost: the rules are re-sent five times; ~7-9 % of the
    estimated pilot cost (tahmin). --dry-run counts exactly this.
  * The identity description is a parameter, never in this code. A card is
    {card_id, style, text}: `text` is the complete description (identity AND
    style are written together, as in the 12-card design of kararlar.md) and
    goes into the system message; `style` is only a label for the output.
    Cards come from a JSON file (--cards) or the API. Homogeneous group =
    the same card for all 4 agents.
  * No numeric disposition score appears anywhere: prompts are built here
    from the rules only, and card texts that look like a score ("7/10",
    "fairness 7", "score: 3") are rejected (heuristic guard, check_card_text).
  * Players are referred to by a fixed number within a game. With punishment
    a player is told only the TOTAL number of points received, not who
    assigned them (assumption, to be confirmed against the Herrmann
    instructions); punishment spending is capped by the player's total
    earnings of the round (before punishment); final earnings are not
    clamped at zero.
  * Labels in the prompts: "earnings from the project" is only
    0.4 x (sum of contributions); "total earnings" of a round is
    20 - c + 0.4 x (sum of contributions). Rules and history use both.
  * Every answer carries a short `rationale` string (written after the
    decision; --no-rationale removes it) so that models without native
    reasoning text (e.g. gemini-2.5-flash-lite) can still be read after the
    pilot. Only the decision field is validated. Native reasoning text of
    the response goes to `reasoning` when the provider returns it.
  * Every call goes through llm_client.call_llm_valid(return_parse_fail=True).
    Payloads outside the schema (25, "abc", 12.0, true, missing key, wrong
    keys, over budget) are re-requested and counted in n_invalid; broken
    JSON is counted in n_parse_fail. Nothing is ever defaulted or coded. If
    the retry limit is exceeded the run stops with RunAborted and an
    "pgg_run_aborted" event goes to logs/raw_calls.jsonl.
  * Seed = llm_client.stable_seed("pgg", run, model, card, style, ...) (crc32,
    never hash()), recorded on every row as the identifier of the call cell.
    It is NOT sent to the API: llm_client has no seed pass-through, and
    re-sending one seed on a re-request could return the same invalid
    payload.
  * temperature is not sent (rows say "default"); reasoning_effort and
    max_tokens are configurable and written to every row.
  * Rows are written when a round (both steps) is complete, because earnings
    are part of the row; an aborted round is only in the raw log.
  * A decision of the isolated arm has round = null, agent_id = 1 and
    others_mean = the conditioning value.
  * Every row carries the length of its card text, card_n_words (whitespace-
    separated words) and card_n_chars (characters): card length differs
    between styles and is a covariate (prereg_pilot.md amendment, A6 item 9).

Run guards (prereg_pilot.md §8; all off by default, configs/pilot.json turns
them on). They are checked before EVERY attempt, retries included, through
llm_client's before_call / on_response hooks:
  budget_usd        hard cap on the accumulated usage.cost of every response
                    that arrived (also re-requested and unparseable ones).
                    When reached, no new call is sent; the run stops with
                    RunStopped and a "pgg_run_stopped" event. Calls already in
                    flight finish, so the total can overshoot by at most their
                    cost (keep parallel_units x workers small). A response
                    without usage.cost is priced from its tokens with
                    pgg_cost.PRICES_USD_PER_M and counted (n_cost_estimated).
  invalid_rate_cap  per model: n_invalid + n_parse_fail above this fraction of
                    the planned calls (540 x 0.05 = 27 in the pilot) stops that
                    model only ("pgg_model_stopped"); the others go on.
  stop_on_length    the first finish_reason "length" stops the run.
  check_snapshot    a response whose model differs from the requested slug
                    (other than a "-<suffix>") stops the run.
  providers         per model {"slug", "name"[, "quantizations"]}: sent as
                    OpenRouter provider routing (order + only = [slug],
                    allow_fallbacks false, require_parameters true: the
                    provider must support every parameter of the request).
                    Every response's provider name (and quantization, if the
                    response has one) goes to the raw log and the row.
                    A response without a provider name does not stop the
                    run; it is counted as n_provider_unknown (per model and
                    in total in the summary).
  provider mismatch (A4) a response whose provider name is not "name" is NOT
                    a decision: llm_client logs it as a failed attempt
                    (error_kind "provider_mismatch", "provider_mismatch":
                    true, its content and usage), its cost goes into the cost
                    and the budget, and the same decision is re-requested.
                    Counted as n_provider_mismatch on the row (re-requests of
                    that decision), per model, per segment and in total.
                    Outside the invalid-rate cap. Limit: the attempt limit of
                    one llm_client call (max_retries = 4 attempts, shared with
                    parse failures, provider errors and transport errors);
                    when its last attempt is a mismatch too, the run stops
                    with stop_reason "provider_mismatch_limit" (RunAborted).
                    THIS CHANGES prereg_pilot.md §8.2 item 5, which stopped
                    the run at the first mismatch (stop_reason
                    "provider_mismatch"); the amendment is written apart.
Provider errors (finish_reason "error", or 0 tokens at 0 cost) are retried and
counted as n_provider_error, apart from n_parse_fail and outside the
invalid-rate cap. A RunAborted (no valid decision for one call) also stops
the other units. Units = one group game or one isolated schedule;
parallel_units of them run at the same time, each with its own `workers`.
Run order: shuffled round-robin over the cells (card x model), keyed by
stable_seed(seed_namespace, run, "order", ...): every block of len(cards)
units has every card, so a run stopped early still has data from every card.
The order is in the "pgg_run_start" raw-log event and the summary. Rows of a
stopped (incomplete) round are not written. At the end <run>_summary.json
holds per-model cost, response counts, invalid / parse / provider-error
counts, the stop reason and the output files with their line counts
("pgg_run_end" event in the raw log).

Output: <runs_dir>/<run>/ with <run>.jsonl (one row per decision, never
overwritten: an existing file is an error), <run>_summary.json and
raw_calls.jsonl. runs_dir must be an absolute, existing directory outside the
git worktree (worktrees are deleted after merging, with their git-ignored
outputs); CLI: --runs-dir, else config "runs_dir", else $PGG_RUNS_DIR, else
<orc project>/workspace/runs when run from an orc worktree; otherwise the
run does not start. Config values starting with "<" are placeholders (e.g.
"<TBD_PREREG: ...>"), in any setting: a real run does not start while one is
left. --dry-run prints call counts and an estimated cost without importing
llm_client (no key, no ../.env, no API); when a setting the counts depend on
is still a placeholder it says so instead of counting.

Pre-registration lock. A config with "prereg_approved" (configs/minipilot.json)
starts a real run (also --resume) only when it is exactly true, i.e. after the
user approved its prereg_*.md; otherwise the run stops before llm_client is
imported and before any call. Dry runs (also --resume --dry-run) still work.
A config without the field (configs/pilot.json, approved 2026-10-05) is not
gated by it. The config may also hold the run name ("run"; --run wins).

Models: llm_client.MODELS (= pgg_cost.PILOT_MODELS) is the mini-pilot set and
the default; a run may name any model of llm_client.MODELS_KNOWN, which also
holds pilot v2's gemini (MODELS_PILOT_V2), so configs/pilot.json still runs.

Resume (--resume; Engine.run(resume=True)). A run that was cut off goes on in
the same directory as a new segment (0 = the first run, then 1, 2, ...). The
results file is opened for appending only; no earlier byte is changed.
  * Unit = one group game or one isolated schedule, labelled as in unit_order
    ("gpt|boston_value|value|N|group|0"). Rows are matched to units by their
    session_id (deterministic); rows of the first run, which have no
    "segment" field, are segment 0. A ROUND of a group game is complete in a
    segment when that segment holds all its rows (every agent, contribute,
    plus punish under P); an isolated schedule is one block (every
    conditioning value).
  * Valid rows of a unit (_unit_chain): the segments are read in order; a
    segment's rows of the unit start at some round j and replace the rounds
    >= j accepted from earlier segments (this code always starts at the
    first round not yet accepted; the code before A1 re-ran a unit from round
    1, so its re-runs replace the earlier rows). From j on, complete rounds
    are accepted in order; the first incomplete round and everything after it
    in that segment are superseded. A unit is COMPLETE when every round is
    accepted. Analysis rule: a row counts only if it is accepted
    (Engine.valid_rows); the summary lists every other row in
    "superseded_rows" as {"unit", "segment", "rounds", "n_rows"}.
  * Complete units are skipped. A group game with accepted rounds goes on
    from its first round not accepted (round-level resume): its history
    (contributions, and punishments under P) is rebuilt from the accepted
    rows, the earnings are recomputed with the game rules and compared with
    the stored ones, so the prompts equal those of an uninterrupted run.
    Seeds are stable_seed(..., agent, round, step), so a resumed round has
    the seeds it would have had. "resume_points" (summary, raw-log event)
    names every unit that goes on and its round. An isolated schedule with
    rows but not complete is run again whole (its values have no history and
    its rows are written together, so at most its 5 calls are repeated).
  * Budget and invalid-rate cap go on from the earlier segments: their cost
    and counts are rebuilt from the run's raw log (every billed response is
    logged there, also when no summary was written), else taken from the
    previous summary; if the summary shows more cost, the difference is added.
    A model already over the invalid-rate cap stays stopped.
  * Before any call or write, the run's config (models, providers,
    seed_namespace, max_tokens, isolated_frame, reasoning_effort, guards,
    design and card texts) is compared with the previous summary's "config"
    (older summaries: their top-level fields, the unit order, the card
    lengths of the rows and the card texts in the raw log). Any difference,
    or a row that does not fit the design, stops with ValueError.
  * The previous summary is kept as <run>_summary.seg<k>.json (k = the last
    segment it describes) before the new one replaces it; the new summary has
    the totals, a "segments" list and the complete / remaining unit counts.
  * Discarded responses: an accepted (valid) decision that never became a row
    (its round was given up by a stop, a signal or an abort; it arrived
    after that; or its row could not be written) is logged as a
    "pgg_discarded" event with "discarded": true, its "call" (segment, step,
    round, agent_id, others_mean) and a reason. Every raw-log record of a
    call carries the same "call". On resume the run's raw log is compared
    with the rows: an accepted response without a row that has no such event
    yet (e.g. the process was killed) gets one now (reason
    "found_on_resume"; records of the earlier code are matched by their
    prompt). n_discarded is counted per model and segment; the responses
    stay in the cost and the budget.
  * A last line cut off while being written (no newline, not JSON) stays in
    the results file; before new rows are appended after a newline, it is
    recorded in <run>.partial.jsonl (line number, byte offset, length,
    sha256, text). Every later scan ignores exactly the recorded lines (any
    other broken line is an error) and the summary reports them
    ("truncated_lines"). A raw log that ends without a newline gets one
    before the segment's first record.
  * --resume --dry-run prints the plan (units complete / partial / left,
    calls left, cost so far) without writing anything and without llm_client.
Run lock. run() (new or resumed) first creates <output dir>/<run>.lock with
O_EXCL, holding the PID, host and start time; it is removed when the run ends
(also after a signal, a stop or an error). A lock whose PID is alive on this
host (os.kill(pid, 0)) stops the run with RunLocked before anything is
written; a lock of a dead PID is stale: it is taken over, logged
("pgg_stale_lock_taken_over") and reported in the summary ("lock").
SIGINT and SIGTERM stop the run with stop_reason "interrupted": the summary is
written at once, then once more after the calls in flight have ended.

Hangs. Every HTTP attempt has a wall-clock deadline, request_deadline_s
(default llm_client.DEFAULT_REQUEST_DEADLINE_S = 900 s; config / CLI
--request-deadline): past it the attempt is abandoned, logged as a transport
error with error_subkind "deadline" and retried. Its record holds what had
arrived of the response ("response_partial"; usage, content and cost when the
body was whole) and "cost_unknown"; a known cost goes into the cost and the
budget (deadline_cost_usd), an unknown one is counted (n_cost_unknown); such a
response is never a decision. Units run in a thread pool (parallel_units
threads, also when it is 1) while the main thread watches the run's raw log:
when no record (response, error or event) has been written to it for
stall_timeout_s (default DEFAULT_STALL_TIMEOUT_S = 1800 s; config / CLI
--stall-timeout), the run stops with stop_reason "stalled" without waiting
for the calls in flight; the summary is written and the run can go on with
--resume. Both settings are outside the "config" record, but --resume
compares them with the last earlier segment that recorded them (segments of
the code before #46 recorded none: not compared): a difference stops before
any call, unless allow_timeout_change (CLI --allow-timeout-change); an allowed
change is in the segment entry and in "timeout_changes" of the summary.
workers, parallel_units and request_timeout_s may differ between segments.
Every segment's summary entry records the settings and the code version (git
commit and sha256 of the code files).

Code version (A5). code_version() is recorded in every segment entry and
start event and its git_commit is never empty for a real run:
  * code directory = top of a git checkout: git_commit = HEAD; the code is
    dirty when `git status --porcelain --untracked-files=no -- '*.py'` shows
    a tracked .py file changed (source "git").
  * else (e.g. a copy unpacked with git archive into workspace/_kod_<sha>/):
    CODE_VERSION.json in the code directory, written from the git checkout
    with
        git archive <sha> | tar -x -C <dir>
        python pgg_game.py --write-code-version <dir> --code-commit <sha>
    It holds the commit and the sha256 of every tracked .py file of that
    commit (write_code_version checks them against <dir> before writing).
    On every start the hashes are checked again; a missing or changed file
    makes the code dirty (source "stamp", stamp_problems).
  * A real run and --resume do not start when the version is unknown (no
    git checkout, no stamp) or the code is dirty: ValueError / exit 1 before
    the lock, any write and any call. There is no option to override it. A
    dry run (also --resume --dry-run) only prints a warning.
  * --resume records, never refuses, a git_commit other than (or unknown in)
    the earlier segments': "code_change" in the segment entry and in the
    start event, "code_changes" in the summary.

Per row and summary (A2, A3). Every row has elapsed_s (seconds of the accepted
attempt), n_transport and n_deadline (connection errors and attempts past the
deadline while the decision was obtained) and reasoning_capped:
reasoning_tokens >= max_tokens (of the row) - llm_client.REASONING_RESERVE_TOKENS
(4096), null without reasoning_tokens. pilot_v2_20261005: 10 of DeepSeek's
answers stopped reasoning at exactly 11 904 tokens with finish_reason "stop".
Such answers are flagged, kept and not re-requested (re-requesting would
select on the length of the reasoning). The summary (per model, per segment
and in total) counts n_reasoning_capped, n_transport, n_deadline,
n_cost_unknown and deadline_cost_usd.
"""

from __future__ import annotations

import argparse
import dataclasses
import functools
import hashlib
import json
import math
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import zlib
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path

import pgg_cost

PROJECT_DIR = Path(__file__).parent
RUNS_DIR_ENV = "PGG_RUNS_DIR"

CONDITIONS = ("N", "P")
ARMS = ("group", "isolated")
# OpenRouter's reasoning.effort values. Which of them a given model accepts is
# not verified (maliyet_analizi.md §7 question 2).
REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh")
ISOLATED_POINTS = (0, 5, 10, 15, 20)
ISOLATED_FRAMES = ("one_shot", "repeated")
# provider.quantizations values of OpenRouter's provider routing (OpenAPI
# schema "Quantization", https://openrouter.ai/openapi.json).
QUANTIZATIONS = ("int4", "int8", "fp4", "mxfp4", "nvfp4", "fp6", "fp8", "mxfp8",
                 "fp16", "bf16", "fp32", "unknown")
# Seconds without any raw-log record after which a run stops as "stalled".
# Keep it well above request_deadline_s (default 900 s): one attempt may take
# that long.
DEFAULT_STALL_TIMEOUT_S = 1800.0
# Operational limits compared with the previous segment on --resume (a
# difference needs allow_timeout_change / --allow-timeout-change).
TIMEOUT_SETTINGS = ("request_deadline_s", "stall_timeout_s")
# Files whose sha256 goes into code_version().
CODE_FILES = ("pgg_game.py", "llm_client.py", "pgg_cost.py")
# Version stamp of a code directory outside git (A5, write_code_version).
CODE_VERSION_FILE = "CODE_VERSION.json"
# A real run and --resume refuse code whose version is unknown or dirty
# (code_version_problem). Tests of other parts set it False (mock.patch);
# there is deliberately no CLI option or config key for it.
_REQUIRE_VERIFIED_CODE = True
# A config value the user still has to choose, e.g. "<SEÇİLECEK: ...>". A
# real run does not start while one is left (dry runs only warn).
PLACEHOLDER_PREFIX = "<"


def is_placeholder(value) -> bool:
    return isinstance(value, str) and value.strip().startswith(PLACEHOLDER_PREFIX)


def placeholders_in(value, path: str) -> list[str]:
    """Paths of every placeholder string inside a (nested) config value."""
    if is_placeholder(value):
        return [path]
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in placeholders_in(v, f"{path}.{k}")]
    if isinstance(value, (list, tuple)):
        return [p for i, v in enumerate(value) for p in placeholders_in(v, f"{path}[{i}]")]
    return []


def _llm():
    """llm_client, imported on first use: importing it needs the API key."""
    import llm_client
    return llm_client


@functools.lru_cache(maxsize=1)
def _code_version() -> str:
    return json.dumps(_read_code_version())


def code_version() -> dict:
    """Version of the code that runs (A5): git commit, whether it is dirty, and how it is known.

    Read once per process (the code that runs is the code imported at the
    start). See _read_code_version; code_version_problem() says whether a
    real run may start with it.
    """
    return json.loads(_code_version())


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(cwd: Path, *args, binary: bool = False, strip: bool = True):
    """stdout of a git command in cwd (text, stripped unless strip=False; bytes if binary).

    None when git fails or is missing.
    """
    try:
        proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True,
                              text=not binary, timeout=30,
                              env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout if binary or not strip else proc.stdout.strip()


def _is_git_top(path: Path) -> bool:
    """True if path is the top directory of a git checkout (also a linked worktree)."""
    top = _git(path, "rev-parse", "--show-toplevel")
    return top is not None and Path(top).resolve() == Path(path).resolve()


def _read_code_version(code_dir: Path | None = None) -> dict:
    """git_commit, git_dirty, source and files_sha256 (CODE_FILES) of a code directory.

    source "git": code_dir is the top of a git checkout; git_commit = HEAD,
    git_dirty = `git status --porcelain --untracked-files=no -- '*.py'` shows
    a change of a tracked .py file (dirty_files lists them; None if git
    status failed). source "stamp": no git checkout, but code_dir holds
    CODE_VERSION_FILE (write_code_version); every file it lists must exist
    with its sha256 and it must list CODE_FILES, else git_dirty is True and
    stamp_problems says why; git_commit is the stamp's. source None: neither;
    git_commit and git_dirty are None.
    """
    code_dir = Path(code_dir or PROJECT_DIR)
    out = {"git_commit": None, "git_dirty": None, "source": None, "code_dir": str(code_dir),
           "files_sha256": {name: _sha256_file(code_dir / name)
                            for name in CODE_FILES if (code_dir / name).is_file()}}
    if _is_git_top(code_dir):
        out["source"] = "git"
        out["git_commit"] = _git(code_dir, "rev-parse", "HEAD")
        status = _git(code_dir, "status", "--porcelain", "--untracked-files=no", "--", "*.py",
                      strip=False)              # "XY path": the leading blank counts
        if status is not None:
            out["dirty_files"] = sorted(line[3:] for line in status.splitlines() if line.strip())
            out["git_dirty"] = bool(out["dirty_files"])
        return out
    stamp_path = code_dir / CODE_VERSION_FILE
    if not stamp_path.is_file():
        return out
    out.update(source="stamp", stamp_path=str(stamp_path))
    problems = []
    try:
        stamp = json.loads(stamp_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        stamp = None
        problems.append(f"{CODE_VERSION_FILE} cannot be read ({e})")
    if stamp is not None:
        commit = stamp.get("git_commit") if isinstance(stamp, dict) else None
        files = stamp.get("files_sha256") if isinstance(stamp, dict) else None
        if isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit):
            out["git_commit"] = commit
        else:
            problems.append(f"{CODE_VERSION_FILE}: git_commit is not a 40-digit commit id")
        if not isinstance(files, dict) or not files:
            problems.append(f"{CODE_VERSION_FILE}: files_sha256 is missing or empty")
            files = {}
        missing = [n for n in CODE_FILES if n not in files]
        if missing:
            problems.append(f"{CODE_VERSION_FILE} does not cover {missing}")
        for name, sha in sorted(files.items()):
            rel = Path(name)
            if rel.is_absolute() or ".." in rel.parts:
                problems.append(f"{CODE_VERSION_FILE}: path {name!r} is not inside the directory")
            elif not (code_dir / rel).is_file():
                problems.append(f"{name}: listed in {CODE_VERSION_FILE}, missing")
            elif _sha256_file(code_dir / rel) != sha:
                problems.append(f"{name}: sha256 differs from {CODE_VERSION_FILE}")
        out["n_files_verified"] = len(files) if not problems else None
    out["git_dirty"] = bool(problems)
    if problems:
        out["stamp_problems"] = problems
    return out


def code_version_problem(cv: dict) -> str | None:
    """Why a real run (or --resume) may not start with this code version; None if it may."""
    where = cv.get("code_dir", "the code directory")
    if cv.get("source") is None:
        return (f"the code version is unknown: {where} is not the top of a git checkout and has "
                f"no {CODE_VERSION_FILE} (write it with python pgg_game.py --write-code-version "
                "<dir> --code-commit <sha>, from the git checkout)")
    if cv.get("source") == "git" and cv.get("git_commit") is None:
        return f"git HEAD of {where} could not be read"
    if cv.get("source") == "stamp" and cv.get("git_dirty") is not False:
        return (f"{CODE_VERSION_FILE} does not match the code: "
                + "; ".join(cv.get("stamp_problems") or ["not verified"]))
    if cv.get("git_dirty") is None:
        return "git status could not be read: whether the code is dirty is unknown"
    if cv.get("git_dirty"):
        return (f"the code is dirty: tracked .py files differ from commit {cv.get('git_commit')} "
                f"({', '.join(cv.get('dirty_files') or [])}); commit them first")
    return None


def write_code_version(target_dir, commit: str = "HEAD", repo_dir: Path | None = None) -> Path:
    """Write CODE_VERSION_FILE into a code directory copied out of git (A5).

    For a code directory that is not a git checkout, e.g. the one a builder
    unpacks with `git archive <sha> | tar -x -C workspace/_kod_<sha>`. Run in
    the git checkout (repo_dir, default this code's directory):

        python pgg_game.py --write-code-version workspace/_kod_<sha> --code-commit <sha>

    The stamp holds the commit and the sha256 of every tracked .py file of
    that commit (`git ls-tree`, blobs as committed). Each must equal the
    file in target_dir, else ValueError and nothing is written. An existing
    stamp with the same commit and hashes is kept; another one is an error.
    """
    repo_dir = Path(repo_dir or PROJECT_DIR)
    target = Path(target_dir).resolve()
    if not target.is_dir():
        raise ValueError(f"{target} is not a directory")
    if _is_git_top(target):
        raise ValueError(f"{target} is a git checkout: its HEAD is the code version, no stamp")
    sha = _git(repo_dir, "rev-parse", "--verify", f"{commit}^{{commit}}")
    if sha is None:
        raise ValueError(f"{commit!r} is not a commit of the git checkout {repo_dir}")
    names = _git(repo_dir, "ls-tree", "-r", "--name-only", sha)
    files = {}
    problems = []
    for name in sorted((names or "").splitlines()):
        if not name.endswith(".py"):
            continue
        blob = _git(repo_dir, "show", f"{sha}:{name}", binary=True)
        if blob is None:
            raise ValueError(f"cannot read {name} of commit {sha}")
        files[name] = hashlib.sha256(blob).hexdigest()
        path = target / name
        if not path.is_file():
            problems.append(f"{name} missing")
        elif _sha256_file(path) != files[name]:
            problems.append(f"{name} differs")
    missing = [n for n in CODE_FILES if n not in files]
    if missing:
        problems.append(f"commit {sha} has no {missing}")
    if problems:
        raise ValueError(f"{target} does not hold the tracked .py files of commit {sha}: "
                         + "; ".join(problems) + f". {CODE_VERSION_FILE} not written")
    stamp = {"git_commit": sha, "files_sha256": files,
             "written_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "written_by": "pgg_game.write_code_version"}
    path = target / CODE_VERSION_FILE
    if path.exists():
        try:
            old = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            old = None
        if (isinstance(old, dict) and old.get("git_commit") == sha
                and old.get("files_sha256") == files):
            return path
        raise ValueError(f"{path} exists with another commit or other hashes; not overwritten")
    with open(path, "x", encoding="utf-8") as f:
        f.write(json.dumps(stamp, indent=2) + "\n")
    return path


def _offline_stable_seed(namespace: str, *parts, base: int = 0) -> int:
    """Copy of llm_client.stable_seed (crc32) for dry runs, which must not import
    llm_client; a test checks that both agree."""
    key = "|".join([namespace, *map(str, parts)])
    return base + zlib.crc32(key.encode()) % 1_000_000


def _offline_reasoning_capped(usage, max_tokens: int) -> bool | None:
    """Copy of llm_client.reasoning_capped for dry runs; a test checks that both agree."""
    details = usage.get("completion_tokens_details") if isinstance(usage, dict) else None
    n = details.get("reasoning_tokens") if isinstance(details, dict) else None
    if not isinstance(n, int) or isinstance(n, bool):
        return None
    return n >= max_tokens - OfflineLLM.REASONING_RESERVE_TOKENS


class OfflineLLM:
    """What a read-only resume plan (--resume --dry-run) needs of llm_client.

    No key, no ../.env, no API; the constants equal llm_client's (a test
    checks it). Writing a log is an error.
    """
    DEFAULT_MAX_TOKENS = 16000
    DEFAULT_TIMEOUT_S = 300.0
    DEFAULT_REQUEST_DEADLINE_S = 900.0
    REASONING_RESERVE_TOKENS = 4096
    LOG_PATH = None
    stable_seed = staticmethod(_offline_stable_seed)
    reasoning_capped = staticmethod(_offline_reasoning_capped)

    @staticmethod
    def reasoning_effort_label(reasoning_effort):
        return "default" if reasoning_effort is None else reasoning_effort

    @staticmethod
    def _append_log(record, path=None):
        raise RuntimeError("offline: a dry run writes no log")


class RunAborted(RuntimeError):
    """A decision could not be obtained validly; the run was stopped.

    reason: the run's stop_reason, "run_aborted", or "provider_mismatch_limit"
    when the last attempt of the failed call was a provider mismatch (A4).
    """

    def __init__(self, message: str, reason: str = "run_aborted"):
        super().__init__(message)
        self.reason = reason


# Not RuntimeError subclasses: Engine._ask turns RuntimeError into RunAborted.
class RunStopped(Exception):
    """A run guard (budget, finish_reason length, snapshot) stopped the run."""


class ModelStopped(Exception):
    """The invalid-rate cap stopped this model; other models go on."""


# A BaseException, like KeyboardInterrupt: llm_client's `except Exception`
# must not retry it as a failed attempt.
class RunInterrupted(BaseException):
    """SIGINT or SIGTERM arrived (raised in the main thread)."""


class RunLocked(Exception):
    """Another live process holds the run's lock; nothing was called or written."""


# --------------------------------------------------------------------------
# Run lock
# --------------------------------------------------------------------------

# A lock file that cannot be read is taken as being written by its creator
# for this long (between O_EXCL and the write), and as stale after it.
LOCK_UNREADABLE_GRACE_S = 5.0


def _pid_alive(pid) -> bool:
    """os.kill(pid, 0): True if a process with this PID exists (also another user's)."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def read_run_lock(path) -> dict | None:
    """The lock file's content plus "state": "alive", "stale" or "unknown"; None if absent.

    "unknown": the lock is from another host (its PID cannot be checked here)
    or it cannot be read yet (just created); a run does not start on it.
    """
    path = Path(path)
    try:
        data = path.read_bytes()
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        return None
    try:
        info = json.loads(data)
        if not isinstance(info, dict):
            raise ValueError("not an object")
    except ValueError:
        young = time.time() - mtime < LOCK_UNREADABLE_GRACE_S
        return {"unreadable": True, "n_bytes": len(data), "state": "unknown" if young else "stale"}
    if info.get("host") not in (None, socket.gethostname()):
        return {**info, "state": "unknown"}
    return {**info, "state": "alive" if _pid_alive(info.get("pid")) else "stale"}


def acquire_run_lock(path) -> dict:
    """Create the lock file (O_EXCL) or take over a stale one; RunLocked if it is held.

    Returns {"path", "pid", "host", "started_at", "started_at_utc",
    "stale_lock"}; stale_lock is the content of a lock taken over (its PID
    was dead), else None. Two processes that find the same stale lock at the
    same instant are not excluded from each other (a known, narrow race).
    """
    path = Path(path)
    stale = None
    for _ in range(5):
        now = time.time()
        info = {"pid": os.getpid(), "host": socket.gethostname(), "started_at": now,
                "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))}
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            held = read_run_lock(path)
            if held is None:
                continue                       # removed meanwhile: try again
            if held["state"] != "stale":
                who = (f"PID {held.get('pid')} on {held.get('host')}, started "
                       f"{held.get('started_at_utc')}" if not held.get("unreadable")
                       else "a lock file that is being written")
                raise RunLocked(
                    f"run directory is locked by {who} ({held['state']}): {path}. Another "
                    "process is running or resuming this run; nothing was called or written. "
                    "If that process is certainly gone, delete the lock file.")
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            stale = {k: v for k, v in held.items() if k != "state"}
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(info) + "\n")
        return {"path": str(path), **info, "stale_lock": stale}
    raise RunLocked(f"could not take the lock {path}")


def release_run_lock(lock: dict | None) -> None:
    """Remove the lock file if it is still this lock (same PID and start time)."""
    if not lock:
        return
    path = Path(lock["path"])
    held = read_run_lock(path)
    if held and held.get("pid") == lock["pid"] and held.get("started_at") == lock["started_at"]:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


# --------------------------------------------------------------------------
# Game rules (pure functions)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class GameParams:
    group_size: int = 4
    rounds: int = 10
    endowment: int = 20
    mpcr: float = 0.4
    punish_cost: int = 1      # points the punisher pays per punishment point
    punish_impact: int = 3    # points the target loses per punishment point
    max_punish: int = 10      # most punishment points to one target


def project_payoffs(params: GameParams, contributions: list[int]) -> list[float]:
    """Total round earnings, before punishment: endowment - c_i + mpcr * sum(c).

    (The name is kept for compatibility; the earnings from the project alone
    are project_share.)
    """
    total = sum(contributions)
    return [round(params.endowment - c + params.mpcr * total, 9) for c in contributions]


def project_share(params: GameParams, contributions: list[int]) -> float:
    """Earnings from the project, the same for every player: mpcr * sum(c)."""
    return round(params.mpcr * sum(contributions), 9)


def apply_punishment(params: GameParams, earnings: list[float], points: list[list[int]]):
    """Final earnings after punishment; points[i][j] = points i assigns to j.

    Returns (final, cost_paid, received_points): the punisher pays punish_cost
    per assigned point, the target loses punish_impact per received point.
    """
    n = len(earnings)
    cost_paid = [sum(points[i]) * params.punish_cost for i in range(n)]
    received = [sum(points[i][j] for i in range(n)) for j in range(n)]
    final = [round(earnings[j] - cost_paid[j] - received[j] * params.punish_impact, 9)
             for j in range(n)]
    return final, cost_paid, received


def is_valid_contribution(payload, params: GameParams) -> bool:
    """Only an integer 0..endowment is a decision (no bool, float or string)."""
    if not isinstance(payload, dict):
        return False
    return _is_int_in(payload.get("contribution"), 0, params.endowment)


def is_valid_punishment(payload, params: GameParams, targets: list[int], budget: int) -> bool:
    """Exactly one integer 0..max_punish per target, total cost within budget."""
    if not isinstance(payload, dict):
        return False
    pun = payload.get("punishments")
    if not isinstance(pun, dict) or set(pun) != {str(t) for t in targets}:
        return False
    if not all(_is_int_in(v, 0, params.max_punish) for v in pun.values()):
        return False
    return sum(pun.values()) * params.punish_cost <= budget


def _is_int_in(value, lo: int, hi: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and lo <= value <= hi


# --------------------------------------------------------------------------
# Cards
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Card:
    card_id: str
    style: str
    text: str


# Heuristic guard against numeric disposition scores on cards (CLAUDE.md).
_SCORE_PATTERNS = (
    re.compile(r"\d\s*/\s*\d"),                                       # 7/10
    re.compile(r"\d\s*(?:out of|von)\s*\d", re.I),                    # 7 out of 10
    re.compile(r"(?:score|rating|salience|skor|puan)\w*\s*(?:of|is|at)?\W{0,3}\d", re.I),
    re.compile(r"\d\W{0,3}(?:score|rating|skor|puan)", re.I),
)


def check_card_text(text: str) -> None:
    """Raise ValueError if the card text looks like it carries a numeric score."""
    for pattern in _SCORE_PATTERNS:
        m = pattern.search(text)
        if m:
            raise ValueError(
                f"card text looks like a numeric disposition score ({m.group(0)!r}); "
                "numeric scores are not allowed on cards")


def load_cards(path: str | Path, cities=None) -> list[Card]:
    """Cards from a JSON list of {"card_id", "style", "text"} objects.

    Other keys (e.g. "city") are allowed and ignored, except that with
    `cities` only the cards whose "city" is in it are kept; then every card
    needs a "city" and every requested city at least one card.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{path}: expected a non-empty JSON list of cards")
    if cities is not None:
        cities = list(cities)
        no_city = [e for e in raw if "city" not in e]
        if no_city:
            raise ValueError(f"{path}: filtering by city, but a card has no city: {no_city[0]!r}")
        unknown = set(cities) - {e["city"] for e in raw}
        if unknown:
            raise ValueError(f"{path}: no card for city {sorted(unknown)}")
        raw = [e for e in raw if e["city"] in cities]
    cards = []
    for entry in raw:
        missing = {"card_id", "style", "text"} - set(entry)
        if missing:
            raise ValueError(f"{path}: card without {sorted(missing)}: {entry!r}")
        cards.append(Card(str(entry["card_id"]), str(entry["style"]), str(entry["text"])))
    return validate_cards(cards)


def card_length(card: Card) -> dict:
    """Length of the card text: whitespace-separated words and characters."""
    return {"card_n_words": len(card.text.split()), "card_n_chars": len(card.text)}


def validate_cards(cards: list[Card]) -> list[Card]:
    seen = set()
    for card in cards:
        if not card.card_id or not card.style or not card.text.strip():
            raise ValueError(f"empty card_id, style or text: {card!r}")
        if (card.card_id, card.style) in seen:
            raise ValueError(f"duplicate card: {card.card_id}/{card.style}")
        seen.add((card.card_id, card.style))
        check_card_text(card.text)
    return cards


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------

def _num(x: float) -> str:
    """12.0 -> "12", 24.4 -> "24.4"."""
    return f"{round(x, 4):.4f}".rstrip("0").rstrip(".")


def _player(j: int) -> str:
    return f"Player {j + 1}"


def _label(j: int, me: int) -> str:
    return _player(j) + (" (you)" if j == me else "")


def system_message(card: Card) -> dict:
    return {"role": "system", "content": (
        "You are a participant in a decision-making experiment. "
        "The following describes you:\n" + card.text)}


def rules_text(params: GameParams, condition: str, *, single_round: bool = False) -> str:
    n, e = params.group_size, params.endowment
    lines = [
        "RULES",
        f"- A group has {n} players: you and {n - 1} others. Players cannot communicate.",
    ]
    if single_round:
        lines.append("- The game is played in rounds; this question is about one round.")
    else:
        lines.append(f"- The same {n} players stay together for all {params.rounds} rounds.")
    lines += [
        f"- In every round each player receives {e} points.",
        f"- Each player then decides how many of these points (a whole number from 0 to {e}) "
        "to contribute to a group project. Points that are not contributed stay with the player.",
        f"- Every point contributed to the project yields {_num(params.mpcr)} points "
        f"for each of the {n} players. Your earnings from the project in a round are therefore:",
        f"  {_num(params.mpcr)} x (sum of all {n} players' contributions)",
        "- Your total earnings in a round are the points you kept plus your earnings "
        "from the project:",
        f"  {e} - (your contribution) + {_num(params.mpcr)} x (sum of all {n} players' contributions)",
    ]
    if condition == "P":
        lines += [
            f"- After the contributions of a round are revealed, each player may assign "
            f"punishment points (0 to {params.max_punish}) to each other player. Each point "
            f"assigned costs the assigning player {_num(params.punish_cost)} point(s) and "
            f"reduces the earnings of the receiving player by {_num(params.punish_impact)} points. "
            "A player is told only the total number of punishment points received, "
            "not who assigned them.",
        ]
    if not single_round:
        lines.append("- After each round you are told every player's contribution and your own earnings.")
    return "\n".join(lines)


@dataclass
class RoundRecord:
    round: int
    contributions: list[int]
    round_earnings: list[float]                 # total, before punishment (project_payoffs)
    punishment: list[list[int]] | None = None   # punishment[i][j]: i -> j
    cost_paid: list[float] | None = None
    received: list[int] | None = None
    final_earnings: list[float] | None = None


def _contributions_line(rec_contributions: list[int], me: int) -> str:
    listing = "; ".join(f"{_label(j, me)}: {c}" for j, c in enumerate(rec_contributions))
    return f"Contributions: {listing}. Group total: {sum(rec_contributions)}."


def history_text(params: GameParams, condition: str, history: list[RoundRecord], me: int) -> str:
    if not history:
        return "HISTORY\nThis is the first round; there is no history yet."
    lines = ["HISTORY OF PREVIOUS ROUNDS"]
    for rec in history:
        lines.append(f"Round {rec.round}")
        lines.append("  " + _contributions_line(rec.contributions, me))
        lines.append(f"  Your earnings from the project: "
                     f"{_num(project_share(params, rec.contributions))}. "
                     f"Your total earnings this round: {_num(rec.round_earnings[me])}.")
        if condition == "P":
            given = ", ".join(f"{_label(j, me)}: {p}" for j, p in enumerate(rec.punishment[me]) if p)
            lines.append(f"  Punishment points you assigned: {given or 'none'} "
                         f"(cost to you: {_num(rec.cost_paid[me])}).")
            lines.append(f"  Punishment points you received: {rec.received[me]} "
                         f"(points lost: {_num(rec.received[me] * params.punish_impact)}).")
            lines.append(f"  Your earnings after punishment: {_num(rec.final_earnings[me])}.")
    return "\n".join(lines)


def contribution_messages(params, condition, card, history, me, round_no) -> list[dict]:
    user = "\n\n".join([
        rules_text(params, condition),
        history_text(params, condition, history, me),
        f"ROUND {round_no} of {params.rounds}. You are {_player(me)}. "
        "All players decide at the same time, without seeing each other's choice for this round.\n"
        f"How many of your {params.endowment} points do you contribute to the group project? "
        f"(a whole number from 0 to {params.endowment})",
    ])
    return [system_message(card), {"role": "user", "content": user}]


def punishment_messages(params, card, history, me, round_no, contributions, earnings) -> list[dict]:
    budget = punishment_budget(earnings)
    user = "\n\n".join([
        rules_text(params, "P"),
        history_text(params, "P", history, me),
        f"ROUND {round_no} of {params.rounds}, punishment step. You are {_player(me)}.\n"
        f"This round: {_contributions_line(contributions, me)} "
        f"Your earnings from the project this round: {_num(project_share(params, contributions))}. "
        f"Your total earnings this round (before punishment): {_num(earnings)}.\n"
        f"You may now assign punishment points (0 to {params.max_punish}) to each other player. "
        f"A point costs you {_num(params.punish_cost)} and reduces the receiving player's earnings "
        f"by {_num(params.punish_impact)}. Your total cost may not exceed your total earnings "
        f"this round, so you can assign at most {budget // params.punish_cost} points in total. "
        "All players decide at the same time.",
    ])
    return [system_message(card), {"role": "user", "content": user}]


def isolated_messages(params, card, others_mean: int, frame: str = "one_shot") -> list[dict]:
    """One value of the conditional schedule.

    frame "one_shot": a single round with no history and no other round (the
    wording of the first engine). frame "repeated": a round of the
    params.rounds-round game, given the others' mean of the previous round.
    """
    n, e = params.group_size, params.endowment
    if frame == "one_shot":
        rules = rules_text(params, "N", single_round=True)
        question = (
            f"Consider one round. Suppose the other {n - 1} players of your group each contribute, "
            f"on average, {others_mean} points. There is no history and no other round.\n"
            f"How many of your {e} points do you contribute to the group project? "
            f"(a whole number from 0 to {e})")
    elif frame == "repeated":
        rules = rules_text(params, "N")
        question = (
            f"Consider a round of this {params.rounds}-round game that is neither the first nor "
            f"the last round. In the previous round the other {n - 1} players of your group "
            f"contributed, on average, {others_mean} points each.\n"
            f"How many of your {e} points do you contribute to the group project in this round? "
            f"(a whole number from 0 to {e})")
    else:
        raise ValueError(f"isolated_frame must be one of {ISOLATED_FRAMES}, got {frame!r}")
    user = "\n\n".join([rules, "QUESTION\n" + question])
    return [system_message(card), {"role": "user", "content": user}]


def punishment_budget(earnings: float) -> int:
    """Whole points a player can pay for: the round's total earnings before punishment."""
    return int(earnings // 1)


def contribution_schema(params: GameParams, rationale: bool) -> dict:
    props = {"contribution": {"type": "integer", "minimum": 0, "maximum": params.endowment}}
    if rationale:
        props["rationale"] = {"type": "string",
                              "description": "One or two sentences on why you chose this."}
    return {"type": "object", "required": ["contribution"], "properties": props}


def punishment_schema(params: GameParams, targets: list[int], rationale: bool) -> dict:
    per_target = {"type": "integer", "minimum": 0, "maximum": params.max_punish}
    props = {"punishments": {
        "type": "object",
        "description": "Punishment points per other player, keyed by player number.",
        "required": [str(t) for t in targets],
        "properties": {str(t): per_target for t in targets},
    }}
    if rationale:
        props["rationale"] = {"type": "string",
                              "description": "One or two sentences on why you chose this."}
    return {"type": "object", "required": ["punishments"], "properties": props}


# --------------------------------------------------------------------------
# Run configuration
# --------------------------------------------------------------------------

def resolve_models(names, available: dict[str, str]) -> dict[str, str]:
    """Short keys or slugs -> {key: slug}, checked against `available`."""
    by_slug = {slug: key for key, slug in available.items()}
    out = {}
    for name in names:
        if name in available:
            out[name] = available[name]
        elif name in by_slug:
            out[by_slug[name]] = name
        else:
            raise ValueError(f"unknown model {name!r}; known: {sorted(available)}")
    return out


def resolve_providers(providers, models: dict[str, str]) -> dict | None:
    """Config "providers" keyed by model key or slug -> keyed by model key."""
    if providers is None:
        return None
    if not isinstance(providers, dict):
        raise ValueError("providers must be a {model: {slug, name[, quantizations]}} object")
    by_slug = {slug: key for key, slug in models.items()}
    out = {}
    for name, spec in providers.items():
        key = name if name in models else by_slug.get(name)
        if key is None:
            raise ValueError(f"providers: {name!r} is not one of the run's models {sorted(models)}")
        out[key] = spec
    return out


_PROVIDER_KEYS = {"slug", "name", "quantizations"}


def check_provider_spec(model_key: str, spec) -> None:
    """A pinned provider: {"slug", "name"[, "quantizations"]}, no placeholder."""
    where = f"providers[{model_key}]"
    if not isinstance(spec, dict):
        raise ValueError(f"{where} must be an object with slug and name")
    unknown = set(spec) - _PROVIDER_KEYS
    if unknown:
        raise ValueError(f"{where}: unknown keys {sorted(unknown)}; allowed {sorted(_PROVIDER_KEYS)}")
    open_ = placeholders_in(spec, where)
    if open_:
        raise ValueError(f"not chosen yet (placeholder): {', '.join(open_)}")
    for k in ("slug", "name"):
        if not isinstance(spec.get(k), str) or not spec[k].strip():
            raise ValueError(f"{where}.{k} must be a non-empty string")
    quants = spec.get("quantizations")
    if quants is not None and (not isinstance(quants, list) or not quants
                               or any(q not in QUANTIZATIONS for q in quants)):
        raise ValueError(f"{where}.quantizations must be a non-empty list from {QUANTIZATIONS}")


def provider_routing(spec: dict) -> dict:
    """OpenRouter provider-routing object that pins one provider, no fallback.

    require_parameters true (A4): only an endpoint that supports every
    parameter of the request (response_format, max_tokens, ...) may serve it,
    so a parameter is never dropped silently.
    https://openrouter.ai/docs/guides/routing/provider-selection
    """
    routing = {"order": [spec["slug"]], "only": [spec["slug"]], "allow_fallbacks": False,
               "require_parameters": True}
    if spec.get("quantizations"):
        routing["quantizations"] = list(spec["quantizations"])
    return routing


# How a pinned model's requests and responses are handled (A4); recorded in
# every segment entry and start event, outside "config".
PROVIDER_POLICY = {"require_parameters": True, "on_mismatch": "re_request",
                   "mismatch_limit": "llm_client max_retries (4 attempts per call)"}


def same_provider(got: str, expected: str) -> bool:
    """Provider names compared case- and punctuation-insensitively.

    Copy of llm_client.same_provider (dry runs must not import llm_client); a
    test checks that both agree.
    """
    def norm(s):
        return re.sub(r"[^a-z0-9]", "", s.casefold())
    return norm(got) == norm(expected)


def default_runs_dir() -> Path | None:
    """<orc project>/workspace/runs when this code runs in an orc worktree.

    The layout <project>/worktrees/<task>/ next to <project>/workspace/ is
    the only case where the workspace is known; elsewhere None, and a real
    run needs the directory given explicitly.
    """
    if PROJECT_DIR.resolve().parent.name == "worktrees":
        workspace = PROJECT_DIR.resolve().parent.parent / "workspace"
        if workspace.is_dir():
            return workspace / "runs"
    return None


def _inside_worktree(path: Path) -> bool:
    """True if path lies in this code's directory and that is a git worktree.

    A linked worktree has a .git FILE; worktrees are deleted after merging,
    and git-ignored outputs inside them are lost with them (pilot_20261005).
    """
    if not (PROJECT_DIR / ".git").is_file():
        return False
    root, p = PROJECT_DIR.resolve(), path.resolve()
    return p == root or root in p.parents


def check_output_dir(path, *, must_exist: bool, what: str) -> Path:
    """An absolute directory outside the worktree; ValueError otherwise."""
    if is_placeholder(path):
        raise ValueError(f"{what} not chosen yet (placeholder): {path!r}")
    path = Path(path)
    if not path.is_absolute():
        raise ValueError(f"{what} must be an absolute path, got {str(path)!r}")
    if must_exist and not path.is_dir():
        raise ValueError(f"{what} {str(path)!r} does not exist (create it first)")
    if not must_exist and not path.parent.is_dir():
        raise ValueError(f"{what}: parent directory of {str(path)!r} does not exist")
    if _inside_worktree(path):
        raise ValueError(f"{what} {str(path)!r} is inside the git worktree {str(PROJECT_DIR)!r}; "
                         "outputs must go to a persistent directory outside it")
    return path


@dataclass
class RunConfig:
    run: str
    cards: list[Card]
    models: dict[str, str]                     # short key -> OpenRouter slug
    params: GameParams = field(default_factory=GameParams)
    conditions: tuple[str, ...] = ("N",)
    arms: tuple[str, ...] = ("group", "isolated")
    groups_per_cell: int = 2                   # homogeneous groups per card x condition
    isolated_reps: int = 2                     # schedule repetitions per card
    isolated_points: tuple[int, ...] = ISOLATED_POINTS
    # None = provider default (not sent); a string for all models, or a
    # {model key: effort} dict (models missing from it get the default).
    reasoning_effort: str | dict | None = None
    max_tokens: int | None = None              # None = llm_client.DEFAULT_MAX_TOKENS
    max_invalid: int = 3
    rationale: bool = True
    workers: int = 1                           # parallel calls within a round / schedule
    parallel_units: int = 1                    # group games / schedules run at once
    seed_namespace: str = "pgg"                # first part of every stable_seed key
    # Run guards (module docstring); None / False = off.
    budget_usd: float | None = None
    invalid_rate_cap: float | None = None
    stop_on_length: bool = False
    check_snapshot: bool = False
    # Output location: exactly one of the two, both absolute and outside the
    # git worktree. runs_dir (must exist) -> runs_dir/<run>/ holds the results,
    # the summary and the raw log. results_dir (created; its parent must
    # exist) holds the results and the summary; the raw log goes to log_path
    # if given, else stays at llm_client.LOG_PATH.
    runs_dir: Path | None = None
    results_dir: Path | None = None
    log_path: Path | None = None
    request_timeout_s: float | None = None     # None = llm_client.DEFAULT_TIMEOUT_S
    # wall-clock limit of one HTTP attempt; None = llm_client.DEFAULT_REQUEST_DEADLINE_S
    request_deadline_s: float | None = None
    # raw log idle this long -> stop_reason "stalled"; None = DEFAULT_STALL_TIMEOUT_S
    stall_timeout_s: float | None = None
    # --resume: request_deadline_s / stall_timeout_s may differ from the
    # previous segment's (recorded in the summary); otherwise a difference stops
    allow_timeout_change: bool = False
    # {model key: {"slug", "name"[, "quantizations"]}}: pins one provider per
    # model (order + only, allow_fallbacks false, require_parameters true); a
    # response from another provider is re-requested (A4; it changes prereg
    # §8.2 item 5, which stopped the run). None = not pinned.
    providers: dict | None = None
    isolated_frame: str = "one_shot"           # ISOLATED_FRAMES

    def effort_for(self, model_key: str) -> str | None:
        if isinstance(self.reasoning_effort, dict):
            return self.reasoning_effort.get(model_key)
        return self.reasoning_effort

    def provider_for(self, model_key: str) -> dict | None:
        return (self.providers or {}).get(model_key)

    def output_dir(self) -> Path:
        """Directory of this run's results and summary."""
        if self.runs_dir is not None:
            return Path(self.runs_dir) / self.run
        return Path(self.results_dir)

    def raw_log_path(self) -> Path | None:
        """Where the raw log is redirected for the run (None = not redirected)."""
        if self.log_path is not None:
            return Path(self.log_path)
        if self.runs_dir is not None:
            return self.output_dir() / "raw_calls.jsonl"
        return None

    def validate(self) -> None:
        if (self.runs_dir is None) == (self.results_dir is None):
            raise ValueError("give exactly one of runs_dir and results_dir")
        if self.runs_dir is not None:
            check_output_dir(self.runs_dir, must_exist=True, what="runs_dir")
        else:
            check_output_dir(self.results_dir, must_exist=False, what="results_dir")
        if self.log_path is not None:
            check_output_dir(Path(self.log_path).parent, must_exist=False,
                             what="log_path directory")
        if is_placeholder(self.isolated_frame):
            raise ValueError(f"isolated_frame not chosen yet (placeholder): {self.isolated_frame!r}; "
                             f"choose one of {ISOLATED_FRAMES}")
        if self.isolated_frame not in ISOLATED_FRAMES:
            raise ValueError(f"isolated_frame must be one of {ISOLATED_FRAMES}, "
                             f"got {self.isolated_frame!r}")
        for name in ("request_timeout_s", "request_deadline_s", "stall_timeout_s"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                      or not value > 0):
                raise ValueError(f"{name} must be positive")
        if not isinstance(self.allow_timeout_change, bool):
            raise ValueError("allow_timeout_change must be true or false")
        if self.providers is not None:
            if not isinstance(self.providers, dict):
                raise ValueError("providers must be a {model key: spec} object")
            extra = set(self.providers) - set(self.models)
            if extra:
                raise ValueError(f"providers for models not in the run: {sorted(extra)}")
            missing = set(self.models) - set(self.providers)
            if missing:
                raise ValueError(f"providers given, but none for {sorted(missing)}")
            for key in self.models:
                check_provider_spec(key, self.providers[key])
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self.run):
            raise ValueError(f"run name must be [A-Za-z0-9_.-]+, got {self.run!r}")
        if not set(self.conditions) <= set(CONDITIONS) or not self.conditions:
            raise ValueError(f"conditions must be a non-empty subset of {CONDITIONS}")
        if not set(self.arms) <= set(ARMS) or not self.arms:
            raise ValueError(f"arms must be a non-empty subset of {ARMS}")
        if not self.models:
            raise ValueError("no models")
        validate_cards(self.cards)
        if not self.cards:
            raise ValueError("no cards")
        p = self.params
        if any(not _is_int_in(x, 1, 10**6) for x in (p.group_size, p.rounds, p.endowment)):
            raise ValueError("group_size, rounds and endowment must be positive integers")
        if p.group_size < 2:
            raise ValueError("group_size must be at least 2")
        for pt in self.isolated_points:
            if not _is_int_in(pt, 0, p.endowment):
                raise ValueError(f"isolated point {pt!r} is not an integer in 0..{p.endowment}")
        for key in self.models:
            effort = self.effort_for(key)
            if effort is not None and effort not in REASONING_EFFORTS:
                raise ValueError(f"reasoning_effort {effort!r} not in {REASONING_EFFORTS}")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if self.workers < 1 or self.parallel_units < 1:
            raise ValueError("workers and parallel_units must be at least 1")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self.seed_namespace):
            raise ValueError(f"seed_namespace must be [A-Za-z0-9_.-]+, got {self.seed_namespace!r}")
        if self.budget_usd is not None and not self.budget_usd > 0:
            raise ValueError("budget_usd must be positive")
        if self.invalid_rate_cap is not None and not 0 < self.invalid_rate_cap <= 1:
            raise ValueError("invalid_rate_cap must be in (0, 1]")

    def planned_calls_per_model(self) -> int:
        """Accepted decisions per model of this design (re-requests not included)."""
        counts = pgg_cost.call_counts(
            n_cells=len(self.cards), conditions=self.conditions,
            groups_per_cell=self.groups_per_cell, isolated_reps=self.isolated_reps,
            n_points=len(self.isolated_points), group_size=self.params.group_size,
            rounds=self.params.rounds, arms=self.arms)
        return sum(counts.values())

    def invalid_limit(self) -> int | None:
        """Most invalid + parse-failed responses a model may have (None = no cap)."""
        if self.invalid_rate_cap is None:
            return None
        return math.floor(self.invalid_rate_cap * self.planned_calls_per_model() + 1e-9)


def _count_lines(path: Path) -> int | None:
    """Number of lines of a file (None if it does not exist)."""
    if not Path(path).exists():
        return None
    with open(path, "rb") as f:
        return sum(1 for _ in f)


def session_id_for(run, model_key, card_id, style, condition, arm, idx: int) -> str:
    """Deterministic session id: (run, model, card, style, condition, arm, group/repetition)."""
    return f"pgg-{run}-{model_key}-{card_id}-{style}-{condition}-{arm}-{idx:03d}"


def unit_label(model_key, card: Card, condition, arm, idx: int) -> str:
    """Label of a unit in unit_order, e.g. "gpt|boston_value|value|N|group|0"."""
    return f"{model_key}|{card.card_id}|{card.style}|{condition}|{arm}|{idx}"


@dataclass(frozen=True)
class UnitSpec:
    """One group game or one isolated schedule of the design."""
    label: str
    model_key: str
    card: Card                  # the card of every agent (homogeneous group)
    condition: str
    arm: str
    idx: int                    # group number / schedule repetition
    session_id: str
    expected: frozenset         # row keys (_row_key) of the complete unit
    calls_by_kind: tuple        # ((pgg_cost call kind, accepted decisions), ...)


def _row_key(row: dict) -> tuple:
    """(step, round, agent_id, others_mean) of a result row."""
    return (row.get("step"), row.get("round"), row.get("agent_id"), row.get("others_mean"))


def _unit_rounds(spec: UnitSpec) -> tuple:
    """Round ids of a unit in order: 1..rounds of a group game, (None,) for a schedule."""
    return tuple(sorted({k[1] for k in spec.expected})) if spec.arm == "group" else (None,)


def _call_key(segment: int, session_id: str, call: dict) -> tuple:
    """Identity of one decision call: (segment, session, step, round, agent, others_mean)."""
    return (segment, session_id, call.get("step"), call.get("round"), call.get("agent_id"),
            call.get("others_mean"))


def _call_of_row(row: dict) -> tuple:
    return _call_key(row.get("segment", 0), row.get("session_id"),
                     dict(zip(("step", "round", "agent_id", "others_mean"), _row_key(row))))


# Prompts written by this code (contribution_messages, punishment_messages,
# isolated_messages): what a raw-log record of the code before A1, which has
# no "call", was asked.
_ROUND_PROMPT = re.compile(r"ROUND (\d+) of \d+(, punishment step)?\. You are Player (\d+)\.")
_ISOLATED_PROMPT = re.compile(r"on average, (\d+) points")


def _call_from_messages(messages) -> dict | None:
    """step / round / agent_id / others_mean of a call, read from its prompt (older logs)."""
    try:
        user = messages[-1]["content"]
    except (TypeError, IndexError, KeyError):
        return None
    if not isinstance(user, str):
        return None
    m = _ROUND_PROMPT.search(user)
    if m:
        return {"step": "punish" if m.group(2) else "contribute", "round": int(m.group(1)),
                "agent_id": int(m.group(3)), "others_mean": None}
    m = _ISOLATED_PROMPT.search(user)
    if "QUESTION\n" in user and m:
        return {"step": "isolated", "round": None, "agent_id": 1, "others_mean": int(m.group(1))}
    return None


def _new_stats() -> dict:
    """Per-model counters of a run or segment."""
    # n_provider_error: provider-error responses (llm_client error_kind
    # "provider"); not in n_parse_fail and not in the invalid-rate cap.
    # providers: provider name of every response -> count ("null" = none).
    # n_discarded: accepted decisions that never became a row (billed).
    # n_reasoning_capped: accepted decisions whose reasoning reached
    # max_tokens - REASONING_RESERVE_TOKENS (kept, flagged on the row).
    # n_transport / n_deadline: attempts that failed with a connection error /
    # passed their deadline. A response past its deadline is billed: its cost
    # is in cost_usd (also in deadline_cost_usd) when its usage arrived, else
    # it is counted in n_cost_unknown (not priced).
    # n_provider_mismatch: responses of a pinned model from another provider
    # (billed, never a decision, re-requested; A4).
    return {"cost_usd": 0.0, "n_responses": 0, "n_accepted": 0,
            "n_invalid": 0, "n_parse_fail": 0, "n_provider_error": 0,
            "n_cost_estimated": 0, "n_length": 0, "finish_reasons": {},
            "providers": {}, "n_provider_unknown": 0, "n_discarded": 0,
            "n_reasoning_capped": 0, "n_transport": 0, "n_deadline": 0,
            "n_cost_unknown": 0, "deadline_cost_usd": 0.0, "n_provider_mismatch": 0}


# Totals of the summary and of each segment entry (A2, A3, A4).
_SEGMENT_TOTALS = ("n_reasoning_capped", "n_transport", "n_deadline", "n_cost_unknown",
                   "deadline_cost_usd", "n_provider_mismatch")


def _merge_stats(*parts: dict) -> dict:
    """Sum of per-model counters (keys missing from _new_stats are ignored)."""
    out = _new_stats()
    for part in parts:
        for k, v in (part or {}).items():
            if k not in out:
                continue
            if isinstance(out[k], dict):
                for kk, vv in v.items():
                    out[k][kk] = out[k].get(kk, 0) + vv
            else:
                out[k] += v
    return out


def _read_jsonl(path: Path) -> tuple[list, bool]:
    """(parsed lines, None for a line that is not JSON; file ends with a newline?)."""
    data = Path(path).read_bytes()
    out = []
    for line in data.splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            out.append(None)
    return out, data.endswith(b"\n") or not data


def _short(value, limit: int = 300) -> str:
    """A config value for an error message."""
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return text if len(text) <= limit else text[:limit] + "..."


def _json_round(value):
    """value as it reads back from JSON (tuples -> lists, int keys -> str)."""
    return json.loads(json.dumps(value, ensure_ascii=False))


@dataclass
class ResumePlan:
    """What --resume found in a run directory; built without writing anything."""
    segment: int                       # number of the new segment
    prior_segments: list[int]
    n_units: int
    complete: dict                     # unit label -> segment that completed it
    superseded: list[dict]             # {"unit", "segment", "rounds", "n_rows"}
    resume_points: list[dict]          # {"unit", "from_round", "rounds_kept", "kept_from_segments"}
    started_without_rows: list[str]    # units with logged calls but no row
    remaining: list[str]               # labels still to run, in run order
    prior_stats: dict                  # model key -> counters of all earlier segments
    prior_source: str                  # "raw_log" or "summary"
    prior_extra_cost: float            # summary cost not found in the raw log
    cost_check: dict
    segments: list[dict]               # summary entries of the earlier segments
    n_rows: int
    rows_per_segment: dict
    results_ends_with_newline: bool
    truncated_last_line: dict | None   # {"line", "offset", "n_bytes", "sha256", "text"}
    truncated_lines: list[dict]        # cut-off lines recorded in <run>.partial.jsonl
    previous_summary: dict | None
    config_checked: list[str]          # what the config was compared on
    problems: list[str]                # config differences and anomalies
    histories: dict = field(default_factory=dict)   # unit label -> [RoundRecord] (resume)
    # request_deadline_s / stall_timeout_s: {"from_segment", "earlier", "now",
    # "allowed"} when they differ from the last earlier segment that recorded
    # them; timeout_check says what they were compared with
    timeout_change: dict | None = None
    timeout_check: str = ""
    # git_commit of this segment differs from (or is unknown in) earlier
    # segments: {"now", "earlier": {segment: commit}, "differs_from_segments"}
    code_change: dict | None = None
    # accepted responses of earlier segments without a row and without a
    # "pgg_discarded" event yet: [(model key, session_id, call)]
    unmarked_discarded: list = field(default_factory=list)
    lock: dict | None = None           # read_run_lock of the run's lock file

    @property
    def prior_cost_usd(self) -> float:
        return sum(s["cost_usd"] for s in self.prior_stats.values()) + self.prior_extra_cost


# --------------------------------------------------------------------------
# Engine
# --------------------------------------------------------------------------

@dataclass
class Answer:
    parsed: dict
    n_invalid: int
    n_parse_fail: int
    meta: dict
    n_provider_error: int = 0
    call: dict | None = None       # call_info of the decision (segment, step, round, ...)
    n_transport: int = 0           # connection errors while this decision was obtained
    n_deadline: int = 0            # attempts past their deadline while it was obtained
    n_provider_mismatch: int = 0   # responses from another provider, re-requested (A4)


class _Pending:
    """Accepted answers of one round (or schedule) whose rows are not written yet.

    An answer that does not become a row is discarded (Engine._discard): the
    round was given up (close() before its rows were written: a stop, a
    signal, an abort of another call), the answer arrived after that (a call
    still in flight), or its row could not be written.
    """

    def __init__(self, engine: "Engine", model_key: str, session_id: str):
        self.engine, self.model_key, self.session_id = engine, model_key, session_id
        self.lock = threading.Lock()
        self.items: dict[tuple, dict] = {}
        self.closed = False

    @staticmethod
    def _id(call: dict) -> tuple:
        return _call_key(call.get("segment"), "", call)

    def add(self, ans: Answer) -> Answer:
        with self.lock:
            if not self.closed:
                self.items[self._id(ans.call)] = ans.call
                return ans
        self.engine._discard(self.model_key, self.session_id, ans.call, "round_not_completed")
        return ans

    def done(self, ans: Answer, written: bool) -> None:
        with self.lock:
            self.items.pop(self._id(ans.call), None)
        if not written:
            self.engine._discard(self.model_key, self.session_id, ans.call, "row_not_written")

    def close(self) -> None:
        with self.lock:
            self.closed = True
            left = list(self.items.values())
            self.items.clear()
        for call in left:
            self.engine._discard(self.model_key, self.session_id, call, "round_not_completed")


class Engine:
    def __init__(self, cfg: RunConfig, *, llm=None):
        cfg.validate()
        self.cfg = cfg
        self.llm = llm or _llm()
        self.max_tokens = cfg.max_tokens or self.llm.DEFAULT_MAX_TOKENS
        self.timeout = cfg.request_timeout_s or self.llm.DEFAULT_TIMEOUT_S
        self.deadline = cfg.request_deadline_s or self.llm.DEFAULT_REQUEST_DEADLINE_S
        self.stall_timeout = cfg.stall_timeout_s or DEFAULT_STALL_TIMEOUT_S
        self.code_version: dict | None = None      # set by run()
        self.stalled = False                       # the stall watchdog stopped the run
        self._out = None
        self._lock = threading.Lock()
        self.invalid_limit = cfg.invalid_limit()
        self.stop_reason: str | None = None        # set once; stops every unit
        self.aborted: RunAborted | None = None
        self.stopped_models: dict[str, str] = {}   # model key -> reason
        self.unit_order: list[str] = []
        self.files: dict | None = None             # output files and line counts (run)
        self.stats = {key: _new_stats() for key in cfg.models}    # this segment
        # Resume: the segment number and what the earlier segments used.
        self.segment = 0
        self.prior_stats = {key: _new_stats() for key in cfg.models}
        self.prior_extra_cost = 0.0
        self.plan: ResumePlan | None = None
        self._specs: list[UnitSpec] = []
        self._histories: dict[str, list[RoundRecord]] = {}   # resume: rebuilt from rows
        self.lock: dict | None = None              # acquire_run_lock of run()
        self._run_log: Path | None = None          # the run's raw log (late discard events)
        # Signals: name of the signal that interrupted the run; thread pools to
        # wait for after the summary; True once the summary is being written.
        self._interrupted: str | None = None
        self._raise_on_signal = False
        self._pools: list[ThreadPoolExecutor] = []
        self._finalizing = False

    # -- seeds / output ----------------------------------------------------

    def seed_for(self, *parts) -> int:
        return self.llm.stable_seed(self.cfg.seed_namespace, self.cfg.run, *parts)

    def _write(self, row: dict) -> bool:
        """Append one row; False if the file is closed (the run has ended: stall, signal)."""
        with self._lock:
            if self._out is None:
                return False
            self._out.write(json.dumps(row, ensure_ascii=False) + "\n")
            self._out.flush()
            return True

    def _log(self, record: dict) -> None:
        """A record for the run's raw log, also after run() has restored the log path."""
        if self._run_log is not None:
            self.llm._append_log(record, self._run_log)
        else:
            self.llm._append_log(record)

    def _discard(self, model_key: str, session_id: str, call: dict, reason: str) -> None:
        """Log an accepted decision that did not become a row ("discarded": true).

        Counted in n_discarded of this segment when the call is of this
        segment (found_on_resume events are of earlier segments, already
        counted from the raw log). Its cost was counted when it arrived.
        """
        if call.get("segment") == self.segment:
            with self._lock:
                self.stats[model_key]["n_discarded"] += 1
        self._log({"ts": time.time(), "event": "pgg_discarded", "discarded": True,
                   "run": self.cfg.run, "segment": self.segment,
                   "model": self.cfg.models[model_key], "session_id": session_id,
                   "call": call, "reason": reason})

    # -- run guards --------------------------------------------------------

    @property
    def segment_cost(self) -> float:
        return sum(s["cost_usd"] for s in self.stats.values())

    @property
    def total_cost(self) -> float:
        """Cost of this segment and of all earlier ones (resume)."""
        return (self.segment_cost + sum(s["cost_usd"] for s in self.prior_stats.values())
                + self.prior_extra_cost)

    def _stop(self, reason: str, **detail) -> None:
        """Stop the whole run (first reason wins); logged once."""
        with self._lock:
            if self.stop_reason is not None:
                return
            self.stop_reason = reason
        self.llm._append_log({"ts": time.time(), "event": "pgg_run_stopped", "run": self.cfg.run,
                              "reason": reason, "total_cost_usd": self.total_cost, **detail})

    def _before_call(self, model_key: str) -> None:
        """Runs before every attempt: raises instead of sending when a guard is hit."""
        budget = self.cfg.budget_usd
        if budget is not None and self.stop_reason is None and self.total_cost >= budget:
            self._stop("budget", budget_usd=budget)
        if self.stop_reason is not None or self._interrupted is not None or self.stalled:
            raise RunStopped(self.stop_reason or ("stalled" if self.stalled else "interrupted"))
        if model_key in self.stopped_models:
            raise ModelStopped(self.stopped_models[model_key])

    def _response_cost(self, model_key: str, usage) -> tuple[float, bool]:
        """(USD, estimated?): usage.cost, else priced from tokens (pgg_cost)."""
        usage = usage if isinstance(usage, dict) else {}
        cost = usage.get("cost")
        if isinstance(cost, (int, float)) and not isinstance(cost, bool):
            return float(cost), False
        price_in, price_out = pgg_cost.PRICES_USD_PER_M.get(
            self.cfg.models[model_key], max(pgg_cost.PRICES_USD_PER_M.values()))
        tokens_in = usage.get("prompt_tokens") or 0
        # unknown tokens: price a full max_tokens completion, the worst case
        tokens_out = usage.get("completion_tokens")
        if tokens_out is None:
            tokens_out = self.max_tokens
        return (tokens_in * price_in + tokens_out * price_out) / 1e6, True

    def _count_response(self, s: dict, model_key: str, info: dict) -> None:
        """Add one response (info as in llm_client._response_info) to counters s."""
        cost, estimated = self._response_cost(model_key, info.get("usage"))
        finish = info.get("finish_reason")
        provider = info.get("provider")
        s["cost_usd"] += cost
        s["n_responses"] += 1
        s["n_cost_estimated"] += estimated
        s["finish_reasons"][str(finish)] = s["finish_reasons"].get(str(finish), 0) + 1
        s["providers"][str(provider)] = s["providers"].get(str(provider), 0) + 1
        if finish == "length":
            s["n_length"] += 1
        if info.get("provider_error"):
            s["n_provider_error"] += 1
        if info.get("provider_mismatch"):
            s["n_provider_mismatch"] += 1
        if self.cfg.provider_for(model_key) and provider is None:
            s["n_provider_unknown"] += 1

    def _on_response(self, model_key: str, info: dict) -> None:
        """Runs for every response that arrived (billed): cost, finish_reason, model, provider.

        A response from another provider than the pinned one does not stop
        the run any more (A4, it changes prereg §8.2 item 5): llm_client
        re-requests it (expected_provider) and it is counted here
        (n_provider_mismatch).
        """
        finish = info.get("finish_reason")
        with self._lock:
            self._count_response(self.stats[model_key], model_key, info)
        slug = self.cfg.models[model_key]
        snapshot = info.get("model_snapshot")
        if self.cfg.stop_on_length and finish == "length":
            self._stop("finish_reason_length", model=slug)
        if (self.cfg.check_snapshot and snapshot is not None and snapshot != slug
                and not snapshot.startswith(slug + "-")):
            self._stop("model_snapshot_mismatch", model=slug, model_snapshot=snapshot)

    def _on_late_response(self, model_key: str, info: dict) -> None:
        """A response that came after its attempt was abandoned: billed, counted, not a decision."""
        with self._lock:
            self._count_response(self.stats[model_key], model_key, info)

    def _count_deadline_cost(self, s: dict, model_key: str, usage, cost_unknown: bool,
                             late_response: bool) -> None:
        """Cost of a response past its deadline (never a decision) into counters s.

        Its usage arrived: priced like any response (usage.cost, else from its
        tokens) into cost_usd and deadline_cost_usd. A late response is counted
        when it arrives (_on_late_response). Otherwise n_cost_unknown.
        """
        if late_response:
            return
        if isinstance(usage, dict):
            cost, estimated = self._response_cost(model_key, usage)
            s["cost_usd"] += cost
            s["deadline_cost_usd"] += cost
            s["n_cost_estimated"] += estimated
        elif cost_unknown:
            s["n_cost_unknown"] += 1

    def _on_deadline(self, model_key: str, info: dict) -> None:
        """An attempt passed its deadline: what arrived of it counts in the budget."""
        with self._lock:
            self._count_deadline_cost(self.stats[model_key], model_key, info.get("usage"),
                                      info.get("cost_unknown", True),
                                      info.get("late_response", False))

    def _count_invalid(self, model_key: str, ans: "Answer") -> None:
        with self._lock:
            s = self.stats[model_key]
            s["n_accepted"] += 1
            s["n_invalid"] += ans.n_invalid
            s["n_parse_fail"] += ans.n_parse_fail
            s["n_reasoning_capped"] += bool(
                self.llm.reasoning_capped(ans.meta.get("usage"), self.max_tokens))
            prior = self.prior_stats[model_key]          # earlier segments (resume)
            n_invalid = s["n_invalid"] + prior["n_invalid"]
            n_parse_fail = s["n_parse_fail"] + prior["n_parse_fail"]
            hit = (self.invalid_limit is not None and n_invalid + n_parse_fail > self.invalid_limit
                   and model_key not in self.stopped_models)
            if hit:
                self.stopped_models[model_key] = "invalid_rate_cap"
        if hit:
            self.llm._append_log({
                "ts": time.time(), "event": "pgg_model_stopped", "run": self.cfg.run,
                "model": self.cfg.models[model_key], "reason": "invalid_rate_cap",
                "n_invalid": n_invalid, "n_parse_fail": n_parse_fail,
                "limit": self.invalid_limit})

    def _pool(self, max_workers: int) -> ThreadPoolExecutor:
        pool = ThreadPoolExecutor(max_workers=max_workers)
        with self._lock:
            self._pools.append(pool)
        return pool

    def _release(self, pool: ThreadPoolExecutor) -> None:
        """Wait for the pool, except after a signal (the summary comes first) or a stall."""
        interrupted = self._interrupted is not None or self.stalled
        pool.shutdown(wait=not interrupted, cancel_futures=interrupted)
        if not interrupted:
            with self._lock:
                self._pools.remove(pool)

    def _map(self, fn, items):
        items = list(items)
        if self.cfg.workers <= 1 or len(items) <= 1:
            return [fn(x) for x in items]
        pool = self._pool(self.cfg.workers)
        try:
            return list(pool.map(fn, items))
        finally:
            self._release(pool)

    # -- one validated call ------------------------------------------------

    def _ask(self, model_key, messages, schema, is_valid, session_id, ctx: dict) -> Answer:
        meta: dict = {}
        counts: dict = {}
        last: dict = {}            # info of the last response = the accepted one

        def on_response(info):
            last.clear()
            last.update(info)
            self._on_response(model_key, info)

        pinned = self.cfg.provider_for(model_key)
        # written as "call" into every raw-log record of this decision
        call = {"segment": self.segment, "step": ctx.get("step"), "round": ctx.get("round"),
                "agent_id": ctx.get("agent_id"), "others_mean": ctx.get("others_mean")}
        try:
            parsed, n_invalid, n_parse_fail = self.llm.call_llm_valid(
                self.cfg.models[model_key], messages, schema=schema, session_id=session_id,
                is_valid=is_valid, max_tokens=self.max_tokens, max_invalid=self.cfg.max_invalid,
                return_parse_fail=True, reasoning_effort=self.cfg.effort_for(model_key),
                meta=meta, before_call=lambda: self._before_call(model_key),
                on_response=on_response, timeout=self.timeout, counts=counts,
                provider=provider_routing(pinned) if pinned else None,
                request_deadline_s=self.deadline,
                on_late_response=lambda info: self._on_late_response(model_key, info),
                call_info=call, on_deadline=lambda info: self._on_deadline(model_key, info),
                expected_provider=pinned["name"] if pinned else None)
        except RuntimeError as e:
            mismatch = getattr(e, "last_error_kind", None) == "provider_mismatch"
            reason = "provider_mismatch_limit" if mismatch else "run_aborted"
            self.llm._append_log({
                "ts": time.time(), "event": "pgg_run_aborted", "run": self.cfg.run,
                "model": self.cfg.models[model_key], "session_id": session_id,
                "error": str(e), "reason": reason,
                "n_provider_mismatch": counts.get("n_provider_mismatch", 0), **ctx,
            })
            raise RunAborted(
                f"run {self.cfg.run!r} stopped: no valid decision for {ctx} "
                f"(model {model_key}): {e}"
                + (f" [{counts.get('n_provider_mismatch', 0)} response(s) from another provider "
                   f"than {pinned['name']!r}; attempt limit reached]" if mismatch else ""),
                reason=reason) from e
        finally:
            # connection errors and deadlines also when the call failed or was stopped
            with self._lock:
                for k in ("n_transport", "n_deadline"):
                    self.stats[model_key][k] += counts.get(k, 0)
        meta["provider"] = last.get("provider")
        meta["provider_quantization"] = last.get("provider_quantization")
        ans = Answer(parsed, n_invalid, n_parse_fail, meta,
                     n_provider_error=counts.get("n_provider_error", 0), call=call,
                     n_transport=counts.get("n_transport", 0),
                     n_deadline=counts.get("n_deadline", 0),
                     n_provider_mismatch=counts.get("n_provider_mismatch", 0))
        self._count_invalid(model_key, ans)
        return ans

    def _row(self, *, condition, arm, model_key, card, session_id, group_id, agent_id,
             round_no, step, ans: Answer, seed: int, unit: str, **fields) -> dict:
        rationale = ans.parsed.get("rationale")
        return {
            "run": self.cfg.run, "segment": self.segment, "unit": unit, "condition": condition, "arm": arm, "step": step,
            "model": self.cfg.models[model_key], "model_key": model_key,
            "model_snapshot": ans.meta.get("model_snapshot"),
            "session_id": session_id, "group_id": group_id, "agent_id": agent_id,
            "round": round_no, "card_id": card.card_id, "style": card.style,
            **card_length(card),
            **fields,
            "n_invalid": ans.n_invalid, "n_parse_fail": ans.n_parse_fail,
            "n_provider_error": ans.n_provider_error,
            "n_provider_mismatch": ans.n_provider_mismatch,
            "n_transport": ans.n_transport, "n_deadline": ans.n_deadline,
            "elapsed_s": ans.meta.get("elapsed_s"),
            "reasoning_capped": self.llm.reasoning_capped(ans.meta.get("usage"), self.max_tokens),
            "provider": ans.meta.get("provider"),
            "provider_quantization": ans.meta.get("provider_quantization"),
            "finish_reason": ans.meta.get("finish_reason"), "usage": ans.meta.get("usage"),
            "reasoning": ans.meta.get("reasoning"),
            "rationale": rationale if isinstance(rationale, str) else None,
            "reasoning_effort": self.llm.reasoning_effort_label(self.cfg.effort_for(model_key)),
            "max_tokens": self.max_tokens, "temperature": "default",
            "seed": seed, "ts": time.time(),
        }

    # -- group arm ---------------------------------------------------------

    def play_group(self, model_key: str, cards: list[Card], condition: str, idx: int,
                   history: list[RoundRecord] | None = None) -> None:
        """One group game (rounds x agents); cards[i] is agent i+1's card.

        history: rounds 1..k already played (resume, rebuilt from their rows);
        the game goes on with round k+1.
        """
        p = self.cfg.params
        if len(cards) != p.group_size:
            raise ValueError(f"need {p.group_size} cards, got {len(cards)}")
        lead = cards[0]
        session_id = session_id_for(self.cfg.run, model_key, lead.card_id, lead.style,
                                    condition, "group", idx)
        group_id = f"{lead.card_id}-{lead.style}-{condition}-g{idx:02d}"
        unit = unit_label(model_key, lead, condition, "group", idx)
        history = list(history or [])
        if [rec.round for rec in history] != list(range(1, len(history) + 1)):
            raise ValueError(f"history of {unit} is not rounds 1..{len(history)}")
        for r in range(len(history) + 1, p.rounds + 1):
            ctx = {"round": r, "group_id": group_id, "condition": condition}
            pending = _Pending(self, model_key, session_id)

            def contribute(i):
                return pending.add(self._ask(
                    model_key, contribution_messages(p, condition, cards[i], history, i, r),
                    contribution_schema(p, self.cfg.rationale),
                    lambda c: is_valid_contribution(c, p), session_id,
                    {**ctx, "agent_id": i + 1, "step": "contribute"}))

            try:
                answers = self._map(contribute, range(p.group_size))
                contributions = [a.parsed["contribution"] for a in answers]
                earnings = project_payoffs(p, contributions)
                rec = RoundRecord(r, contributions, earnings, final_earnings=earnings)
                punish_answers = None

                if condition == "P":
                    def punish(i):
                        targets = [j + 1 for j in range(p.group_size) if j != i]
                        budget = punishment_budget(earnings[i])
                        return pending.add(self._ask(
                            model_key,
                            punishment_messages(p, cards[i], history, i, r, contributions,
                                                earnings[i]),
                            punishment_schema(p, targets, self.cfg.rationale),
                            lambda c: is_valid_punishment(c, p, targets, budget), session_id,
                            {**ctx, "agent_id": i + 1, "step": "punish"}))

                    punish_answers = self._map(punish, range(p.group_size))
                    rec.punishment = [
                        [punish_answers[i].parsed["punishments"][str(j + 1)] if j != i else 0
                         for j in range(p.group_size)] for i in range(p.group_size)]
                    rec.final_earnings, rec.cost_paid, rec.received = apply_punishment(
                        p, earnings, rec.punishment)

                for i in range(p.group_size):
                    pending.done(answers[i], self._write(self._row(
                        condition=condition, arm="group", model_key=model_key, card=cards[i],
                        session_id=session_id, group_id=group_id, agent_id=i + 1, round_no=r,
                        step="contribute", ans=answers[i], unit=unit,
                        seed=self.seed_for(model_key, cards[i].card_id, cards[i].style, condition,
                                           "group", idx, i + 1, r, "contribute"),
                        contribution=answers[i].parsed["contribution"],
                        group_total=sum(contributions),
                        payoff_before_punishment=earnings[i], payoff=rec.final_earnings[i])))
                if punish_answers:
                    for i in range(p.group_size):
                        pending.done(punish_answers[i], self._write(self._row(
                            condition=condition, arm="group", model_key=model_key, card=cards[i],
                            session_id=session_id, group_id=group_id, agent_id=i + 1, round_no=r,
                            step="punish", ans=punish_answers[i], unit=unit,
                            seed=self.seed_for(model_key, cards[i].card_id, cards[i].style,
                                               condition, "group", idx, i + 1, r, "punish"),
                            punishments={str(j + 1): rec.punishment[i][j]
                                         for j in range(p.group_size) if j != i},
                            punishment_cost_paid=rec.cost_paid[i],
                            punishment_points_received=rec.received[i],
                            payoff=rec.final_earnings[i])))
            finally:
                pending.close()            # answers left without a row: discarded
            history.append(rec)

    # -- isolated arm ------------------------------------------------------

    def play_isolated(self, model_key: str, card: Card, rep: int) -> None:
        """The conditional schedule for one card: one call per conditioning value."""
        p = self.cfg.params
        condition = "N"
        session_id = session_id_for(self.cfg.run, model_key, card.card_id, card.style,
                                    condition, "isolated", rep)
        group_id = f"{card.card_id}-{card.style}-{condition}-iso{rep:02d}"
        unit = unit_label(model_key, card, condition, "isolated", rep)

        pending = _Pending(self, model_key, session_id)

        def ask_point(x):
            ctx = {"round": None, "group_id": group_id, "condition": condition,
                   "agent_id": 1, "step": "isolated", "others_mean": x}
            return pending.add(self._ask(
                model_key, isolated_messages(p, card, x, self.cfg.isolated_frame),
                contribution_schema(p, self.cfg.rationale),
                lambda c: is_valid_contribution(c, p), session_id, ctx))

        points = list(self.cfg.isolated_points)
        try:
            for x, ans in zip(points, self._map(ask_point, points)):
                pending.done(ans, self._write(self._row(
                    condition=condition, arm="isolated", model_key=model_key, card=card,
                    session_id=session_id, group_id=group_id, agent_id=1, round_no=None,
                    step="isolated", ans=ans, unit=unit,
                    seed=self.seed_for(model_key, card.card_id, card.style, condition,
                                       "isolated", rep, 1, "isolated", x),
                    contribution=ans.parsed["contribution"], others_mean=x,
                    isolated_frame=self.cfg.isolated_frame)))
        finally:
            pending.close()

    # -- whole run ---------------------------------------------------------

    def _order_key(self, *parts) -> tuple:
        """Sort key of the run order: stable_seed (crc32), the parts break ties."""
        return (self.llm.stable_seed(self.cfg.seed_namespace, self.cfg.run, "order", *parts),
                tuple(map(str, parts)))

    def _spec(self, model_key: str, card: Card, condition: str, arm: str, idx: int) -> UnitSpec:
        cfg, p = self.cfg, self.cfg.params
        if arm == "group":
            steps = ("contribute", "punish") if condition == "P" else ("contribute",)
            expected = frozenset((step, r, a, None) for step in steps
                                 for r in range(1, p.rounds + 1)
                                 for a in range(1, p.group_size + 1))
            n = p.rounds * p.group_size
            kinds = ((f"contribute_{condition}", n),) + ((("punish_P", n),) if condition == "P" else ())
        else:
            expected = frozenset(("isolated", None, 1, x) for x in cfg.isolated_points)
            kinds = (("isolated", len(cfg.isolated_points)),)
        return UnitSpec(
            unit_label(model_key, card, condition, arm, idx), model_key, card, condition, arm, idx,
            session_id_for(cfg.run, model_key, card.card_id, card.style, condition, arm, idx),
            expected, kinds)

    def _cell_specs(self, model_key: str, card: Card) -> list[UnitSpec]:
        """Units of one cell (card x model).

        Group games and isolated schedules alternate, so that a run stopped
        early has both arms.
        """
        cfg = self.cfg
        groups, schedules = [], []
        if "group" in cfg.arms:
            groups = [self._spec(model_key, card, condition, "group", idx)
                      for condition in cfg.conditions for idx in range(cfg.groups_per_cell)]
        if "isolated" in cfg.arms:
            schedules = [self._spec(model_key, card, "N", "isolated", rep)
                         for rep in range(cfg.isolated_reps)]
        out = []
        for k in range(max(len(groups), len(schedules))):
            out += groups[k:k + 1] + schedules[k:k + 1]
        return out

    def unit_specs(self) -> list[UnitSpec]:
        """Every group game / schedule of the design, in run order.

        Shuffled round-robin over the cells (card x model), so that a run
        stopped early still has data from every card: pass k runs the k-th
        unit of every cell. Within a pass the cards are in a stable_seed
        order (new per pass) and the models rotate over them (Latin square),
        so every block of len(cards) consecutive units has every card once
        and the pass has every cell once. Never hash().
        """
        cfg = self.cfg
        models = sorted(cfg.models, key=lambda m: self._order_key("model", m))
        cells = {(m, c.card_id, c.style): self._cell_specs(m, c)
                 for m in cfg.models for c in cfg.cards}
        out = []
        for k in range(max(len(u) for u in cells.values())):
            cards = sorted(cfg.cards, key=lambda c: self._order_key("card", k, c.card_id, c.style))
            for j in range(len(models)):
                for i, card in enumerate(cards):
                    cell = cells[(models[(i + j) % len(models)], card.card_id, card.style)]
                    if k < len(cell):
                        out.append(cell[k])
        return out

    def _unit_fn(self, spec: UnitSpec):
        if spec.arm == "group":
            return lambda: self.play_group(spec.model_key, [spec.card] * self.cfg.params.group_size,
                                           spec.condition, spec.idx,
                                           history=self._histories.get(spec.label))
        return lambda: self.play_isolated(spec.model_key, spec.card, spec.idx)

    def units(self, specs: list[UnitSpec] | None = None) -> list[tuple[str, str, object]]:
        """(model key, label, callable) per group game / schedule, in run order (unit_specs)."""
        specs = self.unit_specs() if specs is None else specs
        return [(s.model_key, s.label, self._unit_fn(s)) for s in specs]

    def _run_unit(self, unit) -> None:
        model_key, _label, fn = unit
        if self.stop_reason is not None or model_key in self.stopped_models:
            return
        try:
            fn()
        except (RunStopped, ModelStopped):
            pass
        except RunAborted as e:
            with self._lock:
                if self.aborted is None:
                    self.aborted = e
            self._stop(getattr(e, "reason", "run_aborted"), error=str(e))

    # -- resume ------------------------------------------------------------

    def _providers_summary(self, *, for_config: bool = False) -> dict:
        """Routing sent per model plus the expected provider name (None = not pinned).

        for_config: without require_parameters (A4), so that "config" stays as
        the earlier code wrote it and its runs resume; PROVIDER_POLICY in the
        segment entries records it instead.
        """
        out = {}
        for k in self.cfg.models:
            p = self.cfg.provider_for(k)
            routing = provider_routing(p) | {"name": p["name"]} if p else None
            if routing and for_config:
                routing.pop("require_parameters", None)
            out[k] = routing
        return out

    def _effort_summary(self) -> dict:
        return {k: self.llm.reasoning_effort_label(self.cfg.effort_for(k)) for k in self.cfg.models}

    def config_record(self) -> dict:
        """What every segment of a run must share (summary "config").

        workers, parallel_units and request_timeout_s may differ between
        segments: they change neither the prompts nor the guards.
        request_deadline_s and stall_timeout_s are not in it either (runs of
        the earlier code resume), but resume_plan compares them with the last
        earlier segment that recorded them: a difference stops, unless
        allow_timeout_change (summary "timeout_changes"). The provider
        routing is in it without require_parameters (A4, _providers_summary).
        """
        cfg = self.cfg
        return _json_round({
            "models": dict(cfg.models), "providers": self._providers_summary(for_config=True),
            "seed_namespace": cfg.seed_namespace, "max_tokens": self.max_tokens,
            "isolated_frame": cfg.isolated_frame, "reasoning_effort": self._effort_summary(),
            "params": dataclasses.asdict(cfg.params), "conditions": list(cfg.conditions),
            "arms": list(cfg.arms), "groups_per_cell": cfg.groups_per_cell,
            "isolated_reps": cfg.isolated_reps, "isolated_points": list(cfg.isolated_points),
            "max_invalid": cfg.max_invalid, "rationale": cfg.rationale,
            "budget_usd": cfg.budget_usd, "invalid_rate_cap": cfg.invalid_rate_cap,
            "stop_on_length": cfg.stop_on_length, "check_snapshot": cfg.check_snapshot,
            "cards": [{"card_id": c.card_id, "style": c.style,
                       "text_sha256": hashlib.sha256(c.text.encode("utf-8")).hexdigest(),
                       **card_length(c)} for c in cfg.cards],
        })

    def _legacy_config(self) -> dict:
        """Top-level fields of a summary written before "config" existed."""
        return _json_round({
            "seed_namespace": self.cfg.seed_namespace, "max_tokens": self.max_tokens,
            "isolated_frame": self.cfg.isolated_frame,
            "providers": self._providers_summary(for_config=True),
            "reasoning_effort": self._effort_summary(), "budget_usd": self.cfg.budget_usd,
            "invalid_rate_cap": self.cfg.invalid_rate_cap,
            "planned_calls_per_model": self.cfg.planned_calls_per_model()})

    def _raw_log_path(self) -> Path | None:
        path = self.cfg.raw_log_path() or self.llm.LOG_PATH
        return Path(path) if path is not None else None

    def _partial_path(self) -> Path:
        """<run>.partial.jsonl: cut-off lines of the results file, one record each."""
        return self.cfg.output_dir() / f"{self.cfg.run}.partial.jsonl"

    def _recorded_truncated(self) -> dict[tuple, dict]:
        """(line, sha256) -> record of every cut-off line recorded so far."""
        path = self._partial_path()
        if not path.is_file():
            return {}
        out = {}
        for rec in _read_jsonl(path)[0]:
            if isinstance(rec, dict) and "line" in rec and "sha256" in rec:
                out.setdefault((rec["line"], rec["sha256"]), rec)
        return out

    def _unit_chain(self, spec: UnitSpec, segs: dict[int, dict]) -> dict:
        """Accepted and superseded rows of one unit (module docstring, "Valid rows").

        segs: segment -> round -> rows. Returns {"accepted": {round: segment}
        in round order, "superseded": [(segment, round, n_rows)], "problems"}.
        """
        rounds = _unit_rounds(spec)
        want = {r: frozenset(k for k in spec.expected if k[1] == r) for r in rounds}
        accepted: dict = {}
        superseded: list[tuple] = []
        problems: list[str] = []
        for seg in sorted(segs):
            blocks = segs[seg]
            keys = {r: [_row_key(x) for x in rows] for r, rows in blocks.items()}
            if any(r not in want or len(set(k)) != len(k) or not set(k) <= want[r]
                   for r, k in keys.items()):
                problems.append(f"unit {spec.label} segment {seg}: rows do not fit the design "
                                "(duplicate or unexpected step / round / agent / value)")
                continue
            if len(accepted) == len(rounds):
                problems.append(f"unit {spec.label} is complete in segment(s) "
                                f"{sorted(set(accepted.values()))} and has rows in segment {seg}")
                continue
            here = [r for r in rounds if r in blocks]
            first, k = rounds.index(here[0]), len(accepted)
            if first > k:
                problems.append(f"unit {spec.label} segment {seg}: starts at round {here[0]}, "
                                f"but only {k} earlier round(s) are complete")
                continue
            # this segment replays the unit from round rounds[first] (the code
            # before A1 re-ran a unit from its start): earlier rounds from there
            # on are replaced
            for r in rounds[first:k]:
                s = accepted.pop(r)
                superseded.append((s, r, len(segs[s][r])))
            taking = True
            for r in rounds[first:]:
                if r not in blocks:
                    taking = False
                    continue
                if taking and set(keys[r]) == want[r]:
                    accepted[r] = seg
                    continue
                if not taking:
                    problems.append(f"unit {spec.label} segment {seg}: rows of round {r} after "
                                    "an incomplete or missing round")
                taking = False
                superseded.append((seg, r, len(blocks[r])))
        return {"accepted": accepted, "superseded": superseded, "problems": problems}

    def _scan_rows(self, path: Path, specs: list[UnitSpec]) -> dict:
        """Rows of the results file: accepted rounds per unit, complete and partial units.

        A line that is not JSON is a problem, except the last line when it has
        no newline (cut off while being written) and the lines recorded in
        <run>.partial.jsonl (cut-off lines of earlier resumes).
        """
        by_session = {s.session_id: s for s in specs}
        order = {s.label: i for i, s in enumerate(specs)}
        lengths = {(c.card_id, c.style): card_length(c) for c in self.cfg.cards}
        data = Path(path).read_bytes()
        ends_with_newline = data.endswith(b"\n") or not data
        lines = data.split(b"\n")
        if ends_with_newline:
            lines = lines[:-1]                 # the text after the last newline is empty
        recorded = self._recorded_truncated()
        blocks: dict[str, dict] = {}           # label -> segment -> round -> rows
        per_segment: dict[int, int] = {}
        problems: list[str] = []
        truncated, truncated_lines = None, []
        row_calls: set = set()                 # _call_of_row of every parsed row
        n_length_checked = 0
        offset = 0
        for i, line in enumerate(lines, 1):
            start, offset = offset, offset + len(line) + 1
            try:
                row = json.loads(line)
            except ValueError:
                row = None
            if not isinstance(row, dict):
                sha = hashlib.sha256(line).hexdigest()
                if i == len(lines) and not ends_with_newline:
                    # cut off while being written
                    truncated = {"line": i, "offset": start, "n_bytes": len(line), "sha256": sha,
                                 "text": line.decode("utf-8", errors="replace")}
                elif (i, sha) in recorded:
                    truncated_lines.append({k: recorded[(i, sha)].get(k) for k in
                                            ("line", "offset", "n_bytes", "sha256",
                                             "found_in_segment")})
                else:
                    problems.append(f"{path.name} line {i}: not a JSON object")
                continue
            spec = by_session.get(row.get("session_id"))
            if spec is None or row.get("run") != self.cfg.run:
                problems.append(f"{path.name} line {i}: session {row.get('session_id')!r} "
                                "is not a unit of this run's design")
                continue
            if row.get("unit", spec.label) != spec.label:
                problems.append(f"{path.name} line {i}: unit {row.get('unit')!r} does not match "
                                f"its session ({spec.label})")
            if "card_n_chars" in row:
                n_length_checked += 1
                got = {k: row.get(k) for k in ("card_n_words", "card_n_chars")}
                want = lengths[(spec.card.card_id, spec.card.style)]
                if got != want:
                    problems.append(f"card {spec.card.card_id}/{spec.card.style}: rows have length "
                                    f"{got}, the cards now {want}")
            seg = row.get("segment", 0)                # rows of the first run have no segment
            per_segment[seg] = per_segment.get(seg, 0) + 1
            row_calls.add(_call_of_row(row))
            (blocks.setdefault(spec.label, {}).setdefault(seg, {})
             .setdefault(row.get("round"), []).append(row))
        by_label = {s.label: s for s in specs}
        complete: dict[str, int] = {}
        progress: dict[str, dict] = {}      # partial unit -> accepted rounds and their rows
        superseded: list[dict] = []
        accepted_rounds: set = set()        # (label, segment, round)
        for label in sorted(blocks, key=order.get):
            spec, segs = by_label[label], blocks[label]
            chain = self._unit_chain(spec, segs)
            problems += chain["problems"]
            accepted = chain["accepted"]
            accepted_rounds |= {(label, s, r) for r, s in accepted.items()}
            by_seg: dict[int, list] = {}
            for s, r, n in chain["superseded"]:
                by_seg.setdefault(s, []).append((r, n))
            for s in sorted(by_seg):
                superseded.append({
                    "unit": label, "segment": s,
                    "rounds": sorted(r for r, _ in by_seg[s]) if spec.arm == "group" else None,
                    "n_rows": sum(n for _, n in by_seg[s])})
            if len(accepted) == len(_unit_rounds(spec)):
                complete[label] = max(accepted.values())
            else:
                progress[label] = {"rounds": {r: segs[s][r] for r, s in accepted.items()},
                                   "segments": sorted(set(accepted.values()))}
        return {"n_rows": sum(per_segment.values()), "rows_per_segment": per_segment,
                "complete": complete, "progress": progress, "superseded": superseded,
                "accepted_rounds": accepted_rounds, "row_calls": row_calls,
                "units_with_rows": set(blocks), "n_length_checked": n_length_checked,
                "ends_with_newline": ends_with_newline, "truncated_last_line": truncated,
                "truncated_lines": truncated_lines, "problems": list(dict.fromkeys(problems))}

    def valid_rows(self, path: Path | None = None) -> list[dict]:
        """The rows that count (accepted rounds of their unit), in file order."""
        path = Path(path) if path is not None else self.cfg.output_dir() / f"{self.cfg.run}.jsonl"
        specs = self.unit_specs()
        by_session = {s.session_id: s for s in specs}
        accepted = self._scan_rows(path, specs)["accepted_rounds"]
        out = []
        for row in _read_jsonl(path)[0]:
            spec = by_session.get(row.get("session_id")) if isinstance(row, dict) else None
            if spec and (spec.label, row.get("segment", 0), row.get("round")) in accepted:
                out.append(row)
        return out

    def _history_from_rows(self, spec: UnitSpec, rounds: dict) -> tuple[list, list[str]]:
        """RoundRecords of the accepted rounds 1..k of a group game, rebuilt from their rows.

        Earnings, punishment cost and points received are recomputed with the
        game rules (as play_group does); the stored values must agree.
        """
        p, n = self.cfg.params, self.cfg.params.group_size
        history, problems = [], []
        for r in sorted(rounds):
            rows = rounds[r]
            where = f"unit {spec.label} round {r}"
            con = {x["agent_id"]: x for x in rows if x.get("step") == "contribute"}
            contributions = [con[a].get("contribution") for a in range(1, n + 1)]
            if not all(is_valid_contribution({"contribution": c}, p) for c in contributions):
                problems.append(f"{where}: a stored contribution is not a valid decision")
                break
            earnings = project_payoffs(p, contributions)
            rec = RoundRecord(r, contributions, earnings, final_earnings=earnings)
            pun = {}
            if spec.condition == "P":
                pun = {x["agent_id"]: x for x in rows if x.get("step") == "punish"}
                try:
                    rec.punishment = [[pun[i + 1]["punishments"][str(j + 1)] if j != i else 0
                                       for j in range(n)] for i in range(n)]
                except (KeyError, TypeError):
                    problems.append(f"{where}: stored punishments are incomplete")
                    break
                if not all(is_valid_punishment({"punishments": pun[i + 1]["punishments"]}, p,
                                               [j + 1 for j in range(n) if j != i],
                                               punishment_budget(earnings[i])) for i in range(n)):
                    problems.append(f"{where}: a stored punishment is not a valid decision")
                    break
                rec.final_earnings, rec.cost_paid, rec.received = apply_punishment(
                    p, earnings, rec.punishment)
            stored = [(con[a].get(k), want) for a in range(1, n + 1) for k, want in (
                ("group_total", sum(contributions)),
                ("payoff_before_punishment", earnings[a - 1]),
                ("payoff", rec.final_earnings[a - 1]))]
            stored += [(pun[a].get(k), want) for a in pun for k, want in (
                ("punishment_cost_paid", rec.cost_paid[a - 1]),
                ("punishment_points_received", rec.received[a - 1]),
                ("payoff", rec.final_earnings[a - 1]))]
            if any(got != want for got, want in stored):
                problems.append(f"{where}: stored earnings differ from the ones recomputed from "
                                "the decisions")
                break
            history.append(rec)
        return history, problems

    def _scan_raw_log(self, path: Path, specs: list[UnitSpec]) -> dict:
        """Counters per segment and model, rebuilt from the run's raw-log records.

        The same counting as _on_response / _count_invalid: a record with
        "usage" is a billed response; an accepted payload is a success record
        not followed by an "invalid_payload" event; parse failures are the
        retried records with error_kind "parse". Segments are delimited by
        the run's pgg_run_start (0) and pgg_run_resume events. The system
        message of each session is compared with the card.

        Also: "accepted", a Counter of _call_key -> accepted responses (the
        record's "call", else read from its prompt; an invalid_payload event
        takes back the success record it rejected), and "marked", the
        _call_keys that already have a "pgg_discarded" event.

        n_reasoning_capped: the success record's "reasoning_capped", else
        computed from its usage (older logs), taken back with its record by an
        invalid_payload event. n_transport / n_deadline: retried attempts with
        error_kind "transport" (error_subkind "deadline"). An attempt past its
        deadline adds its cost when its usage was logged; otherwise (also every
        such record of the code before A3, which logged nothing of the
        response) it is counted in n_cost_unknown.
        """
        sessions = {s.session_id: s for s in specs}
        per_segment: dict[int, dict] = {}
        events, problems, started = [], [], set()
        system_text: dict[str, str] = {}
        accepted: dict[tuple, int] = {}
        marked: set = set()
        recent: dict[str, list] = {}           # session -> [(call key, parsed)] (older logs)
        capped: dict[tuple, bool] = {}         # call key -> its last success record was capped
        n_unparsed = 0
        seg = 0
        lines, ends_with_newline = _read_jsonl(path)
        for rec in lines:
            if not isinstance(rec, dict):
                n_unparsed += 1
                continue
            event = rec.get("event")
            if event in ("pgg_run_start", "pgg_run_resume") and rec.get("run") == self.cfg.run:
                seg = rec.get("segment", 0)
                events.append(rec)
                per_segment.setdefault(seg, {k: _new_stats() for k in self.cfg.models})
                continue
            spec = sessions.get(rec.get("session_id"))
            if spec is None:
                continue
            key = spec.model_key
            if rec.get("model") != self.cfg.models[key]:
                problems.append(f"raw log: session {spec.session_id} was called with model "
                                f"{rec.get('model')!r}, the config has {self.cfg.models[key]!r}")
                continue
            s = per_segment.setdefault(seg, {k: _new_stats() for k in self.cfg.models})[key]
            started.add(spec.label)
            if event == "late_response":        # billed after its attempt was abandoned
                if "usage" in rec:
                    self._count_response(s, key, {
                        "usage": rec.get("usage"), "finish_reason": rec.get("finish_reason"),
                        "provider": rec.get("provider"), "provider_error": False})
                continue
            if event == "invalid_payload":
                s["n_invalid"] += 1
                s["n_accepted"] -= 1            # its success record was counted below
                if isinstance(rec.get("call"), dict):
                    ck = _call_key(rec["call"].get("segment", seg), spec.session_id, rec["call"])
                else:                           # older log: the success record with this payload
                    ck = next((c for c, parsed in reversed(recent.get(spec.session_id, []))
                               if parsed == rec.get("response_parsed")), None)
                    if ck is not None:
                        recent[spec.session_id].remove((ck, rec.get("response_parsed")))
                if ck is not None and accepted.get(ck):
                    accepted[ck] -= 1
                if ck is not None and capped.pop(ck, False):
                    s["n_reasoning_capped"] -= 1
                continue
            if event == "pgg_discarded":
                call = rec.get("call") if isinstance(rec.get("call"), dict) else {}
                marked.add(_call_key(call.get("segment"), spec.session_id, call))
                continue
            if event is not None:
                continue
            messages = rec.get("messages")
            if spec.session_id not in system_text and isinstance(messages, list) and messages:
                system_text[spec.session_id] = (messages[0] or {}).get("content")
            if rec.get("error_kind") == "transport" and rec.get("retrying"):
                if rec.get("error_subkind") == "deadline":
                    s["n_deadline"] += 1
                    self._count_deadline_cost(s, key, rec.get("usage"),
                                              rec.get("cost_unknown", True),
                                              rec.get("late_response", False))
                else:
                    s["n_transport"] += 1
                continue
            if "usage" in rec:                  # a response arrived: billed
                self._count_response(s, key, {
                    "usage": rec.get("usage"), "finish_reason": rec.get("finish_reason"),
                    "provider": rec.get("provider"),
                    "provider_error": rec.get("error_kind") == "provider",
                    "provider_mismatch": rec.get("provider_mismatch") is True})
            if "response_parsed" in rec:
                s["n_accepted"] += 1
                call = rec.get("call") if isinstance(rec.get("call"), dict) else None
                if call is None:
                    call = _call_from_messages(messages)
                    if call is not None:
                        ck = _call_key(seg, spec.session_id, call)
                        recent.setdefault(spec.session_id, []).append(
                            (ck, rec.get("response_parsed")))
                else:
                    ck = _call_key(call.get("segment", seg), spec.session_id, call)
                is_capped = rec.get("reasoning_capped")
                if "reasoning_capped" not in rec:        # older log
                    is_capped = self.llm.reasoning_capped(rec.get("usage"),
                                                          rec.get("max_tokens", self.max_tokens))
                s["n_reasoning_capped"] += bool(is_capped)
                if call is not None:
                    accepted[ck] = accepted.get(ck, 0) + 1
                    capped[ck] = bool(is_capped)
            elif rec.get("retrying") and rec.get("error_kind") == "parse":
                s["n_parse_fail"] += 1
        for session_id, text in system_text.items():
            card = sessions[session_id].card
            if text != system_message(card)["content"]:
                problems.append(f"card {card.card_id}/{card.style}: the text differs from the "
                                "one in the raw log of the earlier segments")
        return {"per_segment": per_segment, "events": events, "started": started,
                "n_sessions_checked": len(system_text), "accepted": accepted, "marked": marked,
                "n_unparsed_lines": n_unparsed, "ends_with_newline": ends_with_newline,
                "problems": list(dict.fromkeys(problems))}

    def resume_plan(self) -> ResumePlan:
        """What a resumed segment of this run has to do. Reads only; writes nothing.

        ValueError when there is nothing to resume; config differences and
        anomalies are collected in .problems (run(resume=True) refuses them).
        """
        cfg = self.cfg
        out_dir = cfg.output_dir()
        path = out_dir / f"{cfg.run}.jsonl"
        if not path.is_file():
            raise ValueError(f"nothing to resume: {path} does not exist")
        problems: list[str] = []
        summary_path = out_dir / f"{cfg.run}_summary.json"
        previous = None
        if summary_path.is_file():
            try:
                previous = json.loads(summary_path.read_text(encoding="utf-8"))
            except ValueError:
                problems.append(f"{summary_path.name} is not valid JSON")
        specs = self.unit_specs()
        rows = self._scan_rows(path, specs)
        problems += rows["problems"]
        log_path = self._raw_log_path()
        log = self._scan_raw_log(log_path, specs) if log_path and log_path.is_file() else None
        if log is not None:
            problems += log["problems"]
            if not log["events"]:
                log = None                     # not this run's log

        # discarded: accepted responses of earlier segments without a row
        unmarked: list = []
        if log is not None:
            by_session = {s.session_id: s for s in specs}
            for ck, n in sorted(log["accepted"].items(), key=lambda kv: _short(kv[0])):
                n_lost = n - (1 if ck in rows["row_calls"] else 0)
                if n_lost <= 0:
                    continue
                seg_k, session_id = ck[0], ck[1]
                model_key = by_session[session_id].model_key
                st = log["per_segment"].setdefault(seg_k, {k: _new_stats() for k in cfg.models})
                st[model_key]["n_discarded"] += n_lost
                if ck not in log["marked"]:
                    call = dict(zip(("segment", "step", "round", "agent_id", "others_mean"),
                                    (seg_k, *ck[2:])))
                    unmarked += [(model_key, session_id, call)] * n_lost

        # partial group games go on from their first round not accepted
        by_label = {s.label: s for s in specs}
        histories: dict = {}
        resume_points: list[dict] = []
        for label, prog in rows["progress"].items():
            spec = by_label[label]
            if spec.arm != "group":
                resume_points.append({"unit": label, "from_round": None, "rounds_kept": 0,
                                      "kept_from_segments": []})
                continue
            history, bad = self._history_from_rows(spec, prog["rounds"])
            problems += bad
            histories[label] = history
            resume_points.append({"unit": label, "from_round": len(history) + 1,
                                  "rounds_kept": len(history),
                                  "kept_from_segments": prog["segments"]})

        # config: the previous summary's "config", else the last start event's;
        # an older summary is compared on the fields it has
        checked: list[str] = []
        current = self.config_record()
        reference = (previous or {}).get("config")
        if reference is None and log is not None:
            reference = next((e["config"] for e in reversed(log["events"]) if "config" in e), None)
        if reference is not None:
            checked.append("config")
            for k in sorted(set(reference) | set(current)):
                if reference.get(k) != current.get(k):
                    problems.append(f"config {k}: earlier {_short(reference.get(k))}, "
                                    f"now {_short(current.get(k))}")
        elif previous is not None:
            for k, v in self._legacy_config().items():
                if k in previous:
                    checked.append(k)
                    if previous[k] != v:
                        problems.append(f"config {k}: earlier {_short(previous[k])}, now {_short(v)}")
            if "per_model" in previous:
                checked.append("models")
                if set(previous["per_model"]) != set(cfg.models.values()):
                    problems.append(f"config models: earlier {sorted(previous['per_model'])}, "
                                    f"now {sorted(cfg.models.values())}")
        else:
            problems.append("no previous summary and no config in the raw log: "
                            "the config cannot be checked")
        unit_order = (previous or {}).get("unit_order")
        if unit_order is None and log is not None:
            unit_order = log["events"][-1].get("unit_order")
        if unit_order is None:
            problems.append("no earlier unit_order to compare")
        else:
            checked.append("unit_order")
            if unit_order != [s.label for s in specs]:
                problems.append("unit_order differs from the earlier one (models, cards, design, "
                                "run name or seed_namespace changed)")
        if log is not None:
            checked.append(f"card texts in the raw log ({log['n_sessions_checked']} sessions)")
        if rows["n_length_checked"]:
            checked.append(f"card lengths of the rows ({rows['n_length_checked']} rows)")

        # segments
        known = {0} | set(rows["rows_per_segment"])
        if log is not None:
            known |= set(log["per_segment"])
        if previous is not None:
            known.add(previous.get("segment", 0))
        segment = max(known) + 1

        # cost and counts of the earlier segments: raw log, else summary
        by_slug = {slug: k for k, slug in cfg.models.items()}
        summary_cost = (previous or {}).get("total_cost_usd")
        extra = 0.0
        if log is not None:
            source = "raw_log"
            prior = {k: _merge_stats(*(st[k] for st in log["per_segment"].values()))
                     for k in cfg.models}
            cost_check = {"source": source}
            if summary_cost is not None:
                covered = previous.get("segment", 0)
                raw_covered = sum(st["cost_usd"] for seg, by_model in log["per_segment"].items()
                                  if seg <= covered for st in by_model.values())
                diff = summary_cost - raw_covered
                cost_check.update(summary_segment=covered, summary_total_cost_usd=summary_cost,
                                  raw_log_cost_usd_same_segments=raw_covered,
                                  match=abs(diff) < 1e-9)
                # the summary saw more than the log holds: count the larger
                extra = diff if diff >= 1e-9 else 0.0
        elif previous is not None:
            source = "summary"
            prior = {k: _new_stats() for k in cfg.models}
            for slug, st in (previous.get("per_model") or {}).items():
                if slug in by_slug:
                    prior[by_slug[slug]] = _merge_stats(st)
            cost_check = {"source": source, "summary_total_cost_usd": summary_cost}
            extra = max(0.0, (summary_cost or 0.0) - sum(s["cost_usd"] for s in prior.values()))
        else:
            source = "none"
            prior = {k: _new_stats() for k in cfg.models}
            cost_check = {"source": source}
            problems.append("neither the run's raw log nor a previous summary holds the cost so "
                            "far: the budget cannot go on")

        # summary entries of the earlier segments
        old = {e.get("segment"): e for e in (previous or {}).get("segments", [])}
        if previous is not None and "segments" not in previous:      # summary of a first run
            old[previous.get("segment", 0)] = {
                "stop_reason": previous.get("stop_reason"), "duration_s": previous.get("duration_s"),
                "cost_usd": previous.get("total_cost_usd"), "per_model": previous.get("per_model")}
        started_by_seg = {e.get("segment", 0): e for e in (log["events"] if log else [])}
        segments = []
        for seg in sorted(known):
            entry = old.get(seg, {})
            item = {"segment": seg, "summary_written": seg in old,
                    "stop_reason": entry.get("stop_reason"), "duration_s": entry.get("duration_s")}
            # operational settings and code version, as the segment recorded them
            # (summary entry, else its start / resume event; absent before #46)
            for k in ("stalled", "request_deadline_s", "stall_timeout_s", "code_version", "lock",
                      "resume_points", "n_discarded", "timeout_change", "code_change",
                      "provider_policy"):
                if k in entry:
                    item[k] = entry[k]
                elif k in started_by_seg.get(seg, {}):
                    item[k] = started_by_seg[seg][k]
            if log is not None:
                by_model = log["per_segment"].get(seg, {})
                item.update(cost_usd=sum(s["cost_usd"] for s in by_model.values()),
                            n_responses=sum(s["n_responses"] for s in by_model.values()),
                            n_discarded=sum(s["n_discarded"] for s in by_model.values()),
                            **{k: sum(s[k] for s in by_model.values()) for k in _SEGMENT_TOTALS},
                            per_model={cfg.models[k]: s for k, s in by_model.items()})
            else:
                item.update(cost_usd=entry.get("cost_usd"), per_model=entry.get("per_model"))
            item["n_rows"] = rows["rows_per_segment"].get(seg, 0)
            item["n_units_completed"] = sum(1 for s in rows["complete"].values() if s == seg)
            segments.append(item)

        # request_deadline_s / stall_timeout_s: as the last earlier segment that
        # recorded them (segments of the code before #46 recorded none)
        now = {"request_deadline_s": self.deadline, "stall_timeout_s": self.stall_timeout}
        last = next((e for e in reversed(segments)
                     if any(e.get(k) is not None for k in TIMEOUT_SETTINGS)), None)
        timeout_change = None
        if last is None:
            timeout_check = ("not compared: no earlier segment recorded request_deadline_s / "
                             "stall_timeout_s (code before #46)")
        else:
            earlier = {k: last.get(k) for k in TIMEOUT_SETTINGS}
            timeout_check = f"compared with segment {last['segment']}: {earlier}"
            checked.append(f"request_deadline_s / stall_timeout_s (segment {last['segment']})")
            if earlier != now:
                timeout_change = {"from_segment": last["segment"], "earlier": earlier, "now": now,
                                  "allowed": cfg.allow_timeout_change}
                if not cfg.allow_timeout_change:
                    problems.append(
                        "request_deadline_s / stall_timeout_s differ from segment "
                        f"{last['segment']}: earlier {_short(earlier)}, now {_short(now)}; give the "
                        "same values (config / --request-deadline / --stall-timeout) or allow the "
                        "change with --allow-timeout-change")

        # A5: the code of this segment against the earlier segments' (recorded,
        # never refused: pilot_v2_20261005 went on with other commits too)
        now_commit = (self.code_version if self.code_version is not None
                      else code_version()).get("git_commit")
        earlier_commits = {e["segment"]: (e.get("code_version") or {}).get("git_commit")
                           for e in segments}
        differs = sorted(seg for seg, c in earlier_commits.items() if c != now_commit)
        code_change = None
        if differs:
            code_change = {"now": now_commit,
                           "earlier": {str(seg): c for seg, c in earlier_commits.items()},
                           "differs_from_segments": differs}

        if previous is not None:
            backup = self._backup_path(previous)
            if backup.exists() and backup.read_bytes() != summary_path.read_bytes():
                problems.append(f"{backup.name} exists with other content than {summary_path.name}")

        started = log["started"] if log is not None else set()
        return ResumePlan(
            segment=segment, prior_segments=sorted(known), n_units=len(specs),
            complete=rows["complete"], superseded=rows["superseded"], resume_points=resume_points,
            started_without_rows=[s.label for s in specs
                                  if s.label in started and s.label not in rows["units_with_rows"]],
            remaining=[s.label for s in specs if s.label not in rows["complete"]],
            prior_stats=prior, prior_source=source, prior_extra_cost=extra,
            cost_check=cost_check, segments=segments, n_rows=rows["n_rows"],
            rows_per_segment=rows["rows_per_segment"],
            results_ends_with_newline=rows["ends_with_newline"],
            truncated_last_line=rows["truncated_last_line"],
            truncated_lines=rows["truncated_lines"], previous_summary=previous,
            config_checked=checked, problems=list(dict.fromkeys(problems)),
            histories=histories, unmarked_discarded=unmarked,
            lock=read_run_lock(self._lock_path()),
            timeout_change=timeout_change, timeout_check=timeout_check,
            code_change=code_change)

    def _lock_path(self) -> Path:
        return self.cfg.output_dir() / f"{self.cfg.run}.lock"

    def _backup_path(self, previous: dict) -> Path:
        """<run>_summary.seg<k>.json, k = the last segment the summary describes."""
        return self.cfg.output_dir() / f"{self.cfg.run}_summary.seg{previous.get('segment', 0)}.json"

    def _apply_plan(self, plan: ResumePlan) -> None:
        self.plan = plan
        self.segment = plan.segment
        self.prior_stats = {k: _merge_stats(s) for k, s in plan.prior_stats.items()}
        self.prior_extra_cost = plan.prior_extra_cost
        self._histories = dict(plan.histories)
        for key, s in self.prior_stats.items():
            if (self.invalid_limit is not None
                    and s["n_invalid"] + s["n_parse_fail"] > self.invalid_limit):
                self.stopped_models[key] = "invalid_rate_cap"

    def _backup_summary(self, summary_path: Path) -> Path | None:
        """Copy the previous summary before it is replaced (never overwrites a copy)."""
        if self.plan.previous_summary is None or not summary_path.is_file():
            return None
        data = summary_path.read_bytes()
        backup = self._backup_path(self.plan.previous_summary)
        if backup.exists():
            if backup.read_bytes() != data:
                raise ValueError(f"{backup} exists with other content; not overwritten")
            return backup
        with open(backup, "xb") as f:
            f.write(data)
        return backup

    # -- signals -----------------------------------------------------------

    def _on_signal(self, signum, frame) -> None:
        """SIGINT / SIGTERM: no new call; inside the unit loop, leave it at once."""
        if self._interrupted is not None:
            return
        self._interrupted = signal.Signals(signum).name
        if self._raise_on_signal:
            raise RunInterrupted(self._interrupted)

    def _catch_signals(self, saved: dict) -> None:
        """Install _on_signal for SIGINT and SIGTERM (main thread only)."""
        if threading.current_thread() is not threading.main_thread():
            return
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous = signal.getsignal(sig)
            saved[sig] = previous if previous is not None else signal.SIG_DFL
            signal.signal(sig, self._on_signal)

    @staticmethod
    def _restore_signals(saved: dict) -> None:
        for sig, handler in saved.items():
            signal.signal(sig, handler)
        saved.clear()

    def _wait_pools(self) -> None:
        """After a signal: let the calls in flight end (they are billed and logged)."""
        while True:
            with self._lock:
                if not self._pools:
                    return
                pool = self._pools.pop(0)
            pool.shutdown(wait=True)

    # -- summary -----------------------------------------------------------

    def summary(self, started: float, results_path: Path | None = None) -> dict:
        """Totals over all segments, this segment, the earlier ones and the units."""
        per_model = {self.cfg.models[k]: _merge_stats(self.prior_stats[k], s)
                     for k, s in self.stats.items()}
        duration = time.time() - started
        units, superseded, rows, truncated = None, [], None, []
        if results_path is not None and self._specs and Path(results_path).is_file():
            rows = self._scan_rows(Path(results_path), self._specs)
            done = rows["complete"]
            superseded = rows["superseded"]
            truncated = rows["truncated_lines"] + ([{
                k: v for k, v in rows["truncated_last_line"].items() if k != "text"}]
                if rows["truncated_last_line"] else [])
            units = {"n_units": len(self._specs), "n_complete": len(done),
                     "n_complete_this_segment": sum(1 for s in done.values() if s == self.segment),
                     "n_partial": len(rows["progress"]),
                     "n_remaining": len(self._specs) - len(done)}
        resume_points = self.plan.resume_points if self.plan else []
        lock = ({k: v for k, v in self.lock.items()} if self.lock else None)
        current = {
            "segment": self.segment, "summary_written": True, "stop_reason": self.stop_reason,
            "duration_s": duration, "cost_usd": self.segment_cost,
            "n_responses": sum(s["n_responses"] for s in self.stats.values()),
            "per_model": {self.cfg.models[k]: dict(s) for k, s in self.stats.items()},
            "n_rows": rows["rows_per_segment"].get(self.segment, 0) if rows else None,
            "n_units_completed": units["n_complete_this_segment"] if units else None,
            "n_discarded": sum(s["n_discarded"] for s in self.stats.values()),
            **{k: sum(s[k] for s in self.stats.values()) for k in _SEGMENT_TOTALS},
            "stalled": self.stalled,
            "request_deadline_s": self.deadline, "stall_timeout_s": self.stall_timeout,
            "timeout_change": self.plan.timeout_change if self.plan else None,
            "code_version": self.code_version,
            "code_change": self.plan.code_change if self.plan else None,
            "provider_policy": dict(PROVIDER_POLICY),
            "lock": lock, "resume_points": resume_points,
        }
        segments = [*(self.plan.segments if self.plan else []), current]
        out = {
            "run": self.cfg.run, "seed_namespace": self.cfg.seed_namespace,
            "segment": self.segment, "resumed": self.segment > 0,
            "stop_reason": self.stop_reason, "stopped_models": dict(self.stopped_models),
            "budget_usd": self.cfg.budget_usd, "invalid_rate_cap": self.cfg.invalid_rate_cap,
            "invalid_limit_per_model": self.invalid_limit,
            "planned_calls_per_model": self.cfg.planned_calls_per_model(),
            "max_tokens": self.max_tokens, "request_timeout_s": self.timeout,
            "request_deadline_s": self.deadline, "stall_timeout_s": self.stall_timeout,
            "stalled": self.stalled, "code_version": self.code_version,
            "reasoning_effort": self._effort_summary(),
            "providers": self._providers_summary(),
            "isolated_frame": self.cfg.isolated_frame,
            "parallel_units": self.cfg.parallel_units, "workers": self.cfg.workers,
            "total_cost_usd": self.total_cost, "segment_cost_usd": self.segment_cost,
            "duration_s": duration,
            "n_provider_error": sum(s["n_provider_error"] for s in per_model.values()),
            "n_provider_unknown": sum(s["n_provider_unknown"] for s in per_model.values()),
            "n_discarded": sum(s["n_discarded"] for s in per_model.values()),
            **{k: sum(s[k] for s in per_model.values()) for k in _SEGMENT_TOTALS},
            "reasoning_capped_rule": (
                "reasoning_tokens >= max_tokens - "
                f"{self.llm.REASONING_RESERVE_TOKENS} (llm_client.REASONING_RESERVE_TOKENS): "
                "flagged on the row (reasoning_capped), kept as a decision, not re-requested; "
                "n_reasoning_capped counts such accepted decisions"),
            "timeout_changes": [s["timeout_change"] for s in segments if s.get("timeout_change")],
            "code_changes": [{"segment": s["segment"], **s["code_change"]}
                             for s in segments if s.get("code_change")],
            "provider_mismatch_rule": (
                "a response of a pinned model from another provider is not a decision: logged "
                "(provider_mismatch: true, content and cost), billed, re-requested within "
                "llm_client's attempt limit (max_retries = 4 per call); a call whose last attempt "
                "is a mismatch stops the run (provider_mismatch_limit). Changes prereg_pilot.md "
                "§8.2 item 5 (stop at the first mismatch)"),
            "per_model": per_model,
            "units": units,
            "resume_points": resume_points,
            "superseded_rows": superseded,
            "n_superseded_rows": sum(e["n_rows"] for e in superseded),
            "truncated_lines": truncated,
            "n_truncated_lines": len(truncated),
            "lock": lock,
            "row_validity_rule": (
                "a row counts only if its round is accepted (pgg_game.Engine.valid_rows): "
                "segments in order; a segment's rows of a unit replace the earlier rows from "
                "its first round on; complete rounds are accepted in order, the first "
                "incomplete round and the rest of that segment are superseded "
                "(superseded_rows); rows without a segment are segment 0; cut-off lines "
                "(truncated_lines) are no rows"),
            "segments": segments,
            "unit_order": list(self.unit_order),
            "config": self.config_record(),
        }
        if self.prior_extra_cost:
            out["prior_cost_not_in_raw_log_usd"] = self.prior_extra_cost
        if rows and rows["problems"]:
            out["row_problems"] = rows["problems"]
        return out

    def _write_summary(self, started, path, summary_path, log_path, event: str) -> dict:
        summary = self.summary(started, path)
        self.llm._append_log({"ts": time.time(), "event": event, **summary})
        raw_log = Path(self.llm.LOG_PATH)
        # line counts after the event; the summary is one JSON document
        summary["files"] = {
            "results": {"path": str(path), "lines": _count_lines(path)},
            "raw_log": {"path": str(raw_log), "lines": _count_lines(raw_log),
                        "redirected_for_run": log_path is not None},
            "summary": {"path": str(summary_path)},
            "summary_backups": [str(p) for p in sorted(
                summary_path.parent.glob(f"{self.cfg.run}_summary.seg*.json"))],
        }
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.files = summary["files"]
        return summary

    # -- whole run ---------------------------------------------------------

    def _start_event(self, out_dir: Path, todo: list[UnitSpec], backup: Path | None) -> dict:
        event = {"ts": time.time(), "event": "pgg_run_resume" if self.plan else "pgg_run_start",
                 "run": self.cfg.run, "segment": self.segment,
                 "seed_namespace": self.cfg.seed_namespace, "output_dir": str(out_dir),
                 "request_deadline_s": self.deadline, "stall_timeout_s": self.stall_timeout,
                 "timeout_change": self.plan.timeout_change if self.plan else None,
                 "code_version": self.code_version,
                 "code_change": self.plan.code_change if self.plan else None,
                 "provider_policy": dict(PROVIDER_POLICY), "lock": self.lock,
                 "unit_order": self.unit_order, "config": self.config_record()}
        if self.plan:
            p = self.plan
            event.update(
                prior_segments=p.prior_segments, prior_cost_usd=p.prior_cost_usd,
                prior_cost_source=p.prior_source, cost_check=p.cost_check,
                n_units=p.n_units, n_complete=len(p.complete), superseded_rows=p.superseded,
                resume_points=p.resume_points, started_without_rows=p.started_without_rows,
                n_discarded_found=len(p.unmarked_discarded),
                truncated_last_line=({k: v for k, v in p.truncated_last_line.items()
                                      if k != "text"} if p.truncated_last_line else None),
                remaining_units=[s.label for s in todo], stopped_models=dict(self.stopped_models),
                config_checked=p.config_checked,
                summary_backup=str(backup) if backup else None)
        return event

    def _log_state(self):
        """(size, mtime) of the raw log the run writes to; None if it does not exist."""
        try:
            st = Path(self.llm.LOG_PATH).stat()
        except (OSError, TypeError):
            return None
        return st.st_size, st.st_mtime_ns

    def _watch(self, futures) -> None:
        """Wait for the units; stop the run as "stalled" when the raw log stays unchanged.

        Returns when every unit has ended, after a signal, or at a stall. An
        exception of a unit cancels the units not started yet and is raised.
        """
        pending = set(futures)
        poll = min(1.0, self.stall_timeout / 4)
        last, since = self._log_state(), time.monotonic()
        while pending and self._interrupted is None:
            done, pending = wait(pending, timeout=poll, return_when=FIRST_EXCEPTION)
            for f in done:
                if f.exception() is not None:
                    for p in pending:
                        p.cancel()
                    raise f.exception()
            state, now = self._log_state(), time.monotonic()
            if state != last:
                last, since = state, now
            elif pending and now - since >= self.stall_timeout:
                self._stall(now - since, len(pending))
                return

    def _stall(self, idle_s: float, n_units_open: int) -> None:
        """The watchdog fired: no new call; the run ends without waiting for the calls in flight."""
        with self._lock:
            self.stalled = True
        detail = {"stall_timeout_s": self.stall_timeout, "idle_s": round(idle_s, 3),
                  "n_units_not_ended": n_units_open, "raw_log": str(self.llm.LOG_PATH)}
        if self.stop_reason is None:
            self._stop("stalled", **detail)
        else:                              # another reason came first; still recorded
            self.llm._append_log({"ts": time.time(), "event": "pgg_run_stalled",
                                  "run": self.cfg.run, "stop_reason": self.stop_reason, **detail})

    def run(self, *, resume: bool = False) -> Path:
        """Run the design, or with resume=True the units an earlier run left (module docstring)."""
        cfg = self.cfg
        cfg.validate()                     # again: the output directory may be gone by now
        self.code_version = code_version()
        problem = code_version_problem(self.code_version)
        if problem is not None and _REQUIRE_VERIFIED_CODE:
            # A5: before the lock, any write and any call
            raise ValueError(f"run {cfg.run!r} not {'resumed' if resume else 'started'}, "
                             f"no call made: {problem}")
        out_dir = cfg.output_dir()
        path = out_dir / f"{cfg.run}.jsonl"
        summary_path = out_dir / f"{cfg.run}_summary.json"
        self._specs = self.unit_specs()
        self.unit_order = [s.label for s in self._specs]
        if resume:
            if not path.is_file():
                raise ValueError(f"nothing to resume: {path} does not exist")
        else:
            out_dir.mkdir(exist_ok=True)   # the parent exists (validate)
        # no other process may run or resume this run at the same time
        self.lock = acquire_run_lock(self._lock_path())
        try:
            return self._run_locked(resume, out_dir, path, summary_path)
        finally:
            release_run_lock(self.lock)

    def _record_truncated(self, cut: dict) -> None:
        """Record the cut-off last line in <run>.partial.jsonl (once), before a newline closes it."""
        if (cut["line"], cut["sha256"]) in self._recorded_truncated():
            return
        rec = {"ts": time.time(), "run": self.cfg.run, "file": f"{self.cfg.run}.jsonl",
               "found_in_segment": self.segment, **cut}
        with open(self._partial_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def _close_raw_log_line(self) -> bool:
        """End a raw log whose last record was cut off with a newline; True if one was added."""
        try:
            with open(self.llm.LOG_PATH, "rb") as f:
                f.seek(-1, os.SEEK_END)
                last = f.read(1)
        except (OSError, TypeError, ValueError):       # missing or empty
            return False
        if last == b"\n":
            return False
        with open(self.llm.LOG_PATH, "ab") as f:
            f.write(b"\n")
        return True

    def _run_locked(self, resume: bool, out_dir: Path, path: Path, summary_path: Path) -> Path:
        cfg = self.cfg
        backup = None
        if resume:
            # everything is checked before the first call and the first write
            plan = self.resume_plan()
            if plan.problems:
                raise ValueError(f"run {cfg.run!r} not resumed, no call made: "
                                 + "; ".join(plan.problems))
            self._apply_plan(plan)
            backup = self._backup_summary(summary_path)
            todo = [s for s in self._specs if s.label not in plan.complete]
        else:
            todo = self._specs
        started = time.time()
        # "x": never overwrite a run; "a": a resumed run only appends
        with open(path, "a" if resume else "x", encoding="utf-8") as out:
            if resume and self.plan.truncated_last_line:
                self._record_truncated(self.plan.truncated_last_line)
            if resume and not self.plan.results_ends_with_newline:
                out.write("\n")            # a cut-off last line stays as it is, on its own
                out.flush()
            log_path = cfg.raw_log_path()
            previous_log = self.llm.set_log_path(log_path) if log_path else None
            self._run_log = Path(self.llm.LOG_PATH)
            self._out = out
            handlers: dict = {}
            try:
                try:
                    self._catch_signals(handlers)
                    raw_closed = self._close_raw_log_line()
                    self.llm._append_log({**self._start_event(out_dir, todo, backup),
                                          "raw_log_cut_line_closed": raw_closed})
                    if self.lock.get("stale_lock"):
                        self._log({"ts": time.time(), "event": "pgg_stale_lock_taken_over",
                                   "run": cfg.run, "segment": self.segment, "lock": self.lock})
                    for model_key, session_id, call in (self.plan.unmarked_discarded
                                                        if self.plan else []):
                        self._discard(model_key, session_id, call, "found_on_resume")
                    units = self.units(todo)
                    # units in a pool (in order when parallel_units is 1); the
                    # main thread watches for a stall and receives the signals
                    pool = self._pool(cfg.parallel_units)
                    try:
                        futures = [pool.submit(self._run_unit, unit) for unit in units]
                        self._raise_on_signal = True
                        self._watch(futures)
                    finally:
                        self._raise_on_signal = False
                        self._release(pool)
                except RunInterrupted:
                    self._raise_on_signal = False
            finally:
                self._raise_on_signal = False
                interrupted = self._interrupted
                if interrupted is not None:
                    self._stop("interrupted", signal=interrupted)
                if self.stalled:
                    with self._lock:       # calls still in flight write no row any more
                        self._out = None
                out.flush()
                summary = self._write_summary(started, path, summary_path, log_path, "pgg_run_end")
                if interrupted is not None and not self.stalled:
                    # the summary is on disk; a second signal now acts as usual
                    self._restore_signals(handlers)
                    self._wait_pools()
                    out.flush()
                    summary = self._write_summary(started, path, summary_path, log_path,
                                                  "pgg_run_summary_updated")
                self._restore_signals(handlers)
                with self._lock:
                    self._out = None
                if previous_log is not None:
                    self.llm.set_log_path(previous_log)
        if self.aborted is not None:
            raise self.aborted
        if self.stop_reason is not None:
            raise RunStopped(f"run {cfg.run!r} stopped: {self.stop_reason} "
                             f"(accumulated cost {self.total_cost:.4f} USD)")
        return path


# --------------------------------------------------------------------------
# Dry run and CLI
# --------------------------------------------------------------------------

def dry_run_report(*, models: dict[str, str], n_cells: int, params: GameParams,
                   conditions, arms, groups_per_cell, isolated_reps, n_points,
                   max_tokens: int | None = None) -> str:
    counts = pgg_cost.call_counts(
        n_cells=n_cells, conditions=conditions, groups_per_cell=groups_per_cell,
        isolated_reps=isolated_reps, n_points=n_points, group_size=params.group_size,
        rounds=params.rounds, arms=arms)
    est = pgg_cost.estimate(models, counts)
    description = (
        f"Tasarım: {n_cells} hücre (kart x stil), koşul {'+'.join(conditions)}, "
        f"kollar {'+'.join(arms)}, hücre başına {groups_per_cell} homojen grup "
        f"({params.group_size} ajan x {params.rounds} tur), izole çizelge "
        f"{isolated_reps} tekrar x {n_points} değer (değer başına ayrı çağrı).")
    report = pgg_cost.format_report(est, description=description)
    if max_tokens:
        report += "\n" + pgg_cost.format_ceiling(models, counts, max_tokens)
    return report


def resolve_output(s: dict) -> dict:
    """RunConfig output fields of a real run; ValueError when not known or not usable.

    Order: runs_dir (CLI --runs-dir, else config "runs_dir"), else the
    PGG_RUNS_DIR environment variable, else default_runs_dir(). The legacy
    results_dir (CLI --results-dir or config) is an explicit alternative: the
    raw log then goes to results_dir/raw_calls.jsonl. Either way the path is
    absolute and outside the git worktree; nothing is created here.
    """
    runs_dir, results_dir = s.get("runs_dir"), s.get("results_dir")
    if runs_dir is not None and results_dir is not None:
        raise ValueError("give either runs_dir or results_dir, not both")
    if results_dir is not None:
        path = check_output_dir(results_dir, must_exist=False, what="results_dir")
        return {"results_dir": path, "log_path": path / "raw_calls.jsonl"}
    source = "--runs-dir / config runs_dir"
    if runs_dir is None and os.environ.get(RUNS_DIR_ENV):
        runs_dir, source = os.environ[RUNS_DIR_ENV], RUNS_DIR_ENV
    if runs_dir is None:
        runs_dir, source = default_runs_dir(), "default (workspace/runs)"
        if runs_dir is None:
            raise ValueError(
                "the runs directory is not known here: give --runs-dir, config \"runs_dir\" "
                f"or {RUNS_DIR_ENV} (an absolute, existing directory outside the worktree)")
    return {"runs_dir": check_output_dir(runs_dir, must_exist=True, what=f"runs_dir [{source}]")}


def open_choices(s: dict) -> list[str]:
    """Config values the user still has to choose (placeholders), in any setting
    except comments (keys starting with "_")."""
    return [p for key, value in s.items() if not key.startswith("_")
            for p in placeholders_in(value, key)]


# Settings the call counts of a dry run depend on (besides "params").
COUNT_SETTINGS = ("conditions", "arms", "groups_per_cell", "isolated_reps", "isolated_points")


def count_blockers(s: dict) -> list[str]:
    """Placeholders that keep a dry run from counting the calls.

    The number of cells comes from the cards file (filtered by "cities"), else
    from "cells"; a placeholder cards file only blocks when no cells are given.
    """
    out = [p for key in COUNT_SETTINGS for p in placeholders_in(s.get(key), key)]
    cards = [p for key in ("cards", "cities") for p in placeholders_in(s.get(key), key)]
    if cards and not (is_placeholder(s.get("cards")) and s.get("cells") is not None):
        out += cards
    return out


def prereg_problem(s: dict) -> str | None:
    """Why a real run may not start under the pre-registration lock (None = it may).

    Only a config with "prereg_approved" is gated: the field must be exactly
    true (the user approved the prereg file). The CLI cannot set it.
    """
    if "prereg_approved" not in s or s["prereg_approved"] is True:
        return None
    return (f"prereg_approved is {json.dumps(s['prereg_approved'], ensure_ascii=False)}, not "
            "true: the pre-registration (prereg_*.md) of this config is not approved by the "
            "user yet, so no game call may be made (dry runs still work)")


def _csv(value: str) -> list[str]:
    return [v for v in value.split(",") if v]


def _parse_effort(value: str):
    if "=" not in value:
        return value
    return dict(item.split("=", 1) for item in _csv(value))


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Public goods game engine. --dry-run prints call counts and an "
                    "estimated cost without any API call.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--resume", action="store_true",
                    help="go on with an interrupted run in the same directory (new segment); "
                         "with --dry-run only print what is complete and what is left")
    ap.add_argument("--run", help="run name (else config \"run\"); output goes to "
                                  "<runs-dir>/<run>/")
    ap.add_argument("--config", help="JSON file with the options below (CLI wins)")
    ap.add_argument("--cards", help="JSON list of {card_id, style, text}")
    ap.add_argument("--cities", help="comma-separated: keep only these cards' \"city\" values")
    ap.add_argument("--cells", type=int, help="dry-run only: number of card x style cells "
                    "(default: cards file, else 6 = 2 identities x 3 styles)")
    ap.add_argument("--models", help="comma-separated keys or slugs (default: the 3 mini-pilot "
                                     "models)")
    ap.add_argument("--conditions", help="comma-separated, N and/or P (default N)")
    ap.add_argument("--arms", help="comma-separated, group and/or isolated (default both)")
    ap.add_argument("--groups-per-cell", type=int)
    ap.add_argument("--isolated-reps", type=int)
    ap.add_argument("--points", help="isolated conditioning values (default 0,5,10,15,20)")
    ap.add_argument("--isolated-frame", choices=ISOLATED_FRAMES,
                    help="isolated arm wording: one_shot (default) or repeated")
    ap.add_argument("--group-size", type=int)
    ap.add_argument("--rounds", type=int)
    ap.add_argument("--endowment", type=int)
    ap.add_argument("--mpcr", type=float)
    ap.add_argument("--reasoning-effort", help="e.g. low, or deepseek=low,gpt=medium "
                    "(default: not sent, provider default)")
    ap.add_argument("--max-tokens", type=int)
    ap.add_argument("--request-timeout", type=float, dest="request_timeout_s",
                    help="client timeout per read / connect operation, seconds (default 300)")
    ap.add_argument("--request-deadline", type=float, dest="request_deadline_s",
                    help="wall-clock limit of one HTTP attempt, seconds (default 900); "
                         "on --resume it must equal the previous segment's")
    ap.add_argument("--stall-timeout", type=float, dest="stall_timeout_s",
                    help="stop the run as \"stalled\" after this many seconds without any "
                         "raw-log record (default 1800); on --resume it must equal the "
                         "previous segment's")
    ap.add_argument("--allow-timeout-change", action="store_true", default=None,
                    help="--resume: allow request_deadline_s / stall_timeout_s other than the "
                         "previous segment's (recorded in the summary, timeout_changes)")
    ap.add_argument("--max-invalid", type=int)
    ap.add_argument("--no-rationale", action="store_true", default=None)
    ap.add_argument("--workers", type=int)
    ap.add_argument("--parallel-units", type=int, help="group games / schedules at once")
    ap.add_argument("--seed-namespace", help="first part of the stable_seed key (default pgg)")
    ap.add_argument("--budget-usd", type=float, help="hard cap on accumulated usage.cost")
    ap.add_argument("--invalid-rate-cap", type=float,
                    help="per model, fraction of planned calls (e.g. 0.05)")
    ap.add_argument("--stop-on-length", action="store_true", default=None)
    ap.add_argument("--check-snapshot", action="store_true", default=None)
    ap.add_argument("--runs-dir", help=f"absolute, existing directory outside the worktree; "
                    f"output goes to <runs-dir>/<run>/ (else config runs_dir, {RUNS_DIR_ENV}, "
                    "or the orc workspace/runs)")
    ap.add_argument("--results-dir", help="legacy: absolute directory outside the worktree "
                    "for <run>.jsonl, the summary and raw_calls.jsonl")
    ap.add_argument("--write-code-version", metavar="DIR",
                    help=f"write {CODE_VERSION_FILE} into a code directory copied out of git "
                         "(e.g. by git archive), run from the git checkout; nothing else is done")
    ap.add_argument("--code-commit", metavar="REV",
                    help="with --write-code-version: the commit DIR was copied from (default HEAD)")
    return ap


def settings_from_args(args) -> dict:
    """Config file first, then explicitly given CLI options on top."""
    s = {}
    if args.config:
        s.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    cli = {
        "run": args.run, "cards": args.cards, "cells": args.cells,
        "cities": _csv(args.cities) if args.cities else None,
        "parallel_units": args.parallel_units, "seed_namespace": args.seed_namespace,
        "budget_usd": args.budget_usd, "invalid_rate_cap": args.invalid_rate_cap,
        "stop_on_length": args.stop_on_length, "check_snapshot": args.check_snapshot,
        "models": _csv(args.models) if args.models else None,
        "conditions": _csv(args.conditions) if args.conditions else None,
        "arms": _csv(args.arms) if args.arms else None,
        "groups_per_cell": args.groups_per_cell, "isolated_reps": args.isolated_reps,
        "isolated_points": [int(x) for x in _csv(args.points)] if args.points else None,
        "isolated_frame": args.isolated_frame,
        "reasoning_effort": _parse_effort(args.reasoning_effort) if args.reasoning_effort else None,
        "max_tokens": args.max_tokens, "max_invalid": args.max_invalid,
        "request_timeout_s": args.request_timeout_s,
        "request_deadline_s": args.request_deadline_s, "stall_timeout_s": args.stall_timeout_s,
        "allow_timeout_change": args.allow_timeout_change,
        "rationale": False if args.no_rationale else None, "workers": args.workers,
        "runs_dir": args.runs_dir, "results_dir": args.results_dir,
    }
    s.update({k: v for k, v in cli.items() if v is not None})
    params = dict(s.get("params", {}))
    params.update({k: v for k, v in (
        ("group_size", args.group_size), ("rounds", args.rounds),
        ("endowment", args.endowment), ("mpcr", args.mpcr)) if v is not None})
    s["params"] = GameParams(**params)
    return s


def run_config(run: str, s: dict, models: dict[str, str], output: dict) -> RunConfig:
    """RunConfig of a real (or resumed) run from settings_from_args."""
    return RunConfig(
        run=run, cards=load_cards(s["cards"], s.get("cities")),
        models=models, params=s["params"], conditions=tuple(s.get("conditions", ("N",))),
        arms=tuple(s.get("arms", ARMS)), groups_per_cell=s.get("groups_per_cell", 2),
        isolated_reps=s.get("isolated_reps", 2),
        isolated_points=tuple(s.get("isolated_points", ISOLATED_POINTS)),
        reasoning_effort=s.get("reasoning_effort"),
        max_tokens=s.get("max_tokens"), max_invalid=s.get("max_invalid", 3),
        rationale=s.get("rationale", True), workers=s.get("workers", 1),
        parallel_units=s.get("parallel_units", 1),
        seed_namespace=s.get("seed_namespace", "pgg"),
        budget_usd=s.get("budget_usd"), invalid_rate_cap=s.get("invalid_rate_cap"),
        stop_on_length=bool(s.get("stop_on_length", False)),
        check_snapshot=bool(s.get("check_snapshot", False)),
        request_timeout_s=s.get("request_timeout_s"),
        request_deadline_s=s.get("request_deadline_s"), stall_timeout_s=s.get("stall_timeout_s"),
        allow_timeout_change=bool(s.get("allow_timeout_change", False)),
        providers=resolve_providers(s.get("providers"), models),
        isolated_frame=s.get("isolated_frame", "one_shot"),
        **output)


def code_version_line(cv: dict) -> str:
    """One line on the code version for a dry run (a dirty code only warns there)."""
    problem = code_version_problem(cv)
    source = {"git": "git deposu", "stamp": CODE_VERSION_FILE}.get(cv.get("source"), "bilinmiyor")
    if problem is None:
        return f"Kod sürümü: {cv['git_commit']} (kaynak: {source}; temiz)"
    return (f"UYARI: kod sürümü doğrulanamadı ya da kod kirli (kaynak: {source}): {problem} — "
            "gerçek koşu ve --resume bu kodla BAŞLAMAZ")


def resume_report(engine: Engine, plan: ResumePlan) -> str:
    """--resume --dry-run: what a resumed segment would do (nothing is written)."""
    cfg = engine.cfg
    specs = {s.label: s for s in engine.unit_specs()}
    remaining = [specs[label] for label in plan.remaining]
    points = {p["unit"]: p for p in plan.resume_points}
    never = [s for s in remaining if s.label not in plan.started_without_rows
             and s.label not in points]
    cut = plan.truncated_last_line
    lines = [
        f"SÜRDÜRME PLANI (salt okunur: API çağrısı yok, hiçbir dosya yazılmadı): {cfg.output_dir()}",
        f"Önceki segmentler: {plan.prior_segments}; sürdürülürse yeni segment: {plan.segment}",
        f"Sonuç dosyası: {plan.n_rows} satır (segment başına {plan.rows_per_segment}); "
        + (f"son satır yarım kesilmiş (satır {cut['line']}, {cut['n_bytes']} bayt; sürdürmede "
           f"{cfg.run}.partial.jsonl'a kaydedilir, dosyada kalır)" if cut else "son satır tam")
        + (f"; daha önce kaydedilmiş yarım satır {len(plan.truncated_lines)} "
           f"(satır {[t['line'] for t in plan.truncated_lines]}, yok sayılır)"
           if plan.truncated_lines else ""),
        f"Birimler: toplam {plan.n_units}; tamam {len(plan.complete)}; "
        f"yarım (kaldığı turdan sürer) {len(points)}; "
        f"satırsız başlamış (çağrı var, satır yok) {len(plan.started_without_rows)}; "
        f"hiç başlanmamış {len(never)}; kalan (koşulacak) {len(remaining)}",
        "Geçerlilik kuralı: segmentler sırayla okunur; bir segmentin bir birime ait satırları "
        "başladığı turdan itibaren öncekilerin yerine geçer; tamamlanmış turlar (turun bütün "
        "ajan satırları, P'de ceza satırları da) sırayla kabul edilir, ilk eksik tur ve "
        "segmentin geri kalanı superseded olur. Birim, her turu kabul edilmişse tamamdır "
        "(izole çizelge tek blok: her koşul değeri bir satır).",
    ]
    for label, seg in plan.complete.items():
        lines.append(f"  tamam: {label} (segment {seg})")
    for p in plan.resume_points:
        if p["from_round"] is None:
            lines.append(f"  yarım -> baştan: {p['unit']} (izole çizelge)")
        else:
            lines.append(f"  yarım -> {p['from_round']}. turdan sürer: {p['unit']} "
                         f"(tur 1-{p['rounds_kept']} korunur, segment {p['kept_from_segments']})"
                         if p["rounds_kept"] else
                         f"  yarım -> 1. turdan: {p['unit']} (kabul edilmiş tur yok)")
    for p in plan.superseded:
        rounds = f", tur {p['rounds']}" if p["rounds"] is not None else ""
        lines.append(f"  superseded: {p['unit']} (segment {p['segment']}{rounds}, "
                     f"{p['n_rows']} satır)")
    for label in plan.started_without_rows:
        lines.append(f"  satırsız başlamış: {label}")
    n_disc = {k: st.get("n_discarded", 0) for k, st in plan.prior_stats.items()}
    lines.append(f"Atılan (discarded) yanıtlar — kabul edilmiş ama satıra dönüşmemiş, maliyeti "
                 f"bütçede: {sum(n_disc.values())} ({', '.join(f'{k} {n}' for k, n in n_disc.items())}"
                 f"); ham logda henüz işaretsiz {len(plan.unmarked_discarded)} (sürdürmede "
                 "found_on_resume olarak işaretlenir)")
    lock = plan.lock
    if lock is None:
        lines.append("Kilit: yok")
    else:
        what = {"alive": "sahibi yaşıyor — sürdürme şu an BAŞLAMAZ",
                "stale": "bayat (sahibi ölü) — sürdürmede devralınır ve loglanır",
                "unknown": "doğrulanamıyor (başka makine ya da okunamıyor) — sürdürme başlamaz"}
        lines.append(f"Kilit: PID {lock.get('pid')} ({lock.get('host')}, "
                     f"{lock.get('started_at_utc')}): {what[lock['state']]}")
    budget = cfg.budget_usd
    lines.append(f"Önceki maliyet: {plan.prior_cost_usd:.6f} USD (kaynak: {plan.prior_source}; "
                 f"kontrol: {plan.cost_check})"
                 + (f"; bütçe {budget} USD, kalan {budget - plan.prior_cost_usd:.6f} USD"
                    if budget is not None else ""))
    limit = cfg.invalid_limit()
    lines.append("Önceki sayımlar (model başına): " + "; ".join(
        f"{k}: yanıt {s['n_responses']}, kabul {s['n_accepted']}, geçersiz {s['n_invalid']}, "
        f"parse {s['n_parse_fail']}, sağlayıcı hatası {s['n_provider_error']}"
        + (" — geçersiz tavanı aşılmış, koşulmaz"
           if limit is not None and s["n_invalid"] + s["n_parse_fail"] > limit else "")
        for k, s in plan.prior_stats.items()) + (f" (geçersiz sınırı {limit})" if limit else ""))
    reserve = engine.llm.REASONING_RESERVE_TOKENS
    lines.append(
        f"Akıl yürütme tavanı (reasoning_tokens >= max_tokens - {reserve} = "
        f"{engine.max_tokens - reserve}; işaretlenir, atılmaz) — kabul edilen kararlarda: "
        + ", ".join(f"{k} {s['n_reasoning_capped']}" for k, s in plan.prior_stats.items()))
    lines.append(
        "Bağlantı hatası / süre aşımı (yeniden denenmiş denemeler): " + ", ".join(
            f"{k} {s['n_transport']} / {s['n_deadline']}" for k, s in plan.prior_stats.items())
        + "; süre aşımında maliyeti bilinmeyen: " + ", ".join(
            f"{k} {s['n_cost_unknown']}" for k, s in plan.prior_stats.items())
        + "; süre aşımı maliyeti (bütçede): "
        f"{sum(s['deadline_cost_usd'] for s in plan.prior_stats.values()):.6f} USD")
    lines.append(
        "Sağlayıcı uyuşmazlığı (karar sayılmadı, yeniden istendi, maliyeti bütçede): " + ", ".join(
            f"{k} {s['n_provider_mismatch']}" for k, s in plan.prior_stats.items()))
    calls: dict[str, dict[str, int]] = {k: {} for k in cfg.models}
    rounds = cfg.params.rounds
    for spec in remaining:
        kept = points.get(spec.label, {}).get("rounds_kept", 0) if spec.arm == "group" else 0
        for kind, n in spec.calls_by_kind:
            n_left = n * (rounds - kept) // rounds       # group kinds are per round
            calls[spec.model_key][kind] = calls[spec.model_key].get(kind, 0) + n_left
    total_calls, total_cost, priced = 0, 0.0, True
    parts = []
    for key, by_kind in calls.items():
        n = sum(by_kind.values())
        total_calls += n
        try:
            total_cost += sum(n_k * pgg_cost.cost_per_call(cfg.models[key], kind)
                              for kind, n_k in by_kind.items())
        except KeyError:
            priced = False
        parts.append(f"{key} {n}")
    lines.append(f"Kalan tahmini çağrı (kabul edilen karar; yeniden istekler hariç): "
                 f"{', '.join(parts)}; toplam {total_calls}")
    if priced:
        lines.append(f"Kalan tahmini maliyet (tahmin, pgg_cost): {total_cost:.4f} USD; "
                     f"önceki ile toplam {plan.prior_cost_usd + total_cost:.4f} USD")
    lines.append("Config karşılaştırması: " + ", ".join(plan.config_checked))
    lines.append(f"Süre sınırları: request_deadline_s={engine.deadline:g}, "
                 f"stall_timeout_s={engine.stall_timeout:g} (sürdürmede önceki segmentle "
                 f"karşılaştırılır; {plan.timeout_check})")
    change = plan.timeout_change
    if change is not None:
        diff = ", ".join(f"{k} {change['earlier'][k]:g} -> {change['now'][k]:g}"
                         for k in TIMEOUT_SETTINGS if change["earlier"][k] != change["now"][k])
        lines.append(
            f"  FARKLI (segment {change['from_segment']}'e göre): {diff}; "
            + ("--allow-timeout-change verildi: sürdürmeye izin var, değişiklik özete "
               "(timeout_changes) yazılır" if change["allowed"] else
               "aynı değerleri verin ya da --allow-timeout-change ile izin verin; "
               "aksi halde sürdürme başlamaz"))
    lines.append(f"İşletim ayarları (config karşılaştırması dışında): "
                 f"request_timeout_s={engine.timeout:g}, workers={cfg.workers}, "
                 f"parallel_units={cfg.parallel_units}")
    if engine.stall_timeout <= engine.deadline:
        lines.append("UYARI: stall_timeout_s, request_deadline_s'den büyük değil; tek bir uzun "
                     "deneme bekçiyi tetikleyebilir")
    lines.append(code_version_line(engine.code_version or code_version()))
    change = plan.code_change
    if change is not None:
        lines.append(
            f"Kod commit'i önceki segment(ler)den farklı ya da onlarda bilinmiyor: segment "
            f"{change['differs_from_segments']} (önceki: {change['earlier']}; şimdi: "
            f"{change['now']}); engellemez, özete code_change olarak yazılır")
    if plan.problems:
        lines.append("SORUN (sürdürme başlamaz):")
        lines += [f"  - {p}" for p in plan.problems]
    else:
        lines.append("Config tutarlı; sorun yok.")
    return "\n".join(lines)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.write_code_version:
        try:
            path = write_code_version(args.write_code_version, args.code_commit or "HEAD")
        except ValueError as e:
            print(f"HATA: {e}", file=sys.stderr)
            return 1
        stamp = json.loads(path.read_text(encoding="utf-8"))
        print(f"yazıldı: {path} (commit {stamp['git_commit']}, "
              f"{len(stamp['files_sha256'])} .py dosyası)")
        return 0
    if args.code_commit:
        build_parser().error("--code-commit needs --write-code-version")
    s = settings_from_args(args)
    params = s["params"]
    conditions = tuple(s.get("conditions", ("N",)))
    arms = tuple(s.get("arms", ARMS))
    groups_per_cell = s.get("groups_per_cell", 2)
    isolated_reps = s.get("isolated_reps", 2)
    points = tuple(s.get("isolated_points", ISOLATED_POINTS))
    names = s.get("models") or list(pgg_cost.PILOT_MODELS)
    run = s.get("run")

    cities = s.get("cities")
    if args.dry_run and args.resume:
        # read-only plan of a resumed run: no llm_client, no key, no write
        if not run or not s.get("cards"):
            build_parser().error("--resume needs --run and --cards")
        open_ = open_choices(s)
        if open_:
            print("SEÇİLMEMİŞ: " + ", ".join(open_), file=sys.stderr)
            return 1
        try:
            models = resolve_models(names, pgg_cost.KNOWN_MODELS)
            engine = Engine(run_config(run, s, models, resolve_output(s)), llm=OfflineLLM())
            plan = engine.resume_plan()
        except ValueError as e:
            print(f"HATA: {e}", file=sys.stderr)
            return 1
        print(resume_report(engine, plan))
        return 1 if plan.problems else 0
    if args.dry_run:
        models = resolve_models(names, pgg_cost.KNOWN_MODELS)
        blockers = count_blockers(s)
        if blockers:
            print("KURU ÇALIŞTIRMA — API çağrısı yapılmadı.\n"
                  f"ÇAĞRI SAYISI HESAPLANAMADI: şu ayarlar henüz seçilmedi (yer tutucu): "
                  f"{', '.join(blockers)}. Modeller: "
                  + ", ".join(f"{k}={v}" for k, v in models.items()))
        else:
            if s.get("cards") and not is_placeholder(s["cards"]):
                n_cells = len(load_cards(s["cards"], cities))
            else:
                n_cells = s.get("cells", 6)
            print(dry_run_report(
                models=models, n_cells=n_cells, params=params, conditions=conditions, arms=arms,
                groups_per_cell=groups_per_cell, isolated_reps=isolated_reps,
                n_points=len(points), max_tokens=s.get("max_tokens")))
        guards = {k: s[k] for k in ("max_tokens", "request_timeout_s", "request_deadline_s",
                                    "stall_timeout_s", "budget_usd",
                                    "invalid_rate_cap", "stop_on_length", "check_snapshot",
                                    "seed_namespace", "parallel_units", "workers",
                                    "isolated_frame") if s.get(k) is not None}
        print(f"Ayarlar: reasoning_effort={s.get('reasoning_effort') or 'gönderilmez'}, "
              + ", ".join(f"{k}={v}" for k, v in guards.items()))
        print(code_version_line(code_version()))
        if "prereg_approved" in s:
            problem = prereg_problem(s)
            print("Ön kayıt: onaylı (prereg_approved=true)" if problem is None else
                  f"ÖN KAYIT ONAYI YOK (gerçek koşu başlamaz): {problem}")
        open_ = open_choices(s)
        if open_:
            print("SEÇİLMEMİŞ (gerçek koşu başlamaz): " + ", ".join(open_))
        else:
            try:
                where = next(iter(resolve_output(s).values()))
                print(f"Çıktı dizini: {where} (mevcut)")
            except ValueError as e:
                print(f"ÇIKTI DİZİNİ KULLANILAMIYOR (gerçek koşu başlamaz): {e}")
        return 0

    # Everything that can stop a real run is checked here, before llm_client is
    # imported and before any call; the pre-registration lock first.
    problem = prereg_problem(s)
    if problem is not None:
        print(f"HATA: {problem}; gerçek koşu başlamadı, çağrı yapılmadı", file=sys.stderr)
        return 1
    if not run or not s.get("cards"):
        build_parser().error("a real run needs --run and --cards (or use --dry-run)")
    open_ = open_choices(s)
    if open_:
        print("HATA: seçilmemiş ayarlar (yer tutucu), gerçek koşu başlamadı: "
              + ", ".join(open_), file=sys.stderr)
        return 1
    try:
        output = resolve_output(s)
    except ValueError as e:
        print(f"HATA: çıktı dizini: {e}", file=sys.stderr)
        return 1
    problem = code_version_problem(code_version())
    if problem is not None and _REQUIRE_VERIFIED_CODE:
        print(f"HATA: kod sürümü: {problem}; gerçek koşu başlamadı, çağrı yapılmadı",
              file=sys.stderr)
        return 1
    llm = _llm()
    try:
        models = resolve_models(names, llm.MODELS_KNOWN)
        cfg = run_config(run, s, models, output)
        engine = Engine(cfg, llm=llm)
    except ValueError as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1
    if engine.stall_timeout <= engine.deadline:
        print(f"UYARI: stall_timeout_s ({engine.stall_timeout:g}) <= request_deadline_s "
              f"({engine.deadline:g}): a single long attempt can stop the run as stalled",
              file=sys.stderr)
    try:
        path = engine.run(resume=args.resume)
    except (ValueError, RunLocked) as e:     # refused before any call
        print(f"HATA: {e}", file=sys.stderr)
        return 1
    except (RunAborted, RunStopped) as e:
        print(f"HATA: {e}", file=sys.stderr)
        _print_files(engine.files, file=sys.stderr)
        _warn_stale_lock(engine)
        if engine.stalled:
            _exit_after_stall(1)
        return 1
    _warn_stale_lock(engine)
    if engine.stopped_models:
        print(f"UYARI: durdurulan modeller: {engine.stopped_models}", file=sys.stderr)
        print(f"yazıldı: {path}")
        _print_files(engine.files)
        return 2
    print(f"yazıldı: {path}")
    _print_files(engine.files)
    return 0


def _warn_stale_lock(engine: Engine) -> None:
    stale = (engine.lock or {}).get("stale_lock")
    if stale:
        print(f"UYARI: bayat kilit devralındı (PID {stale.get('pid')} yaşamıyordu); "
              "ham logda pgg_stale_lock_taken_over", file=sys.stderr)


def _exit_after_stall(code: int) -> None:
    """End the process after a stall: the summary is on disk, but a hung call's
    pool thread would block the interpreter's exit (pool threads are joined)."""
    stuck = [t for t in threading.enumerate()
             if t is not threading.current_thread() and t.is_alive() and not t.daemon]
    if not stuck:
        return
    print(f"durdu (stalled): {len(stuck)} iş parçacığı hâlâ asılı; süreç sonlandırılıyor",
          file=sys.stderr)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def _print_files(files: dict | None, file=None) -> None:
    """Output files of the run and their line counts (summary["files"])."""
    for name, f in (files or {}).items():
        if isinstance(f, list):                     # summary_backups: paths
            for p in f:
                print(f"dosya ({name}): {p}", file=file)
            continue
        lines = f.get("lines")
        print(f"dosya ({name}): {f['path']}" + (f" — {lines} satır" if lines is not None else ""),
              file=file)


if __name__ == "__main__":
    sys.exit(main())
