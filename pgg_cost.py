"""
Call counts and cost estimate for the public goods engine (--dry-run).

Token counts, prices and the paid-but-invalid share come from the calibration
file configs/cost_calibration_pilot_v2.json (task B4), made by
pgg_cost_calibrate.py from the real token distribution of pilot v2
(runs/pilot_v2_20261005): per model x call kind the mean and p95 of prompt,
completion and reasoning tokens. Every cost is still an ESTIMATE ("(tahmin)")
of a future run. Mistral has no pilot data; its entry in that file is marked
"estimate": true and lists its assumptions. Since task #71 the overlay
configs/cost_calibration_minipilot_m1.json (CALIBRATION_OVERLAYS) replaces
it with an entry from the M1 plumbing measurement (round 1 and isolated X =
10 measured, later rounds from pilot v2's round profile, labelled tahmin; its
"report_note" goes into the dry-run report). Deliberately does not import
llm_client: importing it needs the API key and reads ../.env, and a dry run
must touch neither.

Estimate per model:
  base         = sum over kinds of calls x (mean prompt x prompt scale x input
                 price + mean completion x output price)
  paid_invalid = base x paid_invalid_cost_ratio (calls paid but not a valid
                 row in pilot v2: provider errors, superseded units, ...)
  cost_usd     = base + paid_invalid
  p95_upper    = the same with the p95 token counts of every kind
Completion tokens include reasoning tokens (billed at the output price).
Prompt scale (task #61): the calibration measured the prompts of the
abstract_v2 frame; for another frame pgg_game passes, per kind, the ratio of
the frame's prompt characters to abstract_v2's (1 = not scaled). Scaled kinds
are listed and labelled (tahmin). Models whose calibration is "estimate": true
(Mistral of the pilot v2 file, without the overlay) assume no reasoning tokens
on game prompts: their expected cost is a LOWER BOUND (alt sınır); the p95
upper bound includes reasoning.

Call kinds:
  contribute_N  contribution step, no-punishment condition
  contribute_P  contribution step, punishment condition
  punish_P      punishment step (punishment condition only)
  isolated      one point of the isolated conditional schedule
  comprehension one rule-comprehension call (two questions; not in pilot v2:
                contribute_N tokens with the prompt scaled to its length)
"""

from __future__ import annotations

import json
from pathlib import Path

CALL_KINDS = ("contribute_N", "contribute_P", "punish_P", "isolated", "comprehension")

CALIBRATION_PATH = Path(__file__).resolve().parent / "configs" / "cost_calibration_pilot_v2.json"
# Later calibration files (task #71): their model entries replace the base's.
CALIBRATION_OVERLAYS = (
    Path(__file__).resolve().parent / "configs" / "cost_calibration_minipilot_m1.json",
)

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

# Listed USD per 1M tokens: (input, output), GET /api/v1/models/{id}/endpoints
# of the pinned providers (2026-10-05: deepinfra/fp8 0,14 / 0,42, openai
# 0,10 / 0,50, google-vertex 0,10 / 0,40; 2026-10-06: mistral 0,68 / 2,09, its
# "discount": 0.5 not applied, see task #59). Used by pgg_game to price a
# response without usage.cost; the estimate uses the calibration's prices
# (for the pilot v2 models the billed cost / token ratio, which includes
# prompt caching).
PRICES_USD_PER_M = {
    "deepseek/deepseek-v4.1-flash": (0.14, 0.42),
    "openai/gpt-6-luna":            (0.10, 0.50),
    "google/gemini-2.5-flash-lite": (0.10, 0.40),
    "mistralai/mistral-large-4-0":  (0.68, 2.09),
}

