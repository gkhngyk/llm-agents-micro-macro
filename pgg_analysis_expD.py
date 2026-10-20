"""Experiment D: does a count-aware rule predict an unseen group size? (prereg/prereg_expD.md,
approved 2026-10-20). Read-only on run directories, no API calls.

  select   D0: leave-one-size-out on the existing data (stage 1, experiment A arm B, experiment C);
           R3-all vs R4-count vs R4-share; choice of R4 and the decision gate.
  freeze   R3-all and the chosen R4 learned from all existing data, and the unconditional
           forecast for groups of 64 (GPT); both written with their sha256.
  analyse  D-H1, D-H2 and the secondary comparisons on the D2 run; refuses an incomplete run and
           frozen files with another sha256.

State elements (indices): 0 own previous bin, 1 others' mean bin, 2 "one of the others gave 0",
3 rounds-left bin, 4 number of zero-givers among the others (0, 1, 2, 3+), 5 their share
(0, (0, 0.2], (0.2, 0.4], > 0.4).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

import pgg_analysis as pa
import pgg_analysis_expA as ax
import pgg_analysis_expB as pb
import pgg_analysis_expC as pc
import pgg_analysis_expC_explore as px
import pgg_analysis_rules as pr

T, E, LOW = 10, 8, 2.5
N_NEW = 64
MODEL_D = "gpt"
CARDS = pc.CARDS
RUNS_C = {4: "expC_n4_main_20261020", 8: "expC_n8_main_20261020", 16: "expC_n16_main_20261020",
          32: "expC_n32_main_20261020"}
HELD_OUT = {"gpt": (8, 16, 32), "mistral": (8, 16)}
FS = {"R3-tümü": [(0, 1, 2, 3), (0, 1, 2), (0, 1), (1,)],
      "R4-sayı": [(0, 1, 4, 3), (0, 1, 4), (0, 1, 2, 3), (0, 1, 2), (0, 1), (1,)],
      "R4-pay": [(0, 1, 5, 3), (0, 1, 5), (0, 1, 2, 3), (0, 1, 2), (0, 1), (1,)]}
ALL_SETS = sorted({fs for v in FS.values() for fs in v})
GATE_MARGIN = 0.05
NS = "pgg-expD"
S_SEL, S_FC, S_COND, N_BOOT = 500, 4000, 500, 10_000
VALS = np.arange(21)


def seed(*parts) -> int:
    return pa.stable_seed(NS, *parts)


# ---------------------------------------------------------------- states, tables, rules

def keys_n(prev: np.ndarray, t: int, rounds: int = T) -> np.ndarray:
    """prev (s, n) -> (s, n, 6) state elements of every agent deciding round t."""
    n = prev.shape[1]
    own, mb, zero = pc.bins_n(prev)
    z = prev == 0
    k = z.sum(axis=1, keepdims=True) - z
    share = k / (n - 1)
    sb = np.where(k == 0, 0, np.where(share <= 0.2 + 1e-12, 1, np.where(share <= 0.4 + 1e-12, 2, 3)))
    rb = np.full(own.shape, pb.bin_kalan(t, rounds))
    return np.stack([own, mb, zero, rb, np.minimum(k, 3), sb], axis=-1)


def decisions(g: np.ndarray) -> list:
    """(state 6-tuple, contribution) for rounds 2..T of one group (T, n)."""
    out = []
    for t in range(2, g.shape[0] + 1):
        ks = keys_n(g[t - 2][None, :], t)[0]
        out += [(tuple(int(x) for x in k), int(round(y))) for k, y in zip(ks, g[t - 1])]
    return out


class RuleX:
    """Sampling distribution with an explicit back-off order; cell table first, then the model's."""

    def __init__(self, order, cell: pr.Table, model: pr.Table):
        self.order, self.cell, self.model = list(order), cell, model
        self._cache: dict = {}

    def dist(self, key: tuple) -> np.ndarray:
        if key in self._cache:
            return self._cache[key]
        for fs in self.order:
            for tab in (self.cell, self.model):
                c = tab.counts[fs].get(pr.project(key, fs))
                if c is not None and c.sum() > 0:
                    self._cache[key] = c / c.sum()
                    return self._cache[key]
        tot = self.cell.total if self.cell.total.sum() > 0 else self.model.total
        self._cache[key] = tot / tot.sum()
        return self._cache[key]


