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
  sent. Output: `results/<run>.jsonl`, one row per decision (git-ignored).

```bash
.venv/bin/python pgg_game.py --dry-run          # call counts + estimated cost, no API, no key
.venv/bin/python pgg_game.py --run pilot1 --cards cards.json --reasoning-effort low --max-tokens 4000
.venv/bin/python -m unittest discover -s tests -v
```

`--dry-run` takes prices and token estimates from `pgg_cost.py` (copied from
`maliyet_analizi.md`, every figure is an estimate) and never imports
`llm_client`.
