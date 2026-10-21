"""Point every config at an unpacked copy of the run directories (for reproducing the analyses
from the release). Usage: python scripts/set_runs_dir.py /abs/path/to/runs
The configs record the author's runs directory; the analysis scripts read it from there.
The pilot configs keep their recorded path: the pilot runs are not in the release, and a test
checks the approved pilot config values, including this path."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEEP = {"pilot.json", "minipilot.json"}


def main() -> int:
    if len(sys.argv) != 2 or not Path(sys.argv[1]).is_absolute() or not Path(sys.argv[1]).is_dir():
        print("usage: python scripts/set_runs_dir.py /absolute/path/to/runs", file=sys.stderr)
        return 2
    n = 0
    for p in sorted((ROOT / "configs").glob("*.json")):
        c = json.loads(p.read_text(encoding="utf-8"))
        if "runs_dir" in c and p.name not in KEEP:
            c["runs_dir"] = sys.argv[1]
            p.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            n += 1
    print(f"runs_dir set in {n} configs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