def train(parts: list) -> tuple[dict, pr.Table]:
    """parts: list of {card: (G, T, n)}; returns ({card: Table}, model Table)."""
    cells, model = {}, pr.Table(ALL_SETS)
    for part in parts:
        for c, A in part.items():
            cells.setdefault(c, pr.Table(ALL_SETS))
            for g in A:
                d = decisions(g)
                cells[c].add(d)
                model.add(d)
    return cells, model


def rule_of(name: str, cells: dict, model: pr.Table, card: str) -> RuleX:
    return RuleX(FS[name], cells.get(card, pr.Table(ALL_SETS)), model)


def simulate(rule, c1: np.ndarray, rng, rounds: int = T) -> np.ndarray:
    s, n = c1.shape
    traj = np.zeros((s, rounds, n))
    traj[:, 0] = c1
    for t in range(2, rounds + 1):
        k = keys_n(traj[:, t - 2], t, rounds)
        code = (((((k[..., 0] * 6 + k[..., 1]) * 2 + k[..., 2]) * 3 + k[..., 3]) * 4 + k[..., 4]) * 4 + k[..., 5]).ravel()
        flat = k.reshape(-1, 6)
        out = np.zeros(code.shape)
        for u in np.unique(code):
            idx = np.flatnonzero(code == u)
            out[idx] = rng.choice(VALS, size=len(idx), p=rule.dist(tuple(int(x) for x in flat[idx[0]])))
        traj[:, t - 1] = out.reshape(s, n)
    return traj


def predict(rule, G: np.ndarray, s: int, seed_parts, sim=simulate) -> dict:
    """Per-group P(collapse at E), mean 2..T and mean trajectory, from each group's observed round 1."""
    n = G.shape[2]
    rng = np.random.default_rng(seed(*seed_parts))
    traj = sim(rule, np.repeat(G[:, 0, :], s, axis=0), rng).reshape(len(G), s, T, n)
    col, mean = pc.outcomes(traj)
    return {"collapse": col.mean(axis=1), "mean": mean.mean(axis=1), "traj": traj.mean(axis=(1, 3))}


# ---------------------------------------------------------------- data

def load_data(models=("gpt", "mistral")) -> dict:
    """{model: {"base": [S1 parts, AB parts], "C": {n: {card: array}}}} (4 minimal cards)."""
    rows, length, _, _ = pa.load_run("configs/main.json", "main_s1_20261014")
    u1 = pa.Units(rows, length)
    rowsA, lengthA, _, _ = pa.load_run("configs/expA_main.json", "expA_main_20261017")
    gA = ax.groups_by_arm(pa.Units(rowsA, lengthA))
    out = {}
    unitsC = {}
    for n, run in RUNS_C.items():
        r, ln, _, _ = pa.load_run(f"configs/expC_n{n}_main.json", run)
        unitsC[n] = pc.UnitsN(r, ln, n)
    for m in models:
        out[m] = {"base": [{c: u1.group_array(m, c) for c in CARDS}, {c: gA[(m, c, "B")] for c in CARDS}],
                  "C": {n: {c: unitsC[n].group_array(m, c) for c in CARDS} for n in RUNS_C
                        if len(unitsC[n].group_array(m, CARDS[0]))}}
    return out


# ---------------------------------------------------------------- D0: leave one size out

def loso(data_m: dict, model: str, held_out, s: int = S_SEL, frozen: dict | None = None) -> dict:
    out = {}
    for h in held_out:
        parts = data_m["base"] + [data_m["C"][n] for n in data_m["C"] if n != h]
        cells, mtab = train(parts)
        test = data_m["C"][h]
        obs_col = pc.pooled_mean([pc.outcomes(test[c])[0] for c in CARDS])
        obs_traj = np.concatenate([test[c].mean(axis=2) for c in CARDS]).mean(axis=0)[1:]
        res = {"observed_collapse": obs_col, "n_groups": int(sum(len(test[c]) for c in CARDS))}
        rules: dict = {name: (lambda c, name=name: rule_of(name, cells, mtab, c)) for name in FS}   # "R3-tümü": R3 state, all data but h
        if frozen is not None:
            rules["R3-donmuş"] = lambda c: pb.rules_for(frozen, model, c, "R3")
        for name, mk in rules.items():
            preds = [predict(mk(c), test[c], s, ("loso", model, h, name, c),
                             sim=(pc.simulate_rule if name == "R3-donmuş" else simulate)) for c in CARDS]
            pcol = pc.pooled_mean([p["collapse"] for p in preds])
            ptraj = np.concatenate([p["traj"] for p in preds]).mean(axis=0)[1:]
            res[name] = {"collapse": pcol, "abs_err": abs(obs_col - pcol),
                         "rmse": float(np.sqrt(np.mean((obs_traj - ptraj) ** 2)))}
        out[str(h)] = res
    return out


