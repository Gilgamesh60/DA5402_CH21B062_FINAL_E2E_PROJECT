"""Convert docs/project-report.md → docs/project-report.pdf via Playwright.

Renders markdown to styled HTML, then uses headless Chromium to print to PDF.
No system-level dependencies beyond what Playwright already installed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

SRC = Path("docs/project-report.md")
OUT = Path("docs/project-report.pdf")

CSS = """
@page {
    size: A4;
    margin: 2cm 2.5cm;
}
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1f2937;
    max-width: 100%;
}
h1 { font-size: 22pt; color: #0f172a; margin-top: 0; }
h2 { font-size: 16pt; color: #1e3a8a; margin-top: 1.5em; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.3em; }
h3 { font-size: 13pt; color: #334155; margin-top: 1.2em; }
h4 { font-size: 11pt; color: #475569; }
table { border-collapse: collapse; width: 100%; margin: 0.8em 0; font-size: 10pt; }
th, td { border: 1px solid #cbd5e1; padding: 6px 10px; text-align: left; }
th { background: #f1f5f9; font-weight: 600; }
tr:nth-child(even) { background: #f8fafc; }
code {
    background: #f1f5f9; padding: 1px 4px; border-radius: 3px;
    font-family: "SFMono-Regular", Menlo, monospace; font-size: 9.5pt;
}
pre {
    background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
    padding: 12px 16px; font-size: 9pt; line-height: 1.5;
    overflow-x: auto; white-space: pre-wrap; word-wrap: break-word;
}
pre code { background: none; padding: 0; }
blockquote {
    border-left: 3px solid #2563eb; margin: 1em 0; padding: 0.5em 1em;
    background: #eff6ff; color: #1e40af; font-size: 10pt;
}
a { color: #2563eb; text-decoration: none; }
hr { border: none; border-top: 1px solid #e2e8f0; margin: 2em 0; }
ul, ol { padding-left: 1.5em; }
li { margin-bottom: 0.3em; }
"""


def main() -> None:
    if not SRC.exists():
        print(f"source not found: {SRC}", file=sys.stderr)
        sys.exit(1)

    md_text = SRC.read_text(encoding="utf-8")

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "sane_lists"],
    )

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>{CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    html_path = OUT.with_suffix(".html")
    html_path.write_text(full_html, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(full_html, wait_until="networkidle")
        page.pdf(
            path=str(OUT),
            format="A4",
            margin={"top": "2cm", "bottom": "2cm", "left": "2.5cm", "right": "2.5cm"},
            print_background=True,
            display_header_footer=True,
            header_template='<span></span>',
            footer_template='<div style="font-size:9px;color:#888;width:100%;text-align:center;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
        )
        browser.close()

    print(f"wrote {OUT}  ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
