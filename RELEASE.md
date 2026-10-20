# Release: "Rules measured in play, not stated in isolation, generate the macro dynamics of LLM agent groups"

Gökhan Geyik (Empler AI). Open preprint with all plans, code, data and reasoning texts. License: CC BY 4.0.

## What is in the release

Two archives:

- **`publicgoods_repo_<commit>.zip`**: the repository at the release commit, plus `results/`.
  - `paper/`: the preprint (`preprint_v1.md`, `preprint_v1.pdf`), the supplement (`preprint_v1_supplement.md`, `.pdf`), figures, `paper_numbers.py` and its output `numbers.md`. Every number in the paper is in `numbers.md`; values at rounding ties are listed at its end with their exact values. A Turkish reading copy (`preprint_v1_tr.md`, `.pdf`) is included; the English text is authoritative. Earlier drafts (`draft_v*.md`) are kept for the record.
  - `prereg/`: the written plans, one per study, with dated amendments. They were written before the data. They are internal written plans, in Turkish, not entries in a public registry. The plan and forecast of Study 4 were also deposited on Zenodo before its main run: https://doi.org/10.5281/zenodo.23483296.
  - `pgg_game.py`, `pgg_frames.py`, `llm_client.py`, `scripts/runctl.py`: the game engine and the API layer (OpenRouter).
  - `pgg_analysis*.py`: one analysis script per study and exploratory analysis; `tests/`: the test suite (628 tests, no API calls).
  - `configs/`, `frames/`, `cards/`: the exact run settings, prompt frames and identity cards (sha256-locked in the configs).
  - `data/expB/`, `data/expC/`: frozen rule tables and forecasts.
  - `data/herrmann2008/`: the human reference data (Herrmann, Thöni & Gächter, Dryad, CC0) as published.
  - `results/`: the analysis outputs (`*_analysis.json` and the exploratory outputs).
- **`publicgoods_runs_<commit>.zip`**: one folder per run with three kinds of file:
  - every decision with its reasoning text (`<run>.jsonl`);
  - the run summary (`<run>_summary*.json`);
  - the raw API log (`raw_calls.jsonl`).

  **Redaction:** in the raw logs, the OpenRouter account identifier contained in rate-limit error messages is replaced by `[REDACTED_ACCOUNT_ID]`, and the author's local paths by `<PROJECT_ROOT>`. Nothing else was changed.

`SHA256SUMS.txt` (in the repository archive as `SHA256SUMS_release.txt`) lists the hash of every file. `SOURCE_COMMIT.txt` gives the git commit.

## Runs

| study | run(s) | groups | notes |
|---|---|---|---|
| 0b (plumbing check) | `main_s0b_20261012` | | prompt and format check before Study 1 |
| 1 | `main_s1_20261014` | 504 + 144 isolated schedules | identity × interaction |
| 2 | `expA_smoke_20261017`, `expA_main_20261017` | 256 (main) | feedback visibility |
| 3 | `expB_smoke_20261018`, `expB_main_20261018` | 176 (main) | 15-round game, frozen rule |
| 4 | `expC_n{4,8,16,32}_smoke_20261019`, `expC_n{4,8,16,32}_main_20261020` | 264 (main) | group size, frozen forecast |

Smoke-test runs are excluded from all analyses by plan.

## Reproducing the analyses (no API calls)

```bash
pip install -r requirements.lock.txt
unzip publicgoods_repo_<commit>.zip && unzip publicgoods_runs_<commit>.zip
cd repo
python scripts/set_runs_dir.py "$(cd ../runs && pwd)"           # point the configs at the run files
unzip data/herrmann2008/HerrmannThoeniGaechter.zip -d data/herrmann2008/raw
export OPENROUTER_API_KEY=unused                                 # only satisfies an import
python -m unittest discover -s tests                             # 628 tests
python pgg_analysis.py ...                                       # see each script's docstring
python paper/paper_numbers.py > /tmp/numbers.md && cmp /tmp/numbers.md paper/numbers.md
```

The last command must reproduce `paper/numbers.md` byte for byte; this was checked on the release archives. Each analysis script states its command line in its docstring and writes to `results/`. Simulations use fixed seeds (`llm_client.stable_seed`), so the outputs are reproduced exactly; the result files' sha256 are recorded in the plans.

## Re-running the experiments

Re-running needs an OpenRouter key in `../.env` (never in the repository) and costs money. The configs fix the models, providers and request settings. Provider-side changes, such as model updates or rate limits, mean a re-run will not reproduce the decisions exactly. The logged model versions are in the run files.

## Related

- Earlier study: Geyik (2026), https://doi.org/10.5281/zenodo.23119302.
- Study 4 pre-registration deposit: https://doi.org/10.5281/zenodo.23483296.
