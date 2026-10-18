"""Exploratory: micro rules learned from group data (prereg/prereg_main.md amendment F.14).

NOT pre-registered: written after H4, F.12, F.13 and experiment A were seen. It
changes no main label. Question: does the H4 gap (groups below the simulation
from the isolated rule) close when the rule is learned from group decisions?

Rules (per model x card cell; empirical conditional distributions; stochastic
simulation: in every round every agent draws one of the real decisions taken
in the same state in the training data, so the 0 / 10 / 20 discreteness stays):
  R0  H4 itself: isolated f, linear interpolation, deterministic.
  R1  state = (own previous contribution bin, others' previous mean bin)
  R2  R1 + "one of the others gave 0 in the previous round"
  R3  R2 + round bin (2-8, 9, 10)
Back-off when a state is unseen: cell full state -> model (all cards) full
state -> cell, finest feature dropped -> model, same -> ... -> cell, all decisions.

Evaluation 1: stage 1, leave-one-group-out within each cell; the held-out group
starts from its observed round 1 and is simulated S = 200 times.
Evaluation 2: rules from all stage-1 minimal-card groups; experiment A arm B
groups (same prompt, new run) simulated from their observed round 1.
Delta = mean over the cell's groups of (observed - simulated) mean contribution
in the window (rounds 2-10 primary, 2-8); labels as H4 (|Delta| > 2 and
bootstrap p < 0.05, Holm over the model's cells).

Run (read-only, no API calls):
  python pgg_analysis_rules.py [--out results/rules_analysis.json]
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np

import pgg_analysis as pa
import pgg_analysis_expA as ax

SEED_NS = "pgg-main-s1-rules"
RULES = ("R1", "R2", "R3")
# full state = (own_bin, mean_bin, zero, round_bin); the features each rule uses, finest last
RULE_FEATURES = {"R1": (0, 1), "R2": (0, 1, 2), "R3": (0, 1, 2, 3)}
WINDOWS = ((2, 10), (2, 8))
S_SIMS = 200
N_BOOT = 10_000
ROUNDS, N = 10, 4


def seed(*parts) -> int:
    return pa.stable_seed(SEED_NS, *parts)


def own_bin(c: float) -> int:
    return 0 if c == 0 else 1 if c < 10 else 2 if c == 10 else 3 if c < 20 else 4


def mean_bin(m: float) -> int:
    if abs(m) < 1e-9:
        return 0
    if m < 5:
        return 1
    if m < 10 - 1e-9:
        return 2
    if abs(m - 10) < 1e-9:
        return 3
    if m < 15:
        return 4
    return 5


def round_bin(t: int) -> int:
    """t is the round being decided (1-based)."""
    return 0 if t <= 8 else 1 if t == 9 else 2


def state(prev: np.ndarray, i: int, t: int) -> tuple:
    """Full state of agent i deciding round t, from the previous round's contributions."""
    others = np.delete(prev, i)
    return (own_bin(prev[i]), mean_bin(others.mean()), int(others.min() == 0), round_bin(t))


def decisions(group: np.ndarray) -> list[tuple[tuple, int]]:
    """(full state, contribution) for rounds 2..10 of one group (G x 10 x 4 slice: 10 x 4)."""
    out = []
    for t in range(2, ROUNDS + 1):
        for i in range(N):
            out.append((state(group[t - 2], i, t), int(round(group[t - 1, i]))))
    return out


def project(key: tuple, feats: tuple) -> tuple:
    return tuple(key[f] for f in feats)


class Table:
    """Outcome counts (21 values) per projected state, for several feature subsets."""

    def __init__(self, feature_sets):
        self.sets = list(feature_sets)
        self.counts = {fs: collections.defaultdict(lambda: np.zeros(21)) for fs in self.sets}
        self.total = np.zeros(21)

    def add(self, decs, sign: int = 1) -> None:
        for key, y in decs:
            for fs in self.sets:
                self.counts[fs][project(key, fs)][y] += sign
            self.total[y] += sign


