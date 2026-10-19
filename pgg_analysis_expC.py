"""Experiment C: does the rule learned in groups of 4 predict how outcomes change with group
size? (prereg/prereg_expC.md, approved 2026-10-19). Read-only on run directories, no API calls.

  forecast  unconditional forecast before any paid call: for every model x card x group size
            n, the frozen rule (R3, round bins by rounds left) and R0 (isolated response) from
            round-1 contributions drawn agent by agent from the cell's stage-1 round 1.
  analyse   C-H1 (size direction), C-H2 (transfer, mean contribution), C-H3 (transfer, share
            collapsed at round 8), C-H4 (curve), mechanism, sensitivity. Refuses an incomplete
            run, a frozen rule file and a forecast file with another sha256.

State of an agent in a group of n: own previous contribution, the mean of the n - 1 others,
"one of the n - 1 others gave 0", rounds-left bin; at n = 4 identical to stage 1 (test).
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

import pgg_analysis as pa
import pgg_analysis_expA as ax
import pgg_analysis_expB as pb

SIZES = {"mistral": (4, 8, 16), "gpt": (4, 8, 16, 32)}
CARDS = ax.CARDS
T, E = 10, 8                     # rounds; round of the collapse measure (end of the mid game)
LOW = 2.5
FROZEN_SHA = "62b2bae7bcf6560f022181ff5b0813fec4747f2b8e3e13e5dd1301931fbd93d1"
FORECAST_NS, COND_NS, BOOT_NS = "pgg-expC-forecast", "pgg-expC-sim", "pgg-expC-analysis"
S_FORECAST, S_COND, N_BOOT = 4000, 500, 10_000
BAND_SIZE, BAND_SHARE = 0.10, 0.15
VALS = np.arange(21)


def seed(ns: str, *parts) -> int:
    return pa.stable_seed(ns, *parts)


# ---------------------------------------------------------------- states and simulation

def bins_n(prev: np.ndarray):
    """prev (s, n) -> own bin, others' mean bin, someone-else-gave-0, each (s, n)."""
    n = prev.shape[1]
    own = np.select([prev == 0, prev < 10, prev == 10, prev < 20], [0, 1, 2, 3], 4)
    m = (prev.sum(axis=1, keepdims=True) - prev) / (n - 1)
    mb = np.select([np.abs(m) < 1e-9, m < 5, m < 10 - 1e-9, np.abs(m - 10) < 1e-9, m < 15], [0, 1, 2, 3, 4], 5)
    z = prev == 0
    zero = ((z.sum(axis=1, keepdims=True) - z) > 0).astype(int)
    return own, mb, zero


