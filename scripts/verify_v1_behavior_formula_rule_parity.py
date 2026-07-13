#!/usr/bin/env python3
"""Mechanical verifier for the V1 behavior/formula/rule parity map."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


PASS_MARKER = "V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP_PASS"
FAIL_MARKER = "V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP_FAIL"
ALLOWED_STATUSES = {
    "BEHAVIOR_EXACT_MATCH_REQUIRED",
    "BEHAVIOR_NUMERIC_TOLERANCE_ALLOWED",
    "BEHAVIOR_STRUCTURAL_EQUIVALENCE_ALLOWED",
    "BEHAVIOR_INTENTIONAL_CHANGE_REQUIRED",
    "BEHAVIOR_NOT_APPLICABLE_WITH_REASON",
    "BEHAVIOR_UNMAPPED_FAIL",
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
FORMULA_SOURCE_TYPES = {
    "V1_FORMULA_BEHAVIOR",
    "V1_TAX_FIXATION_BEHAVIOR",
    "V1_PENSION_LOGIC_BEHAVIOR",
    "V1_SCENARIO_BEHAVIOR",
}
EMPTY_VALUES = {"", "none", "not applicable", "n/a", "unknown"}


@dataclass(frozen=True)
class BehaviorRow:
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
    behavior_id: str
    expected: str
    actual: str
    source_file: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def parse_behavior_rows(text: str) -> list[BehaviorRow]:
    rows: list[BehaviorRow] = []
    for line in text.splitlines():
        if not re.match(r"^\|\s*V1BEHAVIOR-\d{3}\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 25:
            rows.append(BehaviorRow(*cells))
    return rows


def nonempty(value: str) -> bool:
    return value.strip().lower() not in EMPTY_VALUES


def is_formula_row(row: BehaviorRow) -> bool:
    if row.source_type in FORMULA_SOURCE_TYPES:
        return True
    combined = " ".join((row.summary, row.formula, row.business_rule)).lower()
    return bool(re.search(r"formula|calculation|calculate|tax|fixation|pension|indexation|cpi|scenario|cashflow|annuity|coefficient|commutation|capitalization", combined))


def add_failure(
    failures: list[Failure],
    code: str,
    behavior_id: str,
    expected: str,
    actual: str,
    source_file: Path,
) -> None:
    failures.append(Failure(code, behavior_id or "not_applicable", expected, actual, str(source_file)))


def verify(repo_root: Path) -> tuple[list[Failure], dict[str, int]]:
    map_path = repo_root / "specs/runtime/V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP.md"
    v1item_path = repo_root / "specs/runtime/V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP.md"
    universe_path = repo_root / "specs/runtime/V2_REQUIRED_CAPABILITY_UNIVERSE.md"
    failures: list[Failure] = []
    try:
        map_text = map_path.read_text(encoding="utf-8")
        v1item_text = v1item_path.read_text(encoding="utf-8")
        universe_text = universe_path.read_text(encoding="utf-8")
    except OSError as exc:
        add_failure(failures, "REQUIRED_FILE_READ_ERROR", "", "all required files readable", str(exc), map_path)
        return failures, {}

    rows = parse_behavior_rows(map_text)
    if not rows:
        add_failure(failures, "BEHAVIOR_INVENTORY_EMPTY", "", "one or more behavior rows", "0", map_path)

    ids = [row.behavior_id for row in rows]
    expected_ids = [f"V1BEHAVIOR-{index:03d}" for index in range(1, len(rows) + 1)]
    if len(ids) != len(set(ids)):
        add_failure(failures, "DUPLICATE_BEHAVIOR_ID", "", "unique behavior IDs", "duplicates present", map_path)
    if ids != expected_ids:
        add_failure(
            failures,
            "NON_SEQUENTIAL_BEHAVIOR_ID",
            "",
            f"V1BEHAVIOR-001..V1BEHAVIOR-{len(rows):03d}",
            ",".join(ids[:5]) + ("..." if len(ids) > 5 else ""),
            map_path,
        )

    known_v1items = set(re.findall(r"\bV1ITEM-\d{3}\b", v1item_text))
    known_reqs = set(re.findall(r"\bREQ-\d{3}\b", universe_text))
    req_reference_count = 0
    v1item_reference_count = 0
    formula_rows_checked = 0
    golden_tests_required = 0

    for row in rows:
        if row.status not in ALLOWED_STATUSES:
            add_failure(failures, "INVALID_BEHAVIOR_STATUS", row.behavior_id, "allowed status", row.status, map_path)
        if row.parity_mode != row.status:
            add_failure(failures, "PARITY_STATUS_MISMATCH", row.behavior_id, row.status, row.parity_mode, map_path)
        if row.status == "BEHAVIOR_UNMAPPED_FAIL":
            add_failure(failures, "BEHAVIOR_UNMAPPED_FAIL_PRESENT", row.behavior_id, "mapped or classified behavior", row.status, map_path)

        item_refs = re.findall(r"\bV1ITEM-\d{3}\b", row.v1item_ids)
        v1item_reference_count += len(item_refs)
        if not item_refs:
            if row.source_type != "V1_MANUAL_DOMAIN_BEHAVIOR" or row.reviewer_decision != "YES":
                add_failure(
                    failures,
                    "MISSING_V1ITEM_REFERENCE",
                    row.behavior_id,
                    "V1ITEM reference or manual-domain row with reviewer YES",
                    row.v1item_ids,
                    v1item_path,
                )
        for item_ref in item_refs:
            if item_ref not in known_v1items:
                add_failure(failures, "UNKNOWN_V1ITEM_REFERENCE", row.behavior_id, "existing V1ITEM ID", item_ref, v1item_path)

        reqs = re.findall(r"\bREQ-\d{3}\b", row.req_ids)
        req_reference_count += len(reqs)
        if row.status != "BEHAVIOR_NOT_APPLICABLE_WITH_REASON" and not reqs:
            add_failure(failures, "MISSING_REQ_REFERENCE", row.behavior_id, "at least one REQ ID", row.req_ids, universe_path)
        for req in reqs:
            if req not in known_reqs:
                add_failure(failures, "UNKNOWN_REQ_REFERENCE", row.behavior_id, "existing Universe REQ", req, universe_path)

        required_fields = {
            "business behavior summary": row.summary,
            "V1 evidence source file": row.evidence_file,
            "V1 evidence reference": row.evidence_reference,
            "required V2 behavior": row.required_v2,
        }
        for field_name, value in required_fields.items():
            if not nonempty(value):
                add_failure(failures, "MISSING_REQUIRED_BEHAVIOR_FIELD", row.behavior_id, f"non-empty {field_name}", value or "empty", map_path)

        if is_formula_row(row):
            formula_rows_checked += 1
            if row.status not in {"BEHAVIOR_INTENTIONAL_CHANGE_REQUIRED", "BEHAVIOR_NOT_APPLICABLE_WITH_REASON"}:
                for field_name, value in {
                    "input fields": row.inputs,
                    "output fields": row.outputs,
                    "formula or business rule": row.formula if nonempty(row.formula) else row.business_rule,
                }.items():
                    if not nonempty(value):
                        add_failure(failures, "FORMULA_ROW_FIELD_MISSING", row.behavior_id, f"non-empty {field_name}", value or "empty", map_path)
                if row.golden_test != "YES":
                    add_failure(failures, "FORMULA_ROW_GOLDEN_TEST_REQUIRED", row.behavior_id, "YES", row.golden_test, map_path)

        if row.golden_test == "YES":
            golden_tests_required += 1
        if row.status == "BEHAVIOR_NUMERIC_TOLERANCE_ALLOWED" and not nonempty(row.tolerance):
            add_failure(failures, "NUMERIC_TOLERANCE_MISSING", row.behavior_id, "explicit tolerance", row.tolerance or "empty", map_path)
        if row.status == "BEHAVIOR_INTENTIONAL_CHANGE_REQUIRED":
            if not nonempty(row.notes):
                add_failure(failures, "INTENTIONAL_CHANGE_REASON_MISSING", row.behavior_id, "explicit reason in notes", row.notes or "empty", map_path)
            if row.reviewer_decision != "YES":
                add_failure(failures, "INTENTIONAL_CHANGE_REVIEW_REQUIRED", row.behavior_id, "YES", row.reviewer_decision, map_path)
        if row.status == "BEHAVIOR_NOT_APPLICABLE_WITH_REASON" and not nonempty(row.notes):
            add_failure(failures, "NOT_APPLICABLE_REASON_MISSING", row.behavior_id, "explicit reason in notes", row.notes or "empty", map_path)

    high_risk_match = re.search(
        r"^## 5\. High-Risk Domain Coverage Table\s*$\n(?P<body>.*?)(?=^## 6\.)",
        map_text,
        re.MULTILINE | re.DOTALL,
    )
    high_risk_text = high_risk_match.group("body") if high_risk_match else ""
    for domain in HIGH_RISK_DOMAINS:
        pattern = re.compile(rf"^\|\s*{re.escape(domain)}\s*\|", re.MULTILINE)
        if not pattern.search(high_risk_text):
            add_failure(failures, "HIGH_RISK_DOMAIN_MISSING", "", domain, "missing", map_path)

    pass_count = map_text.count(PASS_MARKER)
    fail_count = map_text.count(FAIL_MARKER)
    if pass_count != 1 or fail_count != 0:
        add_failure(
            failures,
            "INVALID_FINAL_MARKER",
            "",
            "exactly one PASS marker and zero FAIL markers",
            f"PASS={pass_count}; FAIL={fail_count}",
            map_path,
        )

    counts = {
        "v1_behaviors_checked": len(rows),
        "behavior_unmapped_fail": sum(row.status == "BEHAVIOR_UNMAPPED_FAIL" for row in rows),
        "req_references_checked": req_reference_count,
        "v1item_references_checked": v1item_reference_count,
        "formula_rows_checked": formula_rows_checked,
        "golden_tests_required": golden_tests_required,
        "high_risk_domains_checked": len(HIGH_RISK_DOMAINS),
    }
    return failures, counts


def main() -> int:
    args = parse_args()
    failures, counts = verify(args.repo_root.resolve())
    if failures:
        print("V1_BEHAVIOR_FORMULA_RULE_PARITY_VERIFICATION_FAIL")
        for failure in failures:
            print(
                f"failure_code={failure.code}; V1_behavior_id={failure.behavior_id}; "
                f"expected={failure.expected}; actual={failure.actual}; source_file={failure.source_file}"
            )
        return 1
    print("V1_BEHAVIOR_FORMULA_RULE_PARITY_VERIFICATION_PASS")
    for key in (
        "v1_behaviors_checked",
        "behavior_unmapped_fail",
        "req_references_checked",
        "v1item_references_checked",
        "formula_rows_checked",
        "golden_tests_required",
        "high_risk_domains_checked",
    ):
        print(f"{key}={counts[key]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