# Kinds pilot v2 (condition N only) did not have: (measured kind, prompt
# scale, completion scale). The scales are the old (tahmin) ratios of
# workspace/maliyet_analizi.md §2: input 1390 and 1590 vs 1120 tokens, visible
# output 60 and 80 vs 60. Not measured; such kinds are listed as extrapolated.
EXTRAPOLATED_KINDS = {
    "contribute_P": ("contribute_N", 1390 / 1120, 1.0),
    "punish_P":     ("contribute_N", 1590 / 1120, 80 / 60),
    # rule comprehension (task #61): the prompt is scaled by the frame's
    # character ratio to contribute_N (pgg_game.prompt_scales); completion as
    # contribute_N (tahmin, not measured)
    "comprehension": ("contribute_N", 1.0, 1.0),
}


def load_calibration(path: Path = CALIBRATION_PATH, overlays=CALIBRATION_OVERLAYS) -> dict:
    """The base calibration with the model entries of each overlay file put over it.

    "overlays" of the result lists {"file", "run", "models"} per applied overlay,
    "overlays_missing" the overlay files not found (pgg_cost_calibrate.py
    imports this module before it writes one); the report names them.
    """
    cal = json.loads(Path(path).read_text(encoding="utf-8"))
    cal["overlays"], cal["overlays_missing"] = [], []
    for over_path in overlays:
        if not Path(over_path).is_file():
            cal["overlays_missing"].append(Path(over_path).name)
            continue
        over = json.loads(Path(over_path).read_text(encoding="utf-8"))
        if over.get("overlay_of") != Path(path).name:
            raise ValueError(f"{Path(over_path).name} is an overlay of {over.get('overlay_of')!r}, "
                             f"not of {Path(path).name}")
        for slug, entry in over["models"].items():
            if not {"contribute_N", "isolated"} <= set(entry["kinds"]):
                raise ValueError(f"{Path(over_path).name}: {slug} lacks contribute_N or isolated")
            cal["models"][slug] = entry
        cal["overlays"].append({"file": Path(over_path).name, "run": over["source"]["run"],
                                "models": sorted(over["models"])})
    return cal


CALIBRATION = load_calibration()

SOURCE_NOTE = (
    f"Kaynak: configs/{CALIBRATION_PATH.name} (pgg_cost_calibrate.py, koşu "
    f"{CALIBRATION['source']['run']}: model x çağrı türü ortalama/p95 token, gerçek "
    "usage.cost). Tüm sayılar (tahmin): pilot v2 dağılımı yeni koşuda aynı kalmayabilir; "
    "\"estimate\": true olan modeller ölçülmedi, kesin bütçe değil."
    + "".join(f" Üzerine yazılan: configs/{o['file']} (koşu {o['run']}: "
              f"{', '.join(o['models'])})." for o in CALIBRATION["overlays"])
    + "".join(f" EKSİK kalibrasyon dosyası: configs/{name} (yerine pilot v2 girdisi)."
              for name in CALIBRATION["overlays_missing"])
)


def _model(slug: str) -> dict:
    entry = CALIBRATION["models"].get(slug)
    if entry is None:
        raise KeyError(f"no calibration for model {slug!r}; add it to {CALIBRATION_PATH.name}")
    return entry


def price(slug: str) -> tuple[float, float, str]:
    """(input, output) USD per 1M tokens and where they come from."""
    p = _model(slug)["price_usd_per_m"]
    return p["input"], p["output"], p["source"]


def kind_tokens(slug: str, kind: str, stat: str = "mean") -> tuple[float, float, bool]:
    """(prompt, completion) tokens of one call ("mean" or "p95"), extrapolated?"""
    kinds = _model(slug)["kinds"]
    if kind in kinds:
        k = kinds[kind]
        return k["prompt_tokens"][stat], k["completion_tokens"][stat], False
    if kind not in EXTRAPOLATED_KINDS or EXTRAPOLATED_KINDS[kind][0] not in kinds:
        raise KeyError(f"no calibration for call kind {kind!r} of model {slug!r}")
    base, scale_in, scale_out = EXTRAPOLATED_KINDS[kind]
    prompt, completion, _ = kind_tokens(slug, base, stat)
    return prompt * scale_in, completion * scale_out, True


