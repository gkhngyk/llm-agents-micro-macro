"""
Frame files: every prompt text of the public goods engine, outside the code.

A frame file is a JSON document (frames/<name>.json in the repository, or any
path given in the config, e.g. a story file in the workspace) with templates
for the system message, the rules, the history lines, the round question, the
punishment step, the isolated question(s), the rule-comprehension questions
and the field names of the response schema. frames/SCHEMA.md documents the
format; this module loads, validates and renders it.

Numbers are never written in a frame file. They come from GameParams through
placeholders ({n}, {endowment}, {mpcr}, {multiplier}, {rounds}, {round_no},
{others_mean}, ...), formatted as the engine always did (_num). Literal text
may hold no digit except a lone "0" (as in "from 0 to {endowment}") and a
"1. " / "2. " enumeration at the start of a line; a template with an unknown
placeholder, without a required one, with a format spec / conversion or with
unbalanced braces is a validation error (FrameError), and a run with such a
frame does not start.

frames/abstract_v2.json holds the texts of the engine up to c0b91f5 (pilot
v2), character for character (tests/test_frames.py); it is the frame of every
config that names none. Each loaded frame carries the sha256 of its file,
which goes on every result row.

Deliberately imports neither pgg_game nor llm_client (dry runs use it too).
"""

from __future__ import annotations

import hashlib
import json
import re
import string
from dataclasses import dataclass
from pathlib import Path

FRAMES_DIR = Path(__file__).resolve().parent / "frames"
DEFAULT_FRAME = "abstract_v2"
SCHEMA_VERSION = 1

# Wordings of the isolated question; a frame defines the ones it supports.
ISOLATED_FRAMES = ("one_shot", "repeated", "fixed_round")
RULES_VARIANTS = ("single_round", "multi_round")
# Tags of a rules line ("when"): all must hold for the line to be shown.
RULE_TAGS = ("single_round", "multi_round", "N", "P")

# Placeholders of the game parameters, allowed in every template.
GAME_VARS = frozenset({"n", "n_others", "rounds", "endowment", "mpcr", "multiplier",
                       "max_punish", "punish_cost", "punish_impact"})

# Kinds of rule-comprehension question: their values and placeholders. The
# answer key is computed from GameParams (comprehension_key), never written.
COMPREHENSION_KINDS = ("round_earnings", "own_change")

TOP_KEYS = {"schema", "name", "description", "kind", "system", "player_label", "you_suffix",
            "rules", "history", "contribute", "punish", "isolated", "comprehension", "response"}
OPTIONAL_TOP_KEYS = {"description", "kind", "comprehension", "response"}
# "kind" of a frame (task #67): a "story" frame must hold none of the forbidden
# roots of the frame linter (cerceve_linter.ROOTS: game, player, contribut,
# ...), checked at the start of every run; an "abstract" frame (the default)
# says "game" / "contribute" on purpose and is not linted.
FRAME_KINDS = ("abstract", "story")
DEFAULT_KIND = "abstract"
HISTORY_KEYS = {"empty", "header", "list_item", "list_separator", "contributions", "round",
                "round_P", "punish_given_separator", "punish_given_none"}
RESPONSE_DEFAULTS = {
    "decision_key": "contribution",
    "rationale_description": "One or two sentences on why you chose this.",
    "punishment_key": "punishments",
    "punishment_description": "Punishment points per other player, keyed by player number.",
}

# Literal digits allowed: a lone 0, and "1. " enumerations at a line start.
_DIGITS = re.compile(r"\d+(?:[.,]\d+)?")
_ENUMERATION = re.compile(r"(?m)^\d\. ")


class FrameError(ValueError):
    """A frame file does not follow frames/SCHEMA.md; the run does not start."""


def fmt_num(x: float) -> str:
    """12.0 -> "12", 24.4 -> "24.4" (the engine's number format, pgg_game._num)."""
    return f"{round(x, 4):.4f}".rstrip("0").rstrip(".")


def _project_share(params, contributions) -> float:
    """mpcr * sum(c); the same as pgg_game.project_share (a test checks it)."""
    return round(params.mpcr * sum(contributions), 9)