def backoff_order(rule: str) -> list[tuple]:
    feats = RULE_FEATURES[rule]
    order = []
    for k in range(len(feats), 0, -1):
        order.append(feats[:k] if k > 1 else (1,))     # last resort before "all": mean bin only
    out = []
    for fs in dict.fromkeys(order):
        out.append(fs)
    return out


class Rule:
    """Sampling distribution for a rule from a cell table and a model table, with back-off."""

    def __init__(self, rule: str, cell: Table, model: Table):
        self.rule, self.cell, self.model = rule, cell, model
        self.order = backoff_order(rule)
        self.used = collections.Counter()
        self._cache = {}

    def dist(self, key: tuple) -> np.ndarray:
        if key in self._cache:
            return self._cache[key]
        for depth, fs in enumerate(self.order):
            for lvl, tab in (("cell", self.cell), ("model", self.model)):
                c = tab.counts[fs].get(project(key, fs))
                if c is not None and c.sum() > 0:
                    self.used[(depth, lvl)] += 1
                    self._cache[key] = c / c.sum()
                    return self._cache[key]
        self.used[("all", "cell")] += 1
        self._cache[key] = self.cell.total / self.cell.total.sum()
        return self._cache[key]


def states_vec(prev: np.ndarray, t: int) -> list[tuple]:
    """state() for every agent of every simulation at once: prev (s, 4) -> s*4 tuples (row-major)."""
    own = np.select([prev == 0, prev < 10, prev == 10, prev < 20], [0, 1, 2, 3], 4)
    m = (prev.sum(axis=1, keepdims=True) - prev) / (N - 1)
    mb = np.select([np.abs(m) < 1e-9, m < 5, m < 10 - 1e-9, np.abs(m - 10) < 1e-9, m < 15],
                   [0, 1, 2, 3, 4], 5)
    zeros = (prev == 0)
    zero_others = (zeros.sum(axis=1, keepdims=True) - zeros) > 0
    rb = round_bin(t)
    return [(int(a), int(b), int(c), rb) for a, b, c in
            zip(own.ravel(), mb.ravel(), zero_others.astype(int).ravel())]


def simulate_group(rule: Rule, c1: np.ndarray, rng, s: int = S_SIMS) -> np.ndarray:
    """(s, 10, 4) simulated contributions from observed round 1."""
    traj = np.zeros((s, ROUNDS, N))
    traj[:, 0, :] = c1
    vals = np.arange(21)
    for t in range(2, ROUNDS + 1):
        keys = states_vec(traj[:, t - 2, :], t)
        slots = collections.defaultdict(list)
        for idx, key in enumerate(keys):
            slots[key].append(idx)
        flat = np.zeros(s * N)
        for key, idx in slots.items():
            flat[idx] = rng.choice(vals, size=len(idx), p=rule.dist(key))
        traj[:, t - 1, :] = flat.reshape(s, N)
    return traj


def window_mean(x: np.ndarray, w: tuple) -> np.ndarray:
    a, b = w
    return x[..., a - 1:b, :].mean(axis=(-1, -2))


def cell_test(diffs: np.ndarray, seed_parts, n_boot: int) -> dict:
    if len(diffs) == 0:
        return {"est": None}
    rng = np.random.default_rng(seed(*seed_parts))
    draws = diffs[rng.integers(0, len(diffs), (n_boot, len(diffs)))].mean(1)
    return {"est": float(diffs.mean()), "ci": pa.ci(draws), "p": pa.boot_p(draws), "n_groups": int(len(diffs))}


