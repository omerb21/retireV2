from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


EXPECTED_03A = 91
EXPECTED_03B = 45
EXPECTED_TOTAL_CLOSED = 136


@dataclass(frozen=True)
class Failure:
    code: str
    logic_id: str
    expected: str
    actual: str
    source: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify CLOSURE-03B tax formula/rule contracts.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def rows(text: str, width: int, prefix: str) -> list[list[str]]:
    result = []
    for line in text.splitlines():
        if line.startswith(f"| {prefix}"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == width:
                result.append(cells)
    return result


def section(text: str, start: str, end: str) -> str:
    match = re.search(rf"^{re.escape(start)}\s*$.*?(?=^{re.escape(end)}\s*$)", text, re.M | re.S)
    return match.group(0) if match else ""


def verify(root: Path) -> tuple[list[Failure], dict[str, int]]:
    paths = {
        "behavior": root / "specs/runtime/V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP.md",
        "trace": root / "specs/runtime/raw_remediation/closure/CLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX.md",
        "report_03b": root / "specs/runtime/raw_remediation/closure/CLOSURE_03B_TAX_FORMULA_RULE_CONTRACTS.md",
        "report_03a": root / "specs/runtime/raw_remediation/closure/CLOSURE_03A_TAX_BEHAVIOR_CONTRACTS.md",
        "decisions": root / "specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_DECISIONS.md",
    }
    failures: list[Failure] = []
    texts: dict[str, str] = {}

    def fail(code: str, logic_id: str, expected: str, actual: str, source: str) -> None:
        failures.append(Failure(code, logic_id or "n/a", expected, actual, str(paths[source])))

    for key, path in paths.items():
        try:
            texts[key] = path.read_text(encoding="utf-8")
        except OSError as exc:
            fail("READ_ERROR", "", "readable required file", str(exc), key)
    if failures:
        return failures, {}

    decisions = {
        row[0]: row
        for row in rows(texts["decisions"], 7, "V1LOGIC-")
        if row[2] == "TAXMAP_NEEDS_FORMULA_RULE_CONTRACT"
    }
    contracts_text = section(
        texts["behavior"],
        "## 11B. CLOSURE-03B Tax Formula/Rule Contracts",
        "## 12. Final Status",
    )
    contracts = rows(contracts_text, 14, "C03B-FR-")
    reports_03b = rows(texts["report_03b"], 10, "V1LOGIC-")
    reports_03a = rows(texts["report_03a"], 9, "V1LOGIC-")
    traces = rows(texts["trace"], 11, "V1LOGIC-")

    contract_by_logic: dict[str, list[list[str]]] = {}
    report_03b_by_logic: dict[str, list[list[str]]] = {}
    trace_by_logic: dict[str, list[list[str]]] = {}
    for row in contracts:
        contract_by_logic.setdefault(row[1], []).append(row)
    for row in reports_03b:
        report_03b_by_logic.setdefault(row[0], []).append(row)
    for row in traces:
        trace_by_logic.setdefault(row[0], []).append(row)

    if len(decisions) != EXPECTED_03B:
        fail("SELECTED_SCOPE_COUNT", "", str(EXPECTED_03B), str(len(decisions)), "decisions")
    if len(contracts) != EXPECTED_03B or len(contract_by_logic) != EXPECTED_03B:
        fail(
            "FORMULA_RULE_CONTRACT_COUNT",
            "",
            f"{EXPECTED_03B} rows and unique V1LOGIC IDs",
            f"rows={len(contracts)}; unique={len(contract_by_logic)}",
            "behavior",
        )
    if len(reports_03b) != EXPECTED_03B or len(report_03b_by_logic) != EXPECTED_03B:
        fail(
            "REPORT_ROW_COUNT",
            "",
            f"{EXPECTED_03B} rows and unique V1LOGIC IDs",
            f"rows={len(reports_03b)}; unique={len(report_03b_by_logic)}",
            "report_03b",
        )
    expected_contract_ids = [f"C03B-FR-{number:03d}" for number in range(1, EXPECTED_03B + 1)]
    if [row[0] for row in contracts] != expected_contract_ids:
        fail("CONTRACT_ID_SEQUENCE", "", "C03B-FR-001..045", "sequence mismatch", "behavior")
    duplicate_trace_ids = [logic_id for logic_id, matches in trace_by_logic.items() if len(matches) != 1]
    for logic_id in duplicate_trace_ids:
        fail("TRACE_LOGIC_ID_DUPLICATE", logic_id, "exactly one trace row", str(len(trace_by_logic[logic_id])), "trace")

    valid_03b_ids: set[str] = set()
    for logic_id in decisions:
        contract_matches = contract_by_logic.get(logic_id, [])
        report_matches = report_03b_by_logic.get(logic_id, [])
        trace_matches = trace_by_logic.get(logic_id, [])
        if len(contract_matches) != 1:
            fail("FORMULA_RULE_CONTRACT_MISSING", logic_id, "exactly one contract", str(len(contract_matches)), "behavior")
            continue
        contract = contract_matches[0]
        contract_id = contract[0]
        if contract[2] != "RAW-REM-03" or contract[3] != "TAXMAP_NEEDS_FORMULA_RULE_CONTRACT":
            fail(
                "CONTRACT_SOURCE_INVALID",
                logic_id,
                "RAW-REM-03 / TAXMAP_NEEDS_FORMULA_RULE_CONTRACT",
                f"{contract[2]} / {contract[3]}",
                "behavior",
            )
        required_fields = {
            "source decision reference": contract[4],
            "formula/rule statement": contract[5],
            "inputs": contract[6],
            "outputs/effects": contract[7],
            "formula/rule boundary": contract[8],
            "golden exclusion": contract[9],
            "runtime exclusion": contract[10],
            "limitations": contract[13],
        }
        for field_name, value in required_fields.items():
            if not value:
                fail("CONTRACT_FIELD_MISSING", logic_id, f"non-empty {field_name}", "empty", "behavior")
        if logic_id not in contract[4]:
            fail("CONTRACT_SOURCE_REFERENCE_INVALID", logic_id, "source decision reference containing V1LOGIC ID", contract[4], "behavior")
        if "Golden expected-output coverage is excluded" not in contract[9]:
            fail("GOLDEN_EXCLUSION_MISSING", logic_id, "explicit golden exclusion", contract[9], "behavior")
        if "runtime implementation" not in contract[10].lower():
            fail("RUNTIME_EXCLUSION_MISSING", logic_id, "explicit runtime implementation exclusion", contract[10], "behavior")
        if contract[11] != "CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS" or contract[12] != "CLOSED_BY_CLOSURE_03B_FORMULA_RULE_CONTRACT":
            fail(
                "CONTRACT_CLOSURE_INVALID",
                logic_id,
                "CLOSURE-03B package and closure status",
                f"{contract[11]} / {contract[12]}",
                "behavior",
            )

        expected_evidence = f"CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS:{contract_id}"
        if len(report_matches) != 1:
            fail("REPORT_EVIDENCE_MISSING", logic_id, "exactly one report row", str(len(report_matches)), "report_03b")
        else:
            report = report_matches[0]
            if report[1] != contract_id or report[7] != expected_evidence or report[8] != "CLOSED_BY_CLOSURE_03B_FORMULA_RULE_CONTRACT":
                fail(
                    "REPORT_EVIDENCE_MISMATCH",
                    logic_id,
                    f"{contract_id} / {expected_evidence} / CLOSED_BY_CLOSURE_03B_FORMULA_RULE_CONTRACT",
                    f"{report[1]} / {report[7]} / {report[8]}",
                    "report_03b",
                )
        if len(trace_matches) != 1:
            fail("TRACE_SELECTED_MISSING", logic_id, "exactly one trace row", str(len(trace_matches)), "trace")
        else:
            trace = trace_matches[0]
            if trace[1] != "RAW-REM-03" or trace[3] != "TAXMAP_NEEDS_FORMULA_RULE_CONTRACT":
                fail("TRACE_SELECTED_SCOPE_INVALID", logic_id, "RAW-REM-03 formula/rule outcome", f"{trace[1]} / {trace[3]}", "trace")
            if trace[8] != "CLOSED_BY_FUTURE_PATCH":
                fail("TRACE_SELECTED_NOT_CLOSED", logic_id, "CLOSED_BY_FUTURE_PATCH", trace[8], "trace")
            elif trace[9] != expected_evidence:
                fail("TRACE_EVIDENCE_INVALID", logic_id, expected_evidence, trace[9], "trace")
            else:
                valid_03b_ids.add(logic_id)

    report_03a_by_logic = {row[0]: row for row in reports_03a}
    if len(reports_03a) != EXPECTED_03A or len(report_03a_by_logic) != EXPECTED_03A:
        fail("CLOSURE_03A_REPORT_COUNT", "", f"{EXPECTED_03A} unique rows", f"rows={len(reports_03a)}; unique={len(report_03a_by_logic)}", "report_03a")
    valid_03a_ids: set[str] = set()
    for logic_id, report in report_03a_by_logic.items():
        trace_matches = trace_by_logic.get(logic_id, [])
        expected_evidence = report[6]
        if len(trace_matches) != 1:
            fail("CLOSURE_03A_TRACE_MISSING", logic_id, "exactly one trace row", str(len(trace_matches)), "trace")
            continue
        trace = trace_matches[0]
        if trace[8] != "CLOSED_BY_FUTURE_PATCH" or trace[9] != expected_evidence or "CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS" not in trace[9]:
            fail("CLOSURE_03A_TRACE_CHANGED", logic_id, f"CLOSED_BY_FUTURE_PATCH / {expected_evidence}", f"{trace[8]} / {trace[9]}", "trace")
        else:
            valid_03a_ids.add(logic_id)

    allowed_closed = set(decisions) | set(report_03a_by_logic)
    closed = [row for row in traces if row[8] == "CLOSED_BY_FUTURE_PATCH"]
    extras = [row for row in closed if row[0] not in allowed_closed]
    for row in extras:
        if row[1] in {"RAW-REM-04", "RAW-REM-05"}:
            fail("NON_TAX_ROW_CLOSED", row[0], "RAW-REM-04/05 not closed", f"{row[1]} / {row[3]}", "trace")
        else:
            fail("EXTRA_ROW_CLOSED", row[0], "only CLOSURE-03A/03B IDs closed", f"{row[1]} / {row[3]}", "trace")
    if len(closed) != EXPECTED_TOTAL_CLOSED:
        fail("TOTAL_CLOSED_COUNT", "", str(EXPECTED_TOTAL_CLOSED), str(len(closed)), "trace")

    forbidden = re.compile(
        r"(?i)\b(?:assumed|probably|standard tax rule|by law generally|should calculate|use the current Israeli tax brackets|implementation ready|runtime parity proven|full planning completeness proven|02M unfrozen)\b"
    )
    added_text = contracts_text + "\n" + texts["report_03b"]
    match = forbidden.search(added_text)
    if match:
        fail("FORBIDDEN_CONTENT", "", "no invented/readiness language", match.group(0), "behavior")
    golden_creation = re.search(r"(?i)golden expected (?:output|result)\s*(?:created|added|equals|:)\s*(?!coverage is excluded)", added_text)
    if golden_creation:
        fail("GOLDEN_EXPECTED_OUTPUT_CREATED", "", "no golden expected output creation", golden_creation.group(0), "report_03b")

    required_report_patterns = {
        "RAW_STATUS": r"Raw V1 source logic coverage:\s*`?FAIL`?",
        "PLANNING_STATUS": r"Full planning completeness:\s*`?NOT_PROVEN`?",
        "EXECUTION_STATUS": r"Execution authorized:\s*`?NO`?",
        "02M_STATUS": r"02M:\s*`?FROZEN`?",
    }
    for code, pattern in required_report_patterns.items():
        if not re.search(pattern, texts["report_03b"]):
            fail(code, "", pattern, "missing", "report_03b")
    marker = "CLOSURE_03B_TAX_FORMULA_RULE_CONTRACTS_PASS"
    if texts["report_03b"].count(marker) != 1:
        fail("FINAL_MARKER_INVALID", "", "one PASS marker", str(texts["report_03b"].count(marker)), "report_03b")
    if "READY_FOR_REVIEW" in texts["report_03b"]:
        fail("READY_FOR_REVIEW_FORBIDDEN", "", "absent", "present", "report_03b")

    counts = {
        "selected_v1logic_rows": len(decisions),
        "formula_rule_contract_rows": len(contracts),
        "traceability_rows_closed_by_03b": len(valid_03b_ids),
        "existing_closure_03a_rows": len(valid_03a_ids),
        "total_traceability_closed_rows": len(closed),
        "extra_rows_closed": len(extras),
    }
    return failures, counts


def main() -> int:
    failures, counts = verify(parse_args().repo_root.resolve())
    if failures:
        print("CLOSURE_03B_TAX_FORMULA_RULE_CONTRACTS_VERIFICATION_FAIL")
        for failure in failures:
            print(
                f"failure_code={failure.code}; V1_Logic_ID={failure.logic_id}; "
                f"expected={failure.expected}; actual={failure.actual}; source_file={failure.source}"
            )
        return 1
    print("CLOSURE_03B_TAX_FORMULA_RULE_CONTRACTS_VERIFICATION_PASS")
    for key, value in counts.items():
        print(f"{key}={value}")
    print("raw_coverage_expected_status=FAIL")
    print("full_planning_completeness=NOT_PROVEN")
    print("execution_authorized=NO")
    print("02m_status=FROZEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