def game_values(params) -> dict:
    """Values of GAME_VARS for these parameters, formatted as the engine's texts."""
    return {"n": f"{params.group_size}", "n_others": f"{params.group_size - 1}",
            "rounds": f"{params.rounds}", "endowment": f"{params.endowment}",
            "mpcr": fmt_num(params.mpcr), "multiplier": fmt_num(params.mpcr * params.group_size),
            "max_punish": f"{params.max_punish}", "punish_cost": fmt_num(params.punish_cost),
            "punish_impact": fmt_num(params.punish_impact)}


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def template_fields(text: str) -> list[str]:
    """Placeholder names of a template; FrameError on bad syntax.

    Only plain names: no positional "{}", no format spec, no conversion.
    """
    try:
        parts = list(string.Formatter().parse(text))
    except ValueError as e:
        raise FrameError(f"bad braces ({e})") from None
    names = []
    for _literal, name, spec, conversion in parts:
        if name is None:
            continue
        if name == "" or spec or conversion:
            raise FrameError(f"placeholder {{{name}{'!' + conversion if conversion else ''}"
                             f"{':' + spec if spec else ''}}} must be a plain name")
        names.append(name)
    return names


def literal_digits(text: str) -> list[str]:
    """Numbers written in the literal text of a template (not allowed, except a lone 0)."""
    literal = "".join(lit for lit, *_ in string.Formatter().parse(text))
    literal = _ENUMERATION.sub("", literal)
    return [m for m in _DIGITS.findall(literal) if m != "0"]


def _comprehension_vars(answer: dict) -> set[str]:
    """Placeholders a comprehension question of this answer spec may (and must) use."""
    if answer.get("kind") == "round_earnings":
        others = answer.get("others")
        k = len(others) if isinstance(others, list) else 0
        return {"own"} | {f"other_{i}" for i in range(1, k + 1)}
    if answer.get("kind") == "own_change":
        return {"delta"} | ({"example"} if "example" in answer else set())
    return set()


class _Checker:
    def __init__(self, where: str):
        self.where = where
        self.problems: list[str] = []

    def add(self, path: str, message: str) -> None:
        self.problems.append(f"{path}: {message}")

    def string(self, value, path: str, *, empty_ok: bool = False) -> bool:
        if not isinstance(value, str):
            self.add(path, f"must be a string, got {type(value).__name__}")
            return False
        if not empty_ok and not value.strip():
            self.add(path, "must not be empty")
            return False
        return True

    def template(self, value, path: str, allowed=frozenset(), required=(), *,
                 empty_ok: bool = False, game_vars: bool = True) -> set[str]:
        """Check one template; returns its placeholder names (empty set if broken).

        game_vars: GAME_VARS are allowed too (not in the system message, which
        is rendered from the card alone).
        """
        if not self.string(value, path, empty_ok=empty_ok):
            return set()
        try:
            names = set(template_fields(value))
        except FrameError as e:
            self.add(path, str(e))
            return set()
        known = set(allowed) | (GAME_VARS if game_vars else set())
        unknown = names - known
        if unknown:
            self.add(path, f"unknown placeholder(s) {sorted(unknown)}; allowed here: "
                           f"{sorted(known)}")
        for group in required:
            if not names & set(group):
                self.add(path, "missing placeholder " + " or ".join(f"{{{g}}}" for g in sorted(group)))
        digits = literal_digits(value)
        if digits:
            self.add(path, f"numbers written in the text {digits}: numbers come from the game "
                           "parameters through placeholders")
        return names

    def template_lines(self, value, path: str, allowed, required) -> None:
        """A list of template lines; the required placeholders may be on any of them."""
        if not isinstance(value, list) or not value:
            self.add(path, "must be a non-empty list of strings")
            return
        names: set[str] = set()
        for i, line in enumerate(value):
            names |= self.template(line, f"{path}[{i}]", allowed)
        for group in required:
            if not names & set(group):
                self.add(path, "missing placeholder " + " or ".join(f"{{{g}}}" for g in sorted(group)))


