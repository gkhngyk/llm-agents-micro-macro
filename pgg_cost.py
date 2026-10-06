"""
Call counts and cost estimate for the public goods engine (--dry-run).

Everything here is an ESTIMATE ("(tahmin)") taken from the workspace file
maliyet_analizi.md (2026-10-04, G27 update); nothing is measured on the game
prompts. Deliberately does not import llm_client: importing it needs the API
key and reads ../.env, and a dry run must touch neither.

Call kinds:
  contribute_N  contribution step, no-punishment condition
  contribute_P  contribution step, punishment condition
  punish_P      punishment step (punishment condition only)
  isolated      one point of the isolated conditional schedule
"""

from __future__ import annotations

CALL_KINDS = ("contribute_N", "contribute_P", "punish_P", "isolated")

# Generating models of the mini-pilot, the default of the dry run. Must equal
# llm_client.MODELS, and PILOT_V2_MODELS / KNOWN_MODELS llm_client's
# MODELS_PILOT_V2 / MODELS_KNOWN (a test checks it); kept here so the dry run
# does not import llm_client.
PILOT_MODELS = {
    "deepseek": "deepseek/deepseek-v4.1-flash",
    "mistral":  "mistralai/mistral-large-4-0",
    "gpt":      "openai/gpt-6-luna",
}
PILOT_V2_MODELS = {
    "deepseek": "deepseek/deepseek-v4.1-flash",
    "gpt":      "openai/gpt-6-luna",
    "gemini":   "google/gemini-2.5-flash-lite",
}
KNOWN_MODELS = {**PILOT_V2_MODELS, **PILOT_MODELS}

# USD per 1M tokens: (input, output). Reasoning tokens are billed at the
# output price (maliyet_analizi.md §1 "Reasoning" column, line 24-28).
# Source lines of maliyet_analizi.md §1 table:
#   deepseek: line 26 (0,14 / 0,42; billed price of #24, provider not pinned)
#   gpt-6-luna: line 27 (0,10 / 0,50; back-calculated)
#   gemini-2.5-flash-lite: line 28 (0,10 / 0,40; OpenRouter /models list)
# The pinned providers of pilot v2 (configs/pilot.json) have the same prices in
# GET /api/v1/models/{id}/endpoints on 2026-10-05: deepinfra/fp8 0,14 / 0,42,
# openai 0,10 / 0,50, google-vertex 0,10 / 0,40.
# mistral-large-4-0: listed price of its only endpoint (tag "mistral"), GET
# https://openrouter.ai/api/v1/models/mistralai/mistral-large-4-0/endpoints on
# 2026-10-06: prompt 0,00000068, completion 0,00000209 USD per token. The
# endpoint also says "discount": 0.5; what it applies to is not verified, so the
# undiscounted listed price is used.
PRICES_USD_PER_M = {
    "deepseek/deepseek-v4.1-flash": (0.14, 0.42),
    "openai/gpt-6-luna":            (0.10, 0.50),
    "google/gemini-2.5-flash-lite": (0.10, 0.40),
    "mistralai/mistral-large-4-0":  (0.68, 2.09),
}

# Input tokens per call (maliyet_analizi.md §2 table, "Toplam girdi" row,
# line 59). The history is averaged over 10 rounds there.
INPUT_TOKENS = {
    "contribute_N": 1120,
    "contribute_P": 1390,
    "punish_P": 1590,
    "isolated": 630,
}

# Visible output tokens per call (maliyet_analizi.md §2 "Çıktı", lines 61-62).
VISIBLE_OUTPUT_TOKENS = {
    "contribute_N": 60,
    "contribute_P": 60,
    "punish_P": 80,
    "isolated": 40,
}

# Reasoning tokens per call (maliyet_analizi.md §2 "Reasoning varsayımı",
# lines 63-66): deepseek 400 and gpt 200 are unsourced assumptions; gemini 0 is
# one measurement on a tiny prompt. All "(tahmin)". None = not measured yet
# (mistral-large-4-0: the plumbing call of task B2 measures it, B4 calibrates);
# such a model gets call counts but no cost estimate.
REASONING_TOKENS = {
    "deepseek/deepseek-v4.1-flash": 400,
    "openai/gpt-6-luna": 200,
    "google/gemini-2.5-flash-lite": 0,
    "mistralai/mistral-large-4-0": None,
}

SOURCE_NOTE = (
    "Kaynak: workspace/maliyet_analizi.md (§1 fiyatlar, §2 token tahminleri). "
    "Tüm sayılar (tahmin): istem uzunlukları ve DeepSeek/GPT reasoning'i varsayım, "
    "kesin bütçe değil."
)


