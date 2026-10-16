"""Stage 1 analysis of the main experiment (prereg/prereg_main.md §6–§8, amendment F.8).

Written and tested on synthetic data before the stage-1 data were opened
(prereg §7.6). Read-only on the run directory; no API calls.

Unit = group game (group arm) or isolated schedule (isolated arm). Cell =
model x card. Every decision follows the prereg:

  H1  D_val = cell(A_value) - cell(B_value) on m10, 6 city pairs, per model.
  H2  D_fac, the same on the factual cards.
  H3  Delta = |D(10)| - |D(1)| on r(t), 12 pairs (6 value + 6 factual).
  H4  Delta4 = mean over groups of (observed rounds 2-10 mean - simulated
      no-interaction mean), simulated from the isolated response function
      (linear interpolation, observed round-1 start, deterministic update,
      two-level bootstrap), 12 cards per model.
  H5  the same label in all three models (H1 pairs, H3 pairs).

"Var" = |estimate| > 2 and the 95 % CI excludes 0, the latter applied as a
Holm-adjusted bootstrap p < 0.05 within the (model, hypothesis) family.
Bootstrap: groups resampled with replacement within each cell, 10 000
draws, percentile CI, p = min(1, 2 min(P*(x <= 0), P*(x >= 0))), seeds
llm_client.stable_seed("pgg-main-s1-analysis", hypothesis, model, pair).

Implementation choices fixed before the data (prereg amendment F.9):
  - H3 sign flip: D(1) and D(10) are "var" by |D| > 2 and the unadjusted
    95 % CI excluding 0 (they are not a Holm family).
  - H3 "büyür" needs D(10) and D(1) of the same sign; D(1) = 0 exactly has
    no sign to reverse and counts as the same sign.
  - Only complete units count (a group with all 10 rounds x 4 agents, a
    schedule with all 5 points); a cell with fewer units than planned is
    analysed with what it has and marked incomplete; H5 then says
    "belirlenemedi" for every pair that uses it.
  - H4 bootstrap, second level: at every isolated point the schedules'
    answers are resampled with replacement, independently per point.

Sensitivity analyses (§7.5 and F.8; they never change a main label):
  comp_full   only units whose rule-check answers are all correct;
  no_capped   without group units with a reasoning_capped row or a
              finish_reason "length" event; in the isolated arm only that
              point is dropped;
  no_reused   without units with an answer reused from an earlier segment.

Run:
  python pgg_analysis.py --config configs/main.json --run main_s1_20261014 \\
      --runs-dir <runs_dir> [--out results/<run>_analysis.json]
The run must be complete (every unit done), otherwise the analysis refuses
to start: an interim look is not part of the plan. --allow-incomplete exists
only for tests and for the 0b smoke check.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent

# llm_client builds its HTTP client at import and needs a key in the
# environment; the analysis never calls it (stable_seed only).
os.environ.setdefault("OPENROUTER_API_KEY", "offline-analysis-no-calls")
sys.path.insert(0, str(ROOT))
from llm_client import stable_seed  # noqa: E402

SEED_NS = "pgg-main-s1-analysis"
N_BOOT = 10_000
THRESHOLD = 2.0
ALPHA = 0.05
MODELS = ("deepseek", "mistral", "gpt")
CITIES = ("boston", "copenhagen", "athens", "riyadh")
STYLES = ("minimal", "value", "factual")
POINTS = (0, 5, 10, 15, 20)
ROUNDS = 10
GROUP_SIZE = 4

# §6.0: pair A - B is written so that Herrmann N->P rounds 1-10 has A > B.
PAIRS = (("copenhagen", "athens"), ("copenhagen", "riyadh"), ("boston", "athens"),
         ("copenhagen", "boston"), ("boston", "riyadh"), ("riyadh", "athens"))
HERRMANN_R1_10 = {"copenhagen": 11.534, "boston": 9.327, "riyadh": 7.629, "athens": 6.357}
COURT_DAYS = {"boston": 444, "copenhagen": 485, "riyadh": 575, "athens": 1711}

# E2a dictionaries and rules, verbatim from the mini-pilot analysis
# (workspace/minipilot_analiz/analiz.py; prereg_minipilot §5.0-§5.1).
DICT_I = {"public good": ["public good"], "commons": ["commons"], "Fehr": ["fehr"],
          "Gächter": ["gächter", "gachter", "gaechter"], "Herrmann": ["herrmann"],
          "Ostrom": ["ostrom"]}
DICT_EXP = {"experiment": ["experiment"]}
DICT_II = {"Nash": ["nash"], "subgame": ["subgame", "sub game"],
           "backward induction": ["backward induction", "backwards induction"],
           "equilibrium": ["equilibri"]}
DICT_BROAD = {"prisoner": ["prisoner"], "free rid": ["free rid"],
              "dominant strateg": ["dominant strateg"]}
E2A_SETS = {"i_haric": DICT_I, "i_dahil": {**DICT_I, **DICT_EXP}, "ii": DICT_II,
            "genis": DICT_BROAD}
FP_SURFACE = {("nash", "nasheez")}


# ---------------------------------------------------------------- helpers

def card_id(city: str, style: str) -> str:
    return f"{city}_{style}"


def seed(*parts) -> int:
    return stable_seed(SEED_NS, *parts)


def boot_p(draws: np.ndarray) -> float:
    return min(1.0, 2 * min(float(np.mean(draws <= 0)), float(np.mean(draws >= 0))))


def ci(draws: np.ndarray) -> list[float]:
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return [float(lo), float(hi)]


def holm(pvalues: dict) -> dict:
    """Holm step-down adjusted p values, {key: p} -> {key: p_adj}."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def equivalent(interval) -> bool:
    return -THRESHOLD <= interval[0] and interval[1] <= THRESHOLD