def gate(loso_res: dict) -> dict:
    """Choice of R4 and the decision gate (prereg_expD §2)."""
    pairs = [(m, h) for m, d in loso_res.items() for h in d]
    mean_err = {r: float(np.mean([loso_res[m][h][r]["abs_err"] for m, h in pairs])) for r in FS}
    mean_rmse = {r: float(np.mean([loso_res[m][h][r]["rmse"] for m, h in pairs])) for r in FS}
    a, b = mean_err["R4-sayı"], mean_err["R4-pay"]
    if abs(a - b) >= 0.01:
        chosen = "R4-sayı" if a < b else "R4-pay"
    else:
        chosen = "R4-sayı" if mean_rmse["R4-sayı"] <= mean_rmse["R4-pay"] else "R4-pay"
    gpt_wins = sum(loso_res["gpt"][h][chosen]["abs_err"] < loso_res["gpt"][h]["R3-tümü"]["abs_err"] for h in loso_res["gpt"])
    passed = mean_err[chosen] <= mean_err["R3-tümü"] - GATE_MARGIN and gpt_wins >= 2
    return {"mean_abs_err": mean_err, "mean_rmse": mean_rmse, "chosen": chosen,
            "gpt_wins_vs_R3_all": int(gpt_wins), "margin": GATE_MARGIN, "passed": bool(passed)}


# ---------------------------------------------------------------- freeze and forecast

def _tables_json(tab: pr.Table) -> dict:
    return {",".join(map(str, fs)): {",".join(map(str, k)): [int(x) for x in v]
                                      for k, v in tab.counts[fs].items() if v.sum() > 0} for fs in tab.sets}


def _table_from_json(d: dict, total) -> pr.Table:
    tab = pr.Table(ALL_SETS)
    for fs_s, kv in d.items():
        fs = tuple(int(x) for x in fs_s.split(","))
        for k_s, v in kv.items():
            tab.counts[fs][tuple(int(x) for x in k_s.split(","))] = np.array(v, dtype=float)
    tab.total = np.array(total, dtype=float)
    return tab


def build_frozen(data_m: dict, chosen: str, sources: dict) -> dict:
    cells, mtab = train(data_m["base"] + list(data_m["C"].values()))
    return {"model": MODEL_D, "chosen_R4": chosen, "feature_sets": {k: [list(x) for x in v] for k, v in FS.items()},
            "sources": sources, "model_table": _tables_json(mtab), "model_total": [int(x) for x in mtab.total],
            "cells": {c: {"tables": _tables_json(t), "total": [int(x) for x in t.total]} for c, t in cells.items()}}


def frozen_rule(fz: dict, name: str, card: str) -> RuleX:
    cell = fz["cells"][card]
    return RuleX(FS[name], _table_from_json(cell["tables"], cell["total"]),
                 _table_from_json(fz["model_table"], fz["model_total"]))


def forecast(fz: dict, frozen_b: dict, data_m: dict, n: int = N_NEW, s: int = S_FC) -> dict:
    out = {"cards": {}}
    for c in CARDS:
        pool = np.concatenate([data_m["C"][k][c][:, 0, :].ravel() for k in data_m["C"]])
        rng = np.random.default_rng(seed("forecast", c, n))
        c1 = rng.choice(pool, size=(s, n))
        row = {}
        for name, traj in (("R4", simulate(frozen_rule(fz, fz["chosen_R4"], c), c1, rng)),
                           ("R3-tümü", simulate(frozen_rule(fz, "R3-tümü", c), c1, rng)),
                           ("R3-donmuş", pc.simulate_rule(pb.rules_for(frozen_b, MODEL_D, c, "R3"), c1, rng)),
                           ("R0", pc.simulate_r0(frozen_b["models"][MODEL_D]["cells"][c]["iso_f"], c1))):
            col, mean = pc.outcomes(traj)
            row[name] = {"collapse_r8": float(col.mean()), "mean_2_10": float(mean.mean()),
                         "trajectory": [float(x) for x in traj.mean(axis=(0, 2))]}
        out["cards"][c] = row
    out["mean_over_cards"] = {name: {q: float(np.mean([out["cards"][c][name][q] for c in CARDS]))
                                     for q in ("collapse_r8", "mean_2_10")} for name in ("R4", "R3-tümü", "R3-donmuş", "R0")}
    return out


