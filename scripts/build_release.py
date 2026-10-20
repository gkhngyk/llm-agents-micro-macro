"""Build the public release: the repository at one commit, the analysis outputs, and the run
files with the account identifier removed.

Run: .venv/bin/python scripts/build_release.py [--commit HEAD]
Writes release/full/build/{repo,runs}/, SHA256SUMS.txt and two zips:
  release/full/publicgoods_repo_<sha7>.zip   code, plans, configs, frames, cards, data, paper, results
  release/full/publicgoods_runs_<sha7>.zip   per run: decisions (.jsonl), summary, raw API log (redacted)

Redaction: OpenRouter rate-limit errors carry the account id ('user_id'); it is replaced by
[REDACTED_ACCOUNT_ID]. Absolute local paths are replaced by <PROJECT_ROOT>. Afterwards every
output file is searched for every redacted value and for the id patterns; any hit stops the build.
The values themselves are never printed.
"""
import argparse
import hashlib
import io
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT.parent / "orc" / "data" / "projects" / "PublicGoods" / "workspace" / "runs"
RUNS = ["main_s0b_20261012", "main_s1_20261014", "expA_smoke_20261017", "expA_main_20261017",
        "expB_smoke_20261018", "expB_main_20261018",
        *[f"expC_n{n}_smoke_20261019" for n in (4, 8, 16, 32)],
        *[f"expC_n{n}_main_20261020" for n in (4, 8, 16, 32)]]
ID_PATTERNS = [re.compile(r"user_[A-Za-z0-9]{8,}"), re.compile(r"org[-_][A-Za-z0-9]{8,}"),
               re.compile(r"sk-or-[A-Za-z0-9-]{10,}")]
LOCAL = str(ROOT.parent)


def redact(text: str, found: set) -> str:
    for pat in ID_PATTERNS:
        for m in pat.findall(text):
            found.add(m)
        text = pat.sub("[REDACTED_ACCOUNT_ID]", text)
    return text.replace(LOCAL, "<PROJECT_ROOT>")


def copy_redacted(src: Path, dst: Path, found: set) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(src, encoding="utf-8", errors="strict") as fi, open(dst, "w", encoding="utf-8") as fo:
        for line in fi:
            fo.write(redact(line, found))


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def zip_dir(src: Path, z: Path) -> None:
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(x for x in src.rglob("*") if x.is_file()):
            zf.write(p, p.relative_to(src.parent))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", default="HEAD")
    commit = subprocess.check_output(["git", "rev-parse", ap.parse_args().commit], cwd=ROOT, text=True).strip()
    out = ROOT / "release" / "full" / "build"
    shutil.rmtree(out, ignore_errors=True)
    repo = out / "repo"
    repo.mkdir(parents=True)
    tar = subprocess.check_output(["git", "archive", commit], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        t.extractall(repo, filter="data")
    shutil.rmtree(repo / "release", ignore_errors=True)        # builders' own outputs
    found: set = set()
    for f in (x for x in repo.rglob("*") if x.is_file()):      # local paths in configs and notes
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = redact(text, found)
        if new != text:
            f.write_text(new, encoding="utf-8")
    for p in sorted((ROOT / "results").glob("*.json")):
        copy_redacted(p, repo / "results" / p.name, found)
    for run in RUNS:
        src = RUNS_DIR / run
        names = [f"{run}.jsonl", "raw_calls.jsonl"] + sorted(x.name for x in src.glob(f"{run}_summary*.json"))
        for name in names:
            copy_redacted(src / name, out / "runs" / run / name, found)
    # verification: no redacted value and no id pattern anywhere in the output
    needles = [v.encode() for v in found] + [LOCAL.encode()]
    hits = 0
    for p in (x for x in out.rglob("*") if x.is_file()):
        data = p.read_bytes()
        hits += sum(data.count(n) for n in needles)
        text = data.decode("utf-8", errors="ignore")
        hits += sum(len(pat.findall(text)) for pat in ID_PATTERNS)
    if hits:
        print(f"DUR: kırpma sonrası {hits} eşleşme kaldı; paket kurulmadı.", file=sys.stderr)
        return 2
    (out / "SOURCE_COMMIT.txt").write_text(commit + "\n")
    lines = [f"{sha(p)}  {p.relative_to(out)}" for p in sorted(x for x in out.rglob("*") if x.is_file())]
    (out / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")
    shutil.copy(out / "SHA256SUMS.txt", repo / "SHA256SUMS_release.txt")
    zr = out.parent / f"publicgoods_repo_{commit[:7]}.zip"
    zu = out.parent / f"publicgoods_runs_{commit[:7]}.zip"
    zip_dir(repo, zr)
    zip_dir(out / "runs", zu)
    print(f"commit {commit}; distinct redacted ids {len(found)}; files {len(lines)}; verification 0 hits")
    for z in (zr, zu):
        print(f"{z.name}: {z.stat().st_size / 1e6:.1f} MB, sha256 {sha(z)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