def var_unadjusted(est: float, interval) -> bool:
    return abs(est) > THRESHOLD and (interval[0] > 0 or interval[1] < 0)


def _norm(text) -> str:
    return str(text).lower().replace("-", " ").replace("_", " ") if text else ""


def _surface(t: str, j: int, n: int) -> str:
    a, b = j, j + n
    while a > 0 and t[a - 1].isalpha():
        a -= 1
    while b < len(t) and t[b].isalpha():
        b += 1
    return t[a:b]


def match_terms(text, d: dict) -> list[str]:
    t, out = _norm(text), []
    for term, roots in d.items():
        hit = False
        for r in roots:
            j = t.find(r)
            while j >= 0 and not hit:
                if (r, _surface(t, j, len(r))) not in FP_SURFACE:
                    hit = True
                j = t.find(r, j + len(r))
            if hit:
                break
        if hit:
            out.append(term)
    return out


def e2a_label_text(row: dict) -> str:
    """Label field: GPT rationale only; Mistral reasoning + rationale (rationale
    only when no reasoning came back); DeepSeek reasoning + rationale."""
    rat, rea = row.get("rationale") or "", row.get("reasoning") or ""
    if row.get("model_key") == "gpt":
        return rat
    return f"{rea}\n{rat}" if rea else rat


# ---------------------------------------------------------------- data

