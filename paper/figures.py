"""Figures for the paper draft, from the result files (results/, data/expB/) and, for the
end-state histograms, the group data. Read-only, no API calls.
Run: python paper/figures.py  ->  paper/fig/fig1..fig4 (.png)"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import pgg_analysis_dynamics as pd  # noqa: E402

R = ROOT / "results"
OUT = ROOT / "paper" / "fig"
M = ("deepseek", "mistral", "gpt")
NAME = {"deepseek": "DeepSeek", "mistral": "Mistral", "gpt": "GPT", "human": "Humans"}
# Okabe-Ito
C = {"obs": "#000000", "rule": "#0072B2", "abs": "#E69F00", "r0": "#D55E00", "fc": "#56B4E9", "human": "#009E73"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 100, "savefig.dpi": 200, "savefig.bbox": "tight"})

dy = json.load(open(R / "dynamics_analysis.json"))
eb = json.load(open(R / "expB_main_20261018_analysis.json"))["main"]
fc = json.load(open(ROOT / "data" / "expB" / "forecast_v1.json"))["forecast"]


def fig1_study3():
    fig, axes = plt.subplots(1, 3, figsize=(9, 2.8), sharey=True)
    t = np.arange(1, 16)
    for ax, m in zip(axes, M):
        tr = eb["cells"][m]["trajectories"]
        cs = list(tr)
        mean = lambda k: np.mean([tr[c][k] for c in cs], axis=0)               # noqa: E731
        ax.plot(t, np.mean([fc[m][c]["R3-kalan"] for c in cs], axis=0), color=C["fc"], lw=1, ls="--",
                label="frozen forecast, before the run")
        ax.plot(t, mean("R0"), color=C["r0"], lw=1.2, label="stated response (R0)")
        ax.plot(t, mean("R3-mutlak"), color=C["abs"], lw=1.2, label="rule, absolute rounds")
        ax.plot(t, mean("R3-kalan"), color=C["rule"], lw=1.6, label="rule, rounds left (frozen R3)")
        ax.plot(t, mean("observed"), color=C["obs"], marker="o", ms=3, lw=0, label="observed")
        ax.set_title(NAME[m])
        ax.set_xlabel("round")
        ax.set_xticks([1, 5, 10, 15])
        ax.set_ylim(0, 15)
    axes[0].set_ylabel("mean contribution (of 20)")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h[::-1], lab[::-1], frameon=False, fontsize=8, loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.16))
    fig.suptitle("Study 3: a 15-round game predicted by a rule frozen after the 10-round game", y=1.03, fontsize=10)
    fig.savefig(OUT / "fig1_study3_forecast.png")
    plt.close(fig)


def fig2_survival():
    fig, axes = plt.subplots(1, 4, figsize=(11, 2.8), sharey=True)
    for ax, m in zip(axes, M + ("human",)):
        d = dy["datasets"][m]["EB" if m != "human" else "H"]["D1c"]
        t = np.arange(1, len(d["observed"]) + 1)
        if "R0" in d:
            ax.step(t, d["R0"], where="post", color=C["r0"], lw=1.2, label="stated response (R0)")
        ax.step(t, d["rule"], where="post", color=C["rule"] if m != "human" else C["human"], lw=1.6,
                label="in-context rule" if m != "human" else "same rule class, learned from humans")
        ax.step(t, d["observed"], where="post", color=C["obs"], lw=1.6, ls=":", label="observed")
        ax.set_title(NAME[m] + (", Study 3" if m != "human" else ", HTG 2008"))
        ax.set_xlabel("round")
        ax.set_ylim(0, 1.02)
    axes[0].set_ylabel("share of groups not yet collapsed\n(group mean > 2.5)")
    h = {}
    for ax in axes:
        for hh, ll in zip(*ax.get_legend_handles_labels()):
            h.setdefault(ll, hh)
    fig.legend(list(h.values()), list(h.keys()), frameon=False, fontsize=8, loc="lower center", ncol=4,
               bbox_to_anchor=(0.5, -0.16))
    fig.suptitle("Survival of cooperation during the mid game (end-game rounds excluded)", y=1.03, fontsize=10)
    fig.savefig(OUT / "fig2_survival.png")
    plt.close(fig)


def fig3_tipping():
    """Line: the model-level in-context rule from an idealised start (k zeros, 4 - k tens).
    Markers: the real groups of the out-of-sample data set by their number of round-1 zeros
    (classes with >= 5 groups): observed share collapsed, and the mean prediction for the same
    groups of the cell-level rule and of the cell-level stated response (R0)."""
    fig, axes = plt.subplots(1, 4, figsize=(11, 2.8), sharey=True)
    k = np.arange(5)
    for ax, m in zip(axes, M + ("human",)):
        r = "r13" if m != "human" else "r8"
        hum = m == "human"
        by = dy["rules"][m]["model_rule"]["D2"]["by_k"]
        ax.plot(k, [by[str(i)][r]["collapse"] for i in k], color=C["human"] if hum else C["rule"], lw=1.4,
                label="in-context rule, start with k free riders (others give 10)")
        obs = dy["datasets"][m]["H" if hum else "EB"]["D2_by_k1"]
        xs = np.array([int(i) for i, x in obs.items() if "observed" in x])
        o = [obs[str(i)] for i in xs]
        ax.plot(xs - 0.12, [x["rule"] for x in o], ls="", marker="s", mfc="white", ms=5,
                color=C["human"] if hum else C["rule"], label="in-context rule, same groups")
        if not hum:
            ax.plot(xs + 0.12, [x["R0"] for x in o], ls="", marker="^", mfc="white", ms=5, color=C["r0"],
                    label="stated response (R0), same groups")
        err = np.array([[x["observed"]["est"] - x["observed"]["ci"][0], x["observed"]["ci"][1] - x["observed"]["est"]]
                        for x in o]).T
        ax.errorbar(xs, [x["observed"]["est"] for x in o], yerr=err, fmt="o", ms=4, color="black", capsize=2, lw=0.8,
                    label="observed groups (by round-1 zeros)")
        ax.set_title(NAME[m] + (", HTG 2008, round 8" if hum else ", Study 3, round 13"))
        ax.set_xlabel("free riders in round 1")
        ax.set_xticks(k)
        ax.set_ylim(-0.03, 1.03)
    axes[0].set_ylabel("P(group collapsed)")
    h = {}
    for ax in axes:
        for hh, ll in zip(*ax.get_legend_handles_labels()):
            h.setdefault(ll, hh)
    fig.legend(list(h.values()), list(h.keys()), frameon=False, fontsize=8, loc="lower center", ncol=2,
               bbox_to_anchor=(0.5, -0.27))
    fig.suptitle("Tipping point: how many free riders it takes to collapse a group", y=1.03, fontsize=10)
    fig.savefig(OUT / "fig3_tipping.png")
    plt.close(fig)


def fig4_endstates():
    llm = pd.load_llm()
    human = pd.load_human(ROOT / pd.HUMAN_CSV)
    data = {m: np.concatenate([G[:, 7, :].mean(axis=1) for G in llm["S1"][m].values()]) for m in M}
    data["human"] = np.concatenate([G[:, 7, :].mean(axis=1) for G in human.values()])
    fig, axes = plt.subplots(1, 4, figsize=(11, 2.6), sharey=True)
    bins = np.arange(-0.25, 20.5, 1.0)
    for ax, m in zip(axes, M + ("human",)):
        x = data[m]
        ax.axvspan(-0.5, 2.5, color="#eeeeee", lw=0)
        ax.axvspan(7.5, 20.5, color="#e6f0f7", lw=0)
        ax.hist(x, bins=bins, weights=np.full(len(x), 1 / len(x)), color=C["human"] if m == "human" else C["rule"])
        mid = np.mean((x > 2.5) & (x < 7.5))
        ax.set_title(f"{NAME[m]}{', HTG 2008' if m == 'human' else ', Study 1'} (n = {len(x)})")
        ax.text(5, 0.55, f"between\n{mid:.0%}", ha="center", fontsize=8)
        ax.set_xlabel("group mean contribution, round 8")
        ax.set_xlim(-0.5, 20.5)
    axes[0].set_ylabel("share of groups")
    fig.suptitle("End of the mid game (round 8): LLM groups end at one of two extremes, human groups do not",
                 y=1.03, fontsize=10)
    fig.savefig(OUT / "fig4_endstates.png")
    plt.close(fig)


def _wilson(p, n, z=1.96):
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def fig5_scaling():
    ec = json.load(open(R / "expC_main_20261020_analysis.json"))["main"]
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3), sharey=True)
    for ax, m in zip(axes, ("mistral", "gpt")):
        pts = ec["C_H4"][m]["points"]
        ns = sorted(int(k) for k in pts)
        x = np.log2(ns)
        obs = np.array([pts[str(n)]["observed_collapse"] for n in ns])
        g = np.array([ec["n_groups"][m][str(n)] for n in ns])
        lo, hi = _wilson(obs, g)
        ax.plot(x, [pts[str(n)]["rule_unconditional_collapse"] for n in ns], color=C["fc"], ls="--", lw=1.2,
                label="in-play rule, frozen forecast (before the run)")
        ax.plot(x, [pts[str(n)]["rule_collapse"] for n in ns], color=C["rule"], lw=1.6, marker="s", ms=4,
                label="in-play rule, from observed round 1")
        ax.plot(x, [pts[str(n)]["R0_collapse"] for n in ns], color=C["r0"], lw=1.2, marker="^", ms=4,
                label="stated response (R0), from observed round 1")
        ax.errorbar(x, obs, yerr=[obs - lo, hi - obs], fmt="o", color="black", ms=5, capsize=2, lw=0.8,
                    label="observed (95% Wilson CI)")
        ax.set_xticks(x)
        ax.set_xticklabels(ns)
        ax.set_xlabel("group size")
        ax.set_title(f"{NAME[m]} ({', '.join(str(int(v)) for v in g)} groups)")
        ax.set_ylim(-0.03, 1.03)
    axes[0].set_ylabel("share of groups collapsed at round 8")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, frameon=False, fontsize=8, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.2))
    fig.suptitle("Study 4: LLM groups become more fragile as they grow", y=1.03, fontsize=10)
    fig.savefig(OUT / "fig5_scaling.png")
    plt.close(fig)


def fig6_count():
    ex = json.load(open(R / "expC_explore_20261020.json"))["results"]
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3), sharey=True)
    for ax, m in zip(axes, ("mistral", "gpt")):
        ks = ["1", "2", "3+"]
        width = 0.8 / len(ex[m])
        for j, (n, v) in enumerate(sorted(ex[m].items(), key=lambda kv: int(kv[0]))):
            bz = v["T2"]["by_zero_count"]
            ys = [bz[k]["p0"] if k in bz and bz[k]["trials"] >= 10 else np.nan for k in ks]
            xb = np.arange(3) + (j - (len(ex[m]) - 1) / 2) * width
            ax.bar(xb, ys, width=width * 0.95,
                   color=plt.cm.Blues(0.35 + 0.65 * j / max(1, len(ex[m]) - 1)), label=f"group of {n}")
            for xx, yy, k in zip(xb, ys, ks):
                if not np.isnan(yy):
                    ax.text(xx, yy + 0.01, str(bz[k]["trials"]), ha="center", va="bottom", fontsize=6)
        ax.set_xticks(np.arange(3))
        ax.set_xticklabels(["1", "2", "3 or more"])
        ax.set_xlabel("others who gave 0 in the previous round")
        ax.set_title(NAME[m])
        ax.legend(frameon=False, fontsize=7)
    axes[0].set_ylabel("share of cooperators who then give 0")
    fig.suptitle("Cooperators' response to seeing others give 0, by how many did (exploratory; "
                 "others' mean in [5, 10), mid game; numbers = decisions; bars with < 10 omitted)", y=1.04, fontsize=9)
    fig.savefig(OUT / "fig6_count.png")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    fig1_study3()
    fig2_survival()
    fig3_tipping()
    fig4_endstates()
    fig5_scaling()
    fig6_count()
    print("yazıldı:", ", ".join(sorted(p.name for p in OUT.glob("*.png"))))
