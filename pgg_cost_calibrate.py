"""
Token and cost calibration of pgg_cost.py from a finished run (task B4).

Reads a run directory READ-ONLY (results <run>.jsonl, <run>_summary.json,
raw_calls.jsonl) and writes one small JSON (default
configs/cost_calibration_pilot_v2.json) with, per model x call kind, the mean
and p95 of prompt, completion and reasoning tokens and of the billed
usage.cost of the calls behind the valid rows; plus the calls that were paid
but did not become a valid row (provider errors, rows of superseded units,
paid calls without a row) as a separate count and cost ratio.

The output holds aggregates only: no account id, no prompt or response text,
no session ids. The raw log is read, never copied. No API call, no key.

Valid rows: the summary's row_validity_rule; a row counts unless its
(unit, segment) is in summary["superseded_units"] (rows without a segment are
segment 0). Pilot v2 resumed whole units only, so this is the full rule there.

Mistral (mistralai/mistral-large-4-0) has no pilot data; its entry is built
from the measured models and the plumbing call of task B2 and marked
"estimate": true with every assumption written out.

Task #71 (EMIR 2 M2a): --m1-run-dir writes an overlay,
configs/cost_calibration_minipilot_m1.json, with a Mistral entry from the M1
plumbing measurement (runs/tesisat_olcum_<date>: round 1 and isolated X = 10
of abstract_v3; results.jsonl and summary.json, the raw log is not read).
Its later rounds and other isolated values come from pilot v2's round
profile (--later-rounds, every choice labelled tahmin). pgg_cost.py loads
the pilot v2 file and replaces its Mistral entry with the overlay's.

Task #93 (EMIR 5): --minipilot-run-dir writes the overlay
configs/cost_calibration_minipilot.json from the mini-pilot's real token
distribution (runs/minipilot_<date>), per model x call type: group round 1,
group rounds 2-10, isolated, rule comprehension (mean and p95), from the
abstract_v3 rows (the main frame abstract_v4 differs from it only by one
system line). Story rows are summarised apart (information). The raw log is
read for its "model" and "usage" fields only (paid cost per model); nothing
of it is written. A config names the overlay with "cost_calibration"
(pgg_game); the default calibration of pgg_cost is not changed by it.

Usage:
  python pgg_cost_calibrate.py --run-dir <workspace>/runs/pilot_v2_20261005
  python pgg_cost_calibrate.py --m1-run-dir <workspace>/runs/tesisat_olcum_20261007 \
      --ratio-run-dir <workspace>/runs/pilot_v2_20261005
  python pgg_cost_calibrate.py --minipilot-run-dir <workspace>/runs/minipilot_20261008
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "configs" / "cost_calibration_pilot_v2.json"
MINIPILOT_M1_OUT = ROOT / "configs" / "cost_calibration_minipilot_m1.json"
MINIPILOT_OUT = ROOT / "configs" / "cost_calibration_minipilot.json"
MINIPILOT_CONFIG = ROOT / "configs" / "minipilot.json"

MISTRAL = "mistralai/mistral-large-4-0"
# Listed price of the only endpoint (tag "mistral"), GET
# /api/v1/models/mistralai/mistral-large-4-0/endpoints on 2026-10-06 (task #58);
# the plumbing call of task #59 was billed exactly this (94 x 0,68 + 7 x 2,09
# per 1M = 0,00007855 USD), so the endpoint's "discount": 0.5 was not applied.
MISTRAL_PRICE_USD_PER_M = (0.68, 2.09)
# Task #59 (workspace/gorev_mistral_tesisat.md): usage has
# completion_tokens_details.reasoning_tokens, value 0, reasoning text null, with
# reasoning / reasoning_effort not sent (as in the mini-pilot config).
MISTRAL_B2 = {"reasoning_tokens_field": True, "reasoning_tokens": 0,
              "reasoning_text_returned": False, "prompt_tokens": 94, "completion_tokens": 7,
              "cost_usd": 0.00007855, "source": "workspace/gorev_mistral_tesisat.md (task #59)"}

TOKEN_FIELDS = ("prompt_tokens", "completion_tokens", "reasoning_tokens", "visible_tokens")


def quantile(values, q: float) -> float:
    """Linear interpolation between order statistics (numpy's default method)."""
    xs = sorted(values)
    if not xs:
        raise ValueError("no values")
    pos = (len(xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def stats(values, digits: int = 6) -> dict:
    values = list(values)
    return {"mean": round(sum(values) / len(values), digits),
            "p95": round(quantile(values, 0.95), digits)}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def call_kind(row: dict) -> str:
    """pgg_cost call kind of a results row."""
    if row.get("step") == "comprehension":         # rule comprehension (task #61)
        return "comprehension"
    if row["arm"] == "isolated":
        return "isolated"
    return f"{row['step']}_{row['condition']}"


def unit_key(row: dict) -> str:
    """Unit label of a row; built from session_id when the row has no "unit".

    A run with frames (task #61) ends its session ids with "-<frame>" and its
    unit labels with "|<frame>"; rows of other runs have no such suffix.
    """
    session_id, suffix = row["session_id"], ""
    frame = row.get("frame")
    if frame and session_id.endswith(f"-{frame}"):
        session_id, suffix = session_id[:-len(frame) - 1], f"|{frame}"
    arm, idx = session_id.rsplit("-", 2)[-2:]
    key = (f"{row['model_key']}|{row['card_id']}|{row['style']}|{row['condition']}"
           f"|{arm}|{int(idx)}{suffix}")
    if "unit" in row and row["unit"] != key:
        raise ValueError(f"unit {row['unit']!r} does not match session_id {row['session_id']!r}")
    return key


def usage_tokens(usage: dict) -> dict:
    details = usage.get("completion_tokens_details") or {}
    reasoning = details.get("reasoning_tokens") or 0
    return {"prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "reasoning_tokens": reasoning,
            "visible_tokens": usage["completion_tokens"] - reasoning}


def _cost(usage) -> float | None:
    cost = (usage or {}).get("cost")
    return float(cost) if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None


def run_rows(run_dir: Path) -> tuple[Path, dict, Path, list, list, list]:
    """(summary path, summary, results path, rows, valid rows, superseded rows) of a run."""
    run_dir = Path(run_dir)
    summary_path = next(iter(sorted(run_dir.glob("*_summary.json"))))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    results_path = run_dir / f"{summary['run']}.jsonl"
    superseded = {(u["unit"], u["segment"]) for u in summary["superseded_units"]}
    rows = read_jsonl(results_path)
    valid, dropped = [], []
    for r in rows:
        (dropped if (unit_key(r), r.get("segment", 0)) in superseded else valid).append(r)
    return summary_path, summary, results_path, rows, valid, dropped


def calibrate(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    summary_path, summary, results_path, rows, valid, dropped = run_rows(run_dir)
    run = summary["run"]
    raw_path = run_dir / "raw_calls.jsonl"
    models = summary["config"]["models"]                # key -> slug
    planned = summary["planned_calls_per_model"]
    per_model_valid = Counter(r["model"] for r in valid)
    if any(per_model_valid[slug] != planned for slug in models.values()):
        raise ValueError(f"valid rows per model {dict(per_model_valid)} != planned {planned}")

    calls = [c for c in read_jsonl(raw_path) if "event" not in c and "model" in c]

    out_models = {}
    for key, slug in models.items():
        m_valid = [r for r in valid if r["model"] == slug]
        m_rows = [r for r in rows if r["model"] == slug]
        m_dropped = [r for r in dropped if r["model"] == slug]
        m_calls = [c for c in calls if c["model"] == slug]
        paid = [c for c in m_calls if _cost(c.get("usage")) is not None]
        provider_error = [c for c in paid if c.get("finish_reason") == "error"]
        n_no_usage = sum(1 for c in m_calls if _cost(c.get("usage")) is None)

        total_cost = sum(_cost(c["usage"]) for c in paid)
        valid_cost = sum(_cost(r["usage"]) for r in m_valid)
        superseded_cost = sum(_cost(r["usage"]) for r in m_dropped)
        provider_error_cost = sum(_cost(c["usage"]) for c in provider_error)
        n_other = len(paid) - len(m_rows) - len(provider_error)
        if n_other < 0:
            raise ValueError(f"{slug}: more rows than paid calls")
        paid_invalid_cost = total_cost - valid_cost

        # effective price: billed cost / tokens of the valid calls, split with
        # usage.cost_details (prompt / completions); includes prompt caching
        prompt_cost = sum(r["usage"]["cost_details"]["upstream_inference_prompt_cost"]
                          for r in m_valid)
        compl_cost = sum(r["usage"]["cost_details"]["upstream_inference_completions_cost"]
                         for r in m_valid)
        if abs(prompt_cost + compl_cost - valid_cost) > 1e-9:
            raise ValueError(f"{slug}: cost_details do not add up to usage.cost")
        n_prompt = sum(r["usage"]["prompt_tokens"] for r in m_valid)
        n_compl = sum(r["usage"]["completion_tokens"] for r in m_valid)
        cached = sum((r["usage"].get("prompt_tokens_details") or {}).get("cached_tokens") or 0
                     for r in m_valid)

        kinds = {}
        for kind in sorted({call_kind(r) for r in m_valid}):
            k_rows = [r for r in m_valid if call_kind(r) == kind]
            toks = [usage_tokens(r["usage"]) for r in k_rows]
            entry = {"n": len(k_rows)}
            for field in TOKEN_FIELDS:
                entry[field] = stats(t[field] for t in toks)
            entry["cost_usd"] = stats((_cost(r["usage"]) for r in k_rows), digits=12)
            entry["cost_usd_sum"] = round(sum(_cost(r["usage"]) for r in k_rows), 10)
            kinds[kind] = entry

        out_models[slug] = {
            "key": key,
            "estimate": False,
            "price_usd_per_m": {
                "input": round(prompt_cost / n_prompt * 1e6, 6),
                "output": round(compl_cost / n_compl * 1e6, 6),
                "source": (f"calibration: billed usage.cost_details (prompt / completions) "
                           f"/ tokens of the {len(m_valid)} valid calls of {run}"),
            },
            "cached_prompt_token_share": round(cached / n_prompt, 6),
            "provider": summary["providers"][key].get("name"),
            "kinds": kinds,
            "paid": {
                "n_paid_calls": len(paid),
                "n_valid": len(m_valid),
                "n_paid_invalid": len(paid) - len(m_valid),
                "n_provider_error": len(provider_error),
                "n_superseded_rows": len(m_dropped),
                "n_paid_without_row": n_other,
                "n_no_usage": n_no_usage,
                "total_cost_usd": round(total_cost, 10),
                "valid_cost_usd": round(valid_cost, 10),
                "paid_invalid_cost_usd": round(paid_invalid_cost, 10),
                "provider_error_cost_usd": round(provider_error_cost, 10),
                "superseded_cost_usd": round(superseded_cost, 10),
                "without_row_cost_usd": round(paid_invalid_cost - superseded_cost
                                              - provider_error_cost, 10),
                "paid_invalid_call_rate": round((len(paid) - len(m_valid)) / len(m_valid), 6),
                "paid_invalid_cost_ratio": round(paid_invalid_cost / valid_cost, 6),
            },
        }

    out_models[MISTRAL] = mistral_estimate(out_models)
    measured = [m for m in out_models.values() if not m["estimate"]]
    return {
        "_notes": ("pgg_cost.py calibration (task B4). Generated by pgg_cost_calibrate.py from "
                   "the run below; aggregates only, no account id, no text. kinds: per "
                   "pgg_cost call kind, over the valid rows; completion_tokens include "
                   "reasoning_tokens, visible_tokens = completion - reasoning. paid: calls with "
                   "usage.cost in the raw log; paid_invalid = paid - valid (provider errors, "
                   "rows of superseded units, paid calls without a row); paid_invalid_cost_ratio "
                   "= paid_invalid_cost / valid_cost. n_no_usage: transport errors without "
                   "usage, billed as 0 in the run summary. Entries with \"estimate\": true are "
                   "not measured."),
        "schema": 1,
        "p95_method": "linear interpolation between order statistics (numpy default)",
        "source": {
            "run": run,
            "results_file": results_path.name,
            "results_sha256": sha256(results_path),
            "results_lines": len(rows),
            "summary_file": summary_path.name,
            "summary_sha256": sha256(summary_path),
            "raw_log_sha256": sha256(raw_path),
            "raw_log_calls": len(calls),
            "row_validity_rule": summary["row_validity_rule"],
            "n_valid_rows": len(valid),
            "n_superseded_rows": len(dropped),
            "planned_calls_per_model": planned,
        },
        "actual_total_cost_usd": round(summary["total_cost_usd"], 10),
        "recomputed_total_cost_usd": round(sum(m["paid"]["total_cost_usd"] for m in measured), 10),
        "models": out_models,
    }


def pooled_paid_invalid(measured: dict) -> tuple[float, float, float]:
    """(paid-invalid USD, valid USD, paid-invalid call rate) pooled over measured models."""
    return (sum(m["paid"]["paid_invalid_cost_usd"] for m in measured.values()),
            sum(m["paid"]["valid_cost_usd"] for m in measured.values()),
            sum(m["paid"]["n_paid_invalid"] for m in measured.values())
            / sum(m["paid"]["n_valid"] for m in measured.values()))


def mistral_estimate(measured: dict) -> dict:
    """Mistral entry from the measured models (no pilot data); "estimate": true."""
    pooled_invalid, pooled_valid, pooled_rate = pooled_paid_invalid(measured)
    kinds = {}
    for kind in sorted(set.intersection(*(set(m["kinds"]) for m in measured.values()))):
        per = [m["kinds"][kind] for m in measured.values()]
        visible_mean = sum(p["visible_tokens"]["mean"] for p in per) / len(per)
        kinds[kind] = {
            "prompt_tokens": {
                "mean": round(sum(p["prompt_tokens"]["mean"] for p in per) / len(per), 6),
                "p95": max(p["prompt_tokens"]["p95"] for p in per)},
            "completion_tokens": {
                "mean": round(visible_mean + MISTRAL_B2["reasoning_tokens"], 6),
                "p95": max(p["completion_tokens"]["p95"] for p in per)},
            "reasoning_tokens": {"mean": MISTRAL_B2["reasoning_tokens"], "p95": None},
            "visible_tokens": {"mean": round(visible_mean, 6),
                               "p95": max(p["visible_tokens"]["p95"] for p in per)},
        }
    names = ", ".join(m["key"] for m in measured.values())
    return {
        "key": "mistral",
        "estimate": True,
        "price_usd_per_m": {
            "input": MISTRAL_PRICE_USD_PER_M[0],
            "output": MISTRAL_PRICE_USD_PER_M[1],
            "source": ("endpoints list price, GET /api/v1/models/mistralai/mistral-large-4-0/"
                       "endpoints 2026-10-06 (task #58); billed exactly this in the plumbing "
                       "call of task #59 (discount 0.5 not applied)"),
        },
        "provider": "Mistral",
        "b2_measurement": MISTRAL_B2,
        "assumptions": [
            f"prompt_tokens mean = mean of the {names} means of the same prompts (another "
            f"tokenizer: not measured); p95 = largest p95 of the three",
            f"reasoning_tokens mean = {MISTRAL_B2['reasoning_tokens']}: task #59 found the "
            "reasoning_tokens field present and 0 at the default setting (reasoning not sent), "
            "but on a trivial prompt ('Reply with ok'), not a game prompt",
            f"completion_tokens mean = visible answer only: mean of the {names} visible tokens "
            "(completion - reasoning) of the same kind, plus 0 reasoning",
            "completion_tokens p95 = largest completion p95 of the three INCLUDING their "
            "reasoning, so the p95 upper bound also covers Mistral reasoning on game prompts",
            f"paid-invalid share = pooled ratio of the three measured models "
            f"(cost {pooled_invalid / pooled_valid:.6f}, calls {pooled_rate:.6f})",
            "price = listed endpoint price (not a cost/token ratio of pilot data)",
        ],
        "kinds": kinds,
        "paid": {
            "paid_invalid_call_rate": round(pooled_rate, 6),
            "paid_invalid_cost_ratio": round(pooled_invalid / pooled_valid, 6),
            "estimate": True,
        },
    }


def later_round_ratios(run_dir: Path, keys, round_no: int = 1, x: int = 10) -> tuple[str, dict]:
    """(run, ratios): completion tokens of a finished run's valid rows, all / a subset.

    Per model key: contribute_N all rounds / round round_no, isolated all
    values / the value x; mean and p95 each (task #71: M1 measured Mistral at
    round 1 and X = 10 only).
    """
    _, summary, _, _, valid, _ = run_rows(run_dir)
    out = {}
    for key in keys:
        rows = [r for r in valid if r["model_key"] == key]
        if not rows:
            raise ValueError(f"no valid rows of model {key!r} in {run_dir}")
        entry = {}
        for kind, subset in (("contribute_N", lambda r: r["round"] == round_no),
                             ("isolated", lambda r: r["others_mean"] == x)):
            every = [r["usage"]["completion_tokens"] for r in rows if call_kind(r) == kind]
            sub = [r["usage"]["completion_tokens"] for r in rows
                   if call_kind(r) == kind and subset(r)]
            a, b = stats(every), stats(sub)
            entry[kind] = {"n_all": len(every), "n_subset": len(sub),
                           "mean": round(a["mean"] / b["mean"], 6),
                           "p95": round(a["p95"] / b["p95"], 6)}
        out[key] = entry
    return summary["run"], out


# Pilot v2 models also in the mini-pilot (both reasoning models): the ratio
# source for Mistral's later rounds (task #71).
RATIO_MODEL_KEYS = ("deepseek", "gpt")
M1_KINDS = {"contribute": "contribute_N", "isolated": "isolated"}
LATER_ROUNDS = {
    "pilot_v2_max": ("completion tokens of rounds 2-10 and of the other isolated values "
                     "(tahmin): M1 value x the LARGEST all / measured-subset ratio of the "
                     "pilot v2 reasoning models in the mini-pilot ({keys}): contribute_N all "
                     "rounds / round 1, isolated all values / X = 10; mean and p95 each"),
    "round1": ("completion tokens of rounds 2-10 and of the other isolated values (tahmin): "
               "the M1 value (round 1, X = 10) unchanged, ratio 1"),
}


def calibrate_mistral_m1(m1_dir: Path, ratio_run_dir: Path, base_path: Path = DEFAULT_OUT,
                         later_rounds: str = "pilot_v2_max") -> dict:
    """Mistral entry of the M1 plumbing measurement (task #71), an overlay of base_path.

    Reads m1_dir (results.jsonl, summary.json; raw_calls.jsonl is neither read
    nor copied) and the valid rows of ratio_run_dir (pilot v2), both read
    only. M1 measured round 1 of the group arm and X = 10 of the isolated
    arm in the abstract_v3 frame. Prompt tokens: Mistral's tokens per prompt
    character of M1 times the mean characters of the abstract_v2 prompt
    over all rounds (the unit pgg_game's prompt scale expects), cards of M1.
    Completion tokens of the other rounds / values: LATER_ROUNDS[later_rounds].
    The paid-but-invalid share stays the pooled pilot v2 share (tahmin).
    """
    import pgg_frames
    import pgg_game

    if later_rounds not in LATER_ROUNDS:
        raise ValueError(f"later_rounds must be one of {sorted(LATER_ROUNDS)}")
    m1_dir, base_path = Path(m1_dir), Path(base_path)
    base = json.loads(base_path.read_text(encoding="utf-8"))
    summary_path, results_path = m1_dir / "summary.json", m1_dir / "results.jsonl"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    run = summary["run"]
    all_rows = read_jsonl(results_path)
    rows = [r for r in all_rows if r["model"] == MISTRAL]
    if not rows or not all(r["ok"] for r in rows):
        raise ValueError(f"{run}: Mistral rows missing or not all ok")
    billed = sum(_cost(r["usage"]) for r in rows)
    if abs(billed - summary["cost_by_model_usd"]["mistral"]) > 1e-6:
        raise ValueError(f"{run}: Mistral usage.cost {billed} != summary "
                         f"{summary['cost_by_model_usd']['mistral']}")

    # the prompts as sent: re-rendered with this code, must equal the logged ones.
    # The frame file's sha256 may differ from M1's (task #73: abstract_v3
    # changed after M1 only in the q2 text of the rule comprehension, which M1
    # did not measure); every M1 prompt must still re-render byte for byte.
    frame_file = pgg_frames.frame_path(summary["frame"])
    frame = pgg_frames.load_frame(frame_file)
    rationale = json.loads((ROOT / "configs" / "minipilot.json").read_text(
        encoding="utf-8"))["rationale"]
    params = pgg_game.GameParams()
    cards = pgg_game.load_cards(ROOT / summary["cards"], summary["cities"])
    by_id = {c.card_id: c for c in cards}
    schema = pgg_game.contribution_schema(params, rationale, prompt_frame=frame)
    chars = {}
    for i, r in enumerate(rows):
        kind, card = M1_KINDS[r["step"]], by_id[r["card_id"]]
        if kind == "contribute_N":
            expected = pgg_game.contribution_messages(params, "N", card, [], r["agent_id"] - 1,
                                                      r["round"], prompt_frame=frame)
        else:
            expected = pgg_game.isolated_messages(params, card, r["others_mean"],
                                                  summary["isolated_frame"], r["round"],
                                                  prompt_frame=frame)
        if expected != r["prompt_messages"]:
            raise ValueError(f"{run}: the prompt of Mistral row {i} differs from this code's")
        chars[i] = pgg_game._prompt_chars(expected, schema)

    ratio_run, ratios = later_round_ratios(ratio_run_dir, RATIO_MODEL_KEYS,
                                           x=summary["isolated_x"])
    measured_base = {s: m for s, m in base["models"].items() if not m["estimate"]}
    ratio_slugs = [s for s, m in measured_base.items() if m["key"] in RATIO_MODEL_KEYS]
    measured, kinds = {}, {}
    for step, kind in M1_KINDS.items():
        idx = [i for i, r in enumerate(rows) if r["step"] == step]
        k_rows = [rows[i] for i in idx]
        toks = [usage_tokens(r["usage"]) for r in k_rows]
        n_chars = sum(chars[i] for i in idx)
        per_char = sum(t["prompt_tokens"] for t in toks) / n_chars
        elapsed = [r["elapsed_s"] for r in k_rows]
        measured[kind] = {
            "n": len(k_rows),
            "subset": ("group arm, round 1" if kind == "contribute_N"
                       else f"isolated, X = {summary['isolated_x']}, round "
                            f"{summary['isolated_round_no']} ({summary['isolated_frame']})"),
            **{f: stats(t[f] for t in toks) for f in TOKEN_FIELDS},
            "cost_usd": stats((_cost(r["usage"]) for r in k_rows), digits=12),
            "cost_usd_sum": round(sum(_cost(r["usage"]) for r in k_rows), 10),
            "prompt_chars_mean": round(n_chars / len(idx), 6),
            "prompt_tokens_per_char": round(per_char, 6),
            "elapsed_s": {"mean": round(sum(elapsed) / len(elapsed), 3),
                          "median": round(quantile(elapsed, 0.5), 3),
                          "max": round(max(elapsed), 3)},
        }
        ref_chars = pgg_game.mean_prompt_chars(
            pgg_game.default_frame(), kind, params, cards,
            isolated_frame=pgg_game.CALIBRATION_ISOLATED_FRAME,
            isolated_round_no=summary["isolated_round_no"], rationale=rationale)
        prompt_mean = per_char * ref_chars
        prompt_p95_ratio = max(measured_base[s]["kinds"][kind]["prompt_tokens"]["p95"]
                               / measured_base[s]["kinds"][kind]["prompt_tokens"]["mean"]
                               for s in ratio_slugs)
        used = ({"mean": max(ratios[k][kind]["mean"] for k in RATIO_MODEL_KEYS),
                 "p95": max(ratios[k][kind]["p95"] for k in RATIO_MODEL_KEYS)}
                if later_rounds == "pilot_v2_max" else {"mean": 1.0, "p95": 1.0})
        compl = measured[kind]["completion_tokens"]
        kinds[kind] = {
            "n": len(k_rows),
            "prompt_tokens": {"mean": round(prompt_mean, 6),
                              "p95": round(prompt_mean * prompt_p95_ratio, 6)},
            "completion_tokens": {"mean": round(compl["mean"] * used["mean"], 6),
                                  "p95": round(compl["p95"] * used["p95"], 6)},
            "abstract_v2_prompt_chars_mean": round(ref_chars, 6),
            "prompt_p95_over_mean": round(prompt_p95_ratio, 6),
            "completion_ratio_used": used,
        }

    prompt_cost = sum(r["usage"]["cost_details"]["upstream_inference_prompt_cost"] for r in rows)
    compl_cost = sum(r["usage"]["cost_details"]["upstream_inference_completions_cost"]
                     for r in rows)
    n_prompt = sum(r["usage"]["prompt_tokens"] for r in rows)
    n_compl = sum(r["usage"]["completion_tokens"] for r in rows)
    pooled_invalid, pooled_valid, pooled_rate = pooled_paid_invalid(measured_base)
    elapsed_max = max(rows, key=lambda r: r["elapsed_s"])
    n_c, n_i = measured["contribute_N"]["n"], measured["isolated"]["n"]
    rule = LATER_ROUNDS[later_rounds].format(keys=", ".join(RATIO_MODEL_KEYS))
    note = (f"kalibrasyon M1 tesisat ölçümü {run} ({summary['frame']}: {n_c} 1. tur katkı + "
            f"{n_i} izole X={summary['isolated_x']} çağrısı); "
            + ("sonraki turlar ve diğer X değerleri pilot v2'deki en büyük oranla"
               if later_rounds == "pilot_v2_max" else
               "sonraki turlar ve diğer X değerleri 1. tur / X=10 değeriyle")
            + " (tahmin); ödenmiş-geçersiz payı pilot v2 havuzu (tahmin)")
    entry = {
        "key": "mistral",
        "estimate": False,
        "provider": ", ".join(sorted({r["provider"] for r in rows})),
        "model_version": ", ".join(sorted({r["model_version"] for r in rows})),
        "price_usd_per_m": {
            "input": round(prompt_cost / n_prompt * 1e6, 6),
            "output": round(compl_cost / n_compl * 1e6, 6),
            "source": (f"calibration: billed usage.cost_details (prompt / completions) / tokens "
                       f"of the {len(rows)} Mistral calls of {run} (M1)"),
        },
        "later_rounds": {"rule": later_rounds, "text": rule, "ratio_run": ratio_run,
                         "ratios": ratios},
        "assumptions": [
            f"prompt tokens (tahmin): Mistral tokens per prompt character measured in M1 "
            f"(contribute_N {measured['contribute_N']['prompt_tokens_per_char']:.4f}, isolated "
            f"{measured['isolated']['prompt_tokens_per_char']:.4f}; round 1 and X = 10, no "
            "history) x mean characters of the abstract_v2 prompt over rounds 1-10 (synthetic "
            "history, pgg_game.mean_prompt_chars, M1's cards); pgg_game scales it to the frame",
            "prompt p95 (tahmin): mean x the largest pilot v2 p95 / mean of the same kind "
            f"({', '.join(RATIO_MODEL_KEYS)})",
            rule,
            "comprehension (tahmin): as for every model, contribute_N tokens, prompt scaled to "
            "its own length (pgg_cost.EXTRAPOLATED_KINDS)",
            "cost from completion_tokens (billed), not reasoning_tokens: in "
            f"{sum(1 for r in rows if r['reasoning_tokens'] > r['completion_tokens'])} of "
            f"{len(rows)} M1 responses reasoning_tokens > completion_tokens",
            f"paid-invalid share (tahmin) = pooled pilot v2 ratio of the measured models "
            f"(cost {pooled_invalid / pooled_valid:.6f}, calls {pooled_rate:.6f}); M1 had "
            f"{sum(r['n_invalid'] for r in rows)} invalid of {len(rows)}, too few to estimate it",
            "M1 is a plumbing measurement in one frame (abstract_v3), not analysis data",
        ],
        "report_note": note,
        "measured": {
            **measured,
            "n_reasoning_gt_completion": sum(1 for r in rows
                                             if r["reasoning_tokens"] > r["completion_tokens"]),
            "n_invalid": sum(r["n_invalid"] for r in rows),
            "finish_reason": dict(Counter(r["finish_reason"] for r in rows)),
            "cost_usd_sum": round(billed, 10),
            "elapsed_s_max": round(elapsed_max["elapsed_s"], 3),
            "elapsed_s_max_kind": M1_KINDS[elapsed_max["step"]],
        },
        "kinds": kinds,
        "paid": {
            "paid_invalid_call_rate": round(pooled_rate, 6),
            "paid_invalid_cost_ratio": round(pooled_invalid / pooled_valid, 6),
            "estimate": True,
            "source": f"pooled over {', '.join(m['key'] for m in measured_base.values())} of "
                      f"{base['source']['run']}",
            "m1_attempts_sent": summary["n_attempts_sent"]["mistral"],
            "m1_responses_billed": summary["n_responses_billed"]["mistral"],
        },
    }
    return {
        "_notes": ("pgg_cost.py calibration overlay (task #71, EMIR 2 M2a). Generated by "
                   "pgg_cost_calibrate.py --m1-run-dir from the M1 plumbing measurement "
                   "(tesisat ölçümü, not analysis data); aggregates only, no account id, no "
                   "text, raw_calls.jsonl not read. pgg_cost loads the base file and replaces "
                   "its entries of the models below with these. kinds: what pgg_cost uses "
                   "(all rounds, prompt in abstract_v2 prompt units); measured: the M1 calls "
                   "themselves (round 1 / X = 10, abstract_v3). Every number of a kind is "
                   "(tahmin) for a future run; see assumptions."),
        "schema": 1,
        "overlay_of": base_path.name,
        "p95_method": "linear interpolation between order statistics (numpy default)",
        "source": {
            "run": run,
            "results_file": results_path.name,
            "results_sha256": sha256(results_path),
            "results_lines": len(all_rows),
            "summary_file": summary_path.name,
            "summary_sha256": sha256(summary_path),
            "n_mistral_rows": len(rows),
            "frame": summary["frame"],
            "frame_sha256": summary["frame_sha256"],
            "report": "workspace/gorev_tesisat_olcum.md (task #70)",
            "base_sha256": sha256(base_path),
        },
        "models": {MISTRAL: entry},
    }


# Call types of the mini-pilot calibration (task #93): name -> (pgg_cost kind, row test)
MP_TYPES = {
    "group_round_1": ("contribute_N", lambda r: r["step"] == "contribute" and r["round"] == 1),
    "group_rounds_2_10": ("contribute_N",
                          lambda r: r["step"] == "contribute" and r["round"] != 1),
    "isolated": ("isolated", lambda r: r["step"] == "isolated"),
    "comprehension": ("comprehension", lambda r: r["step"] == "comprehension"),
}
MP_FRAME = "abstract_v3"


def _mp_stats(rows: list[dict]) -> dict:
    toks = [usage_tokens(r["usage"]) for r in rows]
    return {"n": len(rows), **{f: stats(t[f] for t in toks) for f in TOKEN_FIELDS},
            "cost_usd": stats((_cost(r["usage"]) for r in rows), digits=12),
            "cost_usd_sum": round(sum(_cost(r["usage"]) for r in rows), 10)}


def _mp_measured(rows: list[dict]) -> dict:
    return {name: _mp_stats([r for r in rows if test(r)])
            for name, (_, test) in MP_TYPES.items() if any(test(r) for r in rows)}


def raw_paid_by_model(raw_path: Path) -> tuple[dict, int]:
    """({model slug: summed usage.cost}, number of call records) of a raw log.

    Reads only the "model" and "usage" fields of call records (no event); the
    rest of a record (messages, response, ids) is not kept.
    """
    paid, n = Counter(), 0
    with open(raw_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if "event" in rec or "model" not in rec:
                continue
            model, cost = rec["model"], _cost(rec.get("usage"))
            del rec
            n += 1
            if cost is not None:
                paid[model] += cost
    return dict(paid), n


def calibrate_minipilot(run_dir: Path, base_path: Path = DEFAULT_OUT,
                        config_path: Path = MINIPILOT_CONFIG) -> dict:
    """Overlay of base_path from the mini-pilot's token distribution (task #93).

    Per model, from the valid abstract_v3 rows: mean and p95 of prompt,
    completion, reasoning and visible tokens and of usage.cost for group
    round 1, group rounds 2-10, isolated and rule comprehension ("measured",
    abstract_v3 prompt units). The pgg_cost kinds:
      contribute_N  = round 1 x 1/10 + rounds 2-10 x 9/10 (rounds = 10), mean
                      and p95 each;
      isolated, comprehension as measured;
    prompt tokens divided by abstract_v3's prompt scale to abstract_v2
    (pgg_game.prompt_scales, the mini-pilot's cards), the unit pgg_game
    scales to a run's frame. Price: billed cost_details / tokens of the same
    rows. Paid-but-invalid share: (paid usage.cost of the raw log - usage.cost
    of every valid row, both frames) / the latter, per model.
    """
    import pgg_frames
    import pgg_game

    run_dir, base_path = Path(run_dir), Path(base_path)
    summary_path = next(iter(sorted(run_dir.glob("*_summary.json"))))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    run = summary["run"]
    results_path, raw_path = run_dir / f"{run}.jsonl", run_dir / "raw_calls.jsonl"
    if summary["superseded_rows"] or summary["truncated_lines"]:
        raise ValueError(f"{run}: superseded or cut-off rows; every row is taken as valid here")
    rows = read_jsonl(results_path)
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    models = summary["config"]["models"]                       # key -> slug
    paid_raw, n_raw = raw_paid_by_model(raw_path)
    paid_summary = {slug: summary["per_model"][slug]["cost_usd"] for slug in models.values()}
    for slug, cost in paid_summary.items():
        if abs(paid_raw.get(slug, 0.0) - cost) > 1e-6:
            raise ValueError(f"{run}: paid cost of {slug} in the raw log {paid_raw.get(slug)} != "
                             f"summary {cost}")

    params = pgg_game.GameParams()
    if params.rounds != 10 or summary["config"]["params"]["rounds"] != 10:
        raise ValueError("the round weights 1/10 and 9/10 assume 10 rounds")
    frame_file = ROOT / cfg["frame_files"][MP_FRAME]["path"]
    frame = pgg_frames.load_frame(frame_file)
    sha = {r["frame_sha256"] for r in rows if r["frame"] == MP_FRAME}
    if sha != {frame.sha256}:
        raise ValueError(f"{run}: abstract_v3 rows have frame sha256 {sha}, the file "
                         f"{frame.sha256}")
    cards = pgg_game.load_cards(ROOT / cfg["cards"], cfg["cities"])
    scale = pgg_game.prompt_scales(frame, params, cards, isolated_frame=cfg["isolated_frame"],
                                   isolated_round_no=cfg["isolated_round_no"],
                                   rationale=cfg["rationale"])
    w1 = 1 / params.rounds

    out_models = {}
    for key, slug in models.items():
        m_rows = [r for r in rows if r["model"] == slug]
        a_rows = [r for r in m_rows if r["frame"] == MP_FRAME]
        measured = _mp_measured(a_rows)
        r1, rl = measured["group_round_1"], measured["group_rounds_2_10"]
        kinds = {"contribute_N": {
            "n": r1["n"] + rl["n"],
            "rule": "round 1 x 1/10 + rounds 2-10 x 9/10 (mean and p95 each)",
            **{f: {s: round(w1 * r1[f][s] + (1 - w1) * rl[f][s], 6) for s in ("mean", "p95")}
               for f in ("prompt_tokens", "completion_tokens")}}}
        for name in ("isolated", "comprehension"):
            kinds[name] = {"n": measured[name]["n"],
                           **{f: dict(measured[name][f])
                              for f in ("prompt_tokens", "completion_tokens")}}
        for kind, k in kinds.items():
            k["prompt_tokens_abstract_v3"] = dict(k["prompt_tokens"])
            k["prompt_scale_abstract_v3"] = round(scale[kind], 6)
            k["prompt_tokens"] = {s: round(v / scale[kind], 6)
                                  for s, v in k["prompt_tokens"].items()}

        prompt_cost = sum(r["usage"]["cost_details"]["upstream_inference_prompt_cost"]
                          for r in a_rows)
        compl_cost = sum(r["usage"]["cost_details"]["upstream_inference_completions_cost"]
                         for r in a_rows)
        n_prompt = sum(r["usage"]["prompt_tokens"] for r in a_rows)
        n_compl = sum(r["usage"]["completion_tokens"] for r in a_rows)
        cached = sum((r["usage"].get("prompt_tokens_details") or {}).get("cached_tokens") or 0
                     for r in a_rows)
        valid_cost = sum(_cost(r["usage"]) for r in m_rows)
        pm = summary["per_model"][slug]
        paid_total = paid_summary[slug]
        entry = {
            "key": key,
            "estimate": False,
            "provider": ", ".join(sorted(pm["providers"])),
            "model_version": ", ".join(sorted(pm["model_versions"])),
            "price_usd_per_m": {
                "input": round(prompt_cost / n_prompt * 1e6, 6),
                "output": round(compl_cost / n_compl * 1e6, 6),
                "source": (f"calibration: billed usage.cost_details (prompt / completions) / "
                           f"tokens of the {len(a_rows)} valid {MP_FRAME} rows of {run}"),
            },
            "cached_prompt_token_share": round(cached / n_prompt, 6),
            "kinds": kinds,
            "measured": measured,
            "measured_story": _mp_measured([r for r in m_rows if r["frame"] != MP_FRAME]) or None,
            "paid": {
                "n_responses": pm["n_responses"],
                "n_valid_rows": len(m_rows),
                "n_invalid": pm["n_invalid"],
                "n_parse_fail": pm["n_parse_fail"],
                "n_provider_error": pm["n_provider_error"],
                "n_discarded": pm["n_discarded"],
                "total_cost_usd": round(paid_total, 10),
                "valid_cost_usd": round(valid_cost, 10),
                "paid_invalid_cost_usd": round(paid_total - valid_cost, 10),
                "paid_invalid_call_rate": round((pm["n_responses"] - len(m_rows)) / len(m_rows),
                                                6),
                "paid_invalid_cost_ratio": round((paid_total - valid_cost) / valid_cost, 6),
                "source": (f"{run}: paid = usage.cost summed over the raw log's call records "
                           f"(equal to the summary's per_model cost_usd), valid = usage.cost "
                           f"of the model's valid rows of every frame"),
            },
            "report_note": (f"kalibrasyon mini-pilot {run} ({MP_FRAME}, {len(a_rows)} geçerli "
                            f"satır: tur 1 {r1['n']}, tur 2-10 {rl['n']}, izole "
                            f"{measured['isolated']['n']}, kural anlama "
                            f"{measured['comprehension']['n']}); ödenmiş-geçersiz payı "
                            f"{(paid_total - valid_cost) / valid_cost:.4f} (tahmin)"),
            "assumptions": [
                "every number is (tahmin) for a future run: the mini-pilot's distribution may "
                "not hold in another design, frame or card set",
                f"from the {MP_FRAME} rows only (the main frame abstract_v4 adds one system "
                "line to it); story rows are in measured_story, not in kinds",
                "contribute_N = round 1 x 1/10 + rounds 2-10 x 9/10 (rounds = 10), mean and p95 "
                "each; the p95 of a kind is a per-call p95, so calls x p95 is an upper bound, "
                "not the p95 of a total",
                "prompt tokens in abstract_v2 units: the measured mean / p95 divided by "
                "abstract_v3's prompt scale (pgg_game.prompt_scales, mini-pilot cards); a "
                "run's frame scales them back by its character ratio (tahmin)",
                "comprehension measured (group and isolated rule-comprehension calls pooled; the "
                "same prompt), no longer extrapolated from contribute_N",
                "paid-but-invalid share of the mini-pilot (re-requests, provider errors, "
                "answers discarded at the resumes of its 23 segments) per model",
            ],
        }
        if any(v["visible_tokens"]["mean"] < 0 for v in measured.values()):
            entry["assumptions"].append(
                "visible_tokens = completion - reasoning is negative where the provider "
                "reports reasoning_tokens above completion_tokens (EMIR 3 3a); the cost uses "
                "completion_tokens, which are billed")
        if key == "mistral":
            entry["assumptions"].append(
                f"Mistral: incomplete data, {len(m_rows)} valid rows of the planned 600 (the run "
                f"stopped Mistral at its invalid-rate cap: {pm['n_invalid']} invalid > "
                f"{summary['model_stops']['mistral']['limit']}); rounds 2-10 from {rl['n']} rows "
                "of 8 groups (the 8th cut off), only abstract_v3, isolated "
                f"{measured['isolated']['n']} rows; its paid-invalid share includes the "
                "invalid answers that stopped it")
            entry["report_note"] += (f"; Mistral eksik veri: {len(m_rows)}/600 satır "
                                     "(geçersiz oranı tavanında durdu)")
        out_models[slug] = entry

    return {
        "_notes": ("pgg_cost.py calibration overlay (task #93, EMIR 5). Generated by "
                   "pgg_cost_calibrate.py --minipilot-run-dir from the mini-pilot run below; "
                   "aggregates only, no account id, no text; of raw_calls.jsonl only the model "
                   "and usage fields of call records are read (paid cost per model). Not a "
                   "default overlay of pgg_cost: a config names it with \"cost_calibration\" "
                   "(configs/main.json). kinds: what pgg_cost uses (prompt in abstract_v2 "
                   "units); measured: per call type, abstract_v3 prompt units, as billed; "
                   "measured_story: the story arm (information). See assumptions."),
        "schema": 1,
        "overlay_of": base_path.name,
        "p95_method": "linear interpolation between order statistics (numpy default)",
        "source": {
            "run": run,
            "results_file": results_path.name,
            "results_sha256": sha256(results_path),
            "results_lines": len(rows),
            "summary_file": summary_path.name,
            "summary_sha256": sha256(summary_path),
            "raw_log_call_records": n_raw,
            "frame": MP_FRAME,
            "frame_sha256": frame.sha256,
            "config": Path(config_path).name,
            "cards": cfg["cards"],
            "base_sha256": sha256(base_path),
        },
        "actual_total_cost_usd": round(summary["total_cost_usd"], 10),
        "recomputed_total_cost_usd": round(sum(paid_summary.values()), 10),
        "models": out_models,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--run-dir", type=Path,
                     help="run directory (read only): <run>.jsonl, <run>_summary.json, "
                          "raw_calls.jsonl")
    src.add_argument("--minipilot-run-dir", type=Path,
                     help="mini-pilot run directory (read only): writes the overlay "
                          "configs/cost_calibration_minipilot.json (task #93)")
    src.add_argument("--m1-run-dir", type=Path,
                     help="M1 plumbing measurement (read only): results.jsonl, summary.json; "
                          "writes the Mistral overlay (task #71)")
    ap.add_argument("--ratio-run-dir", type=Path,
                    help="with --m1-run-dir: the pilot v2 run directory (read only) of the "
                         "later-round ratios")
    ap.add_argument("--later-rounds", choices=sorted(LATER_ROUNDS), default="pilot_v2_max")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    if args.minipilot_run_dir is not None:
        read_only = [args.minipilot_run_dir.resolve()]
        out = (args.out or MINIPILOT_OUT).resolve()
    elif args.m1_run_dir is not None:
        if args.ratio_run_dir is None:
            ap.error("--m1-run-dir needs --ratio-run-dir")
        read_only = [args.m1_run_dir.resolve(), args.ratio_run_dir.resolve()]
        out = (args.out or MINIPILOT_M1_OUT).resolve()
    else:
        read_only = [args.run_dir.resolve()]
        out = (args.out or DEFAULT_OUT).resolve()
    if any(out.parent == d or d in out.parents for d in read_only):
        print("HATA: çıktı koşu dizininin içine yazılmaz (salt okunur)", file=sys.stderr)
        return 1
    if args.minipilot_run_dir is not None:
        cal = calibrate_minipilot(args.minipilot_run_dir)
    elif args.m1_run_dir is not None:
        cal = calibrate_mistral_m1(args.m1_run_dir, args.ratio_run_dir,
                                   later_rounds=args.later_rounds)
    else:
        cal = calibrate(args.run_dir)
    out.write_text(json.dumps(cal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"yazıldı: {out}")
    if args.minipilot_run_dir is not None:
        print(f"mini-pilot {cal['source']['run']}: gerçek toplam "
              f"{cal['actual_total_cost_usd']:.6f} USD, ham logdan "
              f"{cal['recomputed_total_cost_usd']:.6f} USD")
        for slug, m in cal["models"].items():
            for name, k in m["measured"].items():
                print(f"  {m['key']:<9} {name:<18} n={k['n']:>4} istem ort "
                      f"{k['prompt_tokens']['mean']:.1f} / p95 {k['prompt_tokens']['p95']:.1f}, "
                      f"completion ort {k['completion_tokens']['mean']:.1f} / p95 "
                      f"{k['completion_tokens']['p95']:.1f}")
    elif args.m1_run_dir is not None:
        m = cal["models"][MISTRAL]
        print(f"Mistral M1 ({cal['source']['run']}, {cal['source']['n_mistral_rows']} çağrı), "
              f"sonraki turlar: {args.later_rounds}")
        for kind, k in m["kinds"].items():
            print(f"  {kind}: istem ort {k['prompt_tokens']['mean']:.1f} / p95 "
                  f"{k['prompt_tokens']['p95']:.1f}, completion ort "
                  f"{k['completion_tokens']['mean']:.1f} / p95 {k['completion_tokens']['p95']:.1f}")
    else:
        print(f"gerçek toplam {cal['actual_total_cost_usd']:.6f} USD, "
              f"yeniden toplanan {cal['recomputed_total_cost_usd']:.6f} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