class Units:
    """Complete group games and isolated schedules, with their flags."""

    def __init__(self, rows: list[dict], length_calls: set | None = None):
        length_calls = length_calls or set()
        g_rows, i_rows = collections.defaultdict(list), collections.defaultdict(list)
        for r in rows:
            (g_rows if r.get("arm") == "group" else i_rows)[r["unit"]].append(r)
        self.groups, self.schedules, self.incomplete = {}, {}, []
        for unit, rs in g_rows.items():
            con = {(r["round"], r["agent_id"]): r for r in rs if r["step"] == "contribute"}
            comp = [r for r in rs if r["step"] == "comprehension"]
            if len(con) != ROUNDS * GROUP_SIZE:
                self.incomplete.append(unit); continue
            c = np.array([[con[(t, a)]["contribution"] for a in range(1, GROUP_SIZE + 1)]
                          for t in range(1, ROUNDS + 1)], dtype=float)
            first = rs[0]
            sess = first["session_id"]
            self.groups[unit] = {
                "model": first["model_key"], "card": first["card_id"], "c": c,
                "capped": any(r.get("reasoning_capped") for r in rs),
                "length": any(k[0] == sess for k in length_calls),
                "reused": any(r.get("reused") for r in rs),
                "comp_full": len(comp) == GROUP_SIZE and all(
                    not r.get("comp_missing") and r.get("comp_q1_correct") and r.get("comp_q2_correct")
                    for r in comp)}
        for unit, rs in i_rows.items():
            pts = {r["others_mean"]: r for r in rs if r["step"] == "isolated"}
            comp = [r for r in rs if r["step"] == "comprehension"]
            if set(pts) != set(POINTS):
                self.incomplete.append(unit); continue
            first = rs[0]
            sess = first["session_id"]
            self.schedules[unit] = {
                "model": first["model_key"], "card": first["card_id"],
                "y": {x: float(pts[x]["contribution"]) for x in POINTS},
                "capped_pts": {x for x in POINTS
                               if pts[x].get("reasoning_capped") or (sess, x) in length_calls},
                "reused": any(r.get("reused") for r in rs),
                "comp_full": len(comp) == 1 and not comp[0].get("comp_missing")
                and bool(comp[0].get("comp_q1_correct")) and bool(comp[0].get("comp_q2_correct"))}

    def subset(self, variant: str) -> "Units":
        """Units kept by a sensitivity variant (main, comp_full, no_capped, no_reused)."""
        out = Units([])
        out.incomplete = self.incomplete
        for unit, g in self.groups.items():
            if variant == "comp_full" and not g["comp_full"]:
                continue
            if variant == "no_capped" and (g["capped"] or g["length"]):
                continue
            if variant == "no_reused" and g["reused"]:
                continue
            out.groups[unit] = g
        for unit, s in self.schedules.items():
            if variant == "comp_full" and not s["comp_full"]:
                continue
            if variant == "no_reused" and s["reused"]:
                continue
            if variant == "no_capped" and s["capped_pts"]:
                s = {**s, "y": {x: v for x, v in s["y"].items() if x not in s["capped_pts"]}}
            out.schedules[unit] = s
        return out

    def group_array(self, model: str, card: str) -> np.ndarray:
        """(G, 10, 4) contributions of the cell's complete groups."""
        gs = [g["c"] for g in self.groups.values() if g["model"] == model and g["card"] == card]
        return np.stack(gs) if gs else np.zeros((0, ROUNDS, GROUP_SIZE))

    def iso_points(self, model: str, card: str) -> dict:
        """{x: array of the cell's answers at x}."""
        out = {x: [] for x in POINTS}
        for s in self.schedules.values():
            if s["model"] == model and s["card"] == card:
                for x, v in s["y"].items():
                    out[x].append(v)
        return {x: np.array(v, dtype=float) for x, v in out.items()}

    def iso_schedule_means(self, model: str, card: str) -> np.ndarray:
        return np.array([np.mean(list(s["y"].values())) for s in self.schedules.values()
                         if s["model"] == model and s["card"] == card and len(s["y"]) == len(POINTS)])


# ---------------------------------------------------------------- estimates

def _resample_means(values: np.ndarray, rng, n_boot: int) -> np.ndarray:
    idx = rng.integers(0, len(values), size=(n_boot, len(values)))
    return values[idx].mean(axis=1)


def diff_test(a: np.ndarray, b: np.ndarray, seed_parts, n_boot: int) -> dict:
    """D = mean(a) - mean(b), groups resampled within each cell."""
    if len(a) == 0 or len(b) == 0:
        return {"est": None, "n": [len(a), len(b)]}
    rng = np.random.default_rng(seed(*seed_parts))
    draws = _resample_means(a, rng, n_boot) - _resample_means(b, rng, n_boot)
    return {"est": float(a.mean() - b.mean()), "ci": ci(draws), "p": boot_p(draws),
            "n": [len(a), len(b)]}


