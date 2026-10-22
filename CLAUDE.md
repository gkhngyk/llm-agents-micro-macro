# project-publicgoods

Second study with Gökhan Geyik (Empler AI), following the published
Ultimatum Game paper. Status as of 2026-10-22: **four studies run, preprint
published, version 2** (`paper/preprint_v2.md`; Zenodo, all versions:
https://doi.org/10.5281/zenodo.23539450); release contents, versions and reproduction
steps in `RELEASE.md`.

For the design background from before the first run, read
`notes/BACKGROUND.md` (what the first study found, what is already published
by others, the candidate design) and `notes/literature_scan.md`.

## Working rules carried over from the first study

- **Write the plan before the data.** For every test, write hypotheses,
  decision rules and the analysis plan to a `prereg_<name>.md` file before
  the first API call. Pre-specify *both* directions of an effect. After a
  pilot ("smoke") run, read the reasoning texts for design flaws; record any
  change as a dated amendment with its reason; exclude pilot data. Call these
  files what they are: internal written plans, not a public registry.
- **Vary the description from the start.** The first study's main lesson is
  that the wording of the identity description sets the result. Any identity
  manipulation here uses at least the three description styles (value-laden,
  minimal, factual) in the first design, not as a follow-up.
- **No numeric disposition attributes on identity cards** (e.g. a
  "fairness" score). They determined decisions in the first study.
- **Seeds:** `llm_client.stable_seed` (crc32). Never Python `hash()`.
- **Invalid payloads** are re-requested and counted, never coded.
- **Every number in a write-up is checked against the result files**, and
  every cited reference against Crossref/arXiv, before anything is published.
- Explain results to the user in plain Turkish, short and concrete; go deep
  on engineering and science, skip commercial talk.
- Commit or push only when asked.

## Layout

- `llm_client.py` — OpenRouter calls, logging, decision-model calls, seeds.
  API key is read from `../.env`; do not copy it here.
- `notes/` — background and literature scan.
- `prereg/` — the written plans (authoritative copies since 2026-10-12;
  amendments are committed, additions only; see `prereg/README.md`).
- `logs/raw_calls.jsonl` — every API call (git-ignored; contains an account id).
- `results/` — one `.jsonl` per run, one `_analysis.json` per analysis.

The first study lives in `../project-ultimatum` (public repo
`gkhngyk/llm-culture-description`, archived on Zenodo). Treat it as a
published replication package: read from it, do not edit it for this study.
