#!/usr/bin/env python3
"""Verify V1-derived golden-master expected-output case coverage."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


PASS_MARKER = "V1_GOLDEN_MASTER_EXPECTED_OUTPUT_CASES_PASS"
FAIL_MARKER = "V1_GOLDEN_MASTER_EXPECTED_OUTPUT_CASES_FAIL"
ALLOWED_STATUSES = {
    "GOLDEN_CASE_READY",
    "GOLDEN_CASE_MANUAL_DOMAIN_DECISION_REQUIRED",
    "GOLDEN_CASE_NOT_APPLICABLE_WITH_REASON",
    "GOLDEN_CASE_INTENTIONAL_CHANGE_REQUIRED",
    "GOLDEN_CASE_MISSING_FAIL",
}
HIGH_RISK_DOMAINS = (
    "Fixation rights / 161D",
    "Severance grants",
    "Exemptions",
    "Commutation / capitalization",
    "Pension coefficient / annuity logic",
    "Pension portfolio calculations",
    "Capital asset conversion",
    "Indexation / CPI / historical values",
    "Tax brackets / marginal tax / annual parameters",
    "Prisa / spreading if present",
    "Scenario generation",
    "Scenario comparison",
    "Cashflow",
    "Reports / PDF / generated forms",
    "Validation / missing info / warnings",
    "Planner recommendation rules",
    "Audit / traceability behavior",
)
BEHAVIOR_DOMAIN_RE = re.compile(
    r"formula|calculation|report|document|pdf|scenario|tax|fixation|pension|"
    r"indexation|cpi|cashflow|severance|exemption|validation|warning|"
    r"recommendation|audit|trace|capital|commutation",
    re.IGNORECASE,
)
EMPTY_VALUES = {"", "none", "not applicable", "n/a", "unknown", "tbd"}


@dataclass(frozen=True)
class GoldenRow:
    golden_id: str
    behavior_id: str
    v1item_ids: str
    domain: str
    evidence_file: str
    evidence_reference: str
    behavior_summary: str
    input_description: str
    concrete_input: str
    expected_output: str
    intermediates: str
    rounding: str
    validation: str
    generated_output: str
    output_source: str
    future_test_type: str
    req_ids: str
    status: str
    reviewer_decision: str
    missing_note: str
    risk: str


@dataclass(frozen=True)
class BehaviorSourceRow:
    behavior_id: str
    v1item_ids: str
    source_name: str
    source_type: str
    evidence_file: str
    evidence_reference: str
    summary: str
    inputs: str
    outputs: str
    formula: str
    business_rule: str
    edge_cases: str
    rounding: str
    validation: str
    generated_output: str
    required_v2: str
    parity_mode: str
    tolerance: str
    golden_test: str
    expected_output_source: str
    req_ids: str
    planning_target: str
    status: str
    reviewer_decision: str
    notes: str


@dataclass(frozen=True)
class Failure:
    code: str
    golden_id: str
    expected: str
    actual: str
    source_file: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def parse_rows(text: str, prefix: str, width: int, row_type):
    rows = []
    pattern = re.compile(rf"^\|\s*{re.escape(prefix)}-\d{{3}}\s*\|")
    for line in text.splitlines():
        if not pattern.match(line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == width:
            rows.append(row_type(*cells))
    return rows


def nonempty(value: str) -> bool:
    return value.strip().lower() not in EMPTY_VALUES


def add_failure(failures, code, golden_id, expected, actual, source_file):
    failures.append(Failure(code, golden_id or "not_applicable", expected, actual, str(source_file)))


def verify(repo_root: Path):
    case_path = repo_root / "specs/runtime/V1_GOLDEN_MASTER_EXPECTED_OUTPUT_CASES.md"
    behavior_path = repo_root / "specs/runtime/V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP.md"
    v1item_path = repo_root / "specs/runtime/V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP.md"
    universe_path = repo_root / "specs/runtime/V2_REQUIRED_CAPABILITY_UNIVERSE.md"
    failures = []
    try:
        case_text = case_path.read_text(encoding="utf-8")
        behavior_text = behavior_path.read_text(encoding="utf-8")
        v1item_text = v1item_path.read_text(encoding="utf-8")
        universe_text = universe_path.read_text(encoding="utf-8")
    except OSError as exc:
        add_failure(failures, "REQUIRED_FILE_READ_ERROR", "", "all required files readable", str(exc), case_path)
        return failures, {}

    rows = parse_rows(case_text, "V1GOLDEN", 21, GoldenRow)
    behavior_rows = parse_rows(behavior_text, "V1BEHAVIOR", 25, BehaviorSourceRow)
    if not rows:
        add_failure(failures, "GOLDEN_INVENTORY_EMPTY", "", "one or more golden cases", "0", case_path)

    ids = [row.golden_id for row in rows]
    expected_ids = [f"V1GOLDEN-{index:03d}" for index in range(1, len(rows) + 1)]
    if len(ids) != len(set(ids)):
        add_failure(failures, "DUPLICATE_GOLDEN_CASE_ID", "", "unique IDs", "duplicates present", case_path)
    if ids != expected_ids:
        add_failure(failures, "NON_SEQUENTIAL_GOLDEN_CASE_ID", "", f"V1GOLDEN-001..V1GOLDEN-{len(rows):03d}", ",".join(ids[:5]), case_path)

    known_behaviors = {row.behavior_id: row for row in behavior_rows}
    known_v1items = set(re.findall(r"\bV1ITEM-\d{3}\b", v1item_text))
    known_reqs = set(re.findall(r"\bREQ-\d{3}\b", universe_text))
    req_count = behavior_ref_count = item_ref_count = 0

    for row in rows:
        if row.status not in ALLOWED_STATUSES:
            add_failure(failures, "INVALID_GOLDEN_STATUS", row.golden_id, "allowed status", row.status, case_path)
        if row.status == "GOLDEN_CASE_MISSING_FAIL":
            add_failure(failures, "GOLDEN_CASE_MISSING_FAIL_PRESENT", row.golden_id, "non-blocking classified case", row.status, case_path)
        if row.status == "GOLDEN_CASE_MANUAL_DOMAIN_DECISION_REQUIRED":
            add_failure(failures, "MANUAL_DOMAIN_DECISION_PRESENT", row.golden_id, "resolved concrete expected behavior", row.status, case_path)

        behavior_refs = re.findall(r"\bV1BEHAVIOR-\d{3}\b", row.behavior_id)
        behavior_ref_count += len(behavior_refs)
        if not behavior_refs:
            add_failure(failures, "MISSING_BEHAVIOR_REFERENCE", row.golden_id, "one V1BEHAVIOR ID", row.behavior_id, behavior_path)
        for ref in behavior_refs:
            if ref not in known_behaviors:
                add_failure(failures, "UNKNOWN_BEHAVIOR_REFERENCE", row.golden_id, "existing V1BEHAVIOR ID", ref, behavior_path)

        item_refs = re.findall(r"\bV1ITEM-\d{3}\b", row.v1item_ids)
        item_ref_count += len(item_refs)
        for ref in item_refs:
            if ref not in known_v1items:
                add_failure(failures, "UNKNOWN_V1ITEM_REFERENCE", row.golden_id, "existing V1ITEM ID", ref, v1item_path)

        reqs = re.findall(r"\bREQ-\d{3}\b", row.req_ids)
        req_count += len(reqs)
        for ref in reqs:
            if ref not in known_reqs:
                add_failure(failures, "UNKNOWN_REQ_REFERENCE", row.golden_id, "existing REQ ID", ref, universe_path)

        if row.status == "GOLDEN_CASE_READY":
            for field_name, value in {
                "input case description": row.input_description,
                "concrete input fields/payload": row.concrete_input,
                "expected output fields/result": row.expected_output,
                "expected output source": row.output_source,
                "future V2 test type": row.future_test_type,
            }.items():
                if not nonempty(value):
                    add_failure(failures, "READY_CASE_FIELD_MISSING", row.golden_id, f"non-empty {field_name}", value or "empty", case_path)
        if row.status == "GOLDEN_CASE_INTENTIONAL_CHANGE_REQUIRED":
            if not nonempty(row.expected_output) or not nonempty(row.missing_note) or row.reviewer_decision != "YES":
                add_failure(failures, "INTENTIONAL_CHANGE_CASE_INCOMPLETE", row.golden_id, "expected behavior, reason, reviewer YES", f"output={row.expected_output}; note={row.missing_note}; reviewer={row.reviewer_decision}", case_path)
        if row.status == "GOLDEN_CASE_NOT_APPLICABLE_WITH_REASON" and not nonempty(row.missing_note):
            add_failure(failures, "NOT_APPLICABLE_REASON_MISSING", row.golden_id, "explicit reason", row.missing_note or "empty", case_path)

    required_behaviors = set()
    for behavior in behavior_rows:
        combined = " ".join((behavior.source_type, behavior.evidence_reference, behavior.summary, behavior.formula, behavior.generated_output))
        if behavior.golden_test == "YES" or BEHAVIOR_DOMAIN_RE.search(combined):
            required_behaviors.add(behavior.behavior_id)
    covered_behaviors = {ref for row in rows for ref in re.findall(r"\bV1BEHAVIOR-\d{3}\b", row.behavior_id)}
    for behavior_id in sorted(required_behaviors):
        if behavior_id not in covered_behaviors:
            add_failure(failures, "REQUIRED_BEHAVIOR_GOLDEN_CASE_MISSING", "", behavior_id, "not referenced", behavior_path)

    section = re.search(r"^## 4\. Domain Coverage Table\s*$\n(?P<body>.*?)(?=^## 5\.)", case_text, re.MULTILINE | re.DOTALL)
    domain_text = section.group("body") if section else ""
    for domain in HIGH_RISK_DOMAINS:
        if not re.search(rf"^\|\s*{re.escape(domain)}\s*\|", domain_text, re.MULTILINE):
            add_failure(failures, "HIGH_RISK_DOMAIN_MISSING", "", domain, "missing", case_path)

    pass_count = case_text.count(PASS_MARKER)
    fail_count = case_text.count(FAIL_MARKER)
    if pass_count != 1 or fail_count != 0:
        add_failure(failures, "INVALID_FINAL_MARKER", "", "one PASS and zero FAIL markers", f"PASS={pass_count}; FAIL={fail_count}", case_path)

    counts = {
        "golden_cases_checked": len(rows),
        "golden_case_missing_fail": sum(row.status == "GOLDEN_CASE_MISSING_FAIL" for row in rows),
        "manual_domain_decisions": sum(row.status == "GOLDEN_CASE_MANUAL_DOMAIN_DECISION_REQUIRED" for row in rows),
        "behaviors_with_required_golden_tests_checked": len(required_behaviors),
        "req_references_checked": req_count,
        "v1behavior_references_checked": behavior_ref_count,
        "v1item_references_checked": item_ref_count,
        "high_risk_domains_checked": len(HIGH_RISK_DOMAINS),
    }
    return failures, counts


def main() -> int:
    args = parse_args()
    failures, counts = verify(args.repo_root.resolve())
    if failures:
        print("V1_GOLDEN_MASTER_EXPECTED_OUTPUT_VERIFICATION_FAIL")
        for failure in failures:
            print(f"failure_code={failure.code}; Golden_Case_ID={failure.golden_id}; expected={failure.expected}; actual={failure.actual}; source_file={failure.source_file}")
        return 1
    print("V1_GOLDEN_MASTER_EXPECTED_OUTPUT_VERIFICATION_PASS")
    for key in (
        "golden_cases_checked", "golden_case_missing_fail", "manual_domain_decisions",
        "behaviors_with_required_golden_tests_checked", "req_references_checked",
        "v1behavior_references_checked", "v1item_references_checked", "high_risk_domains_checked",
    ):
        print(f"{key}={counts[key]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