def call_counts(
    *,
    n_cells: int,
    conditions=("N",),
    groups_per_cell: int = 2,
    isolated_reps: int = 2,
    n_points: int = 5,
    group_size: int = 4,
    rounds: int = 10,
    arms=("group", "isolated"),
) -> dict[str, int]:
    """Calls per model, by kind, for a homogeneous-group design.

    n_cells = number of (card, style) cells. Each cell plays groups_per_cell
    groups per condition; the isolated arm asks n_points values per cell and
    repetition (one call per value) and exists for the N condition only.
    """
    counts = dict.fromkeys(CALL_KINDS, 0)
    if "group" in arms:
        per_condition = n_cells * groups_per_cell * group_size * rounds
        for condition in conditions:
            counts[f"contribute_{condition}"] = per_condition
            if condition == "P":
                counts["punish_P"] = per_condition
    if "isolated" in arms:
        counts["isolated"] = n_cells * isolated_reps * n_points
    return counts


def cost_per_call(model: str, kind: str) -> float:
    """Estimated USD for one call of this kind to this model (tahmin)."""
    if model not in PRICES_USD_PER_M:
        raise KeyError(f"no price for model {model!r}; add it to PRICES_USD_PER_M")
    if REASONING_TOKENS.get(model) is None:
        raise KeyError(f"no reasoning-token estimate for model {model!r} (not measured yet)")
    price_in, price_out = PRICES_USD_PER_M[model]
    out_tokens = VISIBLE_OUTPUT_TOKENS[kind] + REASONING_TOKENS[model]
    return (INPUT_TOKENS[kind] * price_in + out_tokens * price_out) / 1e6


def estimate(models: dict[str, str], counts: dict[str, int]) -> dict:
    """Per-model and total call counts and estimated cost.

    models maps short key -> slug. Returns
    {"per_model": {key: {"slug", "calls", "calls_by_kind", "cost_usd"}},
     "total_calls", "total_cost_usd", "unpriced"}. A model without a price or
    reasoning-token estimate has cost_usd None, is listed in "unpriced" and is
    left out of total_cost_usd.
    """
    per_model = {}
    for key, slug in models.items():
        try:
            cost = sum(counts[kind] * cost_per_call(slug, kind) for kind in CALL_KINDS)
        except KeyError:
            cost = None
        per_model[key] = {
            "slug": slug,
            "calls": sum(counts.values()),
            "calls_by_kind": {k: v for k, v in counts.items() if v},
            "cost_usd": cost,
        }
    return {
        "per_model": per_model,
        "total_calls": sum(m["calls"] for m in per_model.values()),
        "total_cost_usd": sum(m["cost_usd"] for m in per_model.values()
                              if m["cost_usd"] is not None),
        "unpriced": [k for k, m in per_model.items() if m["cost_usd"] is None],
    }


def ceiling(models: dict[str, str], counts: dict[str, int], max_tokens: int) -> dict:
    """Upper bound per model if every call used all max_tokens (no re-requests).

    Same input-token estimates as estimate(); only the output side changes.
    Returns {key: cost_usd} plus "total".
    """
    out = {}
    for key, slug in models.items():
        if slug not in PRICES_USD_PER_M:
            raise KeyError(f"no price for model {slug!r}; add it to PRICES_USD_PER_M")
        price_in, price_out = PRICES_USD_PER_M[slug]
        out[key] = sum(counts[kind] * (INPUT_TOKENS[kind] * price_in + max_tokens * price_out)
                       for kind in CALL_KINDS) / 1e6
    out["total"] = sum(out.values())
    return out


def format_ceiling(models: dict[str, str], counts: dict[str, int], max_tokens: int) -> str:
    """One report line: the max_tokens ceiling (not an expected cost)."""
    c = ceiling(models, counts, max_tokens)
    per = ", ".join(f"{k} ~{v:.2f}" for k, v in c.items() if k != "total")
    return (f"Tavan (her çağrı max_tokens={max_tokens} çıktıyı doldurursa; beklenen değil): "
            f"{per}; toplam ~{c['total']:.2f} USD (tahmin)")


def format_report(est: dict, *, description: str = "") -> str:
    """Human-readable (Turkish) dry-run report; every cost is labelled (tahmin)."""
    lines = ["KURU ÇALIŞTIRMA — API çağrısı yapılmadı."]
    if description:
        lines.append(description)
    lines.append("")
    for key, m in est["per_model"].items():
        kinds = ", ".join(f"{k}={v}" for k, v in m["calls_by_kind"].items())
        cost = ("maliyet tahmini yok (reasoning token ölçülmedi)" if m["cost_usd"] is None
                else f"~{m['cost_usd']:.2f} USD (tahmin)")
        lines.append(f"{key:<9} {m['slug']:<32} {m['calls']:>6} çağrı ({kinds})  {cost}")
    unpriced = est.get("unpriced") or []
    lines.append(
        f"{'TOPLAM':<9} {'':<32} {est['total_calls']:>6} çağrı"
        f"{'':<30}~{est['total_cost_usd']:.2f} USD (tahmin"
        + (f"; {', '.join(unpriced)} HARİÇ — eksik toplam)" if unpriced else ")"))
    lines.append("")
    lines.append(SOURCE_NOTE)
    return "\n".join(lines)