def finish_family(fam: dict) -> dict:
    pa._apply_holm(fam)
    for t in fam.values():
        t["label"] = pa.label_h4(t)
    labs = [pa.coarse(t["label"]).split(" —")[0] for t in fam.values() if t.get("est") is not None]
    ests = [t["est"] for t in fam.values() if t.get("est") is not None]
    return {"cells": fam, "aşağı": sum(l.startswith("aşağı") for l in labs),
            "yukarı": sum(l.startswith("yukarı") for l in labs),
            "uyumlu": sum(l.startswith("uyumlu") for l in labs),
            "mean_delta": float(np.mean(ests)), "mean_abs_delta": float(np.mean(np.abs(ests)))}


def trajectory_rmse(obs: np.ndarray, sim_means: np.ndarray) -> float:
    """Cell RMSE over rounds 2-10 of mean group trajectories (obs G x 10 x 4; sim_means G x 10)."""
    o = obs.mean(axis=2).mean(axis=0)[1:]
    s = sim_means.mean(axis=0)[1:]
    return float(np.sqrt(np.mean((o - s) ** 2)))


def evaluate_logo(groups: dict, iso: dict, models, n_boot: int = N_BOOT, s: int = S_SIMS) -> dict:
    """Evaluation 1. groups {(model, card): (G,10,4)}; iso {(model, card): {x: array}}."""
    out = {}
    for m in models:
        cards = [c for (mm, c) in groups if mm == m]
        dec = {(c, g): decisions(groups[(m, c)][g]) for c in cards for g in range(len(groups[(m, c)]))}
        res = {}
        for rule in ("R0",) + RULES:
            fams = {w: {} for w in WINDOWS}
            rmse, used = {}, collections.Counter()
            sets = backoff_order(rule) if rule != "R0" else []
            model_tab = Table(sets)
            if rule != "R0":
                for d in dec.values():
                    model_tab.add(d)
            for c in cards:
                G = groups[(m, c)]
                sim_means = np.zeros((len(G), ROUNDS))
                sim_w = {w: np.zeros(len(G)) for w in WINDOWS}
                if rule == "R0":
                    f = np.array([iso[(m, c)][x].mean() for x in pa.POINTS])
                    sim = pa.simulate(np.broadcast_to(f, (len(G), 5)), G[:, 0, :])
                    sim_means = sim.mean(axis=2)
                    for w in WINDOWS:
                        sim_w[w] = window_mean(sim, w)
                else:
                    cell_tab = Table(sets)
                    for g in range(len(G)):
                        cell_tab.add(dec[(c, g)])
                    for g in range(len(G)):
                        cell_tab.add(dec[(c, g)], -1)
                        model_tab.add(dec[(c, g)], -1)
                        r = Rule(rule, cell_tab, model_tab)
                        rng = np.random.default_rng(seed(m, c, rule, g))
                        sim = simulate_group(r, G[g, 0, :], rng, s)
                        sim_means[g] = sim.mean(axis=(0, 2))
                        for w in WINDOWS:
                            sim_w[w][g] = window_mean(sim, w).mean()
                        used.update(r.used)
                        cell_tab.add(dec[(c, g)])
                        model_tab.add(dec[(c, g)])
                for w in WINDOWS:
                    diffs = window_mean(G, w) - sim_w[w]
                    fams[w][c] = cell_test(diffs, ("boot", m, c, rule, f"{w[0]}-{w[1]}"), n_boot)
                rmse[c] = trajectory_rmse(G, sim_means)
            res[rule] = {f"{w[0]}-{w[1]}": finish_family(fams[w]) for w in WINDOWS}
            res[rule]["rmse"] = rmse
            res[rule]["mean_rmse"] = float(np.mean(list(rmse.values())))
            if rule != "R0":
                tot = sum(used.values())
                res[rule]["backoff"] = {f"{k[0]}|{k[1]}": v / tot for k, v in sorted(used.items(), key=str)}
        out[m] = res
    return out