def delta_test(ga: np.ndarray, gb: np.ndarray, t_late: int, seed_parts, n_boot: int) -> dict:
    """H3: |D(t_late)| - |D(1)| with one resample of the groups for both rounds."""
    if len(ga) == 0 or len(gb) == 0:
        return {"est": None, "n": [len(ga), len(gb)]}
    rng = np.random.default_rng(seed(*seed_parts))
    a1, al = ga[:, 0, :].mean(1), ga[:, t_late - 1, :].mean(1)
    b1, bl = gb[:, 0, :].mean(1), gb[:, t_late - 1, :].mean(1)
    ia = rng.integers(0, len(ga), size=(n_boot, len(ga)))
    ib = rng.integers(0, len(gb), size=(n_boot, len(gb)))
    d1 = a1[ia].mean(1) - b1[ib].mean(1)
    dl = al[ia].mean(1) - bl[ib].mean(1)
    draws = np.abs(dl) - np.abs(d1)
    D1, DL = float(a1.mean() - b1.mean()), float(al.mean() - bl.mean())
    return {"est": abs(DL) - abs(D1), "ci": ci(draws), "p": boot_p(draws),
            "D1": D1, "D1_ci": ci(d1), "Dt": DL, "Dt_ci": ci(dl), "n": [len(ga), len(gb)]}


def simulate(f_vals: np.ndarray, c1: np.ndarray) -> np.ndarray:
    """No-interaction trajectory. f_vals (..., 5) at POINTS; c1 (..., 4) round-1
    contributions. Returns (..., 10, 4): c_i(t) = f(mean of the others at t-1)."""
    xs = np.array(POINTS, dtype=float)
    traj = [c1]
    c = c1
    for _ in range(2, ROUNDS + 1):
        others = (c.sum(axis=-1, keepdims=True) - c) / (GROUP_SIZE - 1)
        c = _interp(others, xs, f_vals)
        traj.append(c)
    return np.stack(traj, axis=-2)


def _interp(z: np.ndarray, xs: np.ndarray, fv: np.ndarray) -> np.ndarray:
    """Piecewise-linear interpolation of z (..., 4) on xs with values fv (..., 5)."""
    z = np.clip(z, xs[0], xs[-1])
    k = np.clip(np.searchsorted(xs, z, side="right") - 1, 0, len(xs) - 2)
    x0, x1 = xs[k], xs[k + 1]
    f0 = np.take_along_axis(fv, k, axis=-1) if fv.ndim > 1 else fv[k]
    f1 = np.take_along_axis(fv, k + 1, axis=-1) if fv.ndim > 1 else fv[k + 1]
    return f0 + (f1 - f0) * (z - x0) / (x1 - x0)


def h4_test(groups: np.ndarray, iso: dict, seed_parts, n_boot: int) -> dict:
    """Delta4 = mean_g (O_g - S_g) over rounds 2-10; also round 10 (descriptive)."""
    if len(groups) == 0 or any(len(iso[x]) == 0 for x in POINTS):
        return {"est": None, "n_groups": len(groups),
                "n_iso": {str(x): len(iso[x]) for x in POINTS}}
    f = np.array([iso[x].mean() for x in POINTS])
    c1 = groups[:, 0, :]
    sim = simulate(np.broadcast_to(f, (len(groups), len(POINTS))), c1)
    o = groups[:, 1:, :].mean(axis=(1, 2)); s = sim[:, 1:, :].mean(axis=(1, 2))
    o10, s10 = groups[:, -1, :].mean(1), sim[:, -1, :].mean(1)
    rng = np.random.default_rng(seed(*seed_parts))
    G = len(groups)
    gi = rng.integers(0, G, size=(n_boot, G))
    fb = np.stack([iso[x][rng.integers(0, len(iso[x]), size=(n_boot, len(iso[x])))].mean(1)
                   for x in POINTS], axis=-1)                                   # (B, 5)
    gb = groups[gi]                                                             # (B, G, 10, 4)
    simb = simulate(np.broadcast_to(fb[:, None, :], (n_boot, G, len(POINTS))), gb[:, :, 0, :])
    draws = (gb[:, :, 1:, :].mean(axis=(2, 3)) - simb[:, :, 1:, :].mean(axis=(2, 3))).mean(1)
    draws10 = (gb[:, :, -1, :].mean(2) - simb[:, :, -1, :].mean(2)).mean(1)
    return {"est": float((o - s).mean()), "ci": ci(draws), "p": boot_p(draws),
            "round10": {"est": float((o10 - s10).mean()), "ci": ci(draws10), "p": boot_p(draws10)},
            "f": [float(v) for v in f], "n_groups": G,
            "n_iso": {str(x): len(iso[x]) for x in POINTS}}


