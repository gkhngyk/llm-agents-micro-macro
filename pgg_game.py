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
                    allow_fallbacks false). Every response's provider name
                    (and quantization, if the response has one) goes to the
                    raw log and the row; a provider name other than "name"
                    stops the run (prereg §8.2 item 5, "provider_mismatch").
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
run does not start. Config values starting with "<" are placeholders: a real
run does not start while one is left. --dry-run prints call counts and an
estimated cost without importing llm_client (no key, no ../.env, no API).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
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


class RunAborted(RuntimeError):
    """A decision could not be obtained validly; the run was stopped."""


# Not RuntimeError subclasses: Engine._ask turns RuntimeError into RunAborted.
class RunStopped(Exception):
    """A run guard (budget, finish_reason length, snapshot) stopped the run."""


class ModelStopped(Exception):
    """The invalid-rate cap stopped this model; other models go on."""


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

    https://openrouter.ai/docs/guides/routing/provider-selection
    """
    routing = {"order": [spec["slug"]], "only": [spec["slug"]], "allow_fallbacks": False}
    if spec.get("quantizations"):
        routing["quantizations"] = list(spec["quantizations"])
    return routing


def same_provider(got: str, expected: str) -> bool:
    """Provider names compared case- and punctuation-insensitively."""
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
    # {model key: {"slug", "name"[, "quantizations"]}}: pins one provider per
    # model (order + only, allow_fallbacks false); a response from another
    # provider stops the run (prereg §8.2 item 5). None = not pinned.
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
        if self.request_timeout_s is not None and not self.request_timeout_s > 0:
            raise ValueError("request_timeout_s must be positive")
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


class Engine:
    def __init__(self, cfg: RunConfig, *, llm=None):
        cfg.validate()
        self.cfg = cfg
        self.llm = llm or _llm()
        self.max_tokens = cfg.max_tokens or self.llm.DEFAULT_MAX_TOKENS
        self.timeout = cfg.request_timeout_s or self.llm.DEFAULT_TIMEOUT_S
        self._out = None
        self._lock = threading.Lock()
        self.invalid_limit = cfg.invalid_limit()
        self.stop_reason: str | None = None        # set once; stops every unit
        self.aborted: RunAborted | None = None
        self.stopped_models: dict[str, str] = {}   # model key -> reason
        self.unit_order: list[str] = []
        self.files: dict | None = None             # output files and line counts (run)
        # n_provider_error: provider-error responses (llm_client error_kind
        # "provider"); not in n_parse_fail and not in the invalid-rate cap.
        # providers: provider name of every response -> count ("null" = none).
        self.stats = {key: {"cost_usd": 0.0, "n_responses": 0, "n_accepted": 0,
                            "n_invalid": 0, "n_parse_fail": 0, "n_provider_error": 0,
                            "n_cost_estimated": 0, "n_length": 0, "finish_reasons": {},
                            "providers": {}, "n_provider_unknown": 0}
                      for key in cfg.models}

    # -- seeds / output ----------------------------------------------------

    def seed_for(self, *parts) -> int:
        return self.llm.stable_seed(self.cfg.seed_namespace, self.cfg.run, *parts)

    def _write(self, row: dict) -> None:
        with self._lock:
            self._out.write(json.dumps(row, ensure_ascii=False) + "\n")
            self._out.flush()

    # -- run guards --------------------------------------------------------

    @property
    def total_cost(self) -> float:
        return sum(s["cost_usd"] for s in self.stats.values())

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
        if self.stop_reason is not None:
            raise RunStopped(self.stop_reason)
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

    def _on_response(self, model_key: str, info: dict) -> None:
        """Runs for every response that arrived (billed): cost, finish_reason, model, provider."""
        cost, estimated = self._response_cost(model_key, info.get("usage"))
        finish = info.get("finish_reason")
        provider = info.get("provider")
        pinned = self.cfg.provider_for(model_key)
        with self._lock:
            s = self.stats[model_key]
            s["cost_usd"] += cost
            s["n_responses"] += 1
            s["n_cost_estimated"] += estimated
            s["finish_reasons"][str(finish)] = s["finish_reasons"].get(str(finish), 0) + 1
            s["providers"][str(provider)] = s["providers"].get(str(provider), 0) + 1
            if finish == "length":
                s["n_length"] += 1
            if info.get("provider_error"):
                s["n_provider_error"] += 1
            if pinned and provider is None:
                s["n_provider_unknown"] += 1
        slug = self.cfg.models[model_key]
        snapshot = info.get("model_snapshot")
        if self.cfg.stop_on_length and finish == "length":
            self._stop("finish_reason_length", model=slug)
        if (self.cfg.check_snapshot and snapshot is not None and snapshot != slug
                and not snapshot.startswith(slug + "-")):
            self._stop("model_snapshot_mismatch", model=slug, model_snapshot=snapshot)
        # prereg §8.2 item 5: the provider changed. A response without a
        # provider name cannot be checked; it is counted (n_provider_unknown).
        if pinned and provider is not None and not same_provider(provider, pinned["name"]):
            self._stop("provider_mismatch", model=slug, provider=provider,
                       expected_provider=pinned["name"],
                       provider_quantization=info.get("provider_quantization"))

    def _count_invalid(self, model_key: str, ans: "Answer") -> None:
        with self._lock:
            s = self.stats[model_key]
            s["n_accepted"] += 1
            s["n_invalid"] += ans.n_invalid
            s["n_parse_fail"] += ans.n_parse_fail
            n_bad = s["n_invalid"] + s["n_parse_fail"]
            hit = (self.invalid_limit is not None and n_bad > self.invalid_limit
                   and model_key not in self.stopped_models)
            if hit:
                self.stopped_models[model_key] = "invalid_rate_cap"
        if hit:
            self.llm._append_log({
                "ts": time.time(), "event": "pgg_model_stopped", "run": self.cfg.run,
                "model": self.cfg.models[model_key], "reason": "invalid_rate_cap",
                "n_invalid": s["n_invalid"], "n_parse_fail": s["n_parse_fail"],
                "limit": self.invalid_limit})

    def _map(self, fn, items):
        items = list(items)
        if self.cfg.workers <= 1 or len(items) <= 1:
            return [fn(x) for x in items]
        with ThreadPoolExecutor(max_workers=self.cfg.workers) as pool:
            return list(pool.map(fn, items))

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
        try:
            parsed, n_invalid, n_parse_fail = self.llm.call_llm_valid(
                self.cfg.models[model_key], messages, schema=schema, session_id=session_id,
                is_valid=is_valid, max_tokens=self.max_tokens, max_invalid=self.cfg.max_invalid,
                return_parse_fail=True, reasoning_effort=self.cfg.effort_for(model_key),
                meta=meta, before_call=lambda: self._before_call(model_key),
                on_response=on_response, timeout=self.timeout, counts=counts,
                provider=provider_routing(pinned) if pinned else None)
        except RuntimeError as e:
            self.llm._append_log({
                "ts": time.time(), "event": "pgg_run_aborted", "run": self.cfg.run,
                "model": self.cfg.models[model_key], "session_id": session_id,
                "error": str(e), **ctx,
            })
            raise RunAborted(
                f"run {self.cfg.run!r} stopped: no valid decision for {ctx} "
                f"(model {model_key}): {e}") from e
        meta["provider"] = last.get("provider")
        meta["provider_quantization"] = last.get("provider_quantization")
        ans = Answer(parsed, n_invalid, n_parse_fail, meta,
                     n_provider_error=counts.get("n_provider_error", 0))
        self._count_invalid(model_key, ans)
        return ans

    def _row(self, *, condition, arm, model_key, card, session_id, group_id, agent_id,
             round_no, step, ans: Answer, seed: int, **fields) -> dict:
        rationale = ans.parsed.get("rationale")
        return {
            "run": self.cfg.run, "condition": condition, "arm": arm, "step": step,
            "model": self.cfg.models[model_key], "model_key": model_key,
            "model_snapshot": ans.meta.get("model_snapshot"),
            "session_id": session_id, "group_id": group_id, "agent_id": agent_id,
            "round": round_no, "card_id": card.card_id, "style": card.style,
            **fields,
            "n_invalid": ans.n_invalid, "n_parse_fail": ans.n_parse_fail,
            "n_provider_error": ans.n_provider_error,
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

    def play_group(self, model_key: str, cards: list[Card], condition: str, idx: int) -> None:
        """One group game (rounds x agents); cards[i] is agent i+1's card."""
        p = self.cfg.params
        if len(cards) != p.group_size:
            raise ValueError(f"need {p.group_size} cards, got {len(cards)}")
        lead = cards[0]
        session_id = session_id_for(self.cfg.run, model_key, lead.card_id, lead.style,
                                    condition, "group", idx)
        group_id = f"{lead.card_id}-{lead.style}-{condition}-g{idx:02d}"
        history: list[RoundRecord] = []
        for r in range(1, p.rounds + 1):
            ctx = {"round": r, "group_id": group_id, "condition": condition}

            def contribute(i):
                return self._ask(
                    model_key, contribution_messages(p, condition, cards[i], history, i, r),
                    contribution_schema(p, self.cfg.rationale),
                    lambda c: is_valid_contribution(c, p), session_id,
                    {**ctx, "agent_id": i + 1, "step": "contribute"})

            answers = self._map(contribute, range(p.group_size))
            contributions = [a.parsed["contribution"] for a in answers]
            earnings = project_payoffs(p, contributions)
            rec = RoundRecord(r, contributions, earnings, final_earnings=earnings)
            punish_answers = None

            if condition == "P":
                def punish(i):
                    targets = [j + 1 for j in range(p.group_size) if j != i]
                    budget = punishment_budget(earnings[i])
                    return self._ask(
                        model_key,
                        punishment_messages(p, cards[i], history, i, r, contributions, earnings[i]),
                        punishment_schema(p, targets, self.cfg.rationale),
                        lambda c: is_valid_punishment(c, p, targets, budget), session_id,
                        {**ctx, "agent_id": i + 1, "step": "punish"})

                punish_answers = self._map(punish, range(p.group_size))
                rec.punishment = [
                    [punish_answers[i].parsed["punishments"][str(j + 1)] if j != i else 0
                     for j in range(p.group_size)] for i in range(p.group_size)]
                rec.final_earnings, rec.cost_paid, rec.received = apply_punishment(
                    p, earnings, rec.punishment)

            for i in range(p.group_size):
                self._write(self._row(
                    condition=condition, arm="group", model_key=model_key, card=cards[i],
                    session_id=session_id, group_id=group_id, agent_id=i + 1, round_no=r,
                    step="contribute", ans=answers[i],
                    seed=self.seed_for(model_key, cards[i].card_id, cards[i].style, condition,
                                       "group", idx, i + 1, r, "contribute"),
                    contribution=answers[i].parsed["contribution"], group_total=sum(contributions),
                    payoff_before_punishment=earnings[i], payoff=rec.final_earnings[i]))
            if punish_answers:
                for i in range(p.group_size):
                    self._write(self._row(
                        condition=condition, arm="group", model_key=model_key, card=cards[i],
                        session_id=session_id, group_id=group_id, agent_id=i + 1, round_no=r,
                        step="punish", ans=punish_answers[i],
                        seed=self.seed_for(model_key, cards[i].card_id, cards[i].style, condition,
                                           "group", idx, i + 1, r, "punish"),
                        punishments={str(j + 1): rec.punishment[i][j]
                                     for j in range(p.group_size) if j != i},
                        punishment_cost_paid=rec.cost_paid[i],
                        punishment_points_received=rec.received[i],
                        payoff=rec.final_earnings[i]))
            history.append(rec)

    # -- isolated arm ------------------------------------------------------

    def play_isolated(self, model_key: str, card: Card, rep: int) -> None:
        """The conditional schedule for one card: one call per conditioning value."""
        p = self.cfg.params
        condition = "N"
        session_id = session_id_for(self.cfg.run, model_key, card.card_id, card.style,
                                    condition, "isolated", rep)
        group_id = f"{card.card_id}-{card.style}-{condition}-iso{rep:02d}"

        def ask_point(x):
            ctx = {"round": None, "group_id": group_id, "condition": condition,
                   "agent_id": 1, "step": "isolated", "others_mean": x}
            return self._ask(
                model_key, isolated_messages(p, card, x, self.cfg.isolated_frame),
                contribution_schema(p, self.cfg.rationale),
                lambda c: is_valid_contribution(c, p), session_id, ctx)

        points = list(self.cfg.isolated_points)
        for x, ans in zip(points, self._map(ask_point, points)):
            self._write(self._row(
                condition=condition, arm="isolated", model_key=model_key, card=card,
                session_id=session_id, group_id=group_id, agent_id=1, round_no=None,
                step="isolated", ans=ans,
                seed=self.seed_for(model_key, card.card_id, card.style, condition,
                                   "isolated", rep, 1, "isolated", x),
                contribution=ans.parsed["contribution"], others_mean=x,
                isolated_frame=self.cfg.isolated_frame))

    # -- whole run ---------------------------------------------------------

    def _order_key(self, *parts) -> tuple:
        """Sort key of the run order: stable_seed (crc32), the parts break ties."""
        return (self.llm.stable_seed(self.cfg.seed_namespace, self.cfg.run, "order", *parts),
                tuple(map(str, parts)))

    def _cell_units(self, model_key: str, card: Card) -> list[tuple[str, str, object]]:
        """(model key, label, callable) of one cell (card x model).

        Group games and isolated schedules alternate, so that a run stopped
        early has both arms.
        """
        cfg = self.cfg
        groups, schedules = [], []
        tag = f"{model_key}|{card.card_id}|{card.style}"
        if "group" in cfg.arms:
            for condition in cfg.conditions:
                for idx in range(cfg.groups_per_cell):
                    groups.append((model_key, f"{tag}|{condition}|group|{idx}",
                                   lambda m=model_key, c=card, k=condition, i=idx:
                                   self.play_group(m, [c] * cfg.params.group_size, k, i)))
        if "isolated" in cfg.arms:
            for rep in range(cfg.isolated_reps):
                schedules.append((model_key, f"{tag}|N|isolated|{rep}",
                                  lambda m=model_key, c=card, r=rep: self.play_isolated(m, c, r)))
        out = []
        for k in range(max(len(groups), len(schedules))):
            out += groups[k:k + 1] + schedules[k:k + 1]
        return out

    def units(self) -> list[tuple[str, str, object]]:
        """(model key, label, callable) per group game / schedule, in run order.

        Shuffled round-robin over the cells (card x model), so that a run
        stopped early still has data from every card: pass k runs the k-th
        unit of every cell. Within a pass the cards are in a stable_seed
        order (new per pass) and the models rotate over them (Latin square),
        so every block of len(cards) consecutive units has every card once
        and the pass has every cell once. Never hash().
        """
        cfg = self.cfg
        models = sorted(cfg.models, key=lambda m: self._order_key("model", m))
        cells = {(m, c.card_id, c.style): self._cell_units(m, c)
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
            self._stop("run_aborted", error=str(e))

    def summary(self, started: float) -> dict:
        return {
            "run": self.cfg.run, "seed_namespace": self.cfg.seed_namespace,
            "stop_reason": self.stop_reason, "stopped_models": dict(self.stopped_models),
            "budget_usd": self.cfg.budget_usd, "invalid_rate_cap": self.cfg.invalid_rate_cap,
            "invalid_limit_per_model": self.invalid_limit,
            "planned_calls_per_model": self.cfg.planned_calls_per_model(),
            "max_tokens": self.max_tokens, "request_timeout_s": self.timeout,
            "reasoning_effort": {k: self.llm.reasoning_effort_label(self.cfg.effort_for(k))
                                 for k in self.cfg.models},
            "providers": {k: (provider_routing(p) | {"name": p["name"]}
                              if (p := self.cfg.provider_for(k)) else None)
                          for k in self.cfg.models},
            "isolated_frame": self.cfg.isolated_frame,
            "parallel_units": self.cfg.parallel_units, "workers": self.cfg.workers,
            "total_cost_usd": self.total_cost, "duration_s": time.time() - started,
            "n_provider_error": sum(s["n_provider_error"] for s in self.stats.values()),
            "per_model": {self.cfg.models[k]: dict(s) for k, s in self.stats.items()},
            "unit_order": list(self.unit_order),
        }

    def run(self) -> Path:
        cfg = self.cfg
        cfg.validate()                     # again: the output directory may be gone by now
        out_dir = cfg.output_dir()
        out_dir.mkdir(exist_ok=True)       # the parent exists (validate)
        path = out_dir / f"{cfg.run}.jsonl"
        summary_path = out_dir / f"{cfg.run}_summary.json"
        started = time.time()
        with open(path, "x", encoding="utf-8") as out:   # "x": never overwrite a run
            log_path = cfg.raw_log_path()
            previous_log = self.llm.set_log_path(log_path) if log_path else None
            self._out = out
            try:
                units = self.units()
                self.unit_order = [label for _, label, _ in units]
                self.llm._append_log({
                    "ts": time.time(), "event": "pgg_run_start", "run": cfg.run,
                    "seed_namespace": cfg.seed_namespace, "output_dir": str(out_dir),
                    "unit_order": self.unit_order})
                if cfg.parallel_units <= 1:
                    for unit in units:
                        self._run_unit(unit)
                else:
                    with ThreadPoolExecutor(max_workers=cfg.parallel_units) as pool:
                        list(pool.map(self._run_unit, units))
            finally:
                self._out = None
                out.flush()
                summary = self.summary(started)
                self.llm._append_log({"ts": time.time(), "event": "pgg_run_end", **summary})
                raw_log = Path(self.llm.LOG_PATH)
                # line counts after the pgg_run_end event; the summary is one JSON document
                summary["files"] = {
                    "results": {"path": str(path), "lines": _count_lines(path)},
                    "raw_log": {"path": str(raw_log), "lines": _count_lines(raw_log),
                                "redirected_for_run": log_path is not None},
                    "summary": {"path": str(summary_path)},
                }
                summary_path.write_text(
                    json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                if previous_log is not None:
                    self.llm.set_log_path(previous_log)
        self.files = summary["files"]
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
    """Config values the user still has to choose (placeholders)."""
    return [p for key in ("providers", "isolated_frame", "runs_dir", "results_dir")
            for p in placeholders_in(s.get(key), key)]


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
    ap.add_argument("--run", help="run name; output goes to <runs-dir>/<run>/")
    ap.add_argument("--config", help="JSON file with the options below (CLI wins)")
    ap.add_argument("--cards", help="JSON list of {card_id, style, text}")
    ap.add_argument("--cities", help="comma-separated: keep only these cards' \"city\" values")
    ap.add_argument("--cells", type=int, help="dry-run only: number of card x style cells "
                    "(default: cards file, else 6 = 2 identities x 3 styles)")
    ap.add_argument("--models", help="comma-separated keys or slugs (default: the 3 pilot models)")
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
                    help="client timeout per request, seconds (default 300)")
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
    return ap


def settings_from_args(args) -> dict:
    """Config file first, then explicitly given CLI options on top."""
    s = {}
    if args.config:
        s.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    cli = {
        "cards": args.cards, "cells": args.cells,
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


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    s = settings_from_args(args)
    params = s["params"]
    conditions = tuple(s.get("conditions", ("N",)))
    arms = tuple(s.get("arms", ARMS))
    groups_per_cell = s.get("groups_per_cell", 2)
    isolated_reps = s.get("isolated_reps", 2)
    points = tuple(s.get("isolated_points", ISOLATED_POINTS))
    names = s.get("models") or list(pgg_cost.PILOT_MODELS)

    cities = s.get("cities")
    if args.dry_run:
        models = resolve_models(names, pgg_cost.PILOT_MODELS)
        if s.get("cards"):
            n_cells = len(load_cards(s["cards"], cities))
        else:
            n_cells = s.get("cells", 6)
        print(dry_run_report(
            models=models, n_cells=n_cells, params=params, conditions=conditions, arms=arms,
            groups_per_cell=groups_per_cell, isolated_reps=isolated_reps, n_points=len(points),
            max_tokens=s.get("max_tokens")))
        guards = {k: s[k] for k in ("max_tokens", "request_timeout_s", "budget_usd",
                                    "invalid_rate_cap", "stop_on_length", "check_snapshot",
                                    "seed_namespace", "parallel_units", "workers",
                                    "isolated_frame") if s.get(k) is not None}
        print(f"Ayarlar: reasoning_effort={s.get('reasoning_effort') or 'gönderilmez'}, "
              + ", ".join(f"{k}={v}" for k, v in guards.items()))
        open_ = open_choices(s)
        if open_:
            print("SEÇİLMEMİŞ (gerçek koşu başlamaz): " + ", ".join(open_))
        return 0

    if not args.run or not s.get("cards"):
        build_parser().error("a real run needs --run and --cards (or use --dry-run)")
    # Everything that can stop a real run is checked here, before llm_client is
    # imported and before any call.
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
    llm = _llm()
    try:
        models = resolve_models(names, llm.MODELS)
        cfg = RunConfig(
            run=args.run, cards=load_cards(s["cards"], cities),
            models=models, params=params, conditions=conditions,
            arms=arms, groups_per_cell=groups_per_cell, isolated_reps=isolated_reps,
            isolated_points=points, reasoning_effort=s.get("reasoning_effort"),
            max_tokens=s.get("max_tokens"), max_invalid=s.get("max_invalid", 3),
            rationale=s.get("rationale", True), workers=s.get("workers", 1),
            parallel_units=s.get("parallel_units", 1),
            seed_namespace=s.get("seed_namespace", "pgg"),
            budget_usd=s.get("budget_usd"), invalid_rate_cap=s.get("invalid_rate_cap"),
            stop_on_length=bool(s.get("stop_on_length", False)),
            check_snapshot=bool(s.get("check_snapshot", False)),
            request_timeout_s=s.get("request_timeout_s"),
            providers=resolve_providers(s.get("providers"), models),
            isolated_frame=s.get("isolated_frame", "one_shot"),
            **output)
        engine = Engine(cfg, llm=llm)
    except ValueError as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1
    try:
        path = engine.run()
    except (RunAborted, RunStopped) as e:
        print(f"HATA: {e}", file=sys.stderr)
        _print_files(engine.files, file=sys.stderr)
        return 1
    if engine.stopped_models:
        print(f"UYARI: durdurulan modeller: {engine.stopped_models}", file=sys.stderr)
        print(f"yazıldı: {path}")
        _print_files(engine.files)
        return 2
    print(f"yazıldı: {path}")
    _print_files(engine.files)
    return 0


def _print_files(files: dict | None, file=None) -> None:
    """Output files of the run and their line counts (summary["files"])."""
    for name, f in (files or {}).items():
        lines = f.get("lines")
        print(f"dosya ({name}): {f['path']}" + (f" — {lines} satır" if lines is not None else ""),
              file=file)


if __name__ == "__main__":
    sys.exit(main())
