"""Build the Zenodo deposit of Experiment C's plan and frozen forecast from one git commit.

Run: .venv/bin/python scripts/build_zenodo_expC.py [--commit HEAD]
Writes release/zenodo_expC/build/<files>, SOURCE_COMMIT.txt, SHA256SUMS.txt and release/zenodo_expC/expC_prereg_<sha7>.zip.
Files come from `git archive <commit>` (committed content only); README.md from the same commit.
"""
import argparse
import hashlib
import io
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [
    "release/zenodo_expC/README.md",
    "prereg/prereg_expC.md",
    "data/expB/frozen_rules_v1.json",
    "data/expC/forecast_v1.json",
    "pgg_analysis_expC.py", "pgg_analysis_expB.py", "pgg_analysis_expA.py", "pgg_analysis_rules.py",
    "pgg_analysis.py", "llm_client.py",
    "frames/abstract_v4.json", "frames/abstract_v4_n8.json", "frames/abstract_v4_n16.json",
    "frames/abstract_v4_n32.json",
    "cards/expA_cards_v1.json",
    *[f"configs/expC_n{n}_{k}.json" for n in (4, 8, 16, 32) for k in ("smoke", "main")],
    "requirements.lock.txt",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", default="HEAD")
    sha = subprocess.check_output(["git", "rev-parse", ap.parse_args().commit], cwd=ROOT, text=True).strip()
    tar = subprocess.check_output(["git", "archive", sha, *FILES], cwd=ROOT)
    out = ROOT / "release" / "zenodo_expC" / "build"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        t.extractall(out, filter="data")
    (out / "README.md").write_bytes((out / "release/zenodo_expC/README.md").read_bytes())
    shutil.rmtree(out / "release")
    (out / "SOURCE_COMMIT.txt").write_text(f"{sha}\n")
    lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out)}"
             for p in sorted(x for x in out.rglob("*") if x.is_file())]
    (out / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")
    z = out.parent / f"expC_prereg_{sha[:7]}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(x for x in out.rglob("*") if x.is_file()):
            zf.write(p, p.relative_to(out))
    print(f"commit {sha}\n{len(lines)} files\nzip {z} sha256 {hashlib.sha256(z.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
