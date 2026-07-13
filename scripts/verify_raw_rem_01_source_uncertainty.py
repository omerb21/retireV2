#!/usr/bin/env python3
"""Verify RAW-REM-01 source-uncertainty triage completeness and integrity."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ALLOWED_OUTCOMES = {
    "SOURCE_CONFIRMED_FOR_FUTURE_MAPPING",
    "SOURCE_FALSE_POSITIVE_WITH_REASON",
    "SOURCE_STILL_UNCERTAIN_BLOCKED",
    "SOURCE_REQUIRES_MANUAL_ARCHIVE_REVIEW",
    "SOURCE_NOT_APPLICABLE_WITH_REASON",
}
PASS_MARKER = "RAW_REM_01_SOURCE_UNCERTAINTY_TRIAGE_PASS"
FAIL_MARKER = "RAW_REM_01_SOURCE_UNCERTAINTY_TRIAGE_FAIL"
DECISIONS_MARKER = "RAW_REM_01_SOURCE_UNCERTAINTY_DECISIONS_CREATED"


@dataclass(frozen=True)
class Failure:
    code: str
    logic_id: str
    expected: str
    actual: str
    source_file: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def parse_rows(text: str, width: int) -> list[list[str]]:
    result = []
    for line in text.splitlines():
        if not re.match(r"^\|\s*V1LOGIC-\d{3,}\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == width:
            result.append(cells)
    return result


def add(failures, code, logic_id, expected, actual, source):
    failures.append(Failure(code, logic_id or "not_applicable", expected, actual, str(source)))


def verify(repo_root: Path):
    paths = {
        "inventory": repo_root / "specs/runtime/V1_SOURCE_RAW_LOGIC_INVENTORY.md",
        "audit": repo_root / "specs/runtime/V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT.md",
        "triage": repo_root / "specs/runtime/raw_remediation/RAW_REM_01_SOURCE_UNCERTAINTY_TRIAGE.md",
        "decisions": repo_root / "specs/runtime/raw_remediation/RAW_REM_01_SOURCE_UNCERTAINTY_DECISIONS.md",
    }
    failures = []
    try:
        text = {key: path.read_text(encoding="utf-8") for key, path in paths.items()}
    except OSError as exc:
        add(failures, "REQUIRED_FILE_READ_ERROR", "", "all required files readable", str(exc), repo_root)
        return failures, {}

    inventory_rows = parse_rows(text["inventory"], 22)
    audit_rows = parse_rows(text["audit"], 13)
    triage_rows = parse_rows(text["triage"], 12)
    decision_rows = parse_rows(text["decisions"], 5)
    inventory_ids = {row[0] for row in inventory_rows}
    uncertain_ids = {row[0] for row in audit_rows if row[9] == "V1LOGIC_SOURCE_UNCERTAIN_FAIL"}
    uncovered_count = sum(row[9] == "V1LOGIC_UNCOVERED_FAIL" for row in audit_rows)

    if len(uncertain_ids) != 234:
        add(failures, "SOURCE_UNCERTAIN_BASELINE_CHANGED", "", "234 source-uncertain IDs", str(len(uncertain_ids)), paths["audit"])
    if uncovered_count != 6457:
        add(failures, "UNCOVERED_BASELINE_CHANGED", "", "6457 uncovered IDs", str(uncovered_count), paths["audit"])
    if text["audit"].count("V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_FAIL") != 1 or text["audit"].count("V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_PASS") != 0:
        add(failures, "ORIGINAL_AUDIT_MARKER_CHANGED", "", "one FAIL and zero PASS markers", "marker mismatch", paths["audit"])

    triage_by_id: dict[str, list[list[str]]] = {}
    decisions_by_id: dict[str, list[list[str]]] = {}
    for row in triage_rows:
        triage_by_id.setdefault(row[0], []).append(row)
    for row in decision_rows:
        decisions_by_id.setdefault(row[0], []).append(row)
    for logic_id in sorted(uncertain_ids):
        if len(triage_by_id.get(logic_id, [])) != 1:
            add(failures, "TRIAGE_CARDINALITY", logic_id, "exactly one triage row", str(len(triage_by_id.get(logic_id, []))), paths["triage"])
        if len(decisions_by_id.get(logic_id, [])) != 1:
            add(failures, "DECISION_CARDINALITY", logic_id, "exactly one decision row", str(len(decisions_by_id.get(logic_id, []))), paths["decisions"])
    for logic_id in sorted(set(decisions_by_id) - uncertain_ids):
        add(failures, "NON_SOURCE_UNCERTAIN_DECISION", logic_id, "original source-uncertain ID", "non-source-uncertain ID", paths["decisions"])

    for row in triage_rows:
        logic_id, outcome, package, blocks = row[0], row[6], row[9], row[10]
        if logic_id not in inventory_ids:
            add(failures, "UNKNOWN_INVENTORY_ID", logic_id, "existing inventory ID", logic_id, paths["inventory"])
        if outcome not in ALLOWED_OUTCOMES:
            add(failures, "INVALID_TRIAGE_OUTCOME", logic_id, "allowed outcome", outcome, paths["triage"])
        if not row[5].strip():
            add(failures, "SOURCE_EVIDENCE_EMPTY", logic_id, "non-empty archive evidence", "empty", paths["triage"])
        if not row[8].strip():
            add(failures, "DECISION_REASON_EMPTY", logic_id, "non-empty reason", "empty", paths["triage"])
        if blocks not in {"YES", "NO"}:
            add(failures, "INVALID_BLOCKS_VALUE", logic_id, "YES or NO", blocks, paths["triage"])
        if outcome == "SOURCE_CONFIRMED_FOR_FUTURE_MAPPING" and not re.fullmatch(r"RAW-REM-(?:0[2-9]|10)", package):
            add(failures, "CONFIRMED_NEXT_PACKAGE_INVALID", logic_id, "RAW-REM-02..RAW-REM-10", package or "empty", paths["triage"])
        if outcome in {"SOURCE_STILL_UNCERTAIN_BLOCKED", "SOURCE_REQUIRES_MANUAL_ARCHIVE_REVIEW"} and blocks != "YES":
            add(failures, "BLOCKING_OUTCOME_NOT_BLOCKING", logic_id, "YES", blocks, paths["triage"])
        if outcome in {"SOURCE_FALSE_POSITIVE_WITH_REASON", "SOURCE_NOT_APPLICABLE_WITH_REASON"} and not row[8].strip():
            add(failures, "CLASSIFICATION_REASON_EMPTY", logic_id, "explicit source-grounded reason", "empty", paths["triage"])

    for row in decision_rows:
        logic_id, outcome, blocks, package, reason = row
        if outcome not in ALLOWED_OUTCOMES:
            add(failures, "INVALID_DECISION_OUTCOME", logic_id, "allowed outcome", outcome, paths["decisions"])
        if not reason.strip():
            add(failures, "DECISION_SUMMARY_REASON_EMPTY", logic_id, "non-empty reason", "empty", paths["decisions"])
        if blocks not in {"YES", "NO"}:
            add(failures, "INVALID_DECISION_BLOCKS_VALUE", logic_id, "YES or NO", blocks, paths["decisions"])
        if outcome == "SOURCE_CONFIRMED_FOR_FUTURE_MAPPING" and not re.fullmatch(r"RAW-REM-(?:0[2-9]|10)", package):
            add(failures, "DECISION_CONFIRMED_PACKAGE_INVALID", logic_id, "RAW-REM-02..RAW-REM-10", package or "empty", paths["decisions"])
        if outcome in {"SOURCE_STILL_UNCERTAIN_BLOCKED", "SOURCE_REQUIRES_MANUAL_ARCHIVE_REVIEW"} and blocks != "YES":
            add(failures, "DECISION_BLOCKING_OUTCOME_NOT_BLOCKING", logic_id, "YES", blocks, paths["decisions"])
        triage = triage_by_id.get(logic_id, [])
        if len(triage) == 1 and (outcome, blocks, package, reason) != (triage[0][6], triage[0][10], triage[0][9], triage[0][8]):
            add(failures, "TRIAGE_DECISION_MISMATCH", logic_id, "matching outcome/blocks/package/reason", "values differ", paths["decisions"])

    if text["triage"].count(PASS_MARKER) != 1 or text["triage"].count(FAIL_MARKER) != 0:
        add(failures, "INVALID_TRIAGE_FINAL_MARKER", "", "one PASS and zero FAIL markers", f"PASS={text['triage'].count(PASS_MARKER)}; FAIL={text['triage'].count(FAIL_MARKER)}", paths["triage"])
    if text["decisions"].count(DECISIONS_MARKER) != 1:
        add(failures, "INVALID_DECISIONS_MARKER", "", "exactly one decisions marker", str(text["decisions"].count(DECISIONS_MARKER)), paths["decisions"])

    outcome_counts = Counter(row[1] for row in decision_rows if row[0] in uncertain_ids)
    counts = {
        "source_uncertain_items_checked": len(uncertain_ids),
        "confirmed_for_future_mapping": outcome_counts["SOURCE_CONFIRMED_FOR_FUTURE_MAPPING"],
        "false_positive": outcome_counts["SOURCE_FALSE_POSITIVE_WITH_REASON"],
        "still_uncertain_blocked": outcome_counts["SOURCE_STILL_UNCERTAIN_BLOCKED"],
        "manual_archive_review": outcome_counts["SOURCE_REQUIRES_MANUAL_ARCHIVE_REVIEW"],
        "not_applicable": outcome_counts["SOURCE_NOT_APPLICABLE_WITH_REASON"],
        "remaining_blocking": sum(row[2] == "YES" for row in decision_rows if row[0] in uncertain_ids),
    }
    return failures, counts


def main() -> int:
    failures, counts = verify(parse_args().repo_root.resolve())
    if failures:
        print("RAW_REM_01_SOURCE_UNCERTAINTY_VERIFICATION_FAIL")
        for failure in failures:
            print(f"failure_code={failure.code}; V1_Logic_ID={failure.logic_id}; expected={failure.expected}; actual={failure.actual}; source_file={failure.source_file}")
        return 1
    print("RAW_REM_01_SOURCE_UNCERTAINTY_VERIFICATION_PASS")
    for key, value in counts.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
