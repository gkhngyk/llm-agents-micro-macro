# project-publicgoods

Second study after *LLMs Simulate the Description of a Culture, Not the
Culture* (https://doi.org/10.5281/zenodo.23119302). Working question: does
group interaction amplify, damp or preserve the effect of an identity
description on LLM agents, in the repeated public goods game?

Status: design not fixed; no experiment run. See `notes/BACKGROUND.md`.

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.lock.txt
.venv/bin/python llm_client.py   # plumbing check: one tiny call per model
```

The OpenRouter key is read from `../.env`.

## Public goods engine (`pgg_game.py`)

Repeated public goods game (groups of 4, 10 rounds, 20 points, MPCR 0.4,
`earnings_i = 20 - c_i + 0.4 * sum(c)`) with conditions N (no punishment) and
P (punishment 1:3), a homogeneous-group arm and an isolated conditional
schedule arm. The pilot uses N + homogeneous groups only; P is coded and
tested. Design choices are in the module docstring; the main ones:

- **Isolated schedule = one call per value** (others' mean 0, 5, 10, 15, 20),
  not one call with five answers: no anchoring of one value on the others,
  an invalid value is re-requested alone, and it is what the pilot cost
  estimate prices (60 isolated calls per model).
- Card and style text are **parameters** (`--cards cards.json`, a list of
  `{card_id, style, text}`), never in the code; the same card goes to all four
  agents of a homogeneous group. No numeric disposition score is in any prompt.
- **Prompt texts are frame files** (`frames/*.json`, format in
  `frames/SCHEMA.md`, module `pgg_frames.py`), never in the code. Numbers come
  from the game parameters through placeholders (`{n}`, `{endowment}`,
  `{mpcr}`, `{multiplier}`, `{rounds}`, `{round_no}`, `{others_mean}`, ...);
  an unknown or missing placeholder, or a number written in the text, is a
  validation error and the run does not start. `frames/abstract_v2.json` is
  the wording of pilot v2, character for character (default when a config
  names no frame; ids and seeds then stay as before). `frames/abstract_v3.json`
  (mini-pilot): the card alone as system message, isolated question
  `fixed_round` ("This is round 5 of 10.", `isolated_round_no`), two
  rule-comprehension questions. Config `"frames": {"abstract_v3": [models],
  "story": [models]}` + `"frame_files": {"story": "/abs/path.json"}`: cell =
  card x model x frame, the frame label is in unit labels, session ids, seeds
  and the run order. Every row has `frame`, `frame_id`, `frame_sha256`;
  `--resume` refuses a changed frame file.
- **Rule comprehension** (`"comprehension": true`): each agent answers the
  frame's questions in a separate call before round 1 of a group game, and
  once before every isolated schedule. Integer answers; only a response
  outside the schema is invalid (re-requested), a wrong answer is recorded
  (`comp_q1_correct`, `comp_q2_correct`, ...) and the game goes on. The
  summary gives the share correct per model x frame.
- **Expected-cost gate** (`"expected_cost_gate_usd"`, mini-pilot 4.5): a real
  run (also `--resume`) does not start when the dry-run estimate of the design
  is above it; the estimate is reported. `budget_usd` (mini-pilot 6) stays the
  hard cap on accumulated `usage.cost`. With frames the dry run prints one
  line per frame x model, prompt tokens scaled by the frame's character ratio
  to abstract_v2 (tahmin), comprehension calls included; Mistral's expected
  cost is labelled a lower bound (ALT SINIR: no reasoning assumed).
- Every call goes through `llm_client.call_llm_valid(return_parse_fail=True)`;
  invalid payloads are re-requested and counted (`n_invalid`, `n_parse_fail`),
  never defaulted. Beyond the retry limit the run stops with an error.
- `reasoning_effort` (`--reasoning-effort low` or `deepseek=low,gpt=medium`) and
  `--max-tokens` are configurable and written to every row; temperature is not
  sent. Output: `<runs-dir>/<run>/<run>.jsonl`, one row per decision.

- Run guards (off by default): `--budget-usd` (hard cap on accumulated
  `usage.cost`, no new call once reached), config `model_budget_usd`
  (per-model caps, e.g. mini-pilot mistral 3 / deepseek 2 / gpt 0.5 USD: a
  model over its cap stops alone, reason and moment in the summary's
  `model_stops`; counted across `--resume` segments), `--invalid-rate-cap`
  (per model, stops that model), `--stop-on-length`, `--check-snapshot`
  (config `snapshot_version_models`: compare the dated `model_version` of the
  serving endpoint instead of the undated response model, e.g. Mistral; every
  row logs `model_version`). The dry run prints mean and p95 per model and in
  total; the expected-cost gate goes by the mean. `--cities` keeps
  only some cards of a file; `--parallel-units` runs several group games at
  once. Per-model cost and counts go to `<runs-dir>/<run>/<run>_summary.json`.
- The pilot (prereg_pilot.md) is `configs/pilot.json`: cards
  `cards/pilot_cards.json` filtered to Boston + Riyadh, N, 3 models,
  `max_tokens` 16000, client timeout 300 s, `reasoning_effort` not sent,
  1 USD cap, 5 % invalid cap, seed namespace `pgg-pilot`.
- **Outputs go outside the repository.** A real run writes
  `<runs-dir>/<run>/{<run>.jsonl, <run>_summary.json, raw_calls.jsonl}`;
  `runs-dir` is `--runs-dir`, else config `runs_dir`, else `$PGG_RUNS_DIR`,
  else the orc `workspace/runs` (only when run from an orc worktree). It must
  be absolute, exist and lie outside the git worktree, else the run does not
  start. The summary lists the files with their line counts.
- **Choices left to the user** are placeholders (`"<SEÇİLECEK: ...>"`) in the
  config: one provider per model (`providers`, OpenRouter provider routing,
  no fallback, `require_parameters: true`) and the
  isolated arm's wording (`isolated_frame`: `one_shot`, `repeated` or
  `fixed_round`; the frame must offer it). A real
  run does not start while one is left; `--dry-run` lists them.
- Provider errors (`finish_reason` "error", or 0 tokens at 0 cost) are
  retried and counted as `n_provider_error`, not as parse failures and not in
  the invalid cap. Units run in a shuffled round-robin over card x model
  (stable_seed), so a stopped run has data from every card.
- `--resume` goes on with an interrupted run in its directory as a new
  segment: complete units are skipped, a partial group game goes on from its
  first round not complete (history rebuilt from the rows, same prompts and
  seeds as without the cut), a partly written round is superseded and played
  again, earlier rows stay untouched (rows that do not count are listed in
  `superseded_rows`; `Engine.valid_rows()` returns the ones that do), budget
  and invalid cap count the earlier segments, and a config difference stops
  before any call. Accepted answers that never became a row are logged as
  `pgg_discarded` (`"discarded": true`) and counted (`n_discarded`). A
  cut-off last line of the results file is recorded in `<run>.partial.jsonl`
  and ignored by every later resume. A lock file (`<run>.lock`, PID) keeps a
  second process off the run; a stale one is taken over and logged.
  SIGINT / SIGTERM write the summary with stop_reason "interrupted". Details
  in the `pgg_game.py` docstring.
- **Hangs:** every HTTP attempt has a wall-clock deadline
  (`--request-deadline`, default 900 s; the 300 s client timeout only bounds
  each read). Past it the attempt is abandoned, logged as `error_kind`
  "transport" / `error_subkind` "deadline" with what had arrived of the
  response (`response_partial`, usage and cost when known, else
  `"cost_unknown": true`) and retried; a known cost counts in the budget, an
  unknown one as the worst case (prompt + `max_tokens` at listed prices;
  `pgg_deadline_cost_estimated`, row `"cost_estimated": true`, summary
  `n_deadline_cost_estimated`), replaced by the real cost if the response
  still arrives. If
  the run's raw log gets no record for `--stall-timeout` seconds (default
  1800), the run stops with stop_reason "stalled" and can go on with
  `--resume`. `--resume` compares both with the previous segment and stops on
  a difference unless `--allow-timeout-change` (recorded in the summary,
  `timeout_changes`); each segment's summary entry records them and the code
  version.
- Every row has `elapsed_s`, `n_transport`, `n_deadline` and
  `reasoning_capped` (reasoning_tokens >= max_tokens - 4096: the provider cut
  the hidden reasoning although finish_reason is "stop"; flagged, kept, not
  re-requested). The summary counts them per model, per segment and in total
  (`n_reasoning_capped`, `n_transport`, `n_deadline`, `n_cost_unknown`,
  `deadline_cost_usd`).
- **Provider mismatch (A4):** a response of a pinned model from another
  provider, or (task #68) without a provider name, is not a decision. It is
  logged (`"provider_mismatch": true`, plus `"provider_missing": true`
  without a name; content and cost), counts in the budget and is
  re-requested, within the same attempt limit as other failures (4 attempts
  per call); the run stops with stop_reason "provider_mismatch_limit" when
  that limit ends on a mismatch. Counted as `n_provider_mismatch` (sub-count
  `n_provider_missing`) per row, model, segment and in total. This replaces
  the "stop at the first mismatch" rule of prereg_pilot.md §8.2 item 5
  (amendment written separately). `n_provider_unknown` (no name, accepted)
  now applies only to unpinned models; pilot v2 counted pinned ones there.
- **Code version (A5):** every segment records `code_version` with a
  `git_commit`. In a git checkout it is HEAD; a code copy outside git (e.g.
  unpacked with git archive into `workspace/_kod_<sha>/`) needs
  `CODE_VERSION.json` (commit + sha256 of the tracked .py files, re-checked
  at every start). A real run and `--resume` refuse unknown or dirty code (a
  tracked .py file changed, or the stamp does not match); a dry run only
  warns. A resumed segment with another commit is recorded (`code_change`,
  `code_changes`).

- **Answer instruction** (task #80, off by default): config `answer_format`.
  Unset or `"schema_text"` sends exactly the requests of 811fdcc (schema text
  after the last message, `json_object`; checked against recorded request
  hashes). `"example_object"` (option A) shows a placeholder example object
  instead (`{"contribution": <whole number from 0 to 20>, ...}`, no new
  number); `"json_schema_strict"` (option B) appends the strict schema (every
  object closed, every field required) as the schema text and sends the same
  schema as `response_format` json_schema with `strict: true`. In A and B
  `rationale` is required in the prompt and in the check (task #90). A or B is
  in the config record (a resume with another value stops); any set value is
  in rows and raw log; it changes `request_sha256`. Comparison:
  `notes/cevap_talimati_tasarim.md`.
- **Reuse safety** (task #90): every row, raw-log record and
  `<run>.accepted.jsonl` record carries `request_sha256`, the sha256 of the
  canonical JSON (keys sorted, separators `,` `:`) of the whole request body
  sent but `session_id` (model, messages with the answer instruction,
  `max_tokens`, `response_format`, provider routing; temperature / reasoning
  only when sent). `--resume` reuses a journaled answer only with the same
  `request_sha256` (records before #90: `prompt_sha256`), only from a segment
  with the same `git_commit` (otherwise the resume does not start;
  `--discard-reuse-on-code-change` discards and asks them again), and only if
  it passes `is_valid` again (`reuse_invalid`, `n_reuse_invalid`).
- **Status file** (task #80): once a run has passed its checks, the run
  process writes `<runs-dir>/<run>/status.json` itself (pid, heartbeat every
  `--heartbeat-interval` s, default 30, units complete, cost, stop_reason, at
  the end outcome). A `stop_request.json` naming its pid makes it send itself
  SIGTERM (for callers that may not signal it, e.g. orc's sandbox).

```bash
.venv/bin/python pgg_game.py --dry-run --config configs/pilot.json   # no API, no key
.venv/bin/python pgg_game.py --config configs/pilot.json --run pilot_<date> --runs-dir /abs/path/runs
.venv/bin/python pgg_game.py --config configs/pilot.json --run pilot_<date> --resume --dry-run  # plan only
.venv/bin/python pgg_game.py --config configs/pilot.json --run pilot_<date> --resume
.venv/bin/python -m unittest discover -s tests -v
# code copy outside git: unpack it, then stamp it from the git checkout
git archive <sha> | tar -x -C /abs/workspace/_kod_<sha>
.venv/bin/python pgg_game.py --write-code-version /abs/workspace/_kod_<sha> --code-commit <sha>
```

`--dry-run` takes prices and token counts from `pgg_cost.py`, calibrated on
pilot v2 (`configs/cost_calibration_pilot_v2.json`: mean and p95 per model x
call kind, paid-but-invalid share; Mistral entries are marked estimates).
Every figure is still an estimate. It never imports `llm_client`. Re-derive
the calibration (reads the run directory only):

```
.venv/bin/python pgg_cost_calibrate.py --run-dir /abs/workspace/runs/pilot_v2_20261005
```

## Long runs outside any tool session (`scripts/runctl.py`, task #80)

A paid run is started by the user in their own Terminal (outside orc's
sandbox), as a detached process: own session (setsid), SIGHUP ignored, output
to `<runs-dir>/<run>/console.log`. orc and the user follow it from the files
only. Comparison of the options (launchd, nohup/setsid, tmux, tool background
command), what was tried in this environment and the step-by-step guide in
Turkish: `notes/uzun_omurlu_kosu.md`.

```bash
cd /abs/workspace/_kod_<sha>                     # stamped code copy (see above)
# the key must be in the environment (a code copy has no ../.env); never print it
PY=/abs/project-publicgoods/.venv/bin/python
$PY pgg_game.py --dry-run --config configs/<config>.json                 # gate first
$PY scripts/runctl.py start  --config configs/<config>.json --run <run> \
    --runs-dir /abs/workspace/runs               # add --resume to go on
$PY scripts/runctl.py status --runs-dir /abs/workspace/runs --run <run>  # files only
$PY scripts/runctl.py stop   --runs-dir /abs/workspace/runs --run <run> --wait 1000
```

- `start` waits until the run's `status.json` names the new pid (or prints
  the console log's tail when the process ended at once, e.g. a refused gate),
  records the launch in `launcher.jsonl` (never the environment) and returns;
  the terminal can be closed. caffeinate is on by default (task #90): it keeps
  the Mac awake while the run lives (not with the lid closed);
  `--no-caffeinate` turns it off; without `caffeinate` on PATH `start` warns
  and goes on.

### A paid run, step by step (the user's own Terminal)

Paid runs are started by the user, never from orc's sandbox. `W` is the
workspace, `SHA` the approved commit, `<run>` an explicit run name.

1. **Pin the code.** In the main checkout:
   `mkdir "$W/_kod_$SHA" && git archive $SHA | tar -x -C "$W/_kod_$SHA"`, then
   `.venv/bin/python pgg_game.py --write-code-version "$W/_kod_$SHA" --code-commit $SHA`.
2. **Key** for this terminal only, never printed:
   `set -a; source /abs/complexity-prj/.env; set +a`.
3. **Gate.** `cd "$W/_kod_$SHA"`; `$PY pgg_game.py --dry-run --config configs/<config>.json`
   (for a resume add `--resume --run <run>`: it prints the resume plan, and a
   reuse refused because of another `git_commit` shows up here as a problem).
4. **Start.** `$PY scripts/runctl.py start --config configs/<config>.json --run <run> --runs-dir "$W/runs"`.
   It prints the pid and the caffeinate pid; the terminal can then be closed
   (keep the lid open and the Mac on power).
5. **Watch.** `$PY scripts/runctl.py status --runs-dir "$W/runs" --run <run>`
   (`--json` too): heartbeat age, units complete, cost, last raw-log write.
   Exit 0 running, 3 ended, 4 heartbeat stale (look at `console.log`), 2 no
   status yet. The heartbeat only says the process lives; progress is in
   units, cost and the raw-log line.
6. **Stop.** `$PY scripts/runctl.py stop --runs-dir "$W/runs" --run <run> --wait 1000`
   (SIGTERM, or `stop_request.json` with `--via-file`): stop_reason
   "interrupted", summary at once, calls in flight waited for.
7. **Resume.** Same code copy (same `SHA`: answers of another commit are not
   reused and stop the resume), step 3 with `--resume`, then step 4 with
   `--resume`. Only the missing decisions are asked.
8. **After.** Report the files of `"$W/runs/<run>/"` and their line counts
   (data-persistence rule); raw logs with the account id are never committed.

Details and the options compared: `notes/uzun_omurlu_kosu.md` §6.
- `status` reads files only. Exit code 0 running, 3 ended, 4 heartbeat stale
  (process may be gone: console log, then `start --resume`), 2 no status yet.
- `stop` sends SIGTERM to the pid of `status.json` if `<run>.lock` holds the
  same pid; where signalling is not allowed (orc's sandbox) or with
  `--via-file`, it writes `stop_request.json`. Either way the run ends with
  stop_reason "interrupted": summary at once, calls in flight waited for.
