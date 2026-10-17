"""Exploratory H4: the end-of-game effect apart (prereg/prereg_main.md amendment F.12).

NOT pre-registered: written after the main H4 results were seen. It never
changes a main H4 label. The simulation is pgg_analysis.simulate (rounds 2-10,
as in §6.4); only the comparison window changes: Delta4[a-b] = mean over the
cell's groups of (observed - simulated) mean contribution in rounds a..b.
Primary window 2-8 (Holm over the 12 cards of a model); 2-9 and 2-5
descriptive. Window 2-10 reproduces the main H4 estimate (tested).

Run (read-only, no API calls):
  python pgg_analysis_explore.py --config configs/main.json --run main_s1_20261014 \\
      [--out results/<run>_explore_h4.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

import pgg_analysis as pa

PRIMARY = (2, 8)
SECONDARY = ((2, 9), (2, 5))
FULL = (2, 10)


def h4_window(groups: np.ndarray, iso: dict, window: tuple, seed_parts, n_boot: int) -> dict:
    """Delta4 over rounds window[0]..window[1] (1-based, inclusive)."""
    a, b = window
    if len(groups) == 0 or any(len(iso[x]) == 0 for x in pa.POINTS):
        return {"est": None}
    sl = slice(a - 1, b)
    f = np.array([iso[x].mean() for x in pa.POINTS])
    sim = pa.simulate(np.broadcast_to(f, (len(groups), len(pa.POINTS))), groups[:, 0, :])
    est = float((groups[:, sl, :].mean(axis=(1, 2)) - sim[:, sl, :].mean(axis=(1, 2))).mean())
    rng = np.random.default_rng(pa.seed(*seed_parts))
    G = len(groups)
    gi = rng.integers(0, G, size=(n_boot, G))
    fb = np.stack([iso[x][rng.integers(0, len(iso[x]), size=(n_boot, len(iso[x])))].mean(1)
                   for x in pa.POINTS], axis=-1)
    gb = groups[gi]
    simb = pa.simulate(np.broadcast_to(fb[:, None, :], (n_boot, G, len(pa.POINTS))), gb[:, :, 0, :])
    draws = (gb[:, :, sl, :].mean(axis=(2, 3)) - simb[:, :, sl, :].mean(axis=(2, 3))).mean(1)
    return {"est": est, "ci": pa.ci(draws), "p": pa.boot_p(draws), "n_groups": G}


def explore(units: pa.Units, n_boot: int = pa.N_BOOT, models=pa.MODELS) -> dict:
    out = {}
    for m in models:
        per = {}
        for window in (FULL, PRIMARY, *SECONDARY):
            key = f"{window[0]}-{window[1]}"
            fam = {}
            for city in pa.CITIES:
                for style in pa.STYLES:
                    cid = pa.card_id(city, style)
                    fam[cid] = h4_window(units.group_array(m, cid), units.iso_points(m, cid), window,
                                         ("H4x", m, cid, key), n_boot)
            if window in (FULL, PRIMARY):
                pa._apply_holm(fam)
                for t in fam.values():
                    t["label"] = pa.label_h4(t)
            else:
                for t in fam.values():          # descriptive: unadjusted p
                    if t.get("est") is not None:
                        t["p_holm"] = t["p"]
                        t["label"] = pa.label_h4(t) + " (düzeltmesiz, betimsel)"
            per[key] = fam
        out[m] = per
    return out


def summary(res: dict) -> dict:
    out = {}
    for m, per in res.items():
        out[m] = {}
        for key, fam in per.items():
            ests = [t["est"] for t in fam.values() if t.get("est") is not None]
            labs = [t["label"].split(" —")[0].split(" (")[0] for t in fam.values() if t.get("label")]
            out[m][key] = {"mean_delta4": float(np.mean(ests)), "n_negative": sum(e < 0 for e in ests),
                           "aşağı": labs.count("aşağı"), "yukarı": labs.count("yukarı"),
                           "uyumlu": labs.count("uyumlu")}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--runs-dir")
    ap.add_argument("--out")
    ap.add_argument("--n-boot", type=int, default=pa.N_BOOT)
    args = ap.parse_args(argv)
    rows, length_calls, planned, meta = pa.load_run(args.config, args.run, args.runs_dir)
    units = pa.Units(rows, length_calls)
    if len(units.groups) + len(units.schedules) < meta["planned_units"]:
        print("DUR: koşu tamamlanmamış.", file=sys.stderr)
        return 2
    models = tuple(m for m in pa.MODELS if m in planned)
    res = explore(units, args.n_boot, models)
    out = {"status": "keşifsel (prereg F.12); ana H4 etiketlerini değiştirmez",
           "summary": summary(res), "result": res,
           "meta": {"run": args.run, "n_boot": args.n_boot, "n_rows": len(rows)}}
    path = Path(args.out) if args.out else pa.ROOT / "results" / f"{args.run}_explore_h4.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=pa._json_default))
    print(f"yazıldı: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
