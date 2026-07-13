#!/usr/bin/env python3
"""Summarize the committed raw V1 source-logic coverage failure baseline."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


KNOWN_TOTAL = 6736
KNOWN_UNCOVERED = 6457
KNOWN_UNCERTAIN = 234
INVENTORY_MARKER = "V1_SOURCE_RAW_LOGIC_INVENTORY_CREATED"
AUDIT_FAIL_MARKER = "V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_FAIL"
AUDIT_PASS_MARKER = "V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_PASS"
UPDATED_BASELINE_RE = re.compile(
    r"V1_SOURCE_RAW_LOGIC_UPDATED_BASELINE\s+"
    r"v1logic_items_total=(\d+)\s+uncovered_fail=(\d+)\s+source_uncertain_fail=(\d+)"
)
HIGH_RISK_DOMAINS = (
    "Retirement age by gender/date/year",
    "Tax brackets / marginal tax / annual parameters",
    "Tax credit points",
    "Severance grants",
    "Exemptions",
    "Fixation rights / 161D",
    "Indexation / CPI / historical values",
    "CBS/LMAS API access",
    "Clearinghouse parsing/import",
    "Balance ledger construction",
    "Pension coefficient / annuity conversion",
    "Pension portfolio calculations",
    "Capital asset conversion",
    "Scenario generation",
    "Scenario comparison",
    "Cashflow",
    "Reports / PDF / generated forms",
    "Validation / missing info / warnings",
    "Audit / source traceability",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def parse_rows(text: str, width: int) -> list[list[str]]:
    parsed: list[list[str]] = []
    for line in text.splitlines():
        if not re.match(r"^\|\s*V1LOGIC-\d{3,}\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == width:
            parsed.append(cells)
    return parsed


def fail(code: str, expected: str, actual: str, source: Path) -> int:
    print("V1_SOURCE_RAW_LOGIC_FAILURE_SUMMARY_FAIL")
    print(f"failure_code={code}; expected={expected}; actual={actual}; source_file={source}")
    return 1


def main() -> int:
    root = parse_args().repo_root.resolve()
    inventory_path = root / "specs/runtime/V1_SOURCE_RAW_LOGIC_INVENTORY.md"
    audit_path = root / "specs/runtime/V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT.md"
    if not inventory_path.is_file():
        return fail("INVENTORY_FILE_MISSING", "readable inventory", "missing", inventory_path)
    if not audit_path.is_file():
        return fail("AUDIT_FILE_MISSING", "readable audit", "missing", audit_path)
    try:
        inventory_text = inventory_path.read_text(encoding="utf-8")
        audit_text = audit_path.read_text(encoding="utf-8")
    except OSError as exc:
        return fail("FILE_READ_ERROR", "readable UTF-8 files", str(exc), root)

    if inventory_text.count(INVENTORY_MARKER) != 1:
        return fail("INVENTORY_MARKER_INVALID", "exactly one inventory marker", str(inventory_text.count(INVENTORY_MARKER)), inventory_path)
    if audit_text.count(AUDIT_FAIL_MARKER) != 1 or audit_text.count(AUDIT_PASS_MARKER) != 0:
        return fail("AUDIT_FINAL_MARKER_INVALID", "one FAIL and zero PASS markers", f"FAIL={audit_text.count(AUDIT_FAIL_MARKER)}; PASS={audit_text.count(AUDIT_PASS_MARKER)}", audit_path)

    inventory = parse_rows(inventory_text, 22)
    audit = parse_rows(audit_text, 13)
    if not inventory or not audit:
        return fail("COUNTS_CANNOT_BE_PARSED", "non-empty inventory and audit tables", f"inventory={len(inventory)}; audit={len(audit)}", root)
    if len(inventory) != len(audit):
        return fail("COUNTS_CANNOT_BE_PARSED", "one audit row per inventory row", f"inventory={len(inventory)}; audit={len(audit)}", root)

    total = len(inventory)
    uncovered = sum(row[9] == "V1LOGIC_UNCOVERED_FAIL" for row in audit)
    uncertain = sum(row[9] == "V1LOGIC_SOURCE_UNCERTAIN_FAIL" for row in audit)
    statuses = {row[9] for row in audit}
    logic_types = {row[2] for row in inventory}
    update = UPDATED_BASELINE_RE.search(audit_text)
    expected = tuple(map(int, update.groups())) if update else (KNOWN_TOTAL, KNOWN_UNCOVERED, KNOWN_UNCERTAIN)
    actual = (total, uncovered, uncertain)
    if actual != expected:
        code = "UPDATED_BASELINE_MISMATCH" if update else "UNAUTHORIZED_BASELINE_DRIFT"
        return fail(code, f"total/uncovered/uncertain={expected}", f"total/uncovered/uncertain={actual}", audit_path)

    domain_section = re.search(
        r"^## 3\. High-Risk Logic Depth Coverage Table\s*$\n(?P<body>.*?)(?=^## 4\.)",
        audit_text,
        re.MULTILINE | re.DOTALL,
    )
    if not domain_section:
        return fail("HIGH_RISK_SECTION_MISSING", "high-risk section", "missing", audit_path)
    body = domain_section.group("body")
    missing = [domain for domain in HIGH_RISK_DOMAINS if not re.search(rf"^\|\s*{re.escape(domain)}\s*\|", body, re.MULTILINE)]
    if missing:
        return fail("HIGH_RISK_DOMAIN_MISSING", "all 19 required domains", ", ".join(missing), audit_path)

    print("V1_SOURCE_RAW_LOGIC_FAILURE_SUMMARY")
    print(f"v1logic_items_total={total}")
    print(f"uncovered_fail={uncovered}")
    print(f"source_uncertain_fail={uncertain}")
    print(f"coverage_statuses_checked={len(statuses)}")
    print(f"logic_types_checked={len(logic_types)}")
    print(f"high_risk_domains_checked={len(HIGH_RISK_DOMAINS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
