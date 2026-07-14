from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


EXPECTED_CANDIDATES = 791
EXPECTED_03A = 91
EXPECTED_03B = 45
TARGET_OUTCOMES = {
    "TAXMAP_NEEDS_BEHAVIOR_AND_GOLDEN",
    "TAXMAP_NEEDS_GOLDEN_EXPECTED_OUTPUT",
}
CLASSIFICATIONS = {
    "GOLDEN_CLOSED_BY_SOURCE_EXPECTED_OUTPUT",
    "GOLDEN_BLOCKED_NO_SOURCE_EXPECTED_OUTPUT",
    "GOLDEN_BLOCKED_NEEDS_MANUAL_SOURCE_REVIEW",
    "GOLDEN_DEFERRED_TO_CLOSURE_03D_BRIDGE",
    "GOLDEN_NOT_APPLICABLE_WITH_EXPLICIT_SOURCE_REASON",
}
EVIDENCE_TYPES = {
    "EXISTING_V1_ASSERTION",
    "SOURCE_OUTPUT_LITERAL",
    "SOURCE_FIELD_PRESENCE",
    "SOURCE_WARNING_ERROR",
    "SOURCE_REPORT_OUTPUT",
    "SOURCE_STRUCTURE_ONLY",
}


@dataclass(frozen=True)
class Failure:
    code: str
    logic_id: str
    expected: str
    actual: str
    source: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify CLOSURE-03C tax golden expected-output evidence.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def rows(text: str, width: int, prefix: str) -> list[list[str]]:
    parsed: list[list[str]] = []
    for line in text.splitlines():
        if line.startswith(f"| {prefix}"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == width:
                parsed.append(cells)
    return parsed


def section(text: str, start: str, end: str) -> str:
    match = re.search(rf"^{re.escape(start)}\s*$.*?(?=^{re.escape(end)}\s*$)", text, re.M | re.S)
    return match.group(0) if match else ""


def verify(root: Path) -> tuple[list[Failure], dict[str, int]]:
    paths = {
        "golden": root / "specs/runtime/V1_GOLDEN_MASTER_EXPECTED_OUTPUT_CASES.md",
        "behavior": root / "specs/runtime/V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP.md",
        "trace": root / "specs/runtime/raw_remediation/closure/CLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX.md",
        "report_03a": root / "specs/runtime/raw_remediation/closure/CLOSURE_03A_TAX_BEHAVIOR_CONTRACTS.md",
        "report_03b": root / "specs/runtime/raw_remediation/closure/CLOSURE_03B_TAX_FORMULA_RULE_CONTRACTS.md",
        "report_03c": root / "specs/runtime/raw_remediation/closure/CLOSURE_03C_TAX_GOLDEN_EXPECTED_OUTPUTS.md",
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

    trace_rows = rows(texts["trace"], 11, "V1LOGIC-")
    trace_by_logic: dict[str, list[list[str]]] = {}
    for row in trace_rows:
        trace_by_logic.setdefault(row[0], []).append(row)
    for logic_id, matches in trace_by_logic.items():
        if len(matches) != 1:
            fail("TRACE_LOGIC_ID_DUPLICATE", logic_id, "exactly one trace row", str(len(matches)), "trace")

    candidates = {
        row[0]: row
        for row in trace_rows
        if row[1] == "RAW-REM-03"
        and row[3] in TARGET_OUTCOMES
        and "CLOSURE-03C_TAX_GOLDEN_EXPECTED_OUTPUTS" in row[5]
    }
    if len(candidates) != EXPECTED_CANDIDATES:
        fail("CANDIDATE_SCOPE_COUNT", "", str(EXPECTED_CANDIDATES), str(len(candidates)), "trace")

    decision_rows = rows(texts["decisions"], 7, "V1LOGIC-")
    decisions = {row[0]: row for row in decision_rows if row[2] in TARGET_OUTCOMES}
    if len(decisions) != EXPECTED_CANDIDATES:
        fail("DECISION_SCOPE_COUNT", "", str(EXPECTED_CANDIDATES), str(len(decisions)), "decisions")
    for logic_id, candidate in candidates.items():
        decision = decisions.get(logic_id)
        if not decision or decision[2] != candidate[3]:
            fail("DECISION_EVIDENCE_MISSING", logic_id, candidate[3], "missing or mismatched", "decisions")

    closure_text = section(texts["report_03c"], "## 4. Golden Expected-Output Closure Table", "## 5. Blocked/Deferred Candidate Table")
    blocked_text = section(texts["report_03c"], "## 5. Blocked/Deferred Candidate Table", "## 6. Non-Closure Statement")
    summary_text = section(texts["report_03c"], "## 3. Candidate Classification Summary", "## 4. Golden Expected-Output Closure Table")
    golden_text = section(texts["golden"], "## 7A. CLOSURE-03C Tax Golden Expected-Output Cases", "## 8. Final Status")
    closure_rows = rows(closure_text, 11, "V1LOGIC-")
    blocked_rows = rows(blocked_text, 7, "V1LOGIC-")
    golden_rows = rows(golden_text, 13, "C03C-GOLDEN-")
    summary_rows = [
        row
        for classification in CLASSIFICATIONS
        for row in rows(summary_text, 5, classification)
    ]

    closure_by_logic: dict[str, list[list[str]]] = {}
    blocked_by_logic: dict[str, list[list[str]]] = {}
    golden_by_id: dict[str, list[list[str]]] = {}
    for row in closure_rows:
        closure_by_logic.setdefault(row[0], []).append(row)
    for row in blocked_rows:
        blocked_by_logic.setdefault(row[0], []).append(row)
    for row in golden_rows:
        golden_by_id.setdefault(row[0], []).append(row)

    for label, mapping, source in (
        ("closure", closure_by_logic, "report_03c"),
        ("blocked", blocked_by_logic, "report_03c"),
        ("golden", golden_by_id, "golden"),
    ):
        for identifier, matches in mapping.items():
            if len(matches) != 1:
                fail(f"DUPLICATE_{label.upper()}_ROW", identifier, "exactly one row", str(len(matches)), source)

    closure_ids = set(closure_by_logic)
    blocked_ids = set(blocked_by_logic)
    overlap = closure_ids & blocked_ids
    for logic_id in overlap:
        fail("CANDIDATE_CLASSIFICATION_OVERLAP", logic_id, "closed or blocked, not both", "both", "report_03c")
    unknown_report_ids = (closure_ids | blocked_ids) - set(candidates)
    for logic_id in unknown_report_ids:
        fail("REPORT_ID_OUTSIDE_SCOPE", logic_id, "selected CLOSURE-03C candidate", "outside scope", "report_03c")
    missing_report_ids = set(candidates) - closure_ids - blocked_ids
    for logic_id in missing_report_ids:
        fail("CANDIDATE_CLASSIFICATION_MISSING", logic_id, "one closure or blocked row", "missing", "report_03c")
    if len(closure_rows) + len(blocked_rows) != EXPECTED_CANDIDATES:
        fail(
            "CANDIDATE_CLASSIFICATION_TOTAL",
            "",
            str(EXPECTED_CANDIDATES),
            str(len(closure_rows) + len(blocked_rows)),
            "report_03c",
        )

    summary_counts: dict[str, int] = {}
    for row in summary_rows:
        try:
            summary_counts[row[0]] = int(row[1])
        except ValueError:
            fail("CLASSIFICATION_COUNT_INVALID", "", "integer", row[1], "report_03c")
    if set(summary_counts) != CLASSIFICATIONS:
        fail("CLASSIFICATION_SET_INVALID", "", ",".join(sorted(CLASSIFICATIONS)), ",".join(sorted(summary_counts)), "report_03c")
    if sum(summary_counts.values()) != EXPECTED_CANDIDATES:
        fail("CLASSIFICATION_SUM_INVALID", "", str(EXPECTED_CANDIDATES), str(sum(summary_counts.values())), "report_03c")
    actual_classifications = Counter(row[1] for row in blocked_rows)
    actual_classifications["GOLDEN_CLOSED_BY_SOURCE_EXPECTED_OUTPUT"] = len(closure_rows)
    for classification in CLASSIFICATIONS:
        if summary_counts.get(classification) != actual_classifications.get(classification, 0):
            fail(
                "CLASSIFICATION_COUNT_MISMATCH",
                "",
                f"{classification}={actual_classifications.get(classification, 0)}",
                str(summary_counts.get(classification)),
                "report_03c",
            )

    allowed_blocked = CLASSIFICATIONS - {"GOLDEN_CLOSED_BY_SOURCE_EXPECTED_OUTPUT"}
    for logic_id, matches in blocked_by_logic.items():
        row = matches[0]
        if row[1] not in allowed_blocked:
            fail("BLOCKED_CLASSIFICATION_INVALID", logic_id, ",".join(sorted(allowed_blocked)), row[1], "report_03c")
        if not row[2] or logic_id not in row[2]:
            fail("BLOCKED_SOURCE_REFERENCE_MISSING", logic_id, "source decision reference containing V1LOGIC ID", row[2], "report_03c")
        if not row[3]:
            fail("BLOCKED_REASON_MISSING", logic_id, "non-empty reason", "empty", "report_03c")
        if not row[4]:
            fail("BLOCKED_NEXT_ACTION_MISSING", logic_id, "non-empty required next action", "empty", "report_03c")
        trace = candidates.get(logic_id)
        if trace and trace[8] == "CLOSED_BY_FUTURE_PATCH":
            fail("BLOCKED_TRACE_CLOSED", logic_id, "not closed", trace[8], "trace")

    valid_03c_ids: set[str] = set()
    golden_logic_seen: set[str] = set()
    for logic_id, matches in closure_by_logic.items():
        row = matches[0]
        golden_id = row[1]
        if row[9] != "CLOSED_BY_CLOSURE_03C_GOLDEN_EXPECTED_OUTPUT":
            fail("CLOSURE_STATUS_INVALID", logic_id, "CLOSED_BY_CLOSURE_03C_GOLDEN_EXPECTED_OUTPUT", row[9], "report_03c")
        if row[5] not in EVIDENCE_TYPES:
            fail("EVIDENCE_TYPE_INVALID", logic_id, ",".join(sorted(EVIDENCE_TYPES)), row[5], "report_03c")
        for index, label in ((2, "source decision reference"), (4, "expected-output statement"), (6, "expected output boundary"), (7, "forbidden inference boundary"), (8, "closure evidence reference")):
            if not row[index]:
                fail("CLOSURE_FIELD_MISSING", logic_id, f"non-empty {label}", "empty", "report_03c")
        if logic_id not in row[2]:
            fail("CLOSURE_SOURCE_REFERENCE_INVALID", logic_id, "source decision reference containing V1LOGIC ID", row[2], "report_03c")
        if "CLOSURE-03C_TAX_GOLDEN_EXPECTED_OUTPUTS" not in row[8] or golden_id not in row[8]:
            fail("CLOSURE_EVIDENCE_INVALID", logic_id, "package and golden case ID", row[8], "report_03c")

        golden_matches = golden_by_id.get(golden_id, [])
        if len(golden_matches) != 1:
            fail("GOLDEN_MAP_EVIDENCE_MISSING", logic_id, f"one {golden_id} row", str(len(golden_matches)), "golden")
            continue
        golden = golden_matches[0]
        golden_logic_ids = set(re.findall(r"V1LOGIC-\d+", golden[1]))
        golden_logic_seen.update(golden_logic_ids)
        if logic_id not in golden_logic_ids:
            fail("GOLDEN_LOGIC_REFERENCE_MISSING", logic_id, "golden case references selected ID", golden[1], "golden")
        if golden[2] != "RAW-REM-03" or golden[3] not in TARGET_OUTCOMES:
            fail("GOLDEN_SCOPE_INVALID", logic_id, "RAW-REM-03 and target golden outcome", f"{golden[2]} / {golden[3]}", "golden")
        if golden[6] not in EVIDENCE_TYPES:
            fail("GOLDEN_EVIDENCE_TYPE_INVALID", logic_id, ",".join(sorted(EVIDENCE_TYPES)), golden[6], "golden")
        for index, label in ((4, "source decision reference"), (5, "expected-output statement"), (8, "expected output boundary"), (9, "forbidden inference boundary"), (12, "limitations")):
            if not golden[index]:
                fail("GOLDEN_FIELD_MISSING", logic_id, f"non-empty {label}", "empty", "golden")
        if golden[10] != "CLOSURE-03C_TAX_GOLDEN_EXPECTED_OUTPUTS" or golden[11] != "CLOSED_BY_CLOSURE_03C_GOLDEN_EXPECTED_OUTPUT":
            fail("GOLDEN_CLOSURE_INVALID", logic_id, "03C package and status", f"{golden[10]} / {golden[11]}", "golden")
        numeric_text = f"{golden[5]} {golden[8]}"
        source_support = f"{golden[4]} {golden[12]}"
        if re.search(r"(?<![A-Za-z])-?\d+(?:[.,]\d+)?", numeric_text) and not re.search(
            r"(?i)(@L\d+|source-quoted|exact source literal)", source_support
        ):
            fail("NUMERIC_EXPECTED_OUTPUT_WITHOUT_SOURCE", logic_id, "explicit source quotation/reference", numeric_text, "golden")

        trace = candidates.get(logic_id)
        if trace:
            if trace[8] != "CLOSED_BY_FUTURE_PATCH":
                fail("TRACE_SELECTED_NOT_CLOSED", logic_id, "CLOSED_BY_FUTURE_PATCH", trace[8], "trace")
            elif "CLOSURE-03C_TAX_GOLDEN_EXPECTED_OUTPUTS" not in trace[9] or golden_id not in trace[9]:
                fail("TRACE_EVIDENCE_INVALID", logic_id, "package and golden case ID", trace[9], "trace")
            else:
                valid_03c_ids.add(logic_id)
    for golden_id, matches in golden_by_id.items():
        logic_ids = set(re.findall(r"V1LOGIC-\d+", matches[0][1]))
        if not logic_ids or not logic_ids <= closure_ids:
            fail("ORPHAN_GOLDEN_CASE", golden_id, "only report-closed V1LOGIC IDs", ",".join(sorted(logic_ids)), "golden")

    reports_03a = rows(texts["report_03a"], 9, "V1LOGIC-")
    reports_03b = rows(texts["report_03b"], 10, "V1LOGIC-")
    report_03a_by_logic = {row[0]: row for row in reports_03a}
    report_03b_by_logic = {row[0]: row for row in reports_03b}
    if len(report_03a_by_logic) != EXPECTED_03A:
        fail("CLOSURE_03A_REPORT_COUNT", "", str(EXPECTED_03A), str(len(report_03a_by_logic)), "report_03a")
    if len(report_03b_by_logic) != EXPECTED_03B:
        fail("CLOSURE_03B_REPORT_COUNT", "", str(EXPECTED_03B), str(len(report_03b_by_logic)), "report_03b")
    valid_03a_ids: set[str] = set()
    valid_03b_ids: set[str] = set()
    for logic_id, report in report_03a_by_logic.items():
        matches = trace_by_logic.get(logic_id, [])
        if len(matches) != 1 or matches[0][8] != "CLOSED_BY_FUTURE_PATCH" or matches[0][9] != report[6] or "CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS" not in report[6]:
            fail("CLOSURE_03A_TRACE_CHANGED", logic_id, f"CLOSED_BY_FUTURE_PATCH / {report[6]}", "missing or changed", "trace")
        else:
            valid_03a_ids.add(logic_id)
    for logic_id, report in report_03b_by_logic.items():
        matches = trace_by_logic.get(logic_id, [])
        if len(matches) != 1 or matches[0][8] != "CLOSED_BY_FUTURE_PATCH" or matches[0][9] != report[7] or "CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS" not in report[7]:
            fail("CLOSURE_03B_TRACE_CHANGED", logic_id, f"CLOSED_BY_FUTURE_PATCH / {report[7]}", "missing or changed", "trace")
        else:
            valid_03b_ids.add(logic_id)

    allowed_closed = set(report_03a_by_logic) | set(report_03b_by_logic) | closure_ids
    closed_rows = [row for row in trace_rows if row[8] == "CLOSED_BY_FUTURE_PATCH"]
    extras = [row for row in closed_rows if row[0] not in allowed_closed]
    for row in extras:
        if row[1] in {"RAW-REM-04", "RAW-REM-05"}:
            fail("NON_TAX_ROW_CLOSED", row[0], "RAW-REM-04/05 not closed", f"{row[1]} / {row[3]}", "trace")
        else:
            fail("EXTRA_RAW03_CLOSED", row[0], "only valid CLOSURE-03A/03B/03C rows closed", f"{row[1]} / {row[3]}", "trace")
    expected_total_closed = EXPECTED_03A + EXPECTED_03B + len(closure_rows)
    if len(closed_rows) != expected_total_closed:
        fail("TOTAL_CLOSED_COUNT", "", str(expected_total_closed), str(len(closed_rows)), "trace")

    forbidden = re.compile(
        r"(?i)\b(?:assumed|probably|standard tax rule|by law generally|should calculate|use the current Israeli tax brackets|implementation ready|runtime parity proven|full planning completeness proven|02M unfrozen)\b"
    )
    added_text = golden_text + "\n" + texts["report_03c"]
    match = forbidden.search(added_text)
    if match:
        fail("FORBIDDEN_CONTENT", "", "no invented/readiness language", match.group(0), "report_03c")
    required_report_patterns = {
        "RAW_STATUS": r"\|\s*Raw V1 source logic coverage\s*\|\s*FAIL\s*\|",
        "PLANNING_STATUS": r"\|\s*Full planning completeness\s*\|\s*NOT_PROVEN\s*\|",
        "EXECUTION_STATUS": r"\|\s*Execution authorized\s*\|\s*NO\s*\|",
        "02M_STATUS": r"\|\s*02M\s*\|\s*FROZEN\s*\|",
    }
    for code, pattern in required_report_patterns.items():
        if not re.search(pattern, texts["report_03c"]):
            fail(code, "", pattern, "missing", "report_03c")
    marker = "CLOSURE_03C_TAX_GOLDEN_EXPECTED_OUTPUTS_PASS"
    if texts["report_03c"].count(marker) != 1:
        fail("FINAL_MARKER_INVALID", "", "one PASS marker", str(texts["report_03c"].count(marker)), "report_03c")
    if "READY_FOR_REVIEW" in texts["report_03c"]:
        fail("READY_FOR_REVIEW_FORBIDDEN", "", "absent", "present", "report_03c")
    if "V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP_PASS" not in texts["behavior"]:
        fail("BEHAVIOR_MAP_MARKER_MISSING", "", "behavior map PASS marker", "missing", "behavior")

    counts = {
        "candidate_v1logic_rows": len(candidates),
        "golden_rows_closed_by_03c": len(valid_03c_ids),
        "blocked_or_deferred_rows": len(blocked_rows),
        "existing_closure_03a_rows": len(valid_03a_ids),
        "existing_closure_03b_rows": len(valid_03b_ids),
        "total_traceability_closed_rows": len(closed_rows),
        "extra_rows_closed": len(extras),
    }
    return failures, counts


def main() -> int:
    failures, counts = verify(parse_args().repo_root.resolve())
    if failures:
        print("CLOSURE_03C_TAX_GOLDEN_EXPECTED_OUTPUTS_VERIFICATION_FAIL")
        for failure in failures:
            print(
                f"failure_code={failure.code}; V1_Logic_ID={failure.logic_id}; "
                f"expected={failure.expected}; actual={failure.actual}; source_file={failure.source}"
            )
        return 1
    print("CLOSURE_03C_TAX_GOLDEN_EXPECTED_OUTPUTS_VERIFICATION_PASS")
    for key, value in counts.items():
        print(f"{key}={value}")
    print("raw_coverage_expected_status=FAIL")
    print("full_planning_completeness=NOT_PROVEN")
    print("execution_authorized=NO")
    print("02m_status=FROZEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
