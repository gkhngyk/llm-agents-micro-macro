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
- Every call goes through `llm_client.call_llm_valid(return_parse_fail=True)`;
  invalid payloads are re-requested and counted (`n_invalid`, `n_parse_fail`),
  never defaulted. Beyond the retry limit the run stops with an error.
- `reasoning_effort` (`--reasoning-effort low` or `deepseek=low,gpt=medium`) and
  `--max-tokens` are configurable and written to every row; temperature is not
  sent. Output: `<runs-dir>/<run>/<run>.jsonl`, one row per decision.

- Run guards (off by default): `--budget-usd` (hard cap on accumulated
  `usage.cost`, no new call once reached), `--invalid-rate-cap` (per model,
  stops that model), `--stop-on-length`, `--check-snapshot`. `--cities` keeps
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
  no fallback; a response from another provider stops the run) and the
  isolated arm's wording (`isolated_frame`: `one_shot` or `repeated`). A real
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
  (`--request-deadline`, default 300 s; the 300 s client timeout only bounds
  each read). Past it the attempt is abandoned, logged as `error_kind`
  "transport" / `error_subkind` "deadline" and retried. If the run's raw log
  gets no record for `--stall-timeout` seconds (default 900), the run stops
  with stop_reason "stalled" and can go on with `--resume`. Both are
  operational settings, not compared on `--resume`; each segment's summary
  entry records them and the code version.

```bash
.venv/bin/python pgg_game.py --dry-run --config configs/pilot.json   # no API, no key
.venv/bin/python pgg_game.py --config configs/pilot.json --run pilot_<date> --runs-dir /abs/path/runs
.venv/bin/python pgg_game.py --config configs/pilot.json --run pilot_<date> --resume --dry-run  # plan only
.venv/bin/python pgg_game.py --config configs/pilot.json --run pilot_<date> --resume
.venv/bin/python -m unittest discover -s tests -v
```

`--dry-run` takes prices and token estimates from `pgg_cost.py` (copied from
`maliyet_analizi.md`, every figure is an estimate) and never imports
`llm_client`.