def simulate_rule(rule, c1: np.ndarray, rng, rounds: int = T) -> np.ndarray:
    """(s, rounds, n) stochastic trajectories from round-1 contributions c1 (s, n)."""
    s, n = c1.shape
    traj = np.zeros((s, rounds, n))
    traj[:, 0] = c1
    for t in range(2, rounds + 1):
        rb = pb.bin_kalan(t, rounds)
        own, mb, zero = bins_n(traj[:, t - 2])
        code = ((own * 6 + mb) * 2 + zero).ravel()
        out = np.zeros(code.shape)
        for u in np.unique(code):
            idx = np.flatnonzero(code == u)
            o, rest = divmod(int(u), 12)
            out[idx] = rng.choice(VALS, size=len(idx), p=rule.dist((o, rest // 2, rest % 2, rb)))
        traj[:, t - 1] = out.reshape(s, n)
    return traj


def simulate_r0(f, c1: np.ndarray, rounds: int = T) -> np.ndarray:
    """Deterministic isolated-response trajectories (..., rounds, n)."""
    xs = np.array(pa.POINTS, dtype=float)
    fv = np.asarray(f, dtype=float)
    c = np.asarray(c1, dtype=float)
    traj = [c]
    for _ in range(2, rounds + 1):
        n = c.shape[-1]
        others = (c.sum(axis=-1, keepdims=True) - c) / (n - 1)
        c = np.interp(others, xs, fv)
        traj.append(c)
    return np.stack(traj, axis=-2)


def outcomes(traj: np.ndarray):
    """Group mean at round E <= LOW, and mean contribution rounds 2..T; over the last two axes."""
    gm = traj.mean(axis=-1)
    return (gm[..., E - 1] <= LOW).astype(float), gm[..., 1:].mean(axis=-1)


# ---------------------------------------------------------------- forecast

def forecast(frozen: dict, s: int = S_FORECAST, sizes=None, cards=CARDS) -> dict:
    sizes = sizes or SIZES
    out = {}
    for m, ns in sizes.items():
        out[m] = {"cards": {}, "mean_over_cards": {}}
        for c in cards:
            cell = frozen["models"][m]["cells"][c]
            rule = pb.rules_for(frozen, m, c, "R3")
            pool = np.array(cell["round1"], dtype=float).ravel()
            out[m]["cards"][c] = {}
            for n in ns:
                rng = np.random.default_rng(seed(FORECAST_NS, m, c, n))
                c1 = rng.choice(pool, size=(s, n))
                row = {}
                for name, traj in (("rule", simulate_rule(rule, c1, rng)), ("R0", simulate_r0(cell["iso_f"], c1))):
                    col, mean = outcomes(traj)
                    row[name] = {"trajectory": [float(x) for x in traj.mean(axis=(0, 2))],
                                 "collapse_r8": float(col.mean()), "mean_2_10": float(mean.mean())}
                out[m]["cards"][c][str(n)] = row
        for n in ns:
            agg = {}
            for name in ("rule", "R0"):
                col = np.mean([out[m]["cards"][c][str(n)][name]["collapse_r8"] for c in cards])
                col4 = np.mean([out[m]["cards"][c]["4"][name]["collapse_r8"] for c in cards])
                agg[name] = {"collapse_r8": float(col), "collapse_r8_minus_n4": float(col - col4),
                             "mean_2_10": float(np.mean([out[m]["cards"][c][str(n)][name]["mean_2_10"] for c in cards]))}
            out[m]["mean_over_cards"][str(n)] = agg
    return out


# ---------------------------------------------------------------- data

class UnitsN:
    """Complete group games of one group size n (rows of one run)."""

    def __init__(self, rows, length_calls=None, n: int = 4, rounds: int = T):
        length_calls = length_calls or set()
        g_rows = collections.defaultdict(list)
        for r in rows:
            if r.get("arm") == "group":
                g_rows[r["unit"]].append(r)
        self.n, self.rounds = n, rounds
        self.groups, self.incomplete = {}, []
        for unit, rs in g_rows.items():
            con = {(r["round"], r["agent_id"]): r for r in rs if r["step"] == "contribute"}
            comp = [r for r in rs if r["step"] == "comprehension"]
            if len(con) != rounds * n:
                self.incomplete.append(unit)
                continue
            c = np.array([[con[(t, a)]["contribution"] for a in range(1, n + 1)] for t in range(1, rounds + 1)], float)
            sess = rs[0]["session_id"]
            self.groups[unit] = {
                "model": rs[0]["model_key"], "card": rs[0]["card_id"], "c": c,
                "capped": any(r.get("reasoning_capped") for r in rs),
                "length": any(k[0] == sess for k in length_calls),
                "comp_full": len(comp) == n and all(not r.get("comp_missing") and r.get("comp_q1_correct")
                                                    and r.get("comp_q2_correct") for r in comp)}

    def subset(self, variant: str) -> "UnitsN":
        out = UnitsN([], n=self.n, rounds=self.rounds)
        keep = {"comp_full": lambda g: g["comp_full"],
                "no_capped": lambda g: not (g["capped"] or g["length"])}[variant]
        out.groups = {u: g for u, g in self.groups.items() if keep(g)}
        return out

    def group_array(self, model: str, card: str) -> np.ndarray:
        gs = [g["c"] for g in self.groups.values() if g["model"] == model and g["card"] == card]
        return np.stack(gs) if gs else np.zeros((0, self.rounds, self.n))


# ---------------------------------------------------------------- per-group predictions

def predict(frozen: dict, model: str, card: str, G: np.ndarray, s: int) -> dict:
    """Observed and conditional (from each group's observed round 1) per-group outcomes."""
    n = G.shape[2]
    obs_col, obs_mean = outcomes(G)
    out = {"obs_collapse": obs_col, "obs_mean": obs_mean}
    if len(G) == 0:
        return {**out, **{k: np.zeros(0) for k in ("rule_collapse", "rule_mean", "r0_collapse", "r0_mean")}}
    rng = np.random.default_rng(seed(COND_NS, model, card, n))
    sim = simulate_rule(pb.rules_for(frozen, model, card, "R3"), np.repeat(G[:, 0, :], s, axis=0), rng)
    col, mean = outcomes(sim.reshape(len(G), s, T, n))
    out["rule_collapse"], out["rule_mean"] = col.mean(axis=1), mean.mean(axis=1)
    out["r0_collapse"], out["r0_mean"] = outcomes(simulate_r0(frozen["models"][model]["cells"][card]["iso_f"], G[:, 0, :]))
    return out


# ---------------------------------------------------------------- statistics

def strat_boot(values_by_card: list, rng, n_boot: int) -> np.ndarray:
    """Bootstrap draws of the pooled mean, groups resampled within cards."""
    vals = [np.asarray(v, float) for v in values_by_card if len(v)]
    total = sum(len(v) for v in vals)
    draws = np.zeros(n_boot)
    for v in vals:
        draws += v[rng.integers(0, len(v), (n_boot, len(v)))].sum(axis=1)
    return draws / total


def pooled_mean(values_by_card: list) -> float:
    return float(np.concatenate([np.asarray(v, float) for v in values_by_card]).mean())


def label_size(t: dict) -> str:
    lo, hi = t["ci"]
    if lo > 0:
        return "artış"
    if hi < 0:
        return "azalış"
    if -BAND_SIZE <= lo and hi <= BAND_SIZE:
        return "değişim yok"
    return "belirsiz"


def label_share(t: dict) -> str:
    lo, hi = t["ci"]
    if abs(t["est"]) <= BAND_SHARE and -BAND_SHARE <= lo and hi <= BAND_SHARE:
        return "yeniden üretiyor"
    if lo > BAND_SHARE:
        return "sapıyor (gerçek daha yüksek)"
    if hi < -BAND_SHARE:
        return "sapıyor (gerçek daha düşük)"
    return "belirsiz"


def holm_labels(fam: dict) -> None:
    """C-H2: Holm over the model's sizes >= 8 for the deviation labels (pb.label_h1)."""
    keys = sorted(fam, key=lambda k: fam[k]["p"])
    m, running = len(keys), 0.0
    for i, k in enumerate(keys):
        running = max(running, min(1.0, (m - i) * fam[k]["p"]))
        fam[k]["p_holm"] = running
    for k in fam:
        fam[k]["label"] = pb.label_h1({**fam[k], "p": fam[k]["p_holm"]})


def mechanism(G: np.ndarray) -> dict:
    """Rounds 2..9, agent gave >= 10 and others' mean >= 5 in the previous round: share of 0
    when one of the others gave 0, and when none did."""
    out = {"zero": [0, 0], "nozero": [0, 0]}
    for g in G:
        for t in range(2, T):
            prev, now = g[t - 2], g[t - 1]
            zero = bins_n(prev[None, :])[2][0]
            n = len(prev)
            others_mean = (prev.sum() - prev) / (n - 1)
            for i in range(n):
                if prev[i] >= 10 and others_mean[i] >= 5:
                    k = "zero" if zero[i] else "nozero"
                    out[k][0] += int(now[i] == 0)
                    out[k][1] += 1
    return {k: {"n": v[1], "share_0": (v[0] / v[1]) if v[1] else None} for k, v in out.items()}


# ---------------------------------------------------------------- analysis

def analyse(frozen: dict, units: dict, s: int = S_COND, n_boot: int = N_BOOT, sizes=None, cards=CARDS,
            forecast_table: dict | None = None, small_hist: dict | None = None, stage1_groups: dict | None = None) -> dict:
    """units {n: UnitsN}; small_hist {model: {card: (G,10,4)}} historical groups of 4 (sensitivity);
    stage1_groups {model: {card: (G,10,4)}} for the mechanism comparison."""
    sizes = sizes or SIZES
    out: dict = {"C_H1": {}, "C_H2": {}, "C_H3": {}, "C_H4": {}, "mechanism": {}, "n_groups": {}}
    for m, ns in sizes.items():
        pred = {n: {c: predict(frozen, m, c, units[n].group_array(m, c), s) for c in cards} for n in ns if n in units}
        out["n_groups"][m] = {str(n): int(sum(len(pred[n][c]["obs_mean"]) for c in cards)) for n in pred}
        # C-H1
        big = max(pred)
        rng = np.random.default_rng(seed(BOOT_NS, "C_H1", m))
        ob = [pred[big][c]["obs_collapse"] for c in cards]
        osm = [pred[4][c]["obs_collapse"] for c in cards]
        t = {"n_big": big, "est": pooled_mean(ob) - pooled_mean(osm),
             "ci": pa.ci(strat_boot(ob, rng, n_boot) - strat_boot(osm, rng, n_boot)),
             "observed": {"n4": pooled_mean(osm), f"n{big}": pooled_mean(ob)},
             "rule_conditional": pooled_mean([pred[big][c]["rule_collapse"] for c in cards])
             - pooled_mean([pred[4][c]["rule_collapse"] for c in cards]),
             "R0_conditional": pooled_mean([pred[big][c]["r0_collapse"] for c in cards])
             - pooled_mean([pred[4][c]["r0_collapse"] for c in cards])}
        t["label"] = label_size(t)
        t["rule_inside_ci"] = bool(t["ci"][0] <= t["rule_conditional"] <= t["ci"][1])
        if forecast_table:
            t["rule_unconditional"] = forecast_table[m]["mean_over_cards"][str(big)]["rule"]["collapse_r8_minus_n4"]
        if small_hist and m in small_hist:
            hs = [small_hist[m][c] for c in cards]
            hcol = [outcomes(h)[0] for h in hs]
            rng = np.random.default_rng(seed(BOOT_NS, "C_H1-hist", m))
            th = {"est": pooled_mean(ob) - pooled_mean(hcol),
                  "ci": pa.ci(strat_boot(ob, rng, n_boot) - strat_boot(hcol, rng, n_boot))}
            th["label"] = label_size(th)
            t["historical_control"] = th
        out["C_H1"][m] = t
        # C-H2 (n >= 8 in the Holm family; n = 4 reported separately)
        fam, ctrl = {}, None
        for n in pred:
            d = [pred[n][c]["obs_mean"] - pred[n][c]["rule_mean"] for c in cards]
            r = pb.pooled(d, ("C_H2", m, n), n_boot)
            r["R0_diff"] = float(np.mean([(pred[n][c]["obs_mean"] - pred[n][c]["r0_mean"]).mean() for c in cards
                                          if len(pred[n][c]["obs_mean"])]))
            if n == 4:
                r["label"] = pb.label_h1(r)
                ctrl = r
            else:
                fam[str(n)] = r
        holm_labels(fam)
        out["C_H2"][m] = {"family": fam, "control_n4": ctrl}
        # C-H3 and C-H4
        c3, c4 = {}, {}
        for n in pred:
            d = [pred[n][c]["obs_collapse"] - pred[n][c]["rule_collapse"] for c in cards]
            rng = np.random.default_rng(seed(BOOT_NS, "C_H3", m, n))
            r = {"est": pooled_mean(d), "ci": pa.ci(strat_boot(d, rng, n_boot)),
                 "R0_diff": pooled_mean([pred[n][c]["obs_collapse"] - pred[n][c]["r0_collapse"] for c in cards])}
            r["label"] = label_share(r)
            c3[str(n)] = r
            c4[str(n)] = {k: pooled_mean([pred[n][c][f"{src}_{q}"] for c in cards])
                          for k, (src, q) in {"observed_collapse": ("obs", "collapse"), "observed_mean": ("obs", "mean"),
                                              "rule_collapse": ("rule", "collapse"), "rule_mean": ("rule", "mean"),
                                              "R0_collapse": ("r0", "collapse"), "R0_mean": ("r0", "mean")}.items()}
            if forecast_table:
                c4[str(n)]["rule_unconditional_collapse"] = forecast_table[m]["mean_over_cards"][str(n)]["rule"]["collapse_r8"]
        out["C_H3"][m] = c3
        out["C_H4"][m] = {"points": c4, "slope_log2n": slope(pred, cards, n_boot, m)}
        # mechanism
        out["mechanism"][m] = {str(n): mechanism(np.concatenate([units[n].group_array(m, c) for c in cards]))
                               for n in pred}
        if stage1_groups and m in stage1_groups:
            out["mechanism"][m]["stage1_n4"] = mechanism(np.concatenate([stage1_groups[m][c] for c in cards]))
    mis, gpt = out["C_H1"].get("mistral"), out["C_H1"].get("gpt")
    out["joint"] = ("ters yönlü ölçek doğrulandı" if mis and gpt and mis["label"] == "artış" and gpt["label"] != "artış"
                    else "ters yönlü ölçek doğrulanmadı")
    return out


def slope(pred: dict, cards, n_boot: int, m: str) -> dict:
    """OLS slope of the group outcome (collapsed at round 8; mean 2..10) on log2 n, groups resampled
    within size x card; the rule's conditional slope as a point value."""
    out = {}
    for q in ("collapse", "mean"):
        xs, ys, yr, strata = [], [], [], []
        for n in pred:
            for c in cards:
                v = pred[n][c][f"obs_{q}"]
                xs += [np.log2(n)] * len(v)
                ys += list(v)
                yr += list(pred[n][c][f"rule_{q}"])
                strata += [(n, c)] * len(v)
        x, y, r = np.array(xs), np.array(ys), np.array(yr)
        b = lambda yy, xx: float(np.polyfit(xx, yy, 1)[0])            # noqa: E731
        rng = np.random.default_rng(seed(BOOT_NS, "slope", m, q))
        idx_by = collections.defaultdict(list)
        for i, s_ in enumerate(strata):
            idx_by[s_].append(i)
        draws = []
        for _ in range(n_boot // 10):
            idx = np.concatenate([rng.choice(v, size=len(v)) for v in idx_by.values()])
            draws.append(b(y[idx], x[idx]))
        out[q] = {"observed": b(y, x), "ci": pa.ci(np.array(draws)), "rule_conditional": b(r, x)}
    return out


def run_analysis(frozen, units: dict, s, n_boot, forecast_table=None, small_hist=None, stage1_groups=None) -> dict:
    res = {"main": analyse(frozen, units, s, n_boot, forecast_table=forecast_table, small_hist=small_hist,
                           stage1_groups=stage1_groups), "sensitivity": {}}
    for v in ("comp_full", "no_capped"):
        sub = {n: u.subset(v) for n, u in units.items()}
        a = analyse(frozen, sub, s, n_boot)
        res["sensitivity"][v] = {
            "excluded_groups": {str(n): len(units[n].groups) - len(sub[n].groups) for n in units},
            "labels": {m: {"C_H1": a["C_H1"][m]["label"],
                           "C_H2": {k: x["label"] for k, x in a["C_H2"][m]["family"].items()}} for m in a["C_H1"]},
            "changed": [m for m in a["C_H1"] if a["C_H1"][m]["label"] != res["main"]["C_H1"][m]["label"]]
            + [f"{m}:n{k}" for m in a["C_H2"] for k, x in a["C_H2"][m]["family"].items()
               if x["label"] != res["main"]["C_H2"][m]["family"][k]["label"]]}
    return res


# ---------------------------------------------------------------- CLI

def _sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    fc = sub.add_parser("forecast")
    fc.add_argument("--frozen", default="data/expB/frozen_rules_v1.json")
    fc.add_argument("--sha256", default=FROZEN_SHA)
    fc.add_argument("--out", default="data/expC/forecast_v1.json")
    fc.add_argument("--sims", type=int, default=S_FORECAST)
    an = sub.add_parser("analyse")
    an.add_argument("--runs", required=True, help="e.g. 4=expC_n4_main_20261020,8=...,16=...,32=...")
    an.add_argument("--frozen", default="data/expB/frozen_rules_v1.json")
    an.add_argument("--sha256", default=FROZEN_SHA)
    an.add_argument("--forecast", default="data/expC/forecast_v1.json")
    an.add_argument("--forecast-sha256", required=True)
    an.add_argument("--out")
    an.add_argument("--sims", type=int, default=S_COND)
    an.add_argument("--n-boot", type=int, default=N_BOOT)
    an.add_argument("--allow-incomplete", action="store_true")
    args = ap.parse_args(argv)
    frozen = pb.load_frozen(args.frozen, args.sha256)
    if args.cmd == "forecast":
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"frozen_sha256": args.sha256, "T": T, "E": E, "low": LOW, "sims": args.sims,
                                   "sizes": SIZES, "cards": list(CARDS), "forecast": forecast(frozen, args.sims)},
                                  sort_keys=True, indent=1) + "\n")
        print(f"yazıldı: {out} sha256 {_sha(out)}")
        return 0
    if _sha(args.forecast) != args.forecast_sha256:
        print(f"DUR: tahmin dosyası {args.forecast} kilitli sha256 ile aynı değil.", file=sys.stderr)
        return 2
    fct = json.loads(Path(args.forecast).read_text())["forecast"]
    runs = dict(x.split("=") for x in args.runs.split(","))
    units, meta = {}, {}
    for n_s, run in runs.items():
        n = int(n_s)
        rows, length, _, mt = pa.load_run(f"configs/expC_n{n}_main.json", run)
        units[n] = UnitsN(rows, length, n)
        meta[n_s] = {"run": run, "n_rows": len(rows), "planned_units": mt["planned_units"],
                     "complete_groups": len(units[n].groups)}
        if len(units[n].groups) < mt["planned_units"] and not args.allow_incomplete:
            print(f"DUR: {run} tamamlanmamış ({len(units[n].groups)}/{mt['planned_units']} grup). "
                  "Ara analiz planda yok.", file=sys.stderr)
            return 2
    rows1, length1, _, _ = pa.load_run("configs/main.json", "main_s1_20261014")
    u1 = pa.Units(rows1, length1)
    stage1 = {m: {c: u1.group_array(m, c) for c in CARDS} for m in SIZES}
    rowsA, lengthA, _, _ = pa.load_run("configs/expA_main.json", "expA_main_20261017")
    gA = ax.groups_by_arm(pa.Units(rowsA, lengthA))
    hist = {m: {c: np.concatenate([stage1[m][c], gA[(m, c, "B")]]) for c in CARDS} for m in SIZES}
    res = run_analysis(frozen, units, args.sims, args.n_boot, fct, hist, stage1)
    res["meta"] = {"runs": meta, "frozen_sha256": args.sha256, "forecast_sha256": args.forecast_sha256,
                   "sims": args.sims, "n_boot": args.n_boot, "allow_incomplete": args.allow_incomplete}
    out = Path(args.out) if args.out else pa.ROOT / "results" / f"expC_main_{min(runs.values())[-8:]}_analysis.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=pa._json_default))
    print(f"yazıldı: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