# ---------------------------------------------------------------- labels

def label_direction(t: dict) -> str:
    """H1 / H2: insan yönü / ters yön / fark yok (+ equivalence note)."""
    if t.get("est") is None:
        return "belirlenemedi"
    if t["est"] > THRESHOLD and t["p_holm"] < ALPHA:
        return "insan yönü"
    if t["est"] < -THRESHOLD and t["p_holm"] < ALPHA:
        return "ters yön"
    return "fark yok — eşdeğerlik sağlandı" if equivalent(t["ci"]) else "fark yok — ayırt edilemedi"


def label_h3(t: dict) -> str:
    if t.get("est") is None:
        return "belirlenemedi"
    d1_var, dt_var = var_unadjusted(t["D1"], t["D1_ci"]), var_unadjusted(t["Dt"], t["Dt_ci"])
    sig = t["p_holm"] < ALPHA if "p_holm" in t else t["p"] < ALPHA
    # same sign; D(1) = 0 exactly has no sign to reverse, so it counts as the same (F.9)
    if t["est"] > THRESHOLD and sig and (t["D1"] == 0 or np.sign(t["Dt"]) == np.sign(t["D1"])):
        return "büyür"
    if t["est"] < -THRESHOLD and sig:
        return "söner"
    if d1_var and dt_var and np.sign(t["D1"]) != np.sign(t["Dt"]):
        return "söner (işaret döndü)"
    return "korunur — eşdeğerlik sağlandı" if equivalent(t["ci"]) else "korunur — ayırt edilemedi"


def label_h4(t: dict) -> str:
    if t.get("est") is None:
        return "belirlenemedi"
    if t["est"] > THRESHOLD and t["p_holm"] < ALPHA:
        return "yukarı"
    if t["est"] < -THRESHOLD and t["p_holm"] < ALPHA:
        return "aşağı"
    return "uyumlu — eşdeğerlik sağlandı" if equivalent(t["ci"]) else "uyumlu — ayırt edilemedi"


def coarse(label: str) -> str:
    """Label class for H5 (notes dropped)."""
    for k in ("insan yönü", "ters yön", "fark yok", "büyür", "söner", "korunur", "belirlenemedi"):
        if label.startswith(k):
            return k
    return label


# ---------------------------------------------------------------- analysis

def m10(groups: np.ndarray) -> np.ndarray:
    return groups.mean(axis=(1, 2))