def evaluate_new_data(train: dict, iso: dict, test: dict, models, n_boot: int = N_BOOT, s: int = S_SIMS) -> dict:
    """Evaluation 2: rules from train {(model, card)} groups, simulate test {(model, card)} groups."""
    out = {}
    for m in models:
        cards = [c for (mm, c) in test if mm == m]
        res = {}
        for rule in ("R0",) + RULES:
            fams = {w: {} for w in WINDOWS}
            rmse = {}
            sets = backoff_order(rule) if rule != "R0" else []
            model_tab = Table(sets)
            if rule != "R0":
                for c in cards:
                    for g in train[(m, c)]:
                        model_tab.add(decisions(g))
            for c in cards:
                T = test[(m, c)]
                if rule == "R0":
                    f = np.array([iso[(m, c)][x].mean() for x in pa.POINTS])
                    sim = pa.simulate(np.broadcast_to(f, (len(T), 5)), T[:, 0, :])
                    sim_means, sim_w = sim.mean(axis=2), {w: window_mean(sim, w) for w in WINDOWS}
                else:
                    cell_tab = Table(sets)
                    for g in train[(m, c)]:
                        cell_tab.add(decisions(g))
                    r = Rule(rule, cell_tab, model_tab)
                    sim_means = np.zeros((len(T), ROUNDS))
                    sim_w = {w: np.zeros(len(T)) for w in WINDOWS}
                    for g in range(len(T)):
                        sim = simulate_group(r, T[g, 0, :], np.random.default_rng(seed("new", m, c, rule, g)), s)
                        sim_means[g] = sim.mean(axis=(0, 2))
                        for w in WINDOWS:
                            sim_w[w][g] = window_mean(sim, w).mean()
                for w in WINDOWS:
                    fams[w][c] = cell_test(window_mean(T, w) - sim_w[w], ("boot-new", m, c, rule, f"{w[0]}-{w[1]}"), n_boot)
                rmse[c] = trajectory_rmse(T, sim_means)
            res[rule] = {f"{w[0]}-{w[1]}": finish_family(fams[w]) for w in WINDOWS}
            res[rule]["rmse"] = rmse
            res[rule]["mean_rmse"] = float(np.mean(list(rmse.values())))
        out[m] = res
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage1-config", default="configs/main.json")
    ap.add_argument("--stage1-run", default="main_s1_20261014")
    ap.add_argument("--expA-config", default="configs/expA_main.json")
    ap.add_argument("--expA-run", default="expA_main_20261017")
    ap.add_argument("--out", default=str(pa.ROOT / "results" / "rules_analysis.json"))
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--sims", type=int, default=S_SIMS)
    args = ap.parse_args(argv)
    rows, length, _, _ = pa.load_run(args.stage1_config, args.stage1_run)
    u1 = pa.Units(rows, length)
    groups = {}
    iso = {}
    for m in pa.MODELS:
        for city in pa.CITIES:
            for style in pa.STYLES:
                c = pa.card_id(city, style)
                groups[(m, c)] = u1.group_array(m, c)
                iso[(m, c)] = u1.iso_points(m, c)
    ev1 = evaluate_logo(groups, iso, pa.MODELS, args.n_boot, args.sims)
    rowsA, lengthA, _, _ = pa.load_run(args.expA_config, args.expA_run)
    gA = ax.groups_by_arm(pa.Units(rowsA, lengthA))
    test = {(m, c): gA[(m, c, "B")] for m in pa.MODELS for c in ax.CARDS}
    train = {(m, c): groups[(m, c)] for m in pa.MODELS for c in ax.CARDS}
    ev2 = evaluate_new_data(train, iso, test, pa.MODELS, args.n_boot, args.sims)
    out = {"status": "keşifsel (prereg_main F.14); ana etiketleri değiştirmez",
           "evaluation1_stage1_logo": ev1, "evaluation2_expA_B": ev2,
           "meta": {"sims": args.sims, "n_boot": args.n_boot, "stage1_run": args.stage1_run,
                    "expA_run": args.expA_run}}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=pa._json_default))
    print(f"yazıldı: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
