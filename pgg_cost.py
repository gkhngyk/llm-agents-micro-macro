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

# Generating models of the pilot. Must equal llm_client.MODELS (a test checks
# it); kept here so the dry run does not import llm_client.
PILOT_MODELS = {
    "deepseek": "deepseek/deepseek-v4.1-flash",
    "gpt":      "openai/gpt-6-luna",
    "gemini":   "google/gemini-2.5-flash-lite",
}

# USD per 1M tokens: (input, output). Reasoning tokens are billed at the
# output price (maliyet_analizi.md §1 "Reasoning" column, line 24-28).
# Source lines of maliyet_analizi.md §1 table:
#   deepseek: line 26 (0,14 / 0,42; billed price of #24, provider not pinned)
#   gpt-6-luna: line 27 (0,10 / 0,50; back-calculated)
#   gemini-2.5-flash-lite: line 28 (0,10 / 0,40; OpenRouter /models list)
PRICES_USD_PER_M = {
    "deepseek/deepseek-v4.1-flash": (0.14, 0.42),
    "openai/gpt-6-luna":            (0.10, 0.50),
    "google/gemini-2.5-flash-lite": (0.10, 0.40),
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
# one measurement on a tiny prompt. All "(tahmin)".
REASONING_TOKENS = {
    "deepseek/deepseek-v4.1-flash": 400,
    "openai/gpt-6-luna": 200,
    "google/gemini-2.5-flash-lite": 0,
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
    price_in, price_out = PRICES_USD_PER_M[model]
    out_tokens = VISIBLE_OUTPUT_TOKENS[kind] + REASONING_TOKENS[model]
    return (INPUT_TOKENS[kind] * price_in + out_tokens * price_out) / 1e6


def estimate(models: dict[str, str], counts: dict[str, int]) -> dict:
    """Per-model and total call counts and estimated cost.

    models maps short key -> slug. Returns
    {"per_model": {key: {"slug", "calls", "calls_by_kind", "cost_usd"}},
     "total_calls", "total_cost_usd"}.
    """
    per_model = {}
    for key, slug in models.items():
        cost = sum(counts[kind] * cost_per_call(slug, kind) for kind in CALL_KINDS)
        per_model[key] = {
            "slug": slug,
            "calls": sum(counts.values()),
            "calls_by_kind": {k: v for k, v in counts.items() if v},
            "cost_usd": cost,
        }
    return {
        "per_model": per_model,
        "total_calls": sum(m["calls"] for m in per_model.values()),
        "total_cost_usd": sum(m["cost_usd"] for m in per_model.values()),
    }


def format_report(est: dict, *, description: str = "") -> str:
    """Human-readable (Turkish) dry-run report; every cost is labelled (tahmin)."""
    lines = ["KURU ÇALIŞTIRMA — API çağrısı yapılmadı."]
    if description:
        lines.append(description)
    lines.append("")
    for key, m in est["per_model"].items():
        kinds = ", ".join(f"{k}={v}" for k, v in m["calls_by_kind"].items())
        lines.append(
            f"{key:<9} {m['slug']:<32} {m['calls']:>6} çağrı ({kinds})  "
            f"~{m['cost_usd']:.2f} USD (tahmin)")
    lines.append(
        f"{'TOPLAM':<9} {'':<32} {est['total_calls']:>6} çağrı"
        f"{'':<30}~{est['total_cost_usd']:.2f} USD (tahmin)")
    lines.append("")
    lines.append(SOURCE_NOTE)
    return "\n".join(lines)