def analyse(units: Units, planned: dict, n_boot: int = N_BOOT, models=MODELS) -> dict:
    """Every hypothesis for one set of units. planned = {model: (G, isolated schedules)}."""
    out = {"H1": {}, "H2": {}, "H3": {}, "H3_t9": {}, "H4": {}, "descriptive": {}, "cells": {}}
    for m in models:
        cells = {}
        for city in CITIES:
            for style in STYLES:
                cid = card_id(city, style)
                g = units.group_array(m, cid)
                n_iso = len(units.iso_schedule_means(m, cid))
                cells[cid] = {"n_groups": len(g), "n_schedules": n_iso,
                              "complete": len(g) >= planned[m][0] and n_iso >= planned[m][1],
                              "m10": float(m10(g).mean()) if len(g) else None}
        out["cells"][m] = cells
        # H1 / H2 (m10), with Holm per family
        for hyp, style in (("H1", "value"), ("H2", "factual")):
            fam = {}
            for a, b in PAIRS:
                ga, gb = units.group_array(m, card_id(a, style)), units.group_array(m, card_id(b, style))
                fam[f"{a}-{b}"] = diff_test(m10(ga), m10(gb), (hyp, m, f"{a}-{b}"), n_boot)
            _apply_holm(fam)
            for k, t in fam.items():
                t["label"] = label_direction(t)
                a, b = k.split("-")
                t["cells_complete"] = cells[card_id(a, style)]["complete"] and cells[card_id(b, style)]["complete"]
            out[hyp][m] = fam
        # H3 (Delta, 12 pairs, one family) and the round-9 version (descriptive)
        fam, fam9 = {}, {}
        for style in ("value", "factual"):
            for a, b in PAIRS:
                ga, gb = units.group_array(m, card_id(a, style)), units.group_array(m, card_id(b, style))
                key = f"{style}:{a}-{b}"
                fam[key] = delta_test(ga, gb, ROUNDS, ("H3", m, key), n_boot)
                fam9[key] = delta_test(ga, gb, 9, ("H3_t9", m, key), n_boot)
                fam[key]["cells_complete"] = (cells[card_id(a, style)]["complete"]
                                              and cells[card_id(b, style)]["complete"])
        _apply_holm(fam)
        for key, t in fam.items():
            t["label"] = label_h3(t)
            t9 = fam9[key]
            t9["label"] = label_h3(t9)
            if t9.get("est") is not None and coarse(t9["label"]) != coarse(t["label"]):
                t["note_last_round"] = f"son tur etkisi: tur 9 ile '{t9['label']}'"
            if t.get("est") is not None and abs(t["D1"]) <= THRESHOLD and var_unadjusted(t["Dt"], t["Dt_ci"]):
                t["note_born"] = "grup içinde doğan fark"
        out["H3"][m], out["H3_t9"][m] = fam, fam9
        # H4 (12 cards, one family)
        fam = {}
        for city in CITIES:
            for style in STYLES:
                cid = card_id(city, style)
                fam[cid] = h4_test(units.group_array(m, cid), units.iso_points(m, cid),
                                   ("H4", m, cid), n_boot)
                fam[cid]["cell_complete"] = cells[cid]["complete"]
        _apply_holm(fam)
        for t in fam.values():
            t["label"] = label_h4(t)
        out["H4"][m] = fam
        # descriptive: minimal pairs (m10 and H3), D_iso per style, Herrmann ranks
        desc = {"D_min": {}, "H3_min": {}, "D_iso": {}, "rank_vs_herrmann": {}}
        for a, b in PAIRS:
            ga, gb = units.group_array(m, card_id(a, "minimal")), units.group_array(m, card_id(b, "minimal"))
            desc["D_min"][f"{a}-{b}"] = diff_test(m10(ga), m10(gb), ("D_min", m, f"{a}-{b}"), n_boot)
            t = delta_test(ga, gb, ROUNDS, ("H3_min", m, f"{a}-{b}"), n_boot)
            t["label"] = label_h3(t)
            desc["H3_min"][f"{a}-{b}"] = t
            for style in STYLES:
                ia = units.iso_schedule_means(m, card_id(a, style))
                ib = units.iso_schedule_means(m, card_id(b, style))
                desc["D_iso"][f"{style}:{a}-{b}"] = diff_test(ia, ib, ("D_iso", m, style, f"{a}-{b}"), n_boot)
        for style in STYLES:
            vals = {c: cells[card_id(c, style)]["m10"] for c in CITIES}
            desc["rank_vs_herrmann"][style] = rank_summary(vals)
        out["descriptive"][m] = desc
    out["H5"] = h5(out, models)
    return out


def _apply_holm(fam: dict) -> None:
    ps = {k: t["p"] for k, t in fam.items() if t.get("est") is not None}
    for k, p in holm(ps).items():
        fam[k]["p_holm"] = p


