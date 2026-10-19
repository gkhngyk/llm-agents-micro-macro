"""Exploratory dynamics of the learned rule (prereg/prereg_dyn.md): traps, tipping point,
path dependence; LLM groups (stage 1, experiment A arm B, experiment B) and human groups
(Herrmann, Thoeni & Gaechter 2008, N experiment played first).

NOT pre-registered as a test: written after every pre-registered result was seen, before
any quantity in this file was computed. It changes no label of prereg_main / expA / expB.

Rules: the frozen R3 tables of experiment B (sha256-locked), mid-game round bin only
(bin 0) in every simulation; the model rule pools the model's 12 cards, the cell rule is
model x card with the F.14 back-off; R0 is the isolated response (deterministic). The
human rule H-R3 is the same state rule learned from all human groups (in sample).

Run (read-only, no API calls):
  python pgg_analysis_dynamics.py [--out results/dynamics_analysis.json]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np

import pgg_analysis as pa
import pgg_analysis_expA as ax
import pgg_analysis_expB as pb
import pgg_analysis_rules as pr

SEED_NS = "pgg-dyn"
N = 4
FROZEN = "data/expB/frozen_rules_v1.json"
FROZEN_SHA = "62b2bae7bcf6560f022181ff5b0813fec4747f2b8e3e13e5dd1301931fbd93d1"
HUMAN_CSV = "data/herrmann2008/raw/HerrmannThoeniGaechterDATA.csv"
LOW, HIGH = 2.5, 7.5
SENS = (1.0, 9.0)
TIP_T = 13                     # round 1 + 12 mid-game rounds (experiment B's mid game)
LIFE_ROUNDS = 100
S_RULE = 2000                  # D1b, D2
S_GROUP = 500                  # D1c, D2 check, D3
N_BOOT = 10_000
MIN_K1, MIN_CLUSTER = 5, 8
SHARE_BAND = 0.15
# symmetric state -> (own bin, others' mean bin, someone gave 0, value repeated)
SYM = {"Z": (0, 0, 1, 0), "C10": (2, 3, 0, 10), "C20": (4, 5, 0, 20)}
# data set -> (end of the mid game E, expected number of groups)
DATASETS = {"S1": (8, 504), "AB": (8, 128), "EB": (13, 176), "H": (8, 230)}


def seed(*parts) -> int:
    return pa.stable_seed(SEED_NS, *parts)


# ---------------------------------------------------------------- rules

def model_rule(frozen: dict, model: str) -> pr.Rule:
    m = frozen["models"][model]
    tab = pb._table_from_json(m["model_tables"], m["model_total"])
    return pr.Rule("R3", tab, tab)


def table_from_groups(groups) -> pr.Table:
    tab = pr.Table(pb.FEATURE_SETS)
    for g in groups:
        tab.add(pr.decisions(g))
    return tab


def pooled_rule(groups) -> pr.Rule:
    tab = table_from_groups(groups)
    return pr.Rule("R3", tab, tab)


def dist_source(rule: pr.Rule, key: tuple) -> dict:
    """Where rule.dist(key) comes from: back-off depth, level and number of decisions."""
    for depth, fs in enumerate(rule.order):
        for lvl, tab in (("cell", rule.cell), ("model", rule.model)):
            c = tab.counts[fs].get(pr.project(key, fs))
            if c is not None and c.sum() > 0:
                return {"depth": depth, "features": list(fs), "level": lvl, "n": int(c.sum())}
    return {"depth": "all", "level": "cell", "n": int(rule.cell.total.sum())}


def persistence(rule: pr.Rule) -> dict:
    """D1a: p_s = pi_s^4 for the symmetric states, with the expected holding time."""
    out = {}
    for s, (own, mb, zero, v) in SYM.items():
        key = (own, mb, zero, 0)
        pi = float(rule.dist(key)[v])
        p = pi ** 4
        out[s] = {"pi": pi, "p": p, "holding_rounds": (1 / (1 - p)) if p < 1 else None,
                  "source": dist_source(rule, key)}
    return out


def simulate_mid(rule: pr.Rule, c1: np.ndarray, rng, s: int, T: int) -> np.ndarray:
    """(s, T, 4): rounds 2..T all with the mid-game round bin (0)."""
    return pb.simulate_T(rule, c1, rng, s, T, None)


def group_means(x: np.ndarray) -> np.ndarray:
    return x.mean(axis=-1)


def collapse_time(m: np.ndarray, low: float = LOW) -> np.ndarray:
    """First round (1-based) with m <= low along the last axis; 0 if never."""
    hit = m <= low
    first = hit.argmax(axis=-1) + 1
    return np.where(hit.any(axis=-1), first, 0)


def lifetime(rule: pr.Rule, start: float, rng, s: int = S_RULE, rounds: int = LIFE_ROUNDS) -> dict:
    """D1b: rounds from a symmetric start until the first collapse, capped at `rounds`."""
    sim = simulate_mid(rule, np.full(N, float(start)), rng, s, rounds + 1)
    tau = collapse_time(group_means(sim))
    life = np.where(tau > 0, tau - 1, rounds).astype(float)
    return {"median": float(np.median(life)), "mean_capped": float(life.mean()),
            "censored_share": float(np.mean(tau == 0)), "cap": rounds, "sims": s}


def tipping(rule: pr.Rule, rng, s: int = S_RULE, T: int = TIP_T) -> dict:
    """D2: start with k zeros and 4 - k tens, mid-game rule to round T."""
    rows = {}
    for k in range(N + 1):
        c1 = np.array([0.0] * k + [10.0] * (N - k))
        m = group_means(simulate_mid(rule, c1, rng, s, T))
        rows[k] = {f"r{t}": {"collapse": float(np.mean(m[:, t - 1] <= LOW)),
                              "coop": float(np.mean(m[:, t - 1] >= HIGH)),
                              "mean": float(m[:, t - 1].mean())} for t in (8, T)}
    return {"by_k": rows, "k_star": k_star({k: v[f"r{T}"]["collapse"] for k, v in rows.items()})}


def k_star(p_collapse: dict):
    for k in sorted(p_collapse):
        if p_collapse[k] >= 0.5:
            return k
    return None


# ---------------------------------------------------------------- R0

def r0_tipping(f: np.ndarray, T: int = TIP_T) -> dict:
    rows = {}
    for k in range(N + 1):
        c1 = np.array([0.0] * k + [10.0] * (N - k))
        m = group_means(pb.simulate_R0(f, c1, T))
        rows[k] = {f"r{t}": {"collapse": float(m[t - 1] <= LOW), "coop": float(m[t - 1] >= HIGH),
                              "mean": float(m[t - 1])} for t in (8, T)}
    return {"by_k": rows, "k_star": k_star({k: v[f"r{T}"]["collapse"] for k, v in rows.items()})}


def fixed_points(f) -> dict:
    """Fixed points of the symmetric map x -> f(x) (piecewise linear on POINTS) and stability
    (|slope| < 1 on every side; a segment with f(x) = x is reported as a continuum)."""
    xs = np.array(pa.POINTS, dtype=float)
    fv = np.asarray(f, dtype=float)
    g = fv - xs
    slopes = np.diff(fv) / np.diff(xs)
    pts, continua = [], []
    for j in range(len(xs) - 1):
        if abs(g[j]) < 1e-9 and abs(g[j + 1]) < 1e-9:
            continua.append([float(xs[j]), float(xs[j + 1])])
            continue
        if abs(g[j]) < 1e-9:
            pts.append((float(xs[j]), j))
        elif g[j] * g[j + 1] < 0:
            x = xs[j] - g[j] * (xs[j + 1] - xs[j]) / (g[j + 1] - g[j])
            pts.append((float(x), j + 0.5))
    if abs(g[-1]) < 1e-9 and not (continua and continua[-1][1] == xs[-1]):
        pts.append((float(xs[-1]), len(xs) - 1))
    out = []
    for x, pos in pts:
        if any(a <= x <= b for a, b in continua):
            continue
        if pos == int(pos):
            j = int(pos)
            sides = ([slopes[j - 1]] if j > 0 else []) + ([slopes[j]] if j < len(slopes) else [])
        else:
            sides = [slopes[int(pos)]]
        out.append({"x": x, "stable": bool(all(abs(a) < 1 for a in sides)),
                    "slopes": [float(a) for a in sides]})
    return {"points": out, "n_stable": sum(p["stable"] for p in out), "continua": continua}


# ---------------------------------------------------------------- observed groups

def observed_persistence(G: np.ndarray, E: int) -> dict:
    """D1a, observed: share of mid-game transitions t -> t+1 (t+1 <= E) that stay in s."""
    out = {}
    for s, (*_, v) in SYM.items():
        inside = np.all(G == v, axis=2)            # (G, T)
        frm = inside[:, :E - 1]
        stay = frm & inside[:, 1:E]
        n = int(frm.sum())
        out[s] = {"n_from": n, "stay_share": float(stay.sum() / n) if n else None}
    return out


def recovery(m: np.ndarray, E: int) -> dict:
    """Among trajectories collapsed at tau <= E - 1: share later >= HIGH, share later > LOW."""
    m = m[..., :E]
    tau = collapse_time(m)
    flat_m, flat_tau = m.reshape(-1, E), tau.ravel()
    n = rec = esc = 0
    for row, t in zip(flat_m, flat_tau):
        if 0 < t <= E - 1:
            n += 1
            rec += bool(np.any(row[t:] >= HIGH))
            esc += bool(np.any(row[t:] > LOW))
    return {"n": n, "to_coop": rec / n if n else None, "leave_collapse": esc / n if n else None}


def categories(m_end: np.ndarray, low: float, high: float) -> np.ndarray:
    return np.stack([m_end <= low, (m_end > low) & (m_end < high), m_end >= high], axis=-1).astype(float)


def group_predictions(sim: np.ndarray, E: int) -> dict:
    """Per-group probabilities from (G, s, T, 4) simulations."""
    m = group_means(sim)[..., :E]
    tau = collapse_time(m)
    return {"surv": np.stack([np.mean((tau == 0) | (tau > t), axis=1) for t in range(1, E + 1)], axis=1),
            "cat": categories(m[..., E - 1], LOW, HIGH).mean(axis=1),
            "cat_sens": categories(m[..., E - 1], *SENS).mean(axis=1),
            "recovery": recovery(m, E)}


def observed_stats(G: np.ndarray, E: int) -> dict:
    m = group_means(G)[:, :E]
    tau = collapse_time(m)
    return {"surv": np.stack([((tau == 0) | (tau > t)).astype(float) for t in range(1, E + 1)], axis=1),
            "cat": categories(m[:, E - 1], LOW, HIGH), "cat_sens": categories(m[:, E - 1], *SENS),
            "recovery": recovery(m, E)}


# ---------------------------------------------------------------- bootstrap

def boot_mean(values: np.ndarray, strata: np.ndarray, seed_parts, n_boot: int = N_BOOT) -> dict:
    """Mean of per-group values with a group bootstrap stratified by card (or city)."""
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return {"est": None, "n": 0}
    rng = np.random.default_rng(seed(*seed_parts))
    total = np.zeros(n_boot)
    for s in dict.fromkeys(strata):
        v = values[strata == s]
        total += v[rng.integers(0, len(v), (n_boot, len(v)))].sum(axis=1)
    draws = total / len(values)
    return {"est": float(values.mean()), "ci": pa.ci(draws), "n": int(len(values))}


def band_label(t: dict, band: float = SHARE_BAND) -> str:
    if t.get("est") is None:
        return "belirlenemedi"
    lo, hi = t["ci"]
    if abs(t["est"]) <= band and -band <= lo and hi <= band:
        return "yeniden üretiyor"
    if lo > band or hi < -band:
        return "sapıyor"
    return "belirsiz"


# ---------------------------------------------------------------- per data set

def analyse_dataset(name: str, cells: dict, E: int, rules: dict, r0: dict | None,
                    s: int = S_GROUP, n_boot: int = N_BOOT) -> dict:
    """cells {card: (G, T, 4)}; rules {card: pr.Rule}; r0 {card: f} or None."""
    cards = [c for c in cells if len(cells[c])]
    obs, pred, pred0 = {}, {}, {}
    for c in cards:
        G = cells[c]
        obs[c] = observed_stats(G, E)
        rng = np.random.default_rng(seed(name, "group-sims", c))
        c1 = np.repeat(G[:, 0, :], s, axis=0)
        sim = simulate_mid(rules[c], c1, rng, len(c1), E).reshape(len(G), s, E, N)
        pred[c] = group_predictions(sim, E)
        if r0 is not None:
            pred0[c] = observed_stats(pb.simulate_R0(np.array(r0[c]), G[:, 0, :], E), E)
    strata = np.concatenate([[c] * len(cells[c]) for c in cards])
    cat = lambda d, k: np.concatenate([d[c][k] for c in cards])                     # noqa: E731
    G_all = np.concatenate([cells[c] for c in cards])
    out = {"E": E, "n_groups": int(len(G_all)), "cards": cards,
           "D1a_observed": observed_persistence(G_all, E)}
    # D1c survival
    so, sp = cat(obs, "surv"), cat(pred, "surv")
    out["D1c"] = {"observed": [float(x) for x in so.mean(0)], "rule": [float(x) for x in sp.mean(0)],
                  "S_E_observed": boot_mean(so[:, -1], strata, (name, "surv-obs"), n_boot),
                  "S_E_obs_minus_rule": boot_mean(so[:, -1] - sp[:, -1], strata, (name, "surv-diff"), n_boot)}
    out["D1c"]["S_E_label"] = band_label(out["D1c"]["S_E_obs_minus_rule"])
    if r0 is not None:
        out["D1c"]["R0"] = [float(x) for x in cat(pred0, "surv").mean(0)]
    rec_o = [obs[c]["recovery"] for c in cards]
    rec_p = [pred[c]["recovery"] for c in cards]
    out["D1c"]["recovery_observed"] = _pool_recovery(rec_o)
    out["D1c"]["recovery_rule"] = _pool_recovery(rec_p)
    # D2 check by the number of zeros in round 1
    k1 = (G_all[:, 0, :] == 0).sum(axis=1)
    co, cp = cat(obs, "cat")[:, 0], cat(pred, "cat")[:, 0]
    c0 = cat(pred0, "cat")[:, 0] if r0 is not None else None
    d2 = {}
    for k in range(N + 1):
        sel = k1 == k
        if sel.sum() < MIN_K1:
            d2[k] = {"n": int(sel.sum())}
            continue
        one = np.zeros(int(sel.sum()))        # prereg_dyn D.1: unstratified inside k1 classes
        d2[k] = {"n": int(sel.sum()),
                 "observed": boot_mean(co[sel], one, (name, "k1-obs", k), n_boot),
                 "rule": float(cp[sel].mean()),
                 "obs_minus_rule": boot_mean(co[sel] - cp[sel], one, (name, "k1-diff", k), n_boot)}
        d2[k]["label"] = band_label(d2[k]["obs_minus_rule"])
        if c0 is not None:
            d2[k]["R0"] = float(c0[sel].mean())
    out["D2_by_k1"] = d2
    # D3a end-state shares
    d3 = {}
    for key, nm in (("cat", "main"), ("cat_sens", "sens_1_9")):
        o, p = cat(obs, key), cat(pred, key)
        d3[nm] = {}
        for j, lab in enumerate(("collapse", "middle", "coop")):
            d3[nm][lab] = {"observed": boot_mean(o[:, j], strata, (name, "d3", nm, lab), n_boot),
                           "rule": float(p[:, j].mean()),
                           "obs_minus_rule": boot_mean(o[:, j] - p[:, j], strata, (name, "d3d", nm, lab), n_boot)}
            d3[nm][lab]["label"] = band_label(d3[nm][lab]["obs_minus_rule"])
            if r0 is not None:
                d3[nm][lab]["R0"] = float(cat(pred0, key)[:, j].mean())
    both = []
    for c in cards:
        o = obs[c]["cat"]
        n_lo, n_hi = o[:, 0].sum(), o[:, 2].sum()
        if min(n_lo, n_hi) >= 2 and min(n_lo, n_hi) / len(o) >= 0.10:
            both.append(c)
    d3["cells_two_ended"] = {"n": len(both), "of": len(cards), "cards": both}
    out["D3a"] = d3
    # D3b same start, different end; undecided starts
    clusters = {}
    starts = [tuple(sorted(int(v) for v in g[0])) for g in G_all]
    for st in sorted(set(starts)):
        idx = np.array([i for i, x in enumerate(starts) if x == st])
        if len(idx) >= MIN_CLUSTER:
            clusters[",".join(map(str, st))] = {"n": int(len(idx)), "collapse": float(co[idx].mean()),
                                               "coop": float(cat(obs, "cat")[idx, 2].mean()),
                                               "rule_collapse": float(cp[idx].mean())}
    out["D3b"] = {"clusters": clusters,
                  "undecided_share_rule": float(np.mean((cp > 0.2) & (cp < 0.8))),
                  "n_groups": int(len(cp))}
    return out


def _pool_recovery(items: list) -> dict:
    n = sum(r["n"] for r in items)
    if n == 0:
        return {"n": 0, "to_coop": None, "leave_collapse": None}
    return {"n": n, "to_coop": sum(r["n"] * r["to_coop"] for r in items if r["n"]) / n,
            "leave_collapse": sum(r["n"] * r["leave_collapse"] for r in items if r["n"]) / n}


# ---------------------------------------------------------------- reading rules

def labels(rule_props: dict, ds: dict, r0_model: dict) -> dict:
    """Reading rules 1-5 of prereg_dyn section 7 for one model."""
    per = rule_props["D1a"]
    pZ, pC = per["Z"]["p"], per["C10"]["p"]
    oos = [ds[d] for d in ("AB", "EB") if d in ds]
    rec = [d["D1c"]["recovery_observed"]["to_coop"] for d in oos]
    trap = pZ >= 0.9 and all(r is not None and r < 0.10 for r in rec)
    med = rule_props["D1b"]["C10"]["median"]
    coop = ("yarı kararlı işbirliği (kilitlenme)" if pC >= 0.8 and med >= 12
            else "kırılgan işbirliği" if med < 4 else "orta")
    shape = [d["D3a"]["main"]["middle"]["observed"]["est"] < 0.20
             and d["D3a"]["main"]["collapse"]["observed"]["est"] >= 0.10
             and d["D3a"]["main"]["coop"]["observed"]["est"] >= 0.10 for d in oos]
    bistable = pZ >= 0.9 and pC >= 0.8 and bool(shape) and all(shape)
    ks = rule_props["D2"]["k_star"]
    sticky = sum(per[s]["p"] >= 0.8 for s in SYM)
    agree = r0_model["fixed_points"]["n_stable"] == sticky and r0_model["D2"]["k_star"] == ks
    return {"1_trap": "çöküş emici (tuzak)" if trap else "tuzak değil",
            "2_coop": coop,
            "3_bistable": "iki çekici" if bistable else "iki çekici değil",
            "4_tipping": {1: "tek bedavacı grubu deviriyor", 2: "iki bedavacı", 3: "üç bedavacı",
                          4: "dört (hepsi)", 0: "bedavacısız da çöküyor"}.get(ks, "devrilme yok"),
            "5_R0": "nitel uyum" if agree else "izole kural makro yapıyı nitel olarak yanlış öngörüyor",
            "inputs": {"p_Z": pZ, "p_C10": pC, "median_life_C10": med, "recovery_to_coop_AB_EB": rec,
                       "shape_AB_EB": shape, "k_star": ks, "sticky_states": sticky,
                       "R0_n_stable": r0_model["fixed_points"]["n_stable"], "R0_k_star": r0_model["D2"]["k_star"]}}


# ---------------------------------------------------------------- data

def load_human(path: str | Path = HUMAN_CSV) -> dict:
    """{city: (G, 10, 4)} of N-experiment groups from sessions with N played first (secseq 0)."""
    text = Path(path).read_bytes().decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    hdr = next(i for i, l in enumerate(lines) if l.startswith("sessionid,"))
    acc: dict = {}
    for r in csv.DictReader(io.StringIO("\n".join(lines[hdr:]))):
        if r["p"] != "N-experiment" or r["secseq"] != "0":
            continue
        g = acc.setdefault((r["city"], r["sessionid"], r["groupid"]), {})
        g[(int(r["period"]), r["subjectid"])] = float(r["senderscontribution"])
    out: dict = {}
    for (city, _, _), d in sorted(acc.items()):
        subj = sorted({s for _, s in d})
        if len(subj) != N or len(d) != 10 * N:
            raise ValueError(f"human group with {len(subj)} subjects / {len(d)} cells")
        out.setdefault(city, []).append([[d[(t, s)] for s in subj] for t in range(1, 11)])
    return {c: np.array(v, dtype=float) for c, v in out.items()}


def load_llm() -> dict:
    """{data set: {model: {card: (G, T, 4)}}} for S1, AB, EB; refuses incomplete runs."""
    out = {"S1": {}, "AB": {}, "EB": {}}
    rows, length, _, _ = pa.load_run("configs/main.json", "main_s1_20261014")
    u = pa.Units(rows, length)
    rowsA, lengthA, _, _ = pa.load_run("configs/expA_main.json", "expA_main_20261017")
    gA = ax.groups_by_arm(pa.Units(rowsA, lengthA))
    rowsB, lengthB, _, _ = pa.load_run("configs/expB_main.json", "expB_main_20261018")
    uB = pb.UnitsT(rowsB, lengthB, 15)
    for m in pa.MODELS:
        out["S1"][m] = {pa.card_id(ci, st): u.group_array(m, pa.card_id(ci, st))
                        for st in pa.STYLES for ci in pa.CITIES}
        out["AB"][m] = {c: gA[(m, c, "B")] for c in ax.CARDS}
        out["EB"][m] = {c: uB.group_array(m, c) for c in pb.CARDS_MAIN}
    for d, (_, n_exp) in DATASETS.items():
        if d in out:
            n = sum(len(G) for mm in out[d].values() for G in mm.values())
            if n != n_exp:
                raise ValueError(f"{d}: {n} complete groups, expected {n_exp}")
    return out


# ---------------------------------------------------------------- main

def rule_properties(rule: pr.Rule, parts, s: int = S_RULE, with_c20: bool = True) -> dict:
    out = {"D1a": persistence(rule),
           "D1b": {"C10": lifetime(rule, 10, np.random.default_rng(seed(*parts, "life", "C10")), s)},
           "D2": tipping(rule, np.random.default_rng(seed(*parts, "tip")), s)}
    if with_c20:
        out["D1b"]["C20"] = lifetime(rule, 20, np.random.default_rng(seed(*parts, "life", "C20")), s)
    return out


def summarise_cells(cells: dict) -> dict:
    def stats(vals):
        vals = [v for v in vals if v is not None]
        return {"median": float(np.median(vals)), "min": float(np.min(vals)), "max": float(np.max(vals))} if vals else None
    out = {}
    for sub, cs in (("all", list(cells)), ("minimal", [c for c in cells if c.endswith("_minimal")])):
        out[sub] = {"p_Z": stats([cells[c]["D1a"]["Z"]["p"] for c in cs]),
                    "p_C10": stats([cells[c]["D1a"]["C10"]["p"] for c in cs]),
                    "median_life_C10": stats([cells[c]["D1b"]["C10"]["median"] for c in cs]),
                    "k_star_counts": {str(k): sum(cells[c]["D2"]["k_star"] == k for c in cs)
                                      for k in [None, 0, 1, 2, 3, 4]}}
    return out


def run(llm: dict, human: dict, frozen: dict, s_rule: int = S_RULE, s_group: int = S_GROUP,
        n_boot: int = N_BOOT, models=pa.MODELS) -> dict:
    res = {"rules": {}, "R0": {}, "datasets": {}, "labels": {}}
    for m in models:
        cells_f = frozen["models"][m]["cells"]
        mr = rule_properties(model_rule(frozen, m), (m, "model"), s_rule)
        cr = {c: rule_properties(pb.rules_for(frozen, m, c, "R3"), (m, c), s_rule, with_c20=False)
              for c in sorted(cells_f)}
        res["rules"][m] = {"model_rule": mr, "cells": cr, "cells_summary": summarise_cells(cr)}
        f_model = np.mean([cells_f[c]["iso_f"] for c in cells_f], axis=0)
        res["R0"][m] = {"model": {"f": [float(x) for x in f_model], "fixed_points": fixed_points(f_model),
                                  "D2": r0_tipping(f_model)},
                        "cells": {c: {"fixed_points": fixed_points(cells_f[c]["iso_f"]),
                                      "D2": r0_tipping(np.array(cells_f[c]["iso_f"]))} for c in sorted(cells_f)}}
        res["datasets"][m] = {}
        for d in ("S1", "AB", "EB"):
            cells = llm[d][m]
            rules = {c: pb.rules_for(frozen, m, c, "R3") for c in cells}
            r0 = {c: cells_f[c]["iso_f"] for c in cells}
            res["datasets"][m][d] = analyse_dataset(f"{d}|{m}", cells, DATASETS[d][0], rules, r0, s_group, n_boot)
        res["labels"][m] = labels(mr, res["datasets"][m], res["R0"][m]["model"])
    hr = pooled_rule([g for G in human.values() for g in G])
    res["rules"]["human"] = {"model_rule": rule_properties(hr, ("human", "pooled"), s_rule)}
    res["datasets"]["human"] = {"H": analyse_dataset("H|human", human, DATASETS["H"][0],
                                                     {c: hr for c in human}, None, s_group, n_boot)}
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(pa.ROOT / "results" / "dynamics_analysis.json"))
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--sims-rule", type=int, default=S_RULE)
    ap.add_argument("--sims-group", type=int, default=S_GROUP)
    args = ap.parse_args(argv)
    frozen = pb.load_frozen(pa.ROOT / FROZEN, FROZEN_SHA)
    human = load_human(pa.ROOT / HUMAN_CSV)
    n_h = sum(len(G) for G in human.values())
    if n_h != DATASETS["H"][1]:
        raise ValueError(f"H: {n_h} groups, expected {DATASETS['H'][1]}")
    llm = load_llm()
    res = run(llm, human, frozen, args.sims_rule, args.sims_group, args.n_boot)
    res["status"] = "keşifsel (prereg_dyn); hiçbir önceden kayıtlı etiketi değiştirmez"
    res["meta"] = {"frozen_sha256": FROZEN_SHA,
                   "human_csv_sha256": hashlib.sha256((pa.ROOT / HUMAN_CSV).read_bytes()).hexdigest(),
                   "n_groups": {"H": n_h, **{d: sum(len(G) for mm in llm[d].values() for G in mm.values())
                                              for d in llm}},
                   "sims_rule": args.sims_rule, "sims_group": args.sims_group, "n_boot": args.n_boot,
                   "thresholds": {"low": LOW, "high": HIGH, "sens": SENS, "band": SHARE_BAND}}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=pa._json_default))
    print(f"yazıldı: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
