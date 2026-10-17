"""Experiment A analysis (prereg/prereg_expA.md §2–§4), written before the data.

Arms: B = frame abstract_v4 (every player's contribution shown), T = frame
abstract_v4_agg (only the others' average). 4 minimal cards, group arm only.

  A-H1  Delta_A = mean over the 4 cards of [cell(T) - cell(B)] on r2-9 (rounds 2-9
        group mean), per model; card-stratified group bootstrap.
  A-H2  Delta_p = p_T - p_B; p = share of 0 among "event" decisions (t = 2..9, own
        contribution at t-1 >= 10, others' mean at t-1 >= 5, one of the others gave 0
        at t-1; computed from the true contributions in both arms), group level.
  Balance: round-1 group mean T - B (descriptive flag when |diff| > 2).

"Var" = |estimate| above the threshold (2 points; 0.10 for A-H2) and bootstrap
p < 0.05 (one test per model and hypothesis, no correction; prereg_expA §4).
Implementation choices fixed before the data (prereg_expA F-A.2): A-H2 pools the
groups with at least one event over the 4 cards within an arm (too few events per
card for strata); its bootstrap resamples those groups within each arm.

Run (read-only, no API calls):
  python pgg_analysis_expA.py --config configs/expA_main.json --run expA_main_<date> \\
      [--stage1-run main_s1_20261014] [--out results/<run>_analysis.json]
Refuses an incomplete run (no interim look) unless --allow-incomplete (tests, smoke).
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np

import pgg_analysis as pa

SEED_NS = "pgg-expA-analysis"
ARMS = {"B": "abstract_v4", "T": "abstract_v4_agg"}
CARDS = ("boston_minimal", "copenhagen_minimal", "athens_minimal", "riyadh_minimal")
THRESHOLD = 2.0
THRESHOLD_P = 0.10
ALPHA = 0.05
N_BOOT = 10_000


def seed(*parts) -> int:
    return pa.stable_seed(SEED_NS, *parts)


def groups_by_arm(units: pa.Units) -> dict:
    """{(model, card, arm): (G, 10, 4) array} of complete groups."""
    out = collections.defaultdict(list)
    frame_arm = {v: k for k, v in ARMS.items()}
    for unit, g in units.groups.items():
        arm = frame_arm.get(unit.split("|")[6])
        if arm:
            out[(g["model"], g["card"], arm)].append(g["c"])
    return {k: np.stack(v) for k, v in out.items()}


def r_window(groups: np.ndarray, a: int, b: int) -> np.ndarray:
    return groups[:, a - 1:b, :].mean(axis=(1, 2))


def stratified_diff(by_card_T: list, by_card_B: list, seed_parts, n_boot: int) -> dict:
    """Mean over cards of mean(T) - mean(B); groups resampled within card and arm."""
    if any(len(x) == 0 for x in by_card_T + by_card_B):
        return {"est": None}
    rng = np.random.default_rng(seed(*seed_parts))
    est = float(np.mean([t.mean() - b.mean() for t, b in zip(by_card_T, by_card_B)]))
    draws = np.zeros(n_boot)
    for t, b in zip(by_card_T, by_card_B):
        draws += (t[rng.integers(0, len(t), (n_boot, len(t)))].mean(1)
                  - b[rng.integers(0, len(b), (n_boot, len(b)))].mean(1))
    draws /= len(by_card_T)
    return {"est": est, "ci": pa.ci(draws), "p": pa.boot_p(draws),
            "n_groups": {"T": [len(x) for x in by_card_T], "B": [len(x) for x in by_card_B]}}


def event_shares(groups: np.ndarray, with_zero: bool) -> np.ndarray:
    """Per group: share of 0 among its event decisions (with_zero) or control decisions;
    groups without such a decision are left out."""
    out = []
    for c in groups:
        hits = n = 0
        for t in range(1, 9):                        # rounds 2..9 (0-based index t)
            for i in range(4):
                others = np.delete(c[t - 1], i)
                if c[t - 1, i] >= 10 and others.mean() >= 5 and (others.min() == 0) == with_zero:
                    n += 1
                    hits += c[t, i] == 0
        if n:
            out.append(hits / n)
    return np.array(out, dtype=float)


def share_diff(sT: np.ndarray, sB: np.ndarray, seed_parts, n_boot: int) -> dict:
    if len(sT) == 0 or len(sB) == 0:
        return {"est": None, "n_groups": {"T": len(sT), "B": len(sB)}}
    rng = np.random.default_rng(seed(*seed_parts))
    draws = (sT[rng.integers(0, len(sT), (n_boot, len(sT)))].mean(1)
             - sB[rng.integers(0, len(sB), (n_boot, len(sB)))].mean(1))
    return {"est": float(sT.mean() - sB.mean()), "p_T": float(sT.mean()), "p_B": float(sB.mean()),
            "ci": pa.ci(draws), "p": pa.boot_p(draws), "n_groups": {"T": len(sT), "B": len(sB)}}


def label_h1(t: dict) -> str:
    if t.get("est") is None:
        return "belirlenemedi"
    if t["est"] > THRESHOLD and t["p"] < ALPHA:
        return "görünürlük çöküşü hızlandırır"
    if t["est"] < -THRESHOLD and t["p"] < ALPHA:
        return "görünürlük işbirliğini destekler"
    inside = -THRESHOLD <= t["ci"][0] and t["ci"][1] <= THRESHOLD
    return "fark yok — eşdeğerlik sağlandı" if inside else "fark yok — ayırt edilemedi"


def label_h2(t: dict) -> str:
    if t.get("est") is None:
        return "belirlenemedi"
    if t["est"] < -THRESHOLD_P and t["p"] < ALPHA:
        return "mekanizma destekleniyor"
    if t["est"] > THRESHOLD_P and t["p"] < ALPHA:
        return "ters"
    inside = -THRESHOLD_P <= t["ci"][0] and t["ci"][1] <= THRESHOLD_P
    return "fark yok — eşdeğerlik sağlandı" if inside else "fark yok — ayırt edilemedi"


def analyse(units: pa.Units, models, n_boot: int = N_BOOT) -> dict:
    g = groups_by_arm(units)
    empty = np.zeros((0, 10, 4))
    out = {"A_H1": {}, "A_H2": {}, "A_H2_control": {}, "balance_round1": {}, "rounds": {}, "cells": {}}
    for m in models:
        T = [g.get((m, c, "T"), empty) for c in CARDS]
        B = [g.get((m, c, "B"), empty) for c in CARDS]
        t = stratified_diff([r_window(x, 2, 9) for x in T], [r_window(x, 2, 9) for x in B], ("A_H1", m), n_boot)
        t["label"] = label_h1(t)
        out["A_H1"][m] = t
        bal = stratified_diff([r_window(x, 1, 1) for x in T], [r_window(x, 1, 1) for x in B], ("balance", m), n_boot)
        if bal.get("est") is not None:
            bal["flag"] = abs(bal["est"]) > THRESHOLD
        out["balance_round1"][m] = bal
        allT, allB = np.concatenate(T), np.concatenate(B)
        h2 = share_diff(event_shares(allT, True), event_shares(allB, True), ("A_H2", m), n_boot)
        h2["label"] = label_h2(h2)
        out["A_H2"][m] = h2
        out["A_H2_control"][m] = share_diff(event_shares(allT, False), event_shares(allB, False),
                                            ("A_H2_control", m), n_boot)
        out["rounds"][m] = {arm: [float(x) for x in a.mean(axis=(0, 2))] if len(a) else None
                            for arm, a in (("T", allT), ("B", allB))}
        out["cells"][m] = {f"{c}|{arm}": {"n_groups": len(a), "r2_9": float(r_window(a, 2, 9).mean()) if len(a) else None}
                           for c, tb in zip(CARDS, zip(T, B)) for arm, a in zip(("T", "B"), tb)}
    return out


def stage1_replication(stage1_rows: list, result: dict, models) -> dict:
    """Arm B cells beside the stage-1 minimal cells (same prompt; descriptive)."""
    s1 = pa.Units(stage1_rows)
    out = {}
    for m in models:
        out[m] = {}
        for c in CARDS:
            a = s1.group_array(m, c)
            b = result["cells"][m][f"{c}|B"]["r2_9"]
            s = float(r_window(a, 2, 9).mean()) if len(a) else None
            out[m][c] = {"expA_B": b, "stage1": s,
                         "diff": None if b is None or s is None else b - s,
                         "flag": None if b is None or s is None else abs(b - s) > THRESHOLD}
    return out


def run_analysis(rows, length_calls, models, n_boot: int = N_BOOT) -> dict:
    units = pa.Units(rows, length_calls)
    res: dict = {"main": analyse(units, models, n_boot), "sensitivity": {}}
    for v in ("comp_full", "no_capped", "no_reused"):
        sub = units.subset(v)
        s = analyse(sub, models, n_boot)
        res["sensitivity"][v] = {
            "excluded_groups": len(units.groups) - len(sub.groups),
            "labels": {m: {"A_H1": s["A_H1"][m]["label"], "A_H2": s["A_H2"][m]["label"]} for m in models},
            "changed": [(h, m) for m in models for h in ("A_H1", "A_H2")
                        if pa.coarse(s[h][m]["label"]) != pa.coarse(res["main"][h][m]["label"])]}
    res["n_groups"] = len(units.groups)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--runs-dir")
    ap.add_argument("--stage1-run")
    ap.add_argument("--stage1-config", default="configs/main.json")
    ap.add_argument("--out")
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--allow-incomplete", action="store_true")
    args = ap.parse_args(argv)
    rows, length_calls, planned, meta = pa.load_run(args.config, args.run, args.runs_dir)
    units = pa.Units(rows, length_calls)
    if len(units.groups) < meta["planned_units"] and not args.allow_incomplete:
        print(f"DUR: koşu tamamlanmamış ({len(units.groups)}/{meta['planned_units']} grup). "
              "Ara analiz planda yok.", file=sys.stderr)
        return 2
    models = tuple(m for m in pa.MODELS if m in planned)
    res = run_analysis(rows, length_calls, models, args.n_boot)
    if args.stage1_run:
        s1_rows, _, _, _ = pa.load_run(args.stage1_config, args.stage1_run, args.runs_dir)
        res["stage1_replication"] = stage1_replication(s1_rows, res["main"], models)
    res["meta"] = {**meta, "run": args.run, "n_rows": len(rows), "n_boot": args.n_boot,
                   "allow_incomplete": args.allow_incomplete}
    out = Path(args.out) if args.out else pa.ROOT / "results" / f"{args.run}_analysis.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=pa._json_default))
    print(f"yazıldı: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