def rank_summary(vals: dict) -> dict:
    """Model's m10 order of the four cities beside Herrmann's (descriptive Spearman)."""
    if any(v is None for v in vals.values()):
        return {"order": None, "spearman": None}
    order = sorted(vals, key=lambda c: -vals[c])
    human = sorted(HERRMANN_R1_10, key=lambda c: -HERRMANN_R1_10[c])
    rm = _ranks([vals[c] for c in CITIES]); rh = _ranks([HERRMANN_R1_10[c] for c in CITIES])
    rho = float(np.corrcoef(rm, rh)[0, 1]) if np.std(rm) > 0 else None
    return {"order": order, "herrmann_order": human, "spearman": rho}


def _ranks(xs) -> np.ndarray:
    xs = np.asarray(xs, dtype=float)
    order = np.argsort(xs)
    r = np.empty(len(xs)); r[order] = np.arange(len(xs), dtype=float)
    for v in np.unique(xs):                       # average ranks for ties
        r[xs == v] = r[xs == v].mean()
    return r


def h5(out: dict, models) -> dict:
    res = {"H1": {}, "H3": {}}
    for a, b in PAIRS:
        k = f"{a}-{b}"
        res["H1"][k] = _same([out["H1"][m][k] for m in models], len(models))
    for style in ("value", "factual"):
        for a, b in PAIRS:
            k = f"{style}:{a}-{b}"
            res["H3"][k] = _same([out["H3"][m][k] for m in models], len(models))
    for h in ("H1", "H3"):
        vals = [v["label"] for v in res[h].values()]
        res[h + "_summary"] = {"aynı": vals.count("aynı"), "toplam": len(vals),
                               "belirlenemedi": vals.count("belirlenemedi")}
    return res


def _same(tests: list, n_models: int) -> dict:
    labels = [coarse(t.get("label", "belirlenemedi")) for t in tests]
    if (len(tests) < n_models or "belirlenemedi" in labels
            or not all(t.get("cells_complete", True) for t in tests)):
        return {"label": "belirlenemedi", "labels": labels}
    return {"label": "aynı" if len(set(labels)) == 1 else "farklı", "labels": labels}


def e2a_table(rows: list[dict]) -> dict:
    """Recognition covariate (descriptive): decision rows matching each set, per model x card."""
    out = collections.defaultdict(lambda: {"n": 0, **{s: 0 for s in E2A_SETS}})
    for r in rows:
        if r.get("step") == "comprehension":
            continue
        d = out[f"{r['model_key']}|{r['card_id']}"]
        d["n"] += 1
        text = e2a_label_text(r)
        for s, dic in E2A_SETS.items():
            d[s] += bool(match_terms(text, dic))
    return dict(out)


def comprehension_table(rows: list[dict]) -> dict:
    out = collections.defaultdict(lambda: {"n": 0, "all_correct": 0, "missing": 0})
    for r in rows:
        if r.get("step") != "comprehension":
            continue
        d = out[f"{r['model_key']}|{r['card_id']}"]
        if r.get("comp_missing"):
            d["missing"] += 1; continue
        d["n"] += 1
        d["all_correct"] += bool(r.get("comp_q1_correct") and r.get("comp_q2_correct"))
    return dict(out)


def excluded_counts(full: Units, sub: Units) -> dict:
    out = collections.Counter()
    for u, g in full.groups.items():
        if u not in sub.groups:
            out[f"{g['model']}|{g['card']}|group"] += 1
    for u, s in full.schedules.items():
        if u not in sub.schedules:
            out[f"{s['model']}|{s['card']}|isolated"] += 1
        elif len(sub.schedules[u]["y"]) < len(s["y"]):
            out[f"{s['model']}|{s['card']}|isolated_points"] += len(s["y"]) - len(sub.schedules[u]["y"])
    return dict(out)


def label_changes(main: dict, sens: dict) -> list[dict]:
    out = []
    for hyp in ("H1", "H2", "H3", "H4"):
        for m, fam in main[hyp].items():
            for k, t in fam.items():
                s = sens[hyp].get(m, {}).get(k, {})
                if coarse(t.get("label", "")) != coarse(s.get("label", "belirlenemedi")):
                    out.append({"hyp": hyp, "model": m, "test": k, "main": t.get("label"),
                                "sensitivity": s.get("label")})
    return out


