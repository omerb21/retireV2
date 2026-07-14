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


def args():
    parser = argparse.ArgumentParser()
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


def verify(root: Path):
    paths = {
        "behavior": root / "specs/runtime/V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP.md",
        "trace": root / "specs/runtime/raw_remediation/closure/CLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX.md",
        "report": root / "specs/runtime/raw_remediation/closure/CLOSURE_03A_TAX_BEHAVIOR_CONTRACTS.md",
        "report_03b": root / "specs/runtime/raw_remediation/closure/CLOSURE_03B_TAX_FORMULA_RULE_CONTRACTS.md",
        "decisions": root / "specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_DECISIONS.md",
    }
    failures = []
    text = {}
    for key, path in paths.items():
        try:
            text[key] = path.read_text(encoding="utf-8")
        except OSError as exc:
            failures.append(Failure("READ_ERROR", "n/a", "readable", str(exc), str(path)))
    if failures:
        return failures, {}

    decisions = {r[0]: r for r in rows(text["decisions"], 7, "V1LOGIC-") if r[2] == "TAXMAP_NEEDS_BEHAVIOR_CONTRACT"}
    contracts_text = section(text["behavior"], "## 11A. CLOSURE-03A Tax Behavior Contracts", "## 11B. CLOSURE-03B Tax Formula/Rule Contracts")
    contracts = rows(contracts_text, 13, "C03A-BEH-")
    reports = rows(text["report"], 9, "V1LOGIC-")
    reports_03b = rows(text["report_03b"], 10, "V1LOGIC-")
    traces = rows(text["trace"], 11, "V1LOGIC-")
    trace_by_id = {r[0]: r for r in traces}
    contract_by_logic = {r[1]: r for r in contracts}
    report_by_logic = {r[0]: r for r in reports}

    def fail(code, lid, expected, actual, path="report"):
        failures.append(Failure(code, lid or "n/a", expected, actual, str(paths[path])))

    if len(decisions) != EXPECTED_03A:
        fail("SELECTED_SCOPE_COUNT", "", str(EXPECTED_03A), str(len(decisions)), "decisions")
    if len(contracts) != EXPECTED_03A or len(contract_by_logic) != EXPECTED_03A:
        fail("BEHAVIOR_CONTRACT_COUNT", "", f"{EXPECTED_03A} unique", f"rows={len(contracts)} unique={len(contract_by_logic)}", "behavior")
    if len(reports) != EXPECTED_03A or len(report_by_logic) != EXPECTED_03A:
        fail("REPORT_ROW_COUNT", "", f"{EXPECTED_03A} unique", f"rows={len(reports)} unique={len(report_by_logic)}")
    expected_contract_ids = [f"C03A-BEH-{i:03d}" for i in range(1, EXPECTED_03A + 1)]
    if [r[0] for r in contracts] != expected_contract_ids:
        fail("CONTRACT_ID_SEQUENCE", "", "C03A-BEH-001..091", "sequence mismatch", "behavior")

    for lid, decision in decisions.items():
        contract = contract_by_logic.get(lid)
        report = report_by_logic.get(lid)
        trace = trace_by_id.get(lid)
        if not contract:
            fail("BEHAVIOR_CONTRACT_MISSING", lid, "contract", "missing", "behavior")
            continue
        cid = contract[0]
        if contract[2] != "RAW-REM-03" or contract[3] != "TAXMAP_NEEDS_BEHAVIOR_CONTRACT":
            fail("CONTRACT_SOURCE_INVALID", lid, "RAW-REM-03 / TAXMAP_NEEDS_BEHAVIOR_CONTRACT", f"{contract[2]} / {contract[3]}", "behavior")
        if lid not in contract[4] or not contract[5] or not contract[6] or not contract[7]:
            fail("CONTRACT_EVIDENCE_FIELD_MISSING", lid, "source reference, statement, inputs, outputs", "missing field", "behavior")
        if "Formula/rule" not in contract[8] or "golden" not in contract[8]:
            fail("CONTRACT_EXCLUSION_MISSING", lid, "formula and golden exclusions", contract[8], "behavior")
        if contract[10] != "CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS" or contract[11] != "CLOSED_BY_CLOSURE_03A_BEHAVIOR_CONTRACT":
            fail("CONTRACT_CLOSURE_INVALID", lid, "03A closure/status", f"{contract[10]} / {contract[11]}", "behavior")
        if not report or report[1] != cid or report[7] != "CLOSED_BY_CLOSURE_03A_BEHAVIOR_CONTRACT":
            fail("REPORT_EVIDENCE_MISMATCH", lid, cid, "missing or mismatched")
        if not trace or trace[8] != "CLOSED_BY_FUTURE_PATCH":
            fail("TRACE_SELECTED_NOT_CLOSED", lid, "CLOSED_BY_FUTURE_PATCH", trace[8] if trace else "missing", "trace")
        elif "CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS" not in trace[9] or cid not in trace[9]:
            fail("TRACE_EVIDENCE_INVALID", lid, f"03A and {cid}", trace[9], "trace")

    report_03b_by_logic = {row[0]: row for row in reports_03b}
    if len(reports_03b) != EXPECTED_03B or len(report_03b_by_logic) != EXPECTED_03B:
        fail(
            "CLOSURE_03B_REPORT_COUNT",
            "",
            f"{EXPECTED_03B} unique",
            f"rows={len(reports_03b)} unique={len(report_03b_by_logic)}",
            "report_03b",
        )
    valid_03b: set[str] = set()
    for logic_id, report_03b in report_03b_by_logic.items():
        trace = trace_by_id.get(logic_id)
        expected_evidence = report_03b[7]
        if (
            not trace
            or trace[1] != "RAW-REM-03"
            or trace[3] != "TAXMAP_NEEDS_FORMULA_RULE_CONTRACT"
            or trace[8] != "CLOSED_BY_FUTURE_PATCH"
            or trace[9] != expected_evidence
            or "CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS" not in trace[9]
            or report_03b[8] != "CLOSED_BY_CLOSURE_03B_FORMULA_RULE_CONTRACT"
        ):
            fail(
                "LATER_CLOSURE_03B_INVALID",
                logic_id,
                f"RAW-REM-03 formula/rule closure / {expected_evidence}",
                "missing or mismatched" if not trace else f"{trace[1]} / {trace[3]} / {trace[8]} / {trace[9]}",
                "trace",
            )
        else:
            valid_03b.add(logic_id)

    closed = [r for r in traces if r[8] == "CLOSED_BY_FUTURE_PATCH"]
    allowed_closed = set(decisions) | set(report_03b_by_logic)
    extras = [r for r in closed if r[0] not in allowed_closed]
    for row in extras:
        if row[1] in {"RAW-REM-04", "RAW-REM-05"}:
            fail("NON_TAX_ROW_CLOSED", row[0], "RAW-REM-04/05 not closed", f"{row[1]} / {row[3]}", "trace")
        else:
            fail("EXTRA_ROW_CLOSED", row[0], "only valid CLOSURE-03A/03B rows closed", f"{row[1]} / {row[3]}", "trace")
    if len(valid_03b) != EXPECTED_03B:
        fail("LATER_CLOSURE_03B_COUNT", "", str(EXPECTED_03B), str(len(valid_03b)), "trace")
    if len(closed) != EXPECTED_TOTAL_CLOSED:
        fail("TOTAL_CLOSED_COUNT", "", str(EXPECTED_TOTAL_CLOSED), str(len(closed)), "trace")

    forbidden = re.compile(r"(?i)\b(?:assumed|probably|standard tax rule|by law generally|should calculate|implementation ready|runtime parity proven|full planning completeness proven|02M unfrozen)\b")
    added = contracts_text + "\n" + text["report"]
    match = forbidden.search(added)
    if match:
        fail("FORBIDDEN_CONTENT", "", "no invented/readiness language", match.group(0), "behavior")
    required = {
        "RAW_STATUS": "Raw V1 source logic coverage: FAIL",
        "PLANNING_STATUS": "Full planning completeness: NOT_PROVEN",
        "EXECUTION_STATUS": "Execution authorized: NO",
        "02M_STATUS": "02M: FROZEN",
    }
    for code, value in required.items():
        if value not in text["report"]:
            fail(code, "", value, "missing")
    marker = "CLOSURE_03A_TAX_BEHAVIOR_CONTRACTS_PASS"
    if text["report"].count(marker) != 1:
        fail("FINAL_MARKER_INVALID", "", "one PASS marker", str(text["report"].count(marker)))
    if "READY_FOR_REVIEW" in text["report"]:
        fail("READY_FOR_REVIEW_FORBIDDEN", "", "absent", "present")

    counts = {
        "selected_v1logic_rows": len(decisions),
        "behavior_contract_rows": len(contracts),
        "traceability_rows_closed_by_03a": sum(r[0] in decisions and r[8] == "CLOSED_BY_FUTURE_PATCH" for r in traces),
        "later_valid_closure_03b_rows": len(valid_03b),
        "total_traceability_closed_rows": len(closed),
        "extra_rows_closed": len(extras),
    }
    return failures, counts


def main():
    failures, counts = verify(args().repo_root.resolve())
    if failures:
        print("CLOSURE_03A_TAX_BEHAVIOR_CONTRACTS_VERIFICATION_FAIL")
        for f in failures:
            print(f"failure_code={f.code}; V1_Logic_ID={f.logic_id}; expected={f.expected}; actual={f.actual}; source_file={f.source}")
        return 1
    print("CLOSURE_03A_TAX_BEHAVIOR_CONTRACTS_VERIFICATION_PASS")
    for key, value in counts.items(): print(f"{key}={value}")
    print("raw_coverage_expected_status=FAIL")
    print("full_planning_completeness=NOT_PROVEN")
    print("execution_authorized=NO")
    print("02m_status=FROZEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