def paid_invalid_ratio(slug: str) -> float:
    """Paid-but-invalid cost per USD of valid calls (pilot v2; pooled for estimates)."""
    return _model(slug)["paid"]["paid_invalid_cost_ratio"]


def cost_per_call(model: str, kind: str, stat: str = "mean", prompt_scale: float = 1.0) -> float:
    """USD for one valid call of this kind to this model (tahmin), paid-invalid share excluded."""
    price_in, price_out, _ = price(model)
    prompt, completion, _ = kind_tokens(model, kind, stat)
    return (prompt * prompt_scale * price_in + completion * price_out) / 1e6


def model_cost(slug: str, counts: dict[str, int], prompt_scale: dict | None = None) -> dict:
    """Estimate of one model for calls by kind; see the module docstring.

    prompt_scale: {kind: factor} on the calibrated prompt tokens (another frame).
    """
    ratio = paid_invalid_ratio(slug)
    kinds = [k for k in CALL_KINDS if counts.get(k)]
    scale = {k: (prompt_scale or {}).get(k, 1.0) for k in kinds}
    base = sum(counts[k] * cost_per_call(slug, k, prompt_scale=scale[k]) for k in kinds)
    upper = sum(counts[k] * cost_per_call(slug, k, "p95", scale[k]) for k in kinds)
    return {
        "base_cost_usd": base,
        "paid_invalid_usd": base * ratio,
        "cost_usd": base * (1 + ratio),
        "p95_upper_usd": upper * (1 + ratio),
        "paid_invalid_cost_ratio": ratio,
        "estimate": bool(_model(slug)["estimate"]),
        # no pilot data: reasoning assumed 0, the expected cost is a lower bound
        "lower_bound": bool(_model(slug)["estimate"]),
        "extrapolated_kinds": [k for k in kinds if kind_tokens(slug, k)[2]],
        "scaled_kinds": {k: v for k, v in scale.items() if v != 1.0},
        "price_usd_per_m": price(slug)[:2],
        "price_source": price(slug)[2],
        "calibration_note": _model(slug).get("report_note"),
    }


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
    comprehension: bool = False,
) -> dict[str, int]:
    """Calls per model, by kind, for a homogeneous-group design.

    n_cells = number of (card, style) cells. Each cell plays groups_per_cell
    groups per condition; the isolated arm asks n_points values per cell and
    repetition (one call per value) and exists for the N condition only.
    comprehension: one call per agent of every group game and one per
    isolated schedule.
    """
    # "comprehension" only when asked (the counts of a design without it are as before)
    counts = {k: 0 for k in CALL_KINDS if k != "comprehension"}
    if "group" in arms:
        per_condition = n_cells * groups_per_cell * group_size * rounds
        for condition in conditions:
            counts[f"contribute_{condition}"] = per_condition
            if condition == "P":
                counts["punish_P"] = per_condition
    if "isolated" in arms:
        counts["isolated"] = n_cells * isolated_reps * n_points
    if comprehension:
        counts["comprehension"] = (
            (n_cells * groups_per_cell * group_size * len(conditions) if "group" in arms else 0)
            + (n_cells * isolated_reps if "isolated" in arms else 0))
    return counts


def estimate(models: dict[str, str], counts: dict[str, int]) -> dict:
    """Per-model and total call counts and estimated cost.

    models maps short key -> slug. Returns
    {"per_model": {key: {"slug", "calls", "calls_by_kind", **model_cost()}},
     "total_calls", "total_cost_usd", "total_p95_upper_usd", "unpriced"}. A model
    without calibration has cost_usd None, is listed in "unpriced" and is left
    out of the totals.
    """
    per_model = {}
    for key, slug in models.items():
        try:
            cost = model_cost(slug, counts)
        except KeyError:
            cost = {"cost_usd": None, "p95_upper_usd": None}
        per_model[key] = {
            "slug": slug,
            "calls": sum(counts.values()),
            "calls_by_kind": {k: v for k, v in counts.items() if v},
            **cost,
        }
    priced = [m for m in per_model.values() if m["cost_usd"] is not None]
    return {
        "per_model": per_model,
        "total_calls": sum(m["calls"] for m in per_model.values()),
        "total_cost_usd": sum(m["cost_usd"] for m in priced),
        "total_p95_upper_usd": sum(m["p95_upper_usd"] for m in priced),
        "unpriced": [k for k, m in per_model.items() if m["cost_usd"] is None],
    }


