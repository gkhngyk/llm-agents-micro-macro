# Frame files (schema 1)

A frame file holds every text a model sees in the public goods engine
(`pgg_game.py`): the system message, the rules, the history lines, the round
question, the punishment step, the isolated question, the rule-comprehension
questions and the field names of the response schema. The engine reads it with
`pgg_frames.load_frame`, validates it and renders it; nothing of the wording is
in the code.

| File | What |
|---|---|
| `frames/abstract_v2.json` | The texts of the engine up to c0b91f5 (pilot v2), character for character. Default of every config without `frames`. Do not edit: earlier rows carry its sha256. |
| `frames/abstract_v3.json` | Mini-pilot main frame (goal C1): the card alone as system message, isolated question at a fixed round, two rule-comprehension questions (C4). |
| `tests/fixtures/story_fixture.json` | Test fixture standing in for the story frame (C2). Not a story. |

## Config

```json
"frames": {"abstract_v3": ["deepseek", "mistral", "gpt"], "story": ["deepseek", "mistral"]},
"frame_files": {"story": "/abs/path/workspace/frames/story_a.json"},
"isolated_frame": "fixed_round",
"isolated_round_no": 5,
"comprehension": true
```

* `frames`: frame label (`[A-Za-z0-9_.]+`) -> models (keys or slugs). A cell is
  card x model x frame; a model plays only the frames it is listed under. The
  label is part of every unit label (`...|0|story`), session id, group id,
  seed key and run-order key. Without `frames` the engine uses `abstract_v2`
  for every model and writes ids and seeds exactly as before (pilot v2 resumes).
* `frame_files`: label -> path (absolute, or relative to the working directory).
  A label without an entry is `frames/<label>.json` of the code directory.
* `isolated_frame`: `one_shot`, `repeated` or `fixed_round`; every frame of the
  run must offer it (key under `isolated`). `isolated_round_no` (default 5) is
  the round `fixed_round` names; it must be in 2..rounds.
* `comprehension`: ask the rule-comprehension questions (every frame needs them).

