"""Render a paper markdown file to PDF (markdown -> HTML -> WeasyPrint).

Run with a Python that has `markdown` and `weasyprint` (here: /opt/miniconda3/bin/python):
  python scripts/build_pdf.py paper/preprint_v2.md paper/preprint_v2.pdf
Images are resolved relative to the markdown file. Strikethrough (~~x~~) is rendered as <del>.
"""
import re
import sys
from pathlib import Path

import markdown
from weasyprint import HTML

CSS = """
@page { size: A4; margin: 22mm 20mm 22mm 20mm;
        @bottom-center { content: counter(page); font-size: 9pt; color: #555; } }
body { font-family: "Charter", "Georgia", "Times New Roman", serif; font-size: 10.5pt; line-height: 1.42; color: #111; }
h1 { font-size: 17pt; line-height: 1.25; margin: 0 0 6pt 0; text-align: center; }
p.subtitle { text-align: center; font-style: italic; font-size: 11pt; margin: 0 0 16pt 0; }
div.titleblock { text-align: center; line-height: 1.45; margin: 0 0 12pt 0; }
h1 + div.titleblock { margin-top: 14pt; }
p.note { font-size: 9pt; color: #333; margin: 6pt 0 8pt 0; }
h2 { font-size: 13pt; margin: 16pt 0 6pt 0; border-bottom: 0.5pt solid #999; padding-bottom: 2pt; }
h3 { font-size: 11pt; margin: 12pt 0 4pt 0; }
p { margin: 0 0 7pt 0; text-align: justify; hyphens: auto; }
ul, ol { margin: 0 0 7pt 0; padding-left: 16pt; }
li { margin: 0 0 2pt 0; }
table { border-collapse: collapse; margin: 6pt 0 10pt 0; font-size: 8.8pt; width: 100%; }
th, td { border-top: 0.4pt solid #bbb; border-bottom: 0.4pt solid #bbb; padding: 2.5pt 4pt; vertical-align: top; }
th { background: #f2f2f2; text-align: left; }
img { width: 100%; margin: 6pt 0 2pt 0; }
code { font-family: "Menlo", monospace; font-size: 8.6pt; }
hr { border: 0; border-top: 0.5pt solid #999; margin: 10pt 0; }
em { font-style: italic; }
"""


LIST = re.compile(r"^(\s*)([-*]|\d+\.)\s")


def fix_lists(text: str) -> str:
    """Python-Markdown needs a blank line before a list and 4-space nesting; the drafts use
    GitHub style (no blank line after "...:" and 2-space nesting)."""
    out, prev = [], ""
    for line in text.split("\n"):
        m = LIST.match(line)
        if m:
            indent = len(m.group(1))
            if indent in (2, 3):
                line = "    " + line.lstrip(" ")
            if prev.strip() and not LIST.match(prev) and not prev.startswith("    ") and indent == 0:
                out.append("")
        out.append(line)
        prev = line
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    text = src.read_text(encoding="utf-8")
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)
    text = fix_lists(text)
    body = markdown.markdown(text, extensions=["tables", "sane_lists"])
    html = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"
    HTML(string=html, base_url=str(src.parent.resolve())).write_pdf(str(dst))
    print(f"yazıldı: {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