def ceiling(models: dict[str, str], counts: dict[str, int], max_tokens: int,
            prompt_scale: dict | None = None) -> dict:
    """Upper bound per model if every call used all max_tokens (no re-requests).

    Mean prompt tokens of the calibration (times prompt_scale), listed prices
    (no caching discount). Returns {key: cost_usd} plus "total".
    """
    prompt_scale = prompt_scale or {}
    out = {}
    for key, slug in models.items():
        if slug not in PRICES_USD_PER_M:
            raise KeyError(f"no price for model {slug!r}; add it to PRICES_USD_PER_M")
        price_in, price_out = PRICES_USD_PER_M[slug]
        out[key] = sum(counts[kind] * (kind_tokens(slug, kind)[0]
                                       * prompt_scale.get(kind, 1.0) * price_in
                                       + max_tokens * price_out)
                       for kind in CALL_KINDS if counts.get(kind)) / 1e6
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
    notes = []
    for key, m in est["per_model"].items():
        kinds = ", ".join(f"{k}={v}" for k, v in m["calls_by_kind"].items())
        if m["cost_usd"] is None:
            cost = "maliyet tahmini yok (kalibrasyon yok)"
        else:
            cost = (f"~{m['cost_usd']:.4f} USD (tahmin"
                    + (", ALT SINIR" if m.get("lower_bound") else "")
                    + f"; geçerli {m['base_cost_usd']:.4f} + "
                    f"ödenmiş-geçersiz {m['paid_invalid_usd']:.4f}); "
                    f"p95 üst sınır ~{m['p95_upper_usd']:.4f} USD")
            price_in, price_out = m["price_usd_per_m"]
            notes.append(f"  {key}: fiyat {price_in:g} / {price_out:g} USD/1M — {m['price_source']}")
            if m["estimate"]:
                notes.append(f"  {key}: pilot verisi yok, token ve ödenmiş-geçersiz payı "
                             "\"estimate\": true varsayımlar (kalibrasyon dosyası, assumptions); "
                             "akıl yürütme 0 varsayıldı: beklenen değer ALT SINIR")
            if m.get("calibration_note"):
                notes.append(f"  {key}: {m['calibration_note']}")
            if m["extrapolated_kinds"]:
                notes.append(f"  {key}: {', '.join(m['extrapolated_kinds'])} pilot v2'de yoktu; "
                             "contribute_N ölçümünden oranla (tahmin)")
        lines.append(f"{key:<9} {m['slug']:<32} {m['calls']:>6} çağrı ({kinds})  {cost}")
    unpriced = est.get("unpriced") or []
    lines.append(
        f"{'TOPLAM':<9} {'':<32} {est['total_calls']:>6} çağrı"
        f"{'':<30}~{est['total_cost_usd']:.4f} USD (tahmin"
        + (f"; {', '.join(unpriced)} HARİÇ — eksik toplam)" if unpriced else ")")
        + f"; p95 üst sınır ~{est['total_p95_upper_usd']:.4f} USD")
    lines.append("")
    lines.append("Fiyat kaynağı ve işaretler:")
    lines.extend(notes)
    lines.append("p95 üst sınır: her çağrı türünde p95 istem ve p95 completion token'ı "
                 "(akıl yürütme dahil) birlikte, artı ödenmiş-geçersiz payı.")
    lines.append(SOURCE_NOTE)
    return "\n".join(lines)