def validate_frame(raw, where: str = "frame") -> None:
    """FrameError listing every problem of a frame document (frames/SCHEMA.md)."""
    c = _Checker(where)
    if not isinstance(raw, dict):
        raise FrameError(f"{where}: a frame file must be a JSON object")
    keys = {k for k in raw if not k.startswith("_")}
    for k in sorted(keys - TOP_KEYS):
        c.add(k, f"unknown key; allowed {sorted(TOP_KEYS)} (and comments starting with _)")
    for k in sorted(TOP_KEYS - OPTIONAL_TOP_KEYS - keys):
        c.add(k, "missing")
    if raw.get("schema") != SCHEMA_VERSION:
        c.add("schema", f"must be {SCHEMA_VERSION}")
    name = raw.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        c.add("name", "must be [A-Za-z0-9_.-]+")
    if "description" in raw:
        c.string(raw["description"], "description")
    if "kind" in raw and raw["kind"] not in FRAME_KINDS:
        c.add("kind", f"must be one of {FRAME_KINDS}")
    if "system" in raw:
        c.template(raw["system"], "system", {"card"}, [{"card"}], game_vars=False)
    if "player_label" in raw:
        c.template(raw["player_label"], "player_label", {"player_no"}, [{"player_no"}])
    if "you_suffix" in raw:
        c.template(raw["you_suffix"], "you_suffix", empty_ok=True)
    _check_rules(c, raw.get("rules"))
    _check_history(c, raw.get("history"))
    if "contribute" in raw:
        c.template(raw["contribute"], "contribute", {"round_no", "me"},
                   [{"round_no"}, {"endowment"}])
    if "punish" in raw:
        c.template(raw["punish"], "punish",
                   {"round_no", "me", "contributions", "project_share", "earnings", "max_points"},
                   [{"round_no"}, {"contributions"}, {"max_points"}])
    _check_isolated(c, raw.get("isolated"))
    if "comprehension" in raw:
        _check_comprehension(c, raw["comprehension"])
    if "response" in raw:
        _check_response(c, raw["response"])
    if c.problems:
        raise FrameError(f"{where}: frame file does not follow frames/SCHEMA.md:\n  - "
                         + "\n  - ".join(c.problems))


def _check_rules(c: _Checker, rules) -> None:
    if rules is None:
        return
    if not isinstance(rules, list) or not rules:
        c.add("rules", "must be a non-empty list of {\"text\"[, \"when\"]} objects")
        return
    names: set[str] = set()
    p_names: set[str] = set()
    for i, item in enumerate(rules):
        path = f"rules[{i}]"
        if not isinstance(item, dict) or "text" not in item or set(item) - {"text", "when"}:
            c.add(path, "must be an object with \"text\" and optionally \"when\"")
            continue
        found = c.template(item["text"], f"{path}.text")
        when = item.get("when", [])
        if not isinstance(when, list) or any(t not in RULE_TAGS for t in when):
            c.add(f"{path}.when", f"must be a list of tags from {RULE_TAGS}")
            when = []
        names |= found
        if "P" in when:
            p_names |= found
    for group in ({"n"}, {"endowment"}, {"mpcr", "multiplier"}):
        if not names & group:
            c.add("rules", "missing placeholder " + " or ".join(f"{{{g}}}" for g in sorted(group)))
    for var in ("max_punish", "punish_cost", "punish_impact"):
        if var not in p_names:
            c.add("rules", f"no line with \"when\": [\"P\"] holds {{{var}}}")


def _check_history(c: _Checker, history) -> None:
    if history is None:
        return
    if not isinstance(history, dict):
        c.add("history", "must be an object")
        return
    for k in sorted(set(history) - HISTORY_KEYS):
        if not k.startswith("_"):
            c.add(f"history.{k}", f"unknown key; allowed {sorted(HISTORY_KEYS)}")
    for k in sorted(HISTORY_KEYS - set(history)):
        c.add(f"history.{k}", "missing")
    h = history
    if "empty" in h:
        c.template(h["empty"], "history.empty")
    if "header" in h:
        c.template(h["header"], "history.header")
    if "list_item" in h:
        c.template(h["list_item"], "history.list_item", {"label", "value"}, [{"label"}, {"value"}])
    for k in ("list_separator", "punish_given_separator"):
        if k in h:
            c.template(h[k], f"history.{k}", empty_ok=True)
    if "punish_given_none" in h:
        c.template(h["punish_given_none"], "history.punish_given_none")
    if "contributions" in h:
        c.template(h["contributions"], "history.contributions",
                   {"contributions_list", "group_total"}, [{"contributions_list"}])
    if "round" in h:
        c.template_lines(h["round"], "history.round",
                         {"round", "contributions", "project_share", "round_earnings"},
                         [{"round"}, {"contributions"}, {"round_earnings"}])
    if "round_P" in h:
        c.template_lines(h["round_P"], "history.round_P",
                         {"punish_given", "cost_paid", "received", "points_lost", "final_earnings"},
                         [{"punish_given"}, {"received"}, {"final_earnings"}])