# ---------------------------------------------------------------- analysis (D2)

def label_improve(t: dict) -> str:
    lo, hi = t["ci"]
    return "R4 daha iyi" if lo > 0 else "R3-tümü daha iyi" if hi < 0 else "ayırt edilemedi"


def analyse(fz: dict, frozen_b: dict, arrays: dict, s: int = S_COND, n_boot: int = N_BOOT) -> dict:
    """arrays {card: (G, T, 64)} of the D2 run."""
    preds = {name: {} for name in ("R4", "R3-tümü", "R3-donmuş")}
    for c in CARDS:
        G = arrays[c]
        preds["R4"][c] = predict(frozen_rule(fz, fz["chosen_R4"], c), G, s, ("cond", "R4", c))
        preds["R3-tümü"][c] = predict(frozen_rule(fz, "R3-tümü", c), G, s, ("cond", "R3-tümü", c))
        preds["R3-donmuş"][c] = predict(pb.rules_for(frozen_b, MODEL_D, c, "R3"), G, s, ("cond", "R3-donmuş", c),
                                        sim=pc.simulate_rule)
    r0 = {c: pc.outcomes(pc.simulate_r0(frozen_b["models"][MODEL_D]["cells"][c]["iso_f"], arrays[c][:, 0, :]))
          for c in CARDS}
    obs = {c: pc.outcomes(arrays[c]) for c in CARDS}
    out = {"n_groups": int(sum(len(arrays[c]) for c in CARDS)),
           "observed": {"collapse": pc.pooled_mean([obs[c][0] for c in CARDS]),
                        "mean": pc.pooled_mean([obs[c][1] for c in CARDS])},
           "predicted": {name: {"collapse": pc.pooled_mean([preds[name][c]["collapse"] for c in CARDS]),
                                "mean": pc.pooled_mean([preds[name][c]["mean"] for c in CARDS])} for name in preds}}
    out["predicted"]["R0"] = {"collapse": pc.pooled_mean([r0[c][0] for c in CARDS]),
                              "mean": pc.pooled_mean([r0[c][1] for c in CARDS])}
    # D-H1 (a) collapse share, (b) mean contribution
    rng = np.random.default_rng(seed("D_H1a"))
    d = [obs[c][0] - preds["R4"][c]["collapse"] for c in CARDS]
    h1a = {"est": pc.pooled_mean(d), "ci": pa.ci(pc.strat_boot(d, rng, n_boot))}
    h1a["label"] = pc.label_share(h1a)
    h1b = pb.pooled([obs[c][1] - preds["R4"][c]["mean"] for c in CARDS], ("expD", "D_H1b"), n_boot)
    h1b["label"] = pb.label_h1(h1b)
    out["D_H1"] = {"a_collapse": h1a, "b_mean": h1b}
    # D-H2 and the secondary mean comparison: |obs - R3-all| - |obs - R4| with groups resampled in cards
    for q, key in (("collapse", "D_H2"), ("mean", "secondary_mean")):
        idx = {c: len(arrays[c]) for c in CARDS}
        rng = np.random.default_rng(seed(key))
        draws = np.zeros(n_boot)
        o_all = {c: (obs[c][0] if q == "collapse" else obs[c][1]) for c in CARDS}
        for b in range(n_boot):
            pick = {c: rng.integers(0, idx[c], idx[c]) for c in CARDS}
            o = np.concatenate([o_all[c][pick[c]] for c in CARDS]).mean()
            r3 = np.concatenate([preds["R3-tümü"][c][q][pick[c]] for c in CARDS]).mean()
            r4 = np.concatenate([preds["R4"][c][q][pick[c]] for c in CARDS]).mean()
            draws[b] = abs(o - r3) - abs(o - r4)
        o = out["observed"][q]
        est = abs(o - out["predicted"]["R3-tümü"][q]) - abs(o - out["predicted"]["R4"][q])
        t = {"est": float(est), "ci": pa.ci(draws)}
        t["label"] = label_improve(t)
        out[key] = t
    out["mechanism"] = px.t2_t3(frozen_b, MODEL_D, arrays, N_NEW)
    return out