def run_analysis(rows: list[dict], length_calls: set, planned: dict, n_boot: int = N_BOOT,
                 models=MODELS) -> dict:
    units = Units(rows, length_calls)
    result = {"main": analyse(units, planned, n_boot, models),
              "n_units": {"groups": len(units.groups), "schedules": len(units.schedules),
                          "incomplete": len(units.incomplete)},
              "e2a": e2a_table(rows), "comprehension": comprehension_table(rows),
              "sensitivity": {}}
    for variant in ("comp_full", "no_capped", "no_reused"):
        sub = units.subset(variant)
        sens = analyse(sub, planned, n_boot, models)
        result["sensitivity"][variant] = {"excluded": excluded_counts(units, sub),
                                          "label_changes": label_changes(result["main"], sens),
                                          "result": sens}
    return result


# ---------------------------------------------------------------- I/O

def load_run(config: str, run: str, runs_dir: str | None = None):
    """Valid rows (pgg_game's own row rule), length events, plan and completeness."""
    import pgg_game
    argv = ["--config", config, "--run", run, "--resume", "--dry-run"]
    if runs_dir:
        argv += ["--runs-dir", runs_dir]
    args = pgg_game.build_parser().parse_args(argv)
    s = pgg_game.settings_from_args(args)
    models = pgg_game.resolve_models(s.get("models"), pgg_game.pgg_cost.KNOWN_MODELS)
    engine = pgg_game.Engine(pgg_game.run_config(run, s, models, pgg_game.resolve_output(s)),
                             llm=pgg_game.OfflineLLM())
    out_dir = engine.cfg.output_dir()
    rows = engine.valid_rows()
    length_calls = set()
    raw = out_dir / "raw_calls.jsonl"
    if raw.exists():
        for line in raw.read_text(encoding="utf-8").splitlines():
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("finish_reason") == "length":
                call = o.get("call") or {}
                length_calls.add((o.get("session_id"), call.get("others_mean")))
    specs = engine.unit_specs()
    planned_units = len(specs)
    by_model = s.get("groups_per_cell_by_model") or {}
    planned = {m: (by_model.get(m, s.get("groups_per_cell")), s.get("isolated_reps"))
               for m in s.get("models_keys", None) or [k for k in MODELS if k in models]}
    status = {}
    if (out_dir / "status.json").exists():
        status = json.loads((out_dir / "status.json").read_text())
    return rows, length_calls, planned, {"planned_units": planned_units, "status": status,
                                         "out_dir": str(out_dir), "models": list(models)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--runs-dir")
    ap.add_argument("--out")
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--allow-incomplete", action="store_true",
                    help="tests and the 0b smoke check only; not for stage-1 results")
    args = ap.parse_args(argv)
    rows, length_calls, planned, meta = load_run(args.config, args.run, args.runs_dir)
    units = Units(rows, length_calls)
    n_done = len(units.groups) + len(units.schedules)
    if n_done < meta["planned_units"] and not args.allow_incomplete:
        print(f"DUR: koşu tamamlanmamış ({n_done}/{meta['planned_units']} birim). Ara analiz planda "
              "yok; analiz yalnız koşu bitince çalışır.", file=sys.stderr)
        return 2
    models = tuple(m for m in MODELS if m in planned)
    result = run_analysis(rows, length_calls, planned, args.n_boot, models)
    result["meta"] = {**meta, "run": args.run, "config": args.config, "n_boot": args.n_boot,
                      "n_rows": len(rows), "n_length_events": len(length_calls),
                      "allow_incomplete": args.allow_incomplete}
    out = Path(args.out) if args.out else ROOT / "results" / f"{args.run}_analysis.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=_json_default))
    print(f"yazıldı: {out}")
    return 0


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, set):
        return sorted(o)
    raise TypeError(type(o))


if __name__ == "__main__":
    sys.exit(main())
