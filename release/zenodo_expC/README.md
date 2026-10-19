# Pre-registered forecast: how cooperation among LLM agents changes with group size

**Experiment C of "Rules measured in play, not stated in isolation, generate the macro dynamics of LLM agent groups".**
Author: Gökhan Geyik (Empler AI). Deposited before the main data collection of Experiment C.

## What this deposit fixes in time

A decision rule was learned from repeated public goods games played by groups of **four** LLM agents and frozen (`data/expB/frozen_rules_v1.json`). The game: 20 points per round, MPCR 0.4, 10 rounds. Before any main-run data, we used the frozen rule to predict what happens in groups of **8, 16 and 32** agents. The plan and the forecast are fixed here.

**Forecast** (`data/expC/forecast_v1.json`, sha256 `00d88e05fed5dcede000a5d2a9e56287383e752787ba2554562f2e21099be9df`). Share of groups whose mean contribution is ≤ 2.5 of 20 at round 8, averaged over four minimal identity cards:

| model | rule | n = 4 | n = 8 | n = 16 | n = 32 |
|---|---|---|---|---|---|
| Mistral-Large-4 | learned in play (R3) | 0.373 | 0.570 | 0.772 | — |
| Mistral-Large-4 | stated in isolation (R0) | 0.297 | 0.298 | 0.311 | — |
| GPT-6-Luna | learned in play (R3) | 0.228 | 0.188 | 0.158 | 0.146 |
| GPT-6-Luna | stated in isolation (R0) | 0.063 | 0.013 | 0.000 | 0.000 |

**In words:**
- The in-play rule predicts that Mistral groups collapse more often as they grow (+0.40 from 4 to 16), and that GPT groups do not (−0.08 from 4 to 32).
- The rule built from each agent's stated response to an isolated question predicts no size effect for Mistral (+0.01).
- The pre-registered hypotheses (C-H1 to C-H4), the decision rules and labels, the design and the stopping rules are in `prereg/prereg_expC.md`:
  - groups of 4, 8 and 16 for Mistral, 24 groups each;
  - groups of 4, 8, 16 and 32 for GPT, 48 groups each;
  - the four-agent groups are a concurrent control.

  Both directions of every effect are written down in advance.

## Status at deposit

- Plan approved on 2026-10-19 (`prereg/prereg_expC.md`; it is an internal written plan, in Turkish, with this English summary).
- The forecast and the analysis code were committed before any paid call (source git commit in `SOURCE_COMMIT.txt`).
- A smoke test (C1, one group per model and size) ran on 2026-10-19 to check the prompts. By plan its data do not enter the analysis.
- **No main-run (C2) data existed when this deposit was made.**

## Files

- `prereg/prereg_expC.md`: the approved plan with its dated amendments.
- `data/expB/frozen_rules_v1.json`: the frozen rule tables (learned from the four-agent study only), sha256 `62b2bae7bcf6560f022181ff5b0813fec4747f2b8e3e13e5dd1301931fbd93d1`.
- `data/expC/forecast_v1.json`: the forecast.
- `pgg_analysis_expC.py` and its imports (`pgg_analysis*.py`, `llm_client.py`): forecast and analysis code.
- `frames/`, `configs/expC_*`, `cards/expA_cards_v1.json`: the exact prompts and run settings.
- `requirements.lock.txt`: Python package versions.
- `SHA256SUMS.txt`: hashes of all files; `SOURCE_COMMIT.txt`: the git commit they were taken from.

## How to verify

```bash
shasum -a 256 -c SHA256SUMS.txt
pip install -r requirements.lock.txt
OPENROUTER_API_KEY=unused python pgg_analysis_expC.py forecast --out /tmp/forecast.json
```

The last command must print sha256 `00d88e05fed5dcede000a5d2a9e56287383e752787ba2554562f2e21099be9df`. It needs no API calls; the key only satisfies an import.

## Related

- Earlier study by the same author: Geyik (2026), https://doi.org/10.5281/zenodo.23119302.
- Human reference data used in the paper: Herrmann, Thöni & Gächter (2017), https://doi.org/10.5061/dryad.87301.
- The full repository (all plans, code, data and reasoning texts) will be released with the paper.

License: CC BY 4.0.
