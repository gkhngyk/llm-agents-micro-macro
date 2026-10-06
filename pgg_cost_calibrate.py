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

Usage:
  python pgg_cost_calibrate.py --run-dir <workspace>/runs/pilot_v2_20261005
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
    if row["arm"] == "isolated":
        return "isolated"
    return f"{row['step']}_{row['condition']}"


def unit_key(row: dict) -> str:
    """Unit label of a row; built from session_id when the row has no "unit"."""
    arm, idx = row["session_id"].rsplit("-", 2)[-2:]
    key = (f"{row['model_key']}|{row['card_id']}|{row['style']}|{row['condition']}"
           f"|{arm}|{int(idx)}")
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


def calibrate(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    summary_path = next(iter(sorted(run_dir.glob("*_summary.json"))))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    run = summary["run"]
    results_path = run_dir / f"{run}.jsonl"
    raw_path = run_dir / "raw_calls.jsonl"
    models = summary["config"]["models"]                # key -> slug
    superseded = {(u["unit"], u["segment"]) for u in summary["superseded_units"]}

    rows = read_jsonl(results_path)
    valid, dropped = [], []
    for r in rows:
        (dropped if (unit_key(r), r.get("segment", 0)) in superseded else valid).append(r)
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


def mistral_estimate(measured: dict) -> dict:
    """Mistral entry from the measured models (no pilot data); "estimate": true."""
    pooled_invalid = sum(m["paid"]["paid_invalid_cost_usd"] for m in measured.values())
    pooled_valid = sum(m["paid"]["valid_cost_usd"] for m in measured.values())
    pooled_rate = (sum(m["paid"]["n_paid_invalid"] for m in measured.values())
                   / sum(m["paid"]["n_valid"] for m in measured.values()))
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--run-dir", required=True, type=Path,
                    help="run directory (read only): <run>.jsonl, <run>_summary.json, "
                         "raw_calls.jsonl")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    run_dir, out = args.run_dir.resolve(), args.out.resolve()
    if out.parent == run_dir or run_dir in out.parents:
        print("HATA: çıktı koşu dizininin içine yazılmaz (salt okunur)", file=sys.stderr)
        return 1
    cal = calibrate(run_dir)
    out.write_text(json.dumps(cal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"yazıldı: {out}")
    print(f"gerçek toplam {cal['actual_total_cost_usd']:.6f} USD, "
          f"yeniden toplanan {cal['recomputed_total_cost_usd']:.6f} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
