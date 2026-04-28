"""Generate `docs/test-report.md` from pytest JUnit XML + acceptance JSON.

The rubric specifically asks for: test plan, test case enlistment, test
report with pass/fail counts, acceptance criteria, and whether they're
met. This script produces item 3 + item 5. Items 1-2-4 live as doc files.
"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

REPORT_OUT = Path("docs/test-report.md")


def _parse_junit(junit_xml: Path) -> dict:
    """Pull aggregate counts + per-suite breakdown from JUnit XML."""
    root = ET.parse(junit_xml).getroot()
    # pytest emits <testsuites> with nested <testsuite>. Accept either.
    suites = (
        list(root) if root.tag == "testsuites" else [root]
    )
    total = failed = errored = skipped = 0
    per_file: dict[str, dict[str, int]] = {}
    failures: list[dict[str, str]] = []
    for s in suites:
        for case in s.findall("testcase"):
            total += 1
            file = case.attrib.get("classname", "").replace(".", "/") or "unknown"
            row = per_file.setdefault(
                file, {"total": 0, "failed": 0, "errored": 0, "skipped": 0}
            )
            row["total"] += 1
            if case.find("failure") is not None:
                failed += 1
                row["failed"] += 1
                failures.append(
                    {
                        "test": case.attrib.get("name", "?"),
                        "file": file,
                        "message": (case.find("failure").attrib.get("message") or "")[:200],
                    }
                )
            elif case.find("error") is not None:
                errored += 1
                row["errored"] += 1
                failures.append(
                    {
                        "test": case.attrib.get("name", "?"),
                        "file": file,
                        "message": (case.find("error").attrib.get("message") or "")[:200],
                    }
                )
            elif case.find("skipped") is not None:
                skipped += 1
                row["skipped"] += 1
    passed = total - failed - errored - skipped
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errored": errored,
        "skipped": skipped,
        "per_file": per_file,
        "failures": failures,
    }


def _render(junit: dict, acceptance: dict | None) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [
        "# Test Report",
        "",
        f"Generated: **{now}**",
        "",
        "This report is generated from `artifacts/junit.xml` and "
        "`artifacts/acceptance_report.json`. Regenerate with `make test-report`.",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Total tests | {junit['total']} |",
        f"| Passed | {junit['passed']} |",
        f"| Failed | {junit['failed']} |",
        f"| Errored | {junit['errored']} |",
        f"| Skipped | {junit['skipped']} |",
    ]
    if junit["total"]:
        pct = round(junit["passed"] / junit["total"] * 100, 1)
        lines.append(f"| Pass rate | **{pct}%** |")
    lines.append("")

    # Per-suite breakdown
    lines.append("## Results by file")
    lines.append("")
    lines.append("| File | Total | Passed | Failed | Errored | Skipped |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for file, row in sorted(junit["per_file"].items()):
        passed_n = row["total"] - row["failed"] - row["errored"] - row["skipped"]
        lines.append(
            f"| `{file}` | {row['total']} | {passed_n} | "
            f"{row['failed']} | {row['errored']} | {row['skipped']} |"
        )
    lines.append("")

    # Failures
    if junit["failures"]:
        lines.append("## Failures")
        lines.append("")
        for f in junit["failures"]:
            lines.append(f"- **{f['test']}** (`{f['file']}`) — {f['message']}")
        lines.append("")

    # Acceptance criteria
    lines.append("## Acceptance criteria")
    lines.append("")
    if not acceptance:
        lines.append("_Acceptance verification not yet run. Execute `python scripts/verify_acceptance.py` and regenerate._")
    else:
        lines.append(f"Generated: {acceptance['generated_at']}")
        overall = "PASS" if acceptance["all_passed"] else "FAIL"
        lines.append(f"")
        lines.append(f"**Overall: {overall}**")
        lines.append("")
        lines.append("| Criterion | Target | Actual | Status |")
        lines.append("|---|---|---|---|")
        for name, c in acceptance["checks"].items():
            target = (
                c.get("target_ms")
                or c.get("target_pct")
                or c.get("target_s")
                or c.get("target_min")
            )
            # Derive actual from whichever key applies
            actual_val = (
                c.get("actual_ms")
                if "actual_ms" in c
                else c.get("actual_pct")
                if "actual_pct" in c
                else c.get("actual")
            )
            if actual_val is None and "passed" in c:
                actual_val = "reached" if c["passed"] else "not reached"
            status = "PASS" if c["passed"] else "FAIL"
            lines.append(f"| {name} | {target} | {actual_val} | {status} |")
        lines.append("")
        raw = acceptance["raw"]["predict"]
        lines.append("### Raw /predict timings")
        lines.append("")
        lines.append(
            f"- requests: {raw['requests']}, successful: {raw['successful']}, errors: {raw['errors']}"
        )
        lines.append(
            f"- p50: {raw['p50_ms']}ms, p95: {raw['p95_ms']}ms, mean: {raw['mean_ms']}ms"
        )
        lines.append("")

    lines.append("## Links")
    lines.append("")
    lines.append("- [Test plan](test-plan.md)")
    lines.append("- [Acceptance criteria](acceptance-criteria.md)")
    lines.append("- [Phase log](phase-log.md)")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description="Generate docs/test-report.md")
    p.add_argument("--junit", default="artifacts/junit.xml")
    p.add_argument("--acceptance", default="artifacts/acceptance_report.json")
    p.add_argument("--out", default=str(REPORT_OUT))
    args = p.parse_args()

    junit_path = Path(args.junit)
    if not junit_path.exists():
        raise SystemExit(f"junit.xml not found at {junit_path}; run pytest first")
    junit = _parse_junit(junit_path)

    acceptance_path = Path(args.acceptance)
    acceptance = (
        json.loads(acceptance_path.read_text())
        if acceptance_path.exists()
        else None
    )

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(_render(junit, acceptance), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