def _check_isolated(c: _Checker, isolated) -> None:
    if isolated is None:
        return
    if not isinstance(isolated, dict) or not isolated:
        c.add("isolated", f"must be an object with at least one of {ISOLATED_FRAMES}")
        return
    for frame, spec in isolated.items():
        path = f"isolated.{frame}"
        if frame.startswith("_"):
            continue
        if frame not in ISOLATED_FRAMES:
            c.add(path, f"unknown isolated frame; allowed {ISOLATED_FRAMES}")
            continue
        if not isinstance(spec, dict) or set(spec) != {"rules", "question"}:
            c.add(path, "must be an object with exactly \"rules\" and \"question\"")
            continue
        if spec["rules"] not in RULES_VARIANTS:
            c.add(f"{path}.rules", f"must be one of {RULES_VARIANTS}")
        allowed = {"others_mean", "round_no"} if frame == "fixed_round" else {"others_mean"}
        c.template(spec["question"], f"{path}.question", allowed, [{v} for v in sorted(allowed)])


def _check_comprehension(c: _Checker, comp) -> None:
    if not isinstance(comp, dict) or set(comp) - {"prompt", "questions"} or "prompt" not in comp \
            or "questions" not in comp:
        c.add("comprehension", "must be an object with exactly \"prompt\" and \"questions\"")
        return
    questions = comp["questions"]
    if not isinstance(questions, list) or not questions:
        c.add("comprehension.questions", "must be a non-empty list")
        return
    ids = []
    for i, q in enumerate(questions):
        path = f"comprehension.questions[{i}]"
        if not isinstance(q, dict) or set(q) != {"id", "text", "answer"}:
            c.add(path, "must be an object with exactly \"id\", \"text\" and \"answer\"")
            continue
        qid = q["id"]
        if not isinstance(qid, str) or not re.fullmatch(r"q[0-9]+", qid) or qid in ids:
            c.add(f"{path}.id", "must be a unique id q1, q2, ...")
            continue
        ids.append(qid)
        answer = q["answer"]
        problem = _answer_spec_problem(answer)
        if problem:
            c.add(f"{path}.answer", problem)
            continue
        allowed = _comprehension_vars(answer)
        c.template(q["text"], f"{path}.text", allowed, [{v} for v in sorted(allowed)])
    c.template(comp["prompt"], "comprehension.prompt", set(ids), [{q} for q in ids])


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _answer_spec_problem(answer) -> str | None:
    if not isinstance(answer, dict) or answer.get("kind") not in COMPREHENSION_KINDS:
        return f"must be an object whose \"kind\" is one of {COMPREHENSION_KINDS}"
    if answer["kind"] == "round_earnings":
        if set(answer) != {"kind", "own", "others"}:
            return "round_earnings takes exactly \"own\" (int) and \"others\" (list of int)"
        others = answer["others"]
        if not _is_int(answer["own"]) or answer["own"] < 0 or not isinstance(others, list) \
                or not others or not all(_is_int(x) and x >= 0 for x in others):
            return "round_earnings: own and others must be non-negative integers"
    else:
        if not {"kind", "delta"} <= set(answer) <= {"kind", "delta", "example"} \
                or not all(_is_int(answer[k]) and answer[k] > 0
                           for k in ("delta", "example") if k in answer):
            return ("own_change takes \"delta\" and optionally \"example\" (a number for the "
                    "sign example of the text), both positive integers")
    return None


def _check_response(c: _Checker, response) -> None:
    if not isinstance(response, dict):
        c.add("response", "must be an object")
        return
    for k in sorted(set(response) - set(RESPONSE_DEFAULTS)):
        c.add(f"response.{k}", f"unknown key; allowed {sorted(RESPONSE_DEFAULTS)}")
    for k in ("decision_key", "punishment_key"):
        if k in response and (not isinstance(response[k], str)
                              or not re.fullmatch(r"[a-z_]+", response[k])):
            c.add(f"response.{k}", "must be a lower-case JSON key [a-z_]+")
    if response.get("decision_key", "contribution") == "rationale" \
            or response.get("punishment_key", "punishments") == "rationale":
        c.add("response", "\"rationale\" is reserved for the rationale field")
    for k in ("rationale_description", "punishment_description"):
        if k in response:
            c.template(response[k], f"response.{k}")


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def frame_path(label: str, path=None) -> Path:
    """File of a frame: the given path, else frames/<label>.json of the repository."""
    return Path(path) if path is not None else FRAMES_DIR / f"{label}.json"


