"""Convert docs/project-report.md → docs/project-report.pdf.

Renders markdown to HTML with embedded screenshots using absolute
file:// paths so Chromium always finds the images. Then uses
Playwright headless Chromium to print to PDF.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

SRC = Path("docs/project-report.md")
OUT = Path("docs/project-report.pdf")
DOCS_DIR = Path("docs").resolve()

CSS = """
@page { size: A4; margin: 1.8cm 2cm; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 11pt; line-height: 1.55; color: #1f2937;
}
h1 { font-size: 20pt; color: #0f172a; margin-top: 0; text-align: center; }
h1 + p { text-align: center; font-size: 12pt; color: #475569; }
h2 { font-size: 15pt; color: #1e3a8a; margin-top: 1.4em; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.25em; page-break-after: avoid; }
h3 { font-size: 12pt; color: #334155; margin-top: 1em; page-break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 0.6em 0; font-size: 9.5pt; }
th, td { border: 1px solid #cbd5e1; padding: 5px 8px; text-align: left; }
th { background: #f1f5f9; font-weight: 600; }
tr:nth-child(even) { background: #f8fafc; }
code { background: #f1f5f9; padding: 1px 4px; border-radius: 3px; font-family: Menlo, monospace; font-size: 9pt; }
pre { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 5px; padding: 10px 14px; font-size: 8.5pt; line-height: 1.45; white-space: pre-wrap; word-wrap: break-word; }
pre code { background: none; padding: 0; }
img { max-width: 100%; border: 1px solid #e2e8f0; border-radius: 4px; margin: 0.5em 0; page-break-inside: avoid; }
a { color: #2563eb; text-decoration: none; }
hr { border: none; border-top: 1px solid #e2e8f0; margin: 1.5em 0; }
ul, ol { padding-left: 1.4em; }
li { margin-bottom: 0.2em; }
"""


def _absolutise_image_paths(html: str, base_dir: Path) -> str:
    """Replace relative src= paths with absolute file:// URIs."""
    def replacer(m: re.Match) -> str:
        src = m.group(1)
        if src.startswith(("http://", "https://", "file://", "data:")):
            return m.group(0)
        abs_path = (base_dir / src).resolve()
        if abs_path.exists():
            return f'src="file://{abs_path}"'
        return m.group(0)
    return re.sub(r'src="([^"]+)"', replacer, html)


def main() -> None:
    if not SRC.exists():
        print(f"source not found: {SRC}", file=sys.stderr)
        sys.exit(1)

    md_text = SRC.read_text(encoding="utf-8")

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "sane_lists"],
    )

    # Absolutise image paths so Chromium finds them
    html_body = _absolutise_image_paths(html_body, DOCS_DIR)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><style>{CSS}</style></head>
<body>{html_body}</body>
</html>"""

    # Write intermediate HTML
    html_path = OUT.with_suffix(".html")
    html_path.write_text(full_html, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"file://{html_path.resolve()}", wait_until="load")
        # Wait for images to render
        page.wait_for_timeout(3000)
        page.pdf(
            path=str(OUT),
            format="A4",
            margin={"top": "1.8cm", "bottom": "1.8cm", "left": "2cm", "right": "2cm"},
            print_background=True,
            display_header_footer=True,
            header_template='<span></span>',
            footer_template='<div style="font-size:8px;color:#999;width:100%;text-align:center;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
        )
        browser.close()

    size_kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT}  ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
