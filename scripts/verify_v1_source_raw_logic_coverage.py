#!/usr/bin/env python3
"""Verify raw V1 source-logic coverage against the existing proof controls."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


INVENTORY_MARKER = "V1_SOURCE_RAW_LOGIC_INVENTORY_CREATED"
PASS_MARKER = "V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_PASS"
FAIL_MARKER = "V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_FAIL"
ALLOWED_TYPES = {
    "V1LOGIC_FUNCTION", "V1LOGIC_CLASS_METHOD", "V1LOGIC_ENDPOINT_HANDLER",
    "V1LOGIC_FORMULA", "V1LOGIC_CONSTANT", "V1LOGIC_BUSINESS_RULE",
    "V1LOGIC_VALIDATION_RULE", "V1LOGIC_WARNING_ERROR_RULE",
    "V1LOGIC_PARSER_RULE", "V1LOGIC_NORMALIZATION_RULE",
    "V1LOGIC_CLASSIFICATION_RULE", "V1LOGIC_EXTERNAL_DATA_API",
    "V1LOGIC_INDEXATION_CPI", "V1LOGIC_TAX_PARAMETER",
    "V1LOGIC_RETIREMENT_AGE_RULE", "V1LOGIC_PENSION_COEFFICIENT_RULE",
    "V1LOGIC_BALANCE_LEDGER_RULE", "V1LOGIC_SCENARIO_CASHFLOW_RULE",
    "V1LOGIC_REPORT_OUTPUT_FIELD", "V1LOGIC_PDF_FORM_OUTPUT",
    "V1LOGIC_AUDIT_TRACE_RULE", "V1LOGIC_TEST_ASSERTION",
    "V1LOGIC_EXPECTED_VALUE", "V1LOGIC_FIXTURE_SAMPLE",
}
ALLOWED_STATUSES = {
    "V1LOGIC_COVERED_BY_BEHAVIOR_AND_GOLDEN",
    "V1LOGIC_COVERED_BY_BEHAVIOR_ONLY_GOLDEN_NOT_REQUIRED",
    "V1LOGIC_COVERED_BY_INTENTIONAL_CHANGE",
    "V1LOGIC_NOT_APPLICABLE_WITH_REASON",
    "V1LOGIC_UNCOVERED_FAIL",
    "V1LOGIC_SOURCE_UNCERTAIN_FAIL",
}
GOLDEN_REQUIRED_TYPES = {
    "V1LOGIC_FORMULA", "V1LOGIC_VALIDATION_RULE", "V1LOGIC_WARNING_ERROR_RULE",
    "V1LOGIC_PARSER_RULE", "V1LOGIC_NORMALIZATION_RULE",
    "V1LOGIC_CLASSIFICATION_RULE", "V1LOGIC_INDEXATION_CPI",
    "V1LOGIC_TAX_PARAMETER", "V1LOGIC_RETIREMENT_AGE_RULE",
    "V1LOGIC_PENSION_COEFFICIENT_RULE", "V1LOGIC_BALANCE_LEDGER_RULE",
    "V1LOGIC_SCENARIO_CASHFLOW_RULE", "V1LOGIC_REPORT_OUTPUT_FIELD",
    "V1LOGIC_PDF_FORM_OUTPUT", "V1LOGIC_EXPECTED_VALUE",
}
BEHAVIOR_REQUIRED_TYPES = GOLDEN_REQUIRED_TYPES | {"V1LOGIC_EXTERNAL_DATA_API"}
HIGH_RISK_DOMAINS = (
    "Retirement age by gender/date/year",
    "Tax brackets / marginal tax / annual parameters",
    "Tax credit points", "Severance grants", "Exemptions",
    "Fixation rights / 161D", "Indexation / CPI / historical values",
    "CBS/LMAS API access", "Clearinghouse parsing/import",
    "Balance ledger construction", "Pension coefficient / annuity conversion",
    "Pension portfolio calculations", "Capital asset conversion",
    "Scenario generation", "Scenario comparison", "Cashflow",
    "Reports / PDF / generated forms", "Validation / missing info / warnings",
    "Audit / source traceability",
)
USER_CHALLENGES = (
    "retirement age by gender",
    "tax brackets and credit points",
    "clearinghouse file analysis and balance ledger",
    "balance conversion to annuity/capital assets and pension coefficients",
    "fixation rights with indexation formula",
    "CBS/LMAS API access for CPI/indexation",
)


@dataclass(frozen=True)
class InventoryRow:
    logic_id: str; name: str; logic_type: str; source_file: str; source_ref: str
    evidence: str; purpose: str; inputs: str; outputs: str; rule: str
    edge_cases: str; rounding: str; external: str; validation: str
    generated: str; related: str; v1items: str; behaviors: str; goldens: str
    reqs: str; raw_status: str; notes: str


@dataclass(frozen=True)
class AuditRow:
    logic_id: str; logic_type: str; name: str; source: str; required: str
    v1items: str; behaviors: str; goldens: str; reqs: str; status: str
    failure_reason: str; required_patch: str; notes: str


@dataclass(frozen=True)
class Failure:
    code: str; logic_id: str; expected: str; actual: str; source_file: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def rows(text: str, prefix: str, width: int, row_type):
    result = []
    for line in text.splitlines():
        if not re.match(rf"^\|\s*{prefix}-\d{{3,}}\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == width:
            result.append(row_type(*cells))
    return result


def refs(value: str, prefix: str) -> list[str]:
    return re.findall(rf"\b{prefix}-\d{{3}}\b", value)


def section(text: str, start: str, end: str) -> str:
    match = re.search(rf"^{re.escape(start)}\s*$\n(?P<body>.*?)(?=^{re.escape(end)}\s*$)", text, re.MULTILINE | re.DOTALL)
    return match.group("body") if match else ""


def add(failures, code, logic_id, expected, actual, source):
    failures.append(Failure(code, logic_id or "not_applicable", expected, actual, str(source)))


def verify(repo_root: Path):
    paths = {
        "inventory": repo_root / "specs/runtime/V1_SOURCE_RAW_LOGIC_INVENTORY.md",
        "audit": repo_root / "specs/runtime/V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT.md",
        "items": repo_root / "specs/runtime/V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP.md",
        "behaviors": repo_root / "specs/runtime/V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP.md",
        "goldens": repo_root / "specs/runtime/V1_GOLDEN_MASTER_EXPECTED_OUTPUT_CASES.md",
        "reqs": repo_root / "specs/runtime/V2_REQUIRED_CAPABILITY_UNIVERSE.md",
    }
    failures = []
    try:
        text = {key: path.read_text(encoding="utf-8") for key, path in paths.items()}
    except OSError as exc:
        add(failures, "REQUIRED_FILE_READ_ERROR", "", "all required files readable", str(exc), repo_root)
        return failures, {}

    inventory = rows(text["inventory"], "V1LOGIC", 22, InventoryRow)
    audit = rows(text["audit"], "V1LOGIC", 13, AuditRow)
    ids = [row.logic_id for row in inventory]
    expected_ids = [f"V1LOGIC-{i:03d}" for i in range(1, len(inventory) + 1)]
    if not inventory:
        add(failures, "INVENTORY_EMPTY", "", "one or more rows", "0", paths["inventory"])
    if len(ids) != len(set(ids)):
        add(failures, "DUPLICATE_V1LOGIC_ID", "", "unique IDs", "duplicates present", paths["inventory"])
    if ids != expected_ids:
        add(failures, "NON_SEQUENTIAL_V1LOGIC_ID", "", f"V1LOGIC-001..V1LOGIC-{len(ids):03d}", ",".join(ids[:5]), paths["inventory"])

    known_items = set(refs(text["items"], "V1ITEM"))
    known_behaviors = set(refs(text["behaviors"], "V1BEHAVIOR"))
    known_goldens = set(refs(text["goldens"], "V1GOLDEN"))
    known_reqs = set(refs(text["reqs"], "REQ"))
    audit_by_id = {}
    for row in audit:
        audit_by_id.setdefault(row.logic_id, []).append(row)
    for logic_id in ids:
        count = len(audit_by_id.get(logic_id, []))
        if count != 1:
            add(failures, "INVENTORY_AUDIT_CARDINALITY", logic_id, "exactly one audit row", str(count), paths["audit"])
    for logic_id in audit_by_id:
        if logic_id not in set(ids):
            add(failures, "AUDIT_LOGIC_ID_NOT_IN_INVENTORY", logic_id, "inventory ID", "audit-only ID", paths["audit"])

    counts = {"behavior": 0, "golden": 0, "req": 0, "item": 0}
    inventory_by_id = {row.logic_id: row for row in inventory}
    for row in inventory:
        if row.logic_type not in ALLOWED_TYPES:
            add(failures, "INVALID_LOGIC_TYPE", row.logic_id, "allowed logic type", row.logic_type, paths["inventory"])
        for label, value in (("source file", row.source_file), ("source reference", row.source_ref), ("evidence basis", row.evidence), ("business/calculation purpose", row.purpose)):
            if not value.strip() or value.strip().lower() in {"none", "unknown", "n/a"}:
                add(failures, "REQUIRED_INVENTORY_FIELD_EMPTY", row.logic_id, f"non-empty {label}", value or "empty", paths["inventory"])

    for row in audit:
        source_row = inventory_by_id.get(row.logic_id)
        if row.status not in ALLOWED_STATUSES:
            add(failures, "INVALID_COVERAGE_STATUS", row.logic_id, "allowed coverage status", row.status, paths["audit"])
        if not row.required.strip():
            add(failures, "REQUIRED_COVERAGE_LEVEL_EMPTY", row.logic_id, "non-empty", "empty", paths["audit"])
        if row.status == "V1LOGIC_UNCOVERED_FAIL":
            add(failures, "UNCOVERED_FAIL_PRESENT", row.logic_id, "covered or classified", row.status, paths["audit"])
        if row.status == "V1LOGIC_SOURCE_UNCERTAIN_FAIL":
            add(failures, "SOURCE_UNCERTAIN_FAIL_PRESENT", row.logic_id, "source-certain row", row.status, paths["audit"])
        if row.status == "V1LOGIC_NOT_APPLICABLE_WITH_REASON" and not row.notes.strip():
            add(failures, "NOT_APPLICABLE_REASON_MISSING", row.logic_id, "explicit reason", "empty", paths["audit"])

        parsed = {
            "item": refs(row.v1items, "V1ITEM"), "behavior": refs(row.behaviors, "V1BEHAVIOR"),
            "golden": refs(row.goldens, "V1GOLDEN"), "req": refs(row.reqs, "REQ"),
        }
        for kind, known, source_path in (("item", known_items, paths["items"]), ("behavior", known_behaviors, paths["behaviors"]), ("golden", known_goldens, paths["goldens"]), ("req", known_reqs, paths["reqs"])):
            counts[kind] += len(parsed[kind])
            for ref in parsed[kind]:
                if ref not in known:
                    add(failures, f"UNKNOWN_{kind.upper()}_REFERENCE", row.logic_id, f"existing {kind} ID", ref, source_path)
        if row.status != "V1LOGIC_NOT_APPLICABLE_WITH_REASON" and not parsed["req"]:
            add(failures, "MISSING_REQUIRED_REQ", row.logic_id, "one or more REQ IDs", row.reqs or "empty", paths["audit"])
        if source_row and source_row.logic_type in BEHAVIOR_REQUIRED_TYPES and not parsed["behavior"]:
            add(failures, "MISSING_REQUIRED_BEHAVIOR", row.logic_id, "one or more V1BEHAVIOR IDs", row.behaviors or "empty", paths["audit"])
        if source_row and source_row.logic_type in GOLDEN_REQUIRED_TYPES and not parsed["golden"]:
            allowed_no_golden = row.status == "V1LOGIC_COVERED_BY_BEHAVIOR_ONLY_GOLDEN_NOT_REQUIRED" and "reason=" in row.notes.lower()
            if not allowed_no_golden:
                add(failures, "MISSING_REQUIRED_GOLDEN", row.logic_id, "one or more V1GOLDEN IDs or explicit reason", row.goldens or "empty", paths["audit"])

    high_risk = section(text["audit"], "## 3. High-Risk Logic Depth Coverage Table", "## 4. Uncovered Logic Failure Register")
    for domain in HIGH_RISK_DOMAINS:
        match = re.search(rf"^\|\s*{re.escape(domain)}\s*\|(?P<row>.*)$", high_risk, re.MULTILINE)
        if not match:
            add(failures, "HIGH_RISK_DOMAIN_MISSING", "", domain, "missing", paths["audit"])
        elif not re.search(r"\|\s*PASS\s*\|", match.group(0)):
            add(failures, "HIGH_RISK_DOMAIN_NOT_PASS", "", f"{domain}=PASS", match.group(0), paths["audit"])

    challenge = section(text["audit"], "## 5. User Example Challenge", "## 6. Final Status")
    for item in USER_CHALLENGES:
        match = re.search(rf"^\|\s*{re.escape(item)}\s*\|(?P<row>.*)$", challenge, re.MULTILINE | re.IGNORECASE)
        if not match:
            add(failures, "USER_EXAMPLE_CHALLENGE_MISSING", "", item, "missing", paths["audit"])
        elif not re.search(r"\|\s*PASS\s*\|", match.group(0)):
            add(failures, "USER_EXAMPLE_CHALLENGE_NOT_PASS", "", f"{item}=PASS", match.group(0), paths["audit"])

    if text["inventory"].count(INVENTORY_MARKER) != 1:
        add(failures, "INVALID_INVENTORY_MARKER", "", "exactly one inventory marker", str(text["inventory"].count(INVENTORY_MARKER)), paths["inventory"])
    pass_count, fail_count = text["audit"].count(PASS_MARKER), text["audit"].count(FAIL_MARKER)
    if pass_count != 1 or fail_count != 0:
        add(failures, "INVALID_AUDIT_FINAL_MARKER", "", "one PASS and zero FAIL markers", f"PASS={pass_count}; FAIL={fail_count}", paths["audit"])

    result_counts = {
        "v1logic_items_checked": len(inventory),
        "uncovered_fail": sum(row.status == "V1LOGIC_UNCOVERED_FAIL" for row in audit),
        "source_uncertain_fail": sum(row.status == "V1LOGIC_SOURCE_UNCERTAIN_FAIL" for row in audit),
        "behavior_refs_checked": counts["behavior"], "golden_refs_checked": counts["golden"],
        "req_refs_checked": counts["req"], "v1item_refs_checked": counts["item"],
        "high_risk_domains_checked": len(HIGH_RISK_DOMAINS),
        "user_example_challenges_checked": len(USER_CHALLENGES),
    }
    return failures, result_counts


def main() -> int:
    failures, counts = verify(parse_args().repo_root.resolve())
    if failures:
        print("V1_SOURCE_RAW_LOGIC_COVERAGE_VERIFICATION_FAIL")
        for failure in failures:
            print(f"failure_code={failure.code}; V1_Logic_ID={failure.logic_id}; expected={failure.expected}; actual={failure.actual}; source_file={failure.source_file}")
        for key, value in counts.items():
            print(f"{key}={value}")
        return 1
    print("V1_SOURCE_RAW_LOGIC_COVERAGE_VERIFICATION_PASS")
    for key, value in counts.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