def load_frame(path) -> "Frame":
    """Read and validate a frame file; FrameError if it is missing or invalid."""
    path = Path(path)
    try:
        data = path.read_bytes()
    except OSError as e:
        raise FrameError(f"frame file {str(path)!r} cannot be read ({e})") from None
    try:
        raw = json.loads(data.decode("utf-8"))
    except ValueError as e:
        raise FrameError(f"frame file {str(path)!r} is not valid JSON ({e})") from None
    validate_frame(raw, str(path))
    return Frame(name=raw["name"], path=str(path), sha256=hashlib.sha256(data).hexdigest(),
                 data=raw)


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

@dataclass(frozen=True, eq=False)
class Frame:
    """A validated frame file; renders the messages of every call."""
    name: str                  # the file's "name"
    path: str
    sha256: str                # of the file's bytes
    data: dict

    # -- small parts ---------------------------------------------------------

    def _fill(self, template: str, params, **values) -> str:
        return template.format_map({**game_values(params), **values})

    @property
    def isolated_frames(self) -> tuple[str, ...]:
        return tuple(k for k in ISOLATED_FRAMES if k in self.data["isolated"])

    @property
    def kind(self) -> str:
        """"story" or "abstract" (FRAME_KINDS); only a story frame is linted."""
        return self.data.get("kind", DEFAULT_KIND)

    @property
    def has_comprehension(self) -> bool:
        return "comprehension" in self.data

    def response(self, key: str) -> str:
        return self.data.get("response", {}).get(key, RESPONSE_DEFAULTS[key])

    @property
    def decision_key(self) -> str:
        return self.response("decision_key")

    @property
    def punishment_key(self) -> str:
        return self.response("punishment_key")

    def player(self, params, j: int) -> str:
        return self._fill(self.data["player_label"], params, player_no=f"{j + 1}")

    def label(self, params, j: int, me: int) -> str:
        return self.player(params, j) + (self._fill(self.data["you_suffix"], params)
                                         if j == me else "")

    def _listing(self, params, items, me: int, separator: str) -> str:
        h = self.data["history"]
        return separator.join(self._fill(h["list_item"], params, label=self.label(params, j, me),
                                         value=f"{v}") for j, v in items)

    # -- texts ---------------------------------------------------------------

    def system_message(self, card) -> dict:
        return {"role": "system", "content": self.data["system"].format_map({"card": card.text})}

    def rules_text(self, params, condition: str, *, single_round: bool = False) -> str:
        tags = {"single_round" if single_round else "multi_round", condition}
        return "\n".join(self._fill(item["text"], params) for item in self.data["rules"]
                         if set(item.get("when", [])) <= tags)

    def contributions_line(self, params, contributions, me: int) -> str:
        h = self.data["history"]
        listing = self._listing(params, enumerate(contributions), me,
                                self._fill(h["list_separator"], params))
        return self._fill(h["contributions"], params, contributions_list=listing,
                          group_total=f"{sum(contributions)}")

    def history_text(self, params, condition: str, history, me: int) -> str:
        h = self.data["history"]
        if not history:
            return self._fill(h["empty"], params)
        lines = [self._fill(h["header"], params)]
        for rec in history:
            values = {"round": f"{rec.round}",
                      "contributions": self.contributions_line(params, rec.contributions, me),
                      "project_share": fmt_num(_project_share(params, rec.contributions)),
                      "round_earnings": fmt_num(rec.round_earnings[me])}
            lines += [self._fill(line, params, **values) for line in h["round"]]
            if condition == "P":
                given = self._listing(
                    params, [(j, p) for j, p in enumerate(rec.punishment[me]) if p], me,
                    self._fill(h["punish_given_separator"], params))
                values = {"punish_given": given or self._fill(h["punish_given_none"], params),
                          "cost_paid": fmt_num(rec.cost_paid[me]),
                          "received": f"{rec.received[me]}",
                          "points_lost": fmt_num(rec.received[me] * params.punish_impact),
                          "final_earnings": fmt_num(rec.final_earnings[me])}
                lines += [self._fill(line, params, **values) for line in h["round_P"]]
        return "\n".join(lines)

    def contribution_messages(self, params, condition, card, history, me, round_no) -> list[dict]:
        user = "\n\n".join([
            self.rules_text(params, condition),
            self.history_text(params, condition, history, me),
            self._fill(self.data["contribute"], params, round_no=f"{round_no}",
                       me=self.player(params, me)),
        ])
        return [self.system_message(card), {"role": "user", "content": user}]

    def punishment_messages(self, params, card, history, me, round_no, contributions,
                            earnings, budget: int) -> list[dict]:
        user = "\n\n".join([
            self.rules_text(params, "P"),
            self.history_text(params, "P", history, me),
            self._fill(self.data["punish"], params, round_no=f"{round_no}",
                       me=self.player(params, me),
                       contributions=self.contributions_line(params, contributions, me),
                       project_share=fmt_num(_project_share(params, contributions)),
                       earnings=fmt_num(earnings), max_points=f"{budget // params.punish_cost}"),
        ])
        return [self.system_message(card), {"role": "user", "content": user}]

    def isolated_messages(self, params, card, others_mean: int, isolated_frame: str,
                          round_no: int | None = None) -> list[dict]:
        spec = self.data["isolated"].get(isolated_frame) if isolated_frame in ISOLATED_FRAMES \
            else None
        if spec is None:
            raise ValueError(f"isolated_frame must be one of {self.isolated_frames} for frame "
                             f"{self.name!r}, got {isolated_frame!r}")
        values = {"others_mean": f"{others_mean}"}
        if isolated_frame == "fixed_round":
            if round_no is None:
                raise ValueError("isolated_frame fixed_round needs a round number")
            values["round_no"] = f"{round_no}"
        rules = self.rules_text(params, "N", single_round=spec["rules"] == "single_round")
        user = "\n\n".join([rules, self._fill(spec["question"], params, **values)])
        return [self.system_message(card), {"role": "user", "content": user}]

    # -- rule comprehension --------------------------------------------------

    def comprehension_questions(self) -> list[dict]:
        return list(self.data["comprehension"]["questions"]) if self.has_comprehension else []

    def comprehension_messages(self, params, card, condition: str = "N", *,
                               single_round: bool = False) -> list[dict]:
        """The rule-comprehension call: the rules, then the questions (no game history)."""
        comp = self.data["comprehension"]
        texts = {}
        for q in comp["questions"]:
            a = q["answer"]
            if a["kind"] == "round_earnings":
                values = {"own": f"{a['own']}",
                          **{f"other_{i}": f"{x}" for i, x in enumerate(a["others"], 1)}}
            else:
                values = {"delta": f"{a['delta']}",
                          **({"example": f"{a['example']}"} if "example" in a else {})}
            texts[q["id"]] = self._fill(q["text"], params, **values)
        user = "\n\n".join([self.rules_text(params, condition, single_round=single_round),
                            self._fill(comp["prompt"], params, **texts)])
        return [self.system_message(card), {"role": "user", "content": user}]

    def comprehension_key(self, params) -> dict[str, int]:
        """Correct answer of every question, computed from the game parameters.

        round_earnings: endowment - own + mpcr * (own + sum(others));
        own_change: delta * (mpcr - 1). ValueError when an answer is not a whole
        number or the values do not fit the parameters (answers are integers).
        """
        out = {}
        for q in self.comprehension_questions():
            a = q["answer"]
            if a["kind"] == "round_earnings":
                if len(a["others"]) != params.group_size - 1:
                    raise ValueError(f"frame {self.name!r} {q['id']}: {len(a['others'])} others, "
                                     f"the group has {params.group_size - 1}")
                if any(x > params.endowment for x in [a["own"], *a["others"]]):
                    raise ValueError(f"frame {self.name!r} {q['id']}: a contribution above the "
                                     f"endowment {params.endowment}")
                value = params.endowment - a["own"] + params.mpcr * (a["own"] + sum(a["others"]))
            else:
                value = a["delta"] * (params.mpcr - 1)
            if abs(value - round(value)) > 1e-9:
                raise ValueError(f"frame {self.name!r} {q['id']}: the answer {value!r} is not a "
                                 "whole number with these parameters; choose other values")
            out[q["id"]] = int(round(value))
        return out

    def comprehension_schema(self, rationale: bool) -> dict:
        ids = [q["id"] for q in self.comprehension_questions()]
        props = {qid: {"type": "integer", "description": f"Answer to question {i}"}
                 for i, qid in enumerate(ids, 1)}
        if rationale:
            props["rationale"] = {"type": "string",
                                  "description": self.response("rationale_description")}
        return {"type": "object", "required": ids, "properties": props}

    def is_valid_comprehension(self, payload) -> bool:
        """Schema only: an integer per question. A wrong answer is still valid."""
        return isinstance(payload, dict) and all(
            _is_int(payload.get(q["id"])) for q in self.comprehension_questions())

    def describe(self) -> dict:
        return {"frame_id": self.name, "kind": self.kind, "sha256": self.sha256,
                "path": self.path}
