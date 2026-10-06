"""Frozen copy of the prompt functions of pgg_game.py at commit c0b91f5 (pilot v2).

Reference for tests/test_frames.py: frames/abstract_v2.json must render exactly
these texts. Copied verbatim (git show c0b91f5:pgg_game.py, from _num to
punishment_budget); do not edit. Card, GameParams and project_share come
from pgg_game (unchanged rules).
"""

from __future__ import annotations

from dataclasses import dataclass

from pgg_game import Card, GameParams, project_share  # noqa: F401  (used by the copy)

ISOLATED_FRAMES = ("one_shot", "repeated")


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