# ---------------------------------------------------------------- CLI

def _sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _write(path, obj) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1, default=pa._json_default) + "\n")
    return _sha(p)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("select").add_argument("--out", default=str(pa.ROOT / "results" / "expD_select.json"))
    fr = sub.add_parser("freeze")
    fr.add_argument("--select", default=str(pa.ROOT / "results" / "expD_select.json"))
    fr.add_argument("--select-sha256", required=True)
    an = sub.add_parser("analyse")
    an.add_argument("--run", required=True)
    an.add_argument("--rules-sha256", required=True)
    an.add_argument("--forecast-sha256", required=True)
    an.add_argument("--allow-incomplete", action="store_true")
    args = ap.parse_args(argv)
    frozen_b = pb.load_frozen(pa.ROOT / "data/expB/frozen_rules_v1.json", pc.FROZEN_SHA)
    if args.cmd == "select":
        data = load_data()
        res = {m: loso(data[m], m, HELD_OUT[m], frozen=frozen_b) for m in HELD_OUT}
        out = {"status": "D0 (prereg_expD §2)", "loso": res, "gate": gate(res), "sims": S_SEL}
        print(f"yazıldı: {args.out} sha256 {_write(args.out, out)}")
        print(json.dumps(out["gate"], ensure_ascii=False))
        return 0
    if args.cmd == "freeze":
        if _sha(args.select) != args.select_sha256:
            print("DUR: seçim dosyası kilitli sha256 ile aynı değil.", file=sys.stderr)
            return 2
        sel = json.loads(Path(args.select).read_text())
        if not sel["gate"]["passed"]:
            print("DUR: karar kapısı geçilmedi; plan gereği dondurma ve D2 yok.", file=sys.stderr)
            return 2
        data = load_data(models=(MODEL_D,))
        sources = {f"expC_n{n}": run for n, run in RUNS_C.items()}
        sources.update({"stage1": "main_s1_20261014", "expA": "expA_main_20261017", "select_sha256": args.select_sha256})
        fz = build_frozen(data[MODEL_D], sel["gate"]["chosen"], sources)
        sha_r = _write(pa.ROOT / "data/expD/rules_v1.json", fz)
        fc = {"rules_sha256": sha_r, "n": N_NEW, "sims": S_FC, "forecast": forecast(fz, frozen_b, data[MODEL_D])}
        sha_f = _write(pa.ROOT / "data/expD/forecast_v1.json", fc)
        print(f"kurallar data/expD/rules_v1.json sha256 {sha_r}\ntahmin data/expD/forecast_v1.json sha256 {sha_f}")
        print(json.dumps(fc["forecast"]["mean_over_cards"], ensure_ascii=False))
        return 0
    if _sha(pa.ROOT / "data/expD/rules_v1.json") != args.rules_sha256 or _sha(pa.ROOT / "data/expD/forecast_v1.json") != args.forecast_sha256:
        print("DUR: dondurulmuş D dosyaları kilitli sha256 ile aynı değil.", file=sys.stderr)
        return 2
    fz = json.loads((pa.ROOT / "data/expD/rules_v1.json").read_text())
    rows, length, _, meta = pa.load_run(f"configs/expD_n{N_NEW}_main.json", args.run)
    units = pc.UnitsN(rows, length, N_NEW)
    if len(units.groups) < meta["planned_units"] and not args.allow_incomplete:
        print(f"DUR: koşu tamamlanmamış ({len(units.groups)}/{meta['planned_units']}).", file=sys.stderr)
        return 2
    res = analyse(fz, frozen_b, {c: units.group_array(MODEL_D, c) for c in CARDS})
    res["meta"] = {"run": args.run, "rules_sha256": args.rules_sha256, "forecast_sha256": args.forecast_sha256,
                   "n_rows": len(rows), "planned_units": meta["planned_units"]}
    out = pa.ROOT / "results" / f"{args.run}_analysis.json"
    print(f"yazıldı: {out} sha256 {_write(out, res)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
