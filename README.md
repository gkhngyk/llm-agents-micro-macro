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