Every result row has `frame` (the label), `frame_id` (the file's `name`) and
`frame_sha256` (sha256 of the file's bytes). A run with `frames` also has
`config.frame_setup` (labels, models, frame ids, sha256, comprehension,
isolated_round_no) in its summary and start event. `--resume` refuses a run
whose rows or `frame_setup` show another sha256 than the frame file now has.

## Document

Top-level keys (keys starting with `_` are comments and ignored):

| Key | Type | Notes |
|---|---|---|
| `schema` | `1` | required |
| `name` | string `[A-Za-z0-9_.-]+` | written to every row as `frame_id` |
| `description` | string | optional |
| `system` | template | system message; only `{card}` (required) |
| `player_label` | template | `{player_no}` (1-based, required) |
| `you_suffix` | template | appended to the player's own label in lists (may be empty) |
| `rules` | list of `{"text": template, "when": [tags]}` | lines joined with `\n`; a line is shown when all its tags hold |
| `history` | object | see below |
| `contribute` | template | round question; `{round_no}`, `{me}`; requires `{round_no}`, `{endowment}` |
| `punish` | template | punishment step (condition P); `{round_no}`, `{me}`, `{contributions}`, `{project_share}`, `{earnings}`, `{max_points}`; requires `{round_no}`, `{contributions}`, `{max_points}` |
| `isolated` | object | `one_shot` / `repeated` / `fixed_round` -> `{"rules": "single_round" or "multi_round", "question": template}`; question requires `{others_mean}`, `fixed_round` also `{round_no}` |
| `comprehension` | object | optional; `{"prompt": template, "questions": [...]}` |
| `response` | object | optional; JSON field names of the answers (defaults below) |

Rule tags (`when`): `single_round` (one-shot isolated question),
`multi_round` (everything else), `N`, `P`. The rules must hold `{n}`,
`{endowment}` and `{mpcr}` or `{multiplier}`; lines tagged `P` must hold
`{max_punish}`, `{punish_cost}`, `{punish_impact}`.

`history`:

| Key | Template placeholders |
|---|---|
| `empty` | shown in round 1 |
| `header` | first line from round 2 on |
| `list_item` | `{label}`, `{value}` (both required): one entry of a list of players |
| `list_separator` | between list entries of the contributions |
| `contributions` | `{contributions_list}` (required), `{group_total}` |
| `round` | list of lines per earlier round: `{round}`, `{contributions}`, `{round_earnings}` (required), `{project_share}` |
| `round_P` | list of lines added under P: `{punish_given}`, `{received}`, `{final_earnings}` (required), `{cost_paid}`, `{points_lost}` |
| `punish_given_separator` | between punishment entries |
| `punish_given_none` | when no point was assigned |

The user message is `rules + "\n\n" + history + "\n\n" + question` (round and
punishment step), `rules + "\n\n" + isolated question`, or
`rules + "\n\n" + comprehension prompt`; the engine then appends the response
schema (llm_client).

### Placeholders

Allowed in every template except `system`; numbers formatted as the engine
always did (`12.0` -> `12`, `0.4` -> `0.4`):

| Placeholder | Value (default game) |
|---|---|
| `{n}` / `{n_others}` | group size 4 / 3 |
| `{rounds}` | 10 |
| `{endowment}` | 20 |
| `{mpcr}` | 0.4 |
| `{multiplier}` | mpcr x n = 1.6 |
| `{max_punish}` / `{punish_cost}` / `{punish_impact}` | 10 / 1 / 3 |

Earnings are always `endowment - c + mpcr x sum(c)` (game rules in code).

**Numbers are never written in a frame file.** Literal text may hold no digit
except a lone `0` (as in "from 0 to {endowment}") and a `1. ` / `2. `
enumeration at the start of a line. A placeholder must be a plain name: no
`{}`, no `{x:>3}`, no `{x!r}`; a literal brace is `{{` / `}}`.

### Rule comprehension

```json
"comprehension": {
  "prompt": "RULE CHECK\n...\n1. {q1}\n2. {q2}\n...",
  "questions": [
    {"id": "q1", "text": "... {own} ... {other_1}, {other_2} and {other_3} ...",
     "answer": {"kind": "round_earnings", "own": 8, "others": [4, 12, 16]}},
    {"id": "q2", "text": "... {delta} ...", "answer": {"kind": "own_change", "delta": 10}}
  ]
}
```

* `prompt` must hold every question id as a placeholder.
* Answer kinds (the key is computed from the game parameters, never written):
  `round_earnings`: `endowment - own + mpcr x (own + sum(others))`
  (`others` has n - 1 values, all at most the endowment; placeholders `{own}`,
  `{other_1}` ...); `own_change`: `delta x (mpcr - 1)` (placeholder `{delta}`).
  A key that is not a whole number with the run's parameters stops the run.
* The response is `{"q1": int, "q2": int[, "rationale"]}`. Only a response
  outside this schema is invalid (re-requested, counted). A wrong answer is a
  valid response: recorded (`comp_<id>_answer`, `comp_<id>_key`,
  `comp_<id>_correct`, `comp_n_correct`), never re-requested, the game goes on.
* When asked: each agent once before round 1 of a group game (a separate
  call, no history; rows with round 1 and step `comprehension`), and once
  before every isolated schedule (row with round null). The summary has the
  share of correct answers per model x frame (`comprehension`).

### Response field names

```json
"response": {"decision_key": "contribution",
             "rationale_description": "One or two sentences on why you chose this.",
             "punishment_key": "punishments",
             "punishment_description": "Punishment points per other player, keyed by player number."}
```

These go into the JSON schema the model sees; a story frame can rename them
(e.g. away from "contribution"). Rows always store `contribution` /
`punishments`.

## Validation

`pgg_frames.validate_frame` collects every problem and raises `FrameError`:
missing or unknown keys, an unknown placeholder, a missing required one, bad
braces, numbers in the text, bad answer specs. `RunConfig.validate` also
checks that every frame offers the run's isolated wording and, with
`comprehension`, has questions whose key is a whole number. A real run,
`--resume` and a dry run with frames stop with the error before any call.

## Cost estimate

The cost calibration (`configs/cost_calibration_pilot_v2.json`) measured
abstract_v2 prompts. With `frames`, the dry run prints one line per frame x
model and scales each kind's prompt tokens by the frame's prompt characters
over abstract_v2's (isolated: over `repeated`; comprehension: over
contribute_N), labelled (tahmin). Comprehension calls are counted (one per
agent and group game, one per isolated schedule) and priced from
contribute_N's completion tokens.
