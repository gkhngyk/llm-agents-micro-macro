"""Structure check of the Herrmann, Thoeni & Gaechter (2008) data.

Source: https://doi.org/10.5061/dryad.87301 (Zenodo record 4969858), CC0.
Stdlib only. Run: .venv/bin/python data/herrmann2008/check_data.py
"""
import csv
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
RAW = HERE / "raw" / "HerrmannThoeniGaechterDATA.csv"


def load_rows():
    # File uses classic-Mac CR line endings and a UTF-8 BOM; first line is a title.
    text = RAW.read_bytes().decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    hdr = next(i for i, l in enumerate(lines) if l.startswith("sessionid,"))
    return list(csv.DictReader(io.StringIO("\n".join(lines[hdr:]))))


def num(x):
    return float(x) if x not in ("", ".") else None


def main():
    rows = load_rows()
    out = {"n_rows": len(rows), "columns": list(rows[0].keys())}

    out["cities"] = sorted({r["city"] for r in rows})
    out["n_cities"] = len(out["cities"])
    out["experiments"] = dict(Counter(r["p"] for r in rows))
    out["secseq"] = dict(Counter(r["secseq"] for r in rows))
    out["periods"] = sorted({int(r["period"]) for r in rows})

    # One row per (subject, period, experiment) per other group member -> 3 rows each.
    per_obs = Counter((r["subjectid"], r["sessionid"], r["p"], r["period"]) for r in rows)
    out["rows_per_subject_period"] = dict(Counter(per_obs.values()))

    # Subjects / groups per city (subjectid is not globally unique: use session+subject).
    subj = defaultdict(set)
    groups = defaultdict(set)
    for r in rows:
        subj[r["city"]].add((r["sessionid"], r["subjectid"]))
        groups[r["city"]].add((r["sessionid"], r["groupid"]))
    out["subjects_per_city"] = {c: len(s) for c, s in sorted(subj.items())}
    out["groups_per_city"] = {c: len(g) for c, g in sorted(groups.items())}

    # Group size check: distinct subjects per (session, group, experiment, period).
    gs = defaultdict(set)
    for r in rows:
        gs[(r["sessionid"], r["groupid"], r["p"], r["period"])].add(r["subjectid"])
    out["group_sizes"] = dict(Counter(len(v) for v in gs.values()))

    # Value ranges.
    contrib = [num(r["senderscontribution"]) for r in rows]
    pun = [num(r["punishment"]) for r in rows if r["p"] == "P-experiment"]
    out["contribution_range"] = [min(c for c in contrib if c is not None),
                                 max(c for c in contrib if c is not None)]
    out["punishment_range_P"] = [min(p for p in pun if p is not None),
                                 max(p for p in pun if p is not None)]
    out["punishment_missing_P"] = sum(p is None for p in pun)
    out["punishment_nonmissing_N"] = sum(
        num(r["punishment"]) is not None for r in rows if r["p"] == "N-experiment")

    # Mean contribution per city x experiment (one value per subject-period).
    seen = set()
    acc = defaultdict(list)
    for r in rows:
        k = (r["sessionid"], r["subjectid"], r["p"], r["period"])
        if k in seen:
            continue
        seen.add(k)
        acc[(r["city"], r["p"])].append(num(r["senderscontribution"]))
    out["mean_contribution"] = {
        f"{c} | {p}": round(sum(v) / len(v), 2) for (c, p), v in sorted(acc.items())}

    # Mean contribution by period, pooled, per experiment (decay check).
    byp = defaultdict(list)
    seen2 = set()
    for r in rows:
        k = (r["sessionid"], r["subjectid"], r["p"], r["period"])
        if k in seen2:
            continue
        seen2.add(k)
        byp[(r["p"], int(r["period"]))].append(num(r["senderscontribution"]))
    out["mean_by_period"] = {
        f"{p} | {per}": round(sum(v) / len(v), 2) for (p, per), v in sorted(byp.items())}

    # Antisocial punishment share: punishment points sent to others contributing
    # >= sender's own contribution, as share of all points sent, per city (P only).
    anti = defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        if r["p"] != "P-experiment":
            continue
        pv = num(r["punishment"])
        if not pv:
            continue
        a = anti[r["city"]]
        a[1] += pv
        if float(r["otherscontribution"]) >= float(r["senderscontribution"]):
            a[0] += pv
    out["antisocial_share_P"] = {c: round(a[0] / a[1], 3) for c, a in sorted(anti.items())}

    # Session order patterns: subjects per (city, sorted set of (experiment, secseq)).
    sess = defaultdict(set)
    sess_subj = defaultdict(set)
    for r in rows:
        k = (r["city"], r["sessionid"])
        sess[k].add(f'{r["p"][0]}{r["secseq"]}')
        sess_subj[k].add(r["subjectid"])
    pat = Counter()
    for k, v in sess.items():
        pat[f'{k[0]} | {"+".join(sorted(v))}'] += len(sess_subj[k])
    out["subjects_by_session_pattern"] = dict(sorted(pat.items()))

    text = json.dumps(out, indent=1, ensure_ascii=False)
    (HERE / "check_output.json").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
