"""Exploratory diagnosis for Experiment C (prereg/prereg_expC.md F-C.8): where does the frozen rule
go wrong in large groups? Written after the C2 results, before this file computed anything.

  T1  one-step error decomposition by state: f_s (observed mean - rule mean) over rounds 2..10
  T2  cooperators who see a zero (own >= 10, others' mean in [5, 10), mid game): observed P(0)
      by group size against the rule, and by the number of zero-givers among the others
  T3  defectors' return (own 0, others' mean >= 5, mid game): observed P(next >= 10) against the rule

Read-only, no API calls. Run:
  python pgg_analysis_expC_explore.py --runs 4=expC_n4_main_20261020,8=...,16=...,32=...
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np

import pgg_analysis as pa
import pgg_analysis_expB as pb
import pgg_analysis_expC as pc

NS = "pgg-expC-explore"
N_BOOT = 2000
COARSE = {0: "bedavacı (önceki 0)", 2: "işbirlikçi (önceki 10)"}


def decisions(G: np.ndarray):
    """Rows (state, contribution, zeros among others, others' exact mean) for rounds 2..T of one group."""
    T, n = G.shape
    out = []
    for t in range(2, T + 1):
        prev, now = G[t - 2], G[t - 1]
        own, mb, zero = (x[0] for x in pc.bins_n(prev[None, :]))
        rb = pb.bin_kalan(t, T)
        zeros = (prev == 0).sum()
        for i in range(n):
            k = int(zeros - (prev[i] == 0))
            out.append(((int(own[i]), int(mb[i]), int(zero[i]), rb), float(now[i]), k,
                        float((prev.sum() - prev[i]) / (n - 1))))
    return out


def rule_stats(rule, state):
    d = rule.dist(state)
    return float(d @ pc.VALS), float(d[0]), float(d[10:].sum())


def t1(frozen, model: str, arrays: dict) -> dict:
    """arrays {card: (G, T, n)}."""
    acc = collections.defaultdict(lambda: np.zeros(5))     # n, sum obs, sum rule, obs zeros, rule p0
    for c, A in arrays.items():
        rule = pb.rules_for(frozen, model, c, "R3")
        for g in A:
            for s, y, _, _ in decisions(g):
                rm, rp0, _ = rule_stats(rule, s)
                acc[s] += [1, y, rm, y == 0, rp0]
    total = sum(v[0] for v in acc.values())
    rows = []
    for s, v in acc.items():
        f = v[0] / total
        rows.append({"state": list(s), "share": f, "obs_mean": v[1] / v[0], "rule_mean": v[2] / v[0],
                     "obs_p0": v[3] / v[0], "rule_p0": v[4] / v[0], "contribution": f * (v[1] - v[2]) / v[0]})
    coarse = collections.defaultdict(float)
    for r in rows:
        coarse[COARSE.get(r["state"][0], "diğer")] += r["contribution"]
    rows.sort(key=lambda r: -abs(r["contribution"]))
    return {"bias_total": float(sum(r["contribution"] for r in rows)), "n_decisions": int(total),
            "top5": rows[:5], "coarse": dict(coarse)}


def _ratio_boot(per_group: list, strata: list, seed_parts) -> dict:
    """per_group [(successes, trials)], groups resampled within strata; ratio of sums."""
    s = np.array([x[0] for x in per_group], float)
    n = np.array([x[1] for x in per_group], float)
    if n.sum() == 0:
        return {"est": None, "trials": 0}
    rng = np.random.default_rng(pa.stable_seed(NS, *seed_parts))
    st_arr = np.array(strata)
    num, den = np.zeros(N_BOOT), np.zeros(N_BOOT)
    for st in dict.fromkeys(strata):
        idx = np.flatnonzero(st_arr == st)
        pick = idx[rng.integers(0, len(idx), (N_BOOT, len(idx)))]
        num += s[pick].sum(axis=1)
        den += n[pick].sum(axis=1)
    return {"est": float(s.sum() / n.sum()), "ci": pa.ci(num / np.maximum(den, 1)), "trials": int(n.sum())}


def t2_t3(frozen, model: str, arrays: dict, n: int) -> dict:
    t2g, t3g, strata = [], [], []
    t2_rule, t3_rule, t2_mean = [], [], []
    by_k = collections.defaultdict(lambda: [0, 0])
    for c, A in arrays.items():
        rule = pb.rules_for(frozen, model, c, "R3")
        for g in A:
            a2, a3 = [0, 0], [0, 0]
            for s, y, k, m in decisions(g):
                own, mb, zero, rb = s
                if rb != 0:
                    continue
                if own >= 2 and mb == 2 and zero == 1:                 # T2
                    a2[0] += y == 0
                    a2[1] += 1
                    t2_rule.append(rule_stats(rule, s)[1])
                    t2_mean.append(m)
                    kk = "1" if k == 1 else "2" if k == 2 else "3+"
                    by_k[kk][0] += y == 0
                    by_k[kk][1] += 1
                if own == 0 and mb >= 2:                              # T3
                    a3[0] += y >= 10
                    a3[1] += 1
                    t3_rule.append(rule_stats(rule, s)[2])
            t2g.append(tuple(a2))
            t3g.append(tuple(a3))
            strata.append(c)
    return {
        "T2": {**_ratio_boot(t2g, strata, ("T2", model, n)),
               "rule_p0": float(np.mean(t2_rule)) if t2_rule else None,
               "others_mean": float(np.mean(t2_mean)) if t2_mean else None,
               "by_zero_count": {k: {"p0": v[0] / v[1], "trials": v[1]} for k, v in sorted(by_k.items()) if v[1]}},
        "T3": {**_ratio_boot(t3g, strata, ("T3", model, n)),
               "rule_p_return": float(np.mean(t3_rule)) if t3_rule else None}}


def run(frozen, units: dict, sizes=None) -> dict:
    sizes = sizes or pc.SIZES
    out = {}
    for m, ns in sizes.items():
        out[m] = {}
        for n in ns:
            if n not in units:
                continue
            arrays = {c: units[n].group_array(m, c) for c in pc.CARDS}
            arrays = {c: A for c, A in arrays.items() if len(A)}
            out[m][str(n)] = {"T1": t1(frozen, m, arrays), **t2_t3(frozen, m, arrays, n)}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out", default=str(pa.ROOT / "results" / "expC_explore_20261020.json"))
    args = ap.parse_args(argv)
    frozen = pb.load_frozen(pa.ROOT / "data/expB/frozen_rules_v1.json", pc.FROZEN_SHA)
    units = {}
    for x in args.runs.split(","):
        n_s, rname = x.split("=")
        rows, length, _, _ = pa.load_run(f"configs/expC_n{n_s}_main.json", rname)
        units[int(n_s)] = pc.UnitsN(rows, length, int(n_s))
    res = {"status": "keşifsel (prereg_expC F-C.8); hiçbir C-H etiketini değiştirmez", "results": run(frozen, units),
           "meta": {"runs": args.runs, "frozen_sha256": pc.FROZEN_SHA, "n_boot": N_BOOT}}
    Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=1, default=pa._json_default))
    print(f"yazıldı: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
