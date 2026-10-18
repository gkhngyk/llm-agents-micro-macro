"""Experiment B: a frozen in-game rule predicts a 15-round game (prereg/prereg_expB.md).

Three subcommands, all read-only on run directories, no API calls:
  freeze    learn the rule tables from stage 1 (all groups) and write them, with the
            isolated responses (R0) and the observed round-1 vectors, to a JSON file
            whose sha256 goes into the prereg before any paid call.
  forecast  unconditional forecast (prereg_expB §2.1): round 1 drawn from stage-1
            groups of the same cell, rounds 1..T simulated with R3-kalan and R3-mutlak.
  analyse   B-H1 (R3-kalan, rounds 2..T), B-H2 (R3-kalan vs R3-mutlak, rounds 9..13),
            B-H3 (trajectory RMSE of every variant), sensitivity; refuses an
            incomplete run and a frozen file with another sha256.

Variants: R3-kalan (round bin by rounds to go: t <= T-2 -> 0, T-1 -> 1, T -> 2),
R3-mutlak (round bin by the absolute round number as in training: t <= 8 -> 0, 9 -> 1,
t >= 10 -> 2), R1 (no round information), R0 (isolated response, deterministic).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

import pgg_analysis as pa
import pgg_analysis_rules as pr

N = 4
FEATURE_SETS = [(0, 1, 2, 3), (0, 1, 2), (0, 1), (1,)]
CARDS_MAIN = tuple(pa.card_id(c, s) for s in ("minimal", "value") for c in pa.CITIES)
VARIANTS = ("R3-kalan", "R3-mutlak", "R1", "R0")
SIM_NS = "pgg-expB-sim"
BOOT_NS = "pgg-expB-analysis"
THRESHOLD = 2.0
TIGHT = 1.0
ALPHA = 0.05


def bin_kalan(t: int, T: int) -> int:
    return 0 if t <= T - 2 else 1 if t == T - 1 else 2


def bin_mutlak(t: int, T: int) -> int:
    return 0 if t <= 8 else 1 if t == 9 else 2


BIN = {"R3-kalan": bin_kalan, "R3-mutlak": bin_mutlak}


# ---------------------------------------------------------------- freeze

def _tables_json(tab: pr.Table) -> dict:
    return {",".join(map(str, fs)): {",".join(map(str, k)): [int(x) for x in v]
                                      for k, v in tab.counts[fs].items() if v.sum() > 0}
            for fs in tab.sets}


def build_frozen(groups: dict, iso: dict, source: dict) -> dict:
    """groups {(model, card): (G,10,4)} from stage 1; iso {(model, card): {x: array}}."""
    out = {"source": source, "rounds_train": 10, "feature_sets": [list(f) for f in FEATURE_SETS],
           "bins": {"own": "0, 1-9, 10, 11-19, 20", "mean": "0, (0,5), [5,10), 10, (10,15), [15,20]",
                    "zero": "one of the others gave 0", "round": "0: t<=8, 1: t=9, 2: t=10 (training)"},
           "models": {}}
    for m in sorted({k[0] for k in groups}):
        model_tab = pr.Table(FEATURE_SETS)
        cells = {}
        for (mm, c), G in sorted(groups.items()):
            if mm != m:
                continue
            tab = pr.Table(FEATURE_SETS)
            for g in G:
                d = pr.decisions(g)
                tab.add(d)
                model_tab.add(d)
            cells[c] = {"tables": _tables_json(tab), "total": [int(x) for x in tab.total],
                        "iso_f": [float(iso[(m, c)][x].mean()) for x in pa.POINTS],
                        "round1": [[int(v) for v in g[0]] for g in G], "n_groups": int(len(G))}
        out["models"][m] = {"model_tables": _tables_json(model_tab),
                            "model_total": [int(x) for x in model_tab.total], "cells": cells}
    return out


def _table_from_json(tables: dict, total) -> pr.Table:
    tab = pr.Table(FEATURE_SETS)
    for fs_s, d in tables.items():
        fs = tuple(int(x) for x in fs_s.split(","))
        for k_s, v in d.items():
            tab.counts[fs][tuple(int(x) for x in k_s.split(","))] = np.array(v, dtype=float)
    tab.total = np.array(total, dtype=float)
    return tab


def load_frozen(path, sha256: str | None) -> dict:
    data = Path(path).read_bytes()
    got = hashlib.sha256(data).hexdigest()
    if sha256 is not None and got != sha256:
        raise ValueError(f"frozen rules file {path}: sha256 {got} is not the locked {sha256}")
    return json.loads(data)


def rules_for(frozen: dict, model: str, card: str, rule: str) -> pr.Rule:
    m = frozen["models"][model]
    cell = m["cells"][card]
    return pr.Rule(rule, _table_from_json(cell["tables"], cell["total"]),
                   _table_from_json(m["model_tables"], m["model_total"]))


# ---------------------------------------------------------------- simulation

def states_rb(prev: np.ndarray, rb: int) -> list[tuple]:
    """pr.states_vec with the round bin given (it depends on the variant's mapping)."""
    keys = pr.states_vec(prev, 2)                  # round 2 -> bin 0; replace the bin
    return [(a, b, c, rb) for a, b, c, _ in keys]


def simulate_T(rule: pr.Rule, c1: np.ndarray, rng, s: int, T: int, binfn) -> np.ndarray:
    """(s, T, 4) stochastic trajectories from round 1 c1 ((4,) or (s, 4))."""
    traj = np.zeros((s, T, N))
    traj[:, 0, :] = c1
    vals = np.arange(21)
    for t in range(2, T + 1):
        rb = binfn(t, T) if binfn is not None else 0
        keys = states_rb(traj[:, t - 2, :], rb)
        slots = {}
        for idx, key in enumerate(keys):
            slots.setdefault(key, []).append(idx)
        flat = np.zeros(s * N)
        for key, idx in slots.items():
            flat[idx] = rng.choice(vals, size=len(idx), p=rule.dist(key))
        traj[:, t - 1, :] = flat.reshape(s, N)
    return traj


def simulate_R0(f: np.ndarray, c1: np.ndarray, T: int) -> np.ndarray:
    """Deterministic isolated-response simulation for T rounds (H4, generalised)."""
    xs = np.array(pa.POINTS, dtype=float)
    c = np.asarray(c1, dtype=float)
    traj = [c]
    for _ in range(2, T + 1):
        others = (c.sum(axis=-1, keepdims=True) - c) / (N - 1)
        c = pa._interp(others, xs, np.broadcast_to(f, c.shape[:-1] + (5,)))
        traj.append(c)
    return np.stack(traj, axis=-2)


def simulate_variant(frozen, model, card, variant, c1, T, s, seed_parts) -> np.ndarray:
    """(s, T, 4) for a variant; R0 is deterministic (s identical copies)."""
    if variant == "R0":
        f = np.array(frozen["models"][model]["cells"][card]["iso_f"])
        one = simulate_R0(f, np.asarray(c1, dtype=float), T)
        return np.broadcast_to(one, (s, T, N)) if one.ndim == 2 else one
    rule = rules_for(frozen, model, card, "R1" if variant == "R1" else "R3")
    rng = np.random.default_rng(pa.stable_seed(SIM_NS, *seed_parts))
    return simulate_T(rule, c1, rng, s, T, BIN.get(variant))


# ---------------------------------------------------------------- forecast

def forecast(frozen: dict, models, cards, T: int = 15, s: int = 2000) -> dict:
    """Unconditional mean trajectory per model x card x variant (R3-kalan, R3-mutlak)."""
    out = {}
    for m in models:
        out[m] = {}
        for c in cards:
            r1 = np.array(frozen["models"][m]["cells"][c]["round1"], dtype=float)
            rng = np.random.default_rng(pa.stable_seed(SIM_NS, "forecast-start", m, c))
            starts = r1[rng.integers(0, len(r1), s)]
            out[m][c] = {}
            for v in ("R3-kalan", "R3-mutlak"):
                sim = simulate_variant(frozen, m, c, v, starts, T, s, ("forecast", m, c, v))
                out[m][c][v] = [float(x) for x in sim.mean(axis=(0, 2))]
    return out


# ---------------------------------------------------------------- analysis

def window(x: np.ndarray, a: int, b: int) -> np.ndarray:
    return x[..., a - 1:b, :].mean(axis=(-1, -2))


def simulate_groups(frozen, model, card, groups: np.ndarray, T: int, s: int) -> dict:
    """{variant: (G, T) mean simulated trajectory per group} from each group's round 1."""
    out = {}
    for v in VARIANTS:
        rows = []
        for g in range(len(groups)):
            sim = simulate_variant(frozen, model, card, v, groups[g, 0, :], T, s, (model, card, v, g))
            rows.append(sim.mean(axis=(0, 2)))
        out[v] = np.array(rows)
    return out


def pooled(diffs_by_card: list, seed_parts, n_boot: int) -> dict:
    """Mean over cards of the mean group difference; card-stratified group bootstrap."""
    diffs_by_card = [d for d in diffs_by_card if len(d)]
    if not diffs_by_card:
        return {"est": None}
    rng = np.random.default_rng(pa.stable_seed(BOOT_NS, *seed_parts))
    est = float(np.mean([d.mean() for d in diffs_by_card]))
    draws = np.mean([d[rng.integers(0, len(d), (n_boot, len(d)))].mean(1) for d in diffs_by_card], axis=0)
    return {"est": est, "ci": pa.ci(draws), "p": pa.boot_p(draws), "n_cards": len(diffs_by_card)}


def inside(t: dict, b: float) -> bool:
    return t.get("est") is not None and -b <= t["ci"][0] and t["ci"][1] <= b


def label_h1(t: dict) -> str:
    if t.get("est") is None:
        return "belirlenemedi"
    if inside(t, THRESHOLD):
        return "tahmin tuttu" + (" (sıkı eşdeğerlik)" if inside(t, TIGHT) else "")
    if t["est"] < -THRESHOLD and t["p"] < ALPHA:
        return "tahmin sapıyor: gerçek daha düşük"
    if t["est"] > THRESHOLD and t["p"] < ALPHA:
        return "tahmin sapıyor: gerçek daha yüksek"
    return "belirsiz"


def label_h2(kalan: dict, mutlak: dict) -> str:
    if kalan.get("est") is None or mutlak.get("est") is None:
        return "belirlenemedi"
    if inside(kalan, THRESHOLD) and mutlak["est"] > THRESHOLD and mutlak["p"] < ALPHA:
        return "açıklanan ufku izliyor"
    if inside(mutlak, THRESHOLD) and kalan["est"] < -THRESHOLD and kalan["p"] < ALPHA:
        return "mutlak tur numarasına bağlı"
    return "ayırt edilemedi"


def rmse_boot(obs: dict, sims: dict, cards, T: int, seed_parts, n_boot: int) -> dict:
    """Model RMSE (rounds 2..T) of the cell-averaged mean trajectory, per variant, with
    the bootstrap CI of each variant's RMSE minus R3-kalan's (groups resampled in cells)."""
    rng = np.random.default_rng(pa.stable_seed(BOOT_NS, *seed_parts))
    point = {}
    boots = {v: np.zeros(n_boot) for v in VARIANTS}
    idx = {c: rng.integers(0, len(obs[c]), (n_boot, len(obs[c]))) for c in cards}
    for v in VARIANTS:
        o = np.mean([obs[c].mean(axis=2).mean(axis=0) for c in cards], axis=0)[1:]
        sm = np.mean([sims[c][v].mean(axis=0) for c in cards], axis=0)[1:]
        point[v] = float(np.sqrt(np.mean((o - sm) ** 2)))
        ob = np.mean([obs[c].mean(axis=2)[idx[c]].mean(axis=1) for c in cards], axis=0)[:, 1:]
        sb = np.mean([sims[c][v][idx[c]].mean(axis=1) for c in cards], axis=0)[:, 1:]
        boots[v] = np.sqrt(np.mean((ob - sb) ** 2, axis=1))
    diffs = {v: {"diff_vs_R3_kalan": float(point[v] - point["R3-kalan"]),
                 "ci": pa.ci(boots[v] - boots["R3-kalan"])} for v in VARIANTS if v != "R3-kalan"}
    return {"rmse": point, "vs_R3_kalan": diffs}


def analyse(frozen: dict, units: pa.Units, models, cards, T: int, s: int, n_boot: int,
            forecast_table: dict | None = None) -> dict:
    out = {"B_H1": {}, "B_H2": {}, "B_H3": {}, "cells": {}, "forecast_rmse": {}}
    for m in models:
        obs = {c: units.group_array(m, c) for c in cards}
        obs = {c: g for c, g in obs.items() if len(g)}
        cs = [c for c in cards if c in obs]
        sims = {c: simulate_groups(frozen, m, c, obs[c], T, s) for c in cs}
        def diffs(v, a, b):
            return [window(obs[c], a, b) - sims[c][v][:, a - 1:b].mean(axis=1) for c in cs]
        h1 = pooled(diffs("R3-kalan", 2, T), ("B_H1", m), n_boot)
        h1["label"] = label_h1(h1)
        out["B_H1"][m] = h1
        k = pooled(diffs("R3-kalan", 9, 13), ("B_H2", m, "kalan"), n_boot)
        mu = pooled(diffs("R3-mutlak", 9, 13), ("B_H2", m, "mutlak"), n_boot)
        out["B_H2"][m] = {"R3-kalan": k, "R3-mutlak": mu, "label": label_h2(k, mu)}
        out["B_H3"][m] = rmse_boot(obs, sims, cs, T, ("B_H3", m), n_boot)
        fam = {}
        for c, d in zip(cs, diffs("R3-kalan", 2, T)):
            fam[c] = pr.cell_test(d, ("expB-cell", m, c), n_boot)
        out["cells"][m] = pr.finish_family(fam)
        out["cells"][m]["trajectories"] = {c: {"observed": [float(x) for x in obs[c].mean(axis=(0, 2))],
                                              **{v: [float(x) for x in sims[c][v].mean(axis=0)] for v in VARIANTS}}
                                          for c in cs}
        if forecast_table:
            o = np.mean([obs[c].mean(axis=(0, 2)) for c in cs], axis=0)[1:]
            out["forecast_rmse"][m] = {v: float(np.sqrt(np.mean((o - np.mean(
                [forecast_table[m][c][v] for c in cs], axis=0)[1:]) ** 2))) for v in ("R3-kalan", "R3-mutlak")}
    return out


def run_analysis(frozen, rows, length_calls, models, cards, T, s, n_boot, forecast_table=None) -> dict:
    units = UnitsT(rows, length_calls, T)
    res: dict = {"main": analyse(frozen, units, models, cards, T, s, n_boot, forecast_table), "sensitivity": {}}
    for v in ("comp_full", "no_capped", "no_reused"):
        sub = units.subset(v)
        a = analyse(frozen, sub, models, cards, T, s, n_boot)
        res["sensitivity"][v] = {
            "excluded_groups": len(units.groups) - len(sub.groups),
            "labels": {m: {"B_H1": a["B_H1"][m]["label"], "B_H2": a["B_H2"][m]["label"]} for m in models},
            "changed": [(h, m) for m in models for h in ("B_H1", "B_H2")
                        if a[h][m]["label"] != res["main"][h][m]["label"]]}
    res["n_groups"] = len(units.groups)
    return res


class UnitsT(pa.Units):
    """pa.Units for a T-round game (pa.Units assumes 10 rounds)."""

    def __init__(self, rows, length_calls=None, T: int = 15):
        import collections
        length_calls = length_calls or set()
        g_rows = collections.defaultdict(list)
        for r in rows:
            if r.get("arm") == "group":
                g_rows[r["unit"]].append(r)
        self.T = T
        self.groups, self.schedules, self.incomplete = {}, {}, []
        for unit, rs in g_rows.items():
            con = {(r["round"], r["agent_id"]): r for r in rs if r["step"] == "contribute"}
            comp = [r for r in rs if r["step"] == "comprehension"]
            if len(con) != T * N:
                self.incomplete.append(unit)
                continue
            c = np.array([[con[(t, a)]["contribution"] for a in range(1, N + 1)] for t in range(1, T + 1)], float)
            sess = rs[0]["session_id"]
            self.groups[unit] = {
                "model": rs[0]["model_key"], "card": rs[0]["card_id"], "c": c,
                "capped": any(r.get("reasoning_capped") for r in rs),
                "length": any(k[0] == sess for k in length_calls),
                "reused": any(r.get("reused") for r in rs),
                "comp_full": len(comp) == N and all(not r.get("comp_missing") and r.get("comp_q1_correct")
                                                    and r.get("comp_q2_correct") for r in comp)}

    def group_array(self, model: str, card: str) -> np.ndarray:
        gs = [g["c"] for g in self.groups.values() if g["model"] == model and g["card"] == card]
        return np.stack(gs) if gs else np.zeros((0, self.T, N))


# ---------------------------------------------------------------- CLI

def _stage1(args):
    rows, length, _, _ = pa.load_run(args.stage1_config, args.stage1_run)
    u = pa.Units(rows, length)
    groups, iso = {}, {}
    for m in pa.MODELS:
        for city in pa.CITIES:
            for style in pa.STYLES:
                c = pa.card_id(city, style)
                groups[(m, c)], iso[(m, c)] = u.group_array(m, c), u.iso_points(m, c)
    return groups, iso


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--stage1-config", default="configs/main.json")
    f.add_argument("--stage1-run", default="main_s1_20261014")
    f.add_argument("--out", default="data/expB/frozen_rules_v1.json")
    fc = sub.add_parser("forecast")
    fc.add_argument("--frozen", default="data/expB/frozen_rules_v1.json")
    fc.add_argument("--sha256", required=True)
    fc.add_argument("--out", default="data/expB/forecast_v1.json")
    fc.add_argument("--sims", type=int, default=2000)
    an = sub.add_parser("analyse")
    an.add_argument("--config", required=True)
    an.add_argument("--run", required=True)
    an.add_argument("--frozen", default="data/expB/frozen_rules_v1.json")
    an.add_argument("--sha256", required=True)
    an.add_argument("--forecast", default="data/expB/forecast_v1.json")
    an.add_argument("--out")
    an.add_argument("--sims", type=int, default=200)
    an.add_argument("--n-boot", type=int, default=10_000)
    an.add_argument("--rounds", type=int, default=15)
    an.add_argument("--allow-incomplete", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "freeze":
        groups, iso = _stage1(args)
        res_path = Path(pa.load_run(args.stage1_config, args.stage1_run)[3]["out_dir"]) / f"{args.stage1_run}.jsonl"
        source = {"run": args.stage1_run, "results_sha256": hashlib.sha256(res_path.read_bytes()).hexdigest()}
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(build_frozen(groups, iso, source), sort_keys=True, separators=(",", ":")) + "\n")
        print(f"yazıldı: {out} sha256 {hashlib.sha256(out.read_bytes()).hexdigest()}")
        return 0
    if args.cmd == "forecast":
        frozen = load_frozen(args.frozen, args.sha256)
        fc_ = forecast(frozen, pa.MODELS, CARDS_MAIN, 15, args.sims)
        out = Path(args.out)
        out.write_text(json.dumps({"frozen_sha256": args.sha256, "T": 15, "sims": args.sims, "forecast": fc_},
                                  sort_keys=True, indent=1) + "\n")
        print(f"yazıldı: {out} sha256 {hashlib.sha256(out.read_bytes()).hexdigest()}")
        return 0
    frozen = load_frozen(args.frozen, args.sha256)
    rows, length, planned, meta = pa.load_run(args.config, args.run)
    units = UnitsT(rows, length, args.rounds)
    if len(units.groups) < meta["planned_units"] and not args.allow_incomplete:
        print(f"DUR: koşu tamamlanmamış ({len(units.groups)}/{meta['planned_units']} grup). "
              "Ara analiz planda yok.", file=sys.stderr)
        return 2
    models = tuple(m for m in pa.MODELS if m in planned)
    cards = tuple(sorted({g["card"] for g in units.groups.values()}, key=lambda c: (c.split("_")[1], c)))
    fct = json.loads(Path(args.forecast).read_text())["forecast"] if Path(args.forecast).exists() else None
    res = run_analysis(frozen, rows, length, models, cards, args.rounds, args.sims, args.n_boot, fct)
    res["meta"] = {**meta, "run": args.run, "frozen_sha256": args.sha256, "n_rows": len(rows),
                   "sims": args.sims, "n_boot": args.n_boot, "allow_incomplete": args.allow_incomplete}
    out = Path(args.out) if args.out else pa.ROOT / "results" / f"{args.run}_analysis.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=pa._json_default))
    print(f"yazıldı: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
