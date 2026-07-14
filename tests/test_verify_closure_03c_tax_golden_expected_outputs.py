from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_closure_03c_tax_golden_expected_outputs.py"
GOLDEN = Path("specs/runtime/V1_GOLDEN_MASTER_EXPECTED_OUTPUT_CASES.md")
BEHAVIOR = Path("specs/runtime/V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP.md")
TRACE = Path("specs/runtime/raw_remediation/closure/CLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX.md")
REPORT_03A = Path("specs/runtime/raw_remediation/closure/CLOSURE_03A_TAX_BEHAVIOR_CONTRACTS.md")
REPORT_03B = Path("specs/runtime/raw_remediation/closure/CLOSURE_03B_TAX_FORMULA_RULE_CONTRACTS.md")
REPORT_03C = Path("specs/runtime/raw_remediation/closure/CLOSURE_03C_TAX_GOLDEN_EXPECTED_OUTPUTS.md")
DECISIONS = Path("specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_DECISIONS.md")
FILES = (GOLDEN, BEHAVIOR, TRACE, REPORT_03A, REPORT_03B, REPORT_03C, DECISIONS)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for relative in FILES:
        (root / relative.parent).mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, root / relative)
    return root


def run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def mutate(root: Path, relative: Path, transform) -> None:
    path = root / relative
    path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")


def cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip("|").split("|")]


def replace_row(text: str, prefix: str, width: int, predicate, updates: dict[int, str]) -> str:
    for line in text.splitlines():
        row = cells(line) if line.startswith(f"| {prefix}") else []
        if len(row) == width and predicate(row):
            for index, value in updates.items():
                row[index] = value
            return text.replace(line, "| " + " | ".join(row) + " |", 1)
    raise AssertionError("matching row not found")


def remove_row(text: str, prefix: str, width: int, predicate) -> str:
    for line in text.splitlines():
        row = cells(line) if line.startswith(f"| {prefix}") else []
        if len(row) == width and predicate(row):
            return text.replace(line + "\n", "", 1)
    raise AssertionError("matching row not found")


def first_blocked(report: str) -> list[str]:
    for line in report.splitlines():
        if line.startswith("| V1LOGIC-"):
            row = cells(line)
            if len(row) == 7 and row[1].startswith("GOLDEN_"):
                return row
    raise AssertionError("blocked row not found")


def trace_row(text: str, logic_id: str) -> list[str]:
    for line in text.splitlines():
        if line.startswith(f"| {logic_id} "):
            row = cells(line)
            if len(row) == 11:
                return row
    raise AssertionError("trace row not found")


def add_closed_case(
    root: Path,
    *,
    include_golden: bool = True,
    close_trace: bool = True,
    evidence_has_case_id: bool = True,
    expected_statement: str = "Preserve the exact source-observed assertion output.",
    expected_boundary: str = "Only the exact output asserted at the cited source span.",
) -> str:
    report_path = root / REPORT_03C
    report = report_path.read_text(encoding="utf-8")
    blocked = first_blocked(report)
    logic_id = blocked[0]
    trace = (root / TRACE).read_text(encoding="utf-8")
    selected = trace_row(trace, logic_id)
    golden_id = "C03C-GOLDEN-001"
    evidence = "CLOSURE-03C_TAX_GOLDEN_EXPECTED_OUTPUTS"
    if evidence_has_case_id:
        evidence += f":{golden_id}"
    closure_line = "| " + " | ".join(
        [
            logic_id,
            golden_id,
            f"specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_DECISIONS.md#{logic_id}",
            selected[4],
            expected_statement,
            "EXISTING_V1_ASSERTION",
            expected_boundary,
            "No numeric, tax, legal, formula, or cross-source inference is permitted.",
            evidence,
            "CLOSED_BY_CLOSURE_03C_GOLDEN_EXPECTED_OUTPUT",
            "Synthetic verifier fixture only.",
        ]
    ) + " |"
    report = remove_row(report, "V1LOGIC-", 7, lambda row: row[0] == logic_id)
    report = report.replace(
        "|---|---|---|---|---|---|---|---|---|---|---|\n\nNo candidate is closed",
        "|---|---|---|---|---|---|---|---|---|---|---|\n" + closure_line + "\n\nNo candidate is closed",
        1,
    )
    report = report.replace("| GOLDEN_CLOSED_BY_SOURCE_EXPECTED_OUTPUT | 0 |", "| GOLDEN_CLOSED_BY_SOURCE_EXPECTED_OUTPUT | 1 |", 1)
    report = report.replace("| GOLDEN_BLOCKED_NEEDS_MANUAL_SOURCE_REVIEW | 791 |", "| GOLDEN_BLOCKED_NEEDS_MANUAL_SOURCE_REVIEW | 790 |", 1)
    report_path.write_text(report, encoding="utf-8")

    if include_golden:
        golden_path = root / GOLDEN
        golden = golden_path.read_text(encoding="utf-8")
        golden_line = "| " + " | ".join(
            [
                golden_id,
                logic_id,
                "RAW-REM-03",
                selected[3],
                f"specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_DECISIONS.md#{logic_id}",
                expected_statement,
                "EXISTING_V1_ASSERTION",
                "Use the exact fixture from the cited V1 source span.",
                expected_boundary,
                "No numeric, tax, legal, formula, or cross-source inference is permitted.",
                "CLOSURE-03C_TAX_GOLDEN_EXPECTED_OUTPUTS",
                "CLOSED_BY_CLOSURE_03C_GOLDEN_EXPECTED_OUTPUT",
                "Synthetic verifier fixture only.",
            ]
        ) + " |"
        golden = golden.replace(
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n\nNo CLOSURE-03C",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n" + golden_line + "\n\nNo CLOSURE-03C",
            1,
        )
        golden_path.write_text(golden, encoding="utf-8")

    if close_trace:
        trace = replace_row(
            trace,
            "V1LOGIC-",
            11,
            lambda row: row[0] == logic_id,
            {8: "CLOSED_BY_FUTURE_PATCH", 9: evidence},
        )
        (root / TRACE).write_text(trace, encoding="utf-8")
    return logic_id


def close_unapproved_trace(text: str, source: str) -> str:
    return replace_row(
        text,
        "V1LOGIC-",
        11,
        lambda row: row[1] == source and row[8] != "CLOSED_BY_FUTURE_PATCH",
        {8: "CLOSED_BY_FUTURE_PATCH", 9: "UNKNOWN-CLOSURE:FAKE"},
    )


def test_current_package_passes() -> None:
    result = run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "candidate_v1logic_rows=791" in result.stdout
    assert "golden_rows_closed_by_03c=0" in result.stdout
    assert "blocked_or_deferred_rows=791" in result.stdout
    assert "total_traceability_closed_rows=136" in result.stdout


def test_candidate_classification_sum_not_791_fails(repo: Path) -> None:
    mutate(repo, REPORT_03C, lambda text: text.replace("| GOLDEN_BLOCKED_NEEDS_MANUAL_SOURCE_REVIEW | 791 |", "| GOLDEN_BLOCKED_NEEDS_MANUAL_SOURCE_REVIEW | 790 |", 1))
    assert "CLASSIFICATION_SUM_INVALID" in run(repo).stdout


def test_closed_logic_missing_from_golden_map_fails(repo: Path) -> None:
    add_closed_case(repo, include_golden=False)
    assert "GOLDEN_MAP_EVIDENCE_MISSING" in run(repo).stdout


def test_closed_selected_trace_not_closed_fails(repo: Path) -> None:
    add_closed_case(repo, close_trace=False)
    assert "TRACE_SELECTED_NOT_CLOSED" in run(repo).stdout


def test_blocked_row_marked_closed_fails(repo: Path) -> None:
    mutate(repo, TRACE, lambda text: close_unapproved_trace(text, "RAW-REM-03"))
    assert "BLOCKED_TRACE_CLOSED" in run(repo).stdout


def test_selected_nonclosed_candidate_missing_from_blocked_table_fails(repo: Path) -> None:
    mutate(repo, REPORT_03C, lambda text: remove_row(text, "V1LOGIC-", 7, lambda row: True))
    assert "CANDIDATE_CLASSIFICATION_MISSING" in run(repo).stdout


def test_extra_raw_rem_03_outside_valid_scope_closed_fails(repo: Path) -> None:
    def transform(text: str) -> str:
        changed = replace_row(
            text,
            "V1LOGIC-",
            11,
            lambda row: row[1] == "RAW-REM-03" and row[3] in {"TAXMAP_NEEDS_BEHAVIOR_AND_GOLDEN", "TAXMAP_NEEDS_GOLDEN_EXPECTED_OUTPUT"},
            {5: "CLOSURE-UNKNOWN", 8: "CLOSED_BY_FUTURE_PATCH", 9: "CLOSURE-UNKNOWN:FAKE"},
        )
        return changed

    mutate(repo, TRACE, transform)
    assert "EXTRA_RAW03_CLOSED" in run(repo).stdout


@pytest.mark.parametrize("source", ["RAW-REM-04", "RAW-REM-05"])
def test_non_tax_row_closed_fails(repo: Path, source: str) -> None:
    mutate(repo, TRACE, lambda text: close_unapproved_trace(text, source))
    assert "NON_TAX_ROW_CLOSED" in run(repo).stdout


def test_closure_03a_row_changed_fails(repo: Path) -> None:
    mutate(repo, TRACE, lambda text: replace_row(text, "V1LOGIC-", 11, lambda row: "CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS" in row[9], {8: "NOT_CLOSED", 9: "EMPTY_NOT_CLOSED"}))
    assert "CLOSURE_03A_TRACE_CHANGED" in run(repo).stdout


def test_closure_03b_row_changed_fails(repo: Path) -> None:
    mutate(repo, TRACE, lambda text: replace_row(text, "V1LOGIC-", 11, lambda row: "CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS" in row[9], {8: "NOT_CLOSED", 9: "EMPTY_NOT_CLOSED"}))
    assert "CLOSURE_03B_TRACE_CHANGED" in run(repo).stdout


def test_closure_evidence_missing_golden_case_id_fails(repo: Path) -> None:
    add_closed_case(repo, evidence_has_case_id=False)
    assert "CLOSURE_EVIDENCE_INVALID" in run(repo).stdout


def test_expected_output_boundary_missing_fails(repo: Path) -> None:
    add_closed_case(repo, expected_boundary="")
    result = run(repo)
    assert "CLOSURE_FIELD_MISSING" in result.stdout or "GOLDEN_FIELD_MISSING" in result.stdout


def test_forbidden_inference_boundary_missing_fails(repo: Path) -> None:
    add_closed_case(repo)
    mutate(repo, GOLDEN, lambda text: replace_row(text, "C03C-GOLDEN-", 13, lambda row: True, {9: ""}))
    assert "GOLDEN_FIELD_MISSING" in run(repo).stdout


def test_forbidden_invented_formula_language_fails(repo: Path) -> None:
    mutate(repo, REPORT_03C, lambda text: text.replace("## 6. Non-Closure Statement", "standard tax rule\n\n## 6. Non-Closure Statement", 1))
    assert "FORBIDDEN_CONTENT" in run(repo).stdout


def test_numeric_expected_output_without_source_reference_fails(repo: Path) -> None:
    add_closed_case(repo, expected_statement="Expected output equals 123.")
    assert "NUMERIC_EXPECTED_OUTPUT_WITHOUT_SOURCE" in run(repo).stdout


def test_implementation_recommendation_fails(repo: Path) -> None:
    mutate(repo, REPORT_03C, lambda text: text.replace("## 7. Effect on Raw Coverage", "implementation ready\n\n## 7. Effect on Raw Coverage", 1))
    assert "FORBIDDEN_CONTENT" in run(repo).stdout


def test_02m_unfrozen_fails(repo: Path) -> None:
    mutate(repo, REPORT_03C, lambda text: text.replace("| 02M | FROZEN |", "| 02M | UNFROZEN |", 1))
    result = run(repo)
    assert "02M_STATUS" in result.stdout or "FORBIDDEN_CONTENT" in result.stdout


def test_full_planning_completeness_proven_fails(repo: Path) -> None:
    mutate(repo, REPORT_03C, lambda text: text.replace("| Full planning completeness | NOT_PROVEN |", "| Full planning completeness | PROVEN |", 1))
    result = run(repo)
    assert "PLANNING_STATUS" in result.stdout or "FORBIDDEN_CONTENT" in result.stdout


def test_final_marker_missing_fails(repo: Path) -> None:
    mutate(repo, REPORT_03C, lambda text: text.replace("CLOSURE_03C_TAX_GOLDEN_EXPECTED_OUTPUTS_PASS", ""))
    assert "FINAL_MARKER_INVALID" in run(repo).stdout


def test_ready_for_review_fails(repo: Path) -> None:
    mutate(repo, REPORT_03C, lambda text: text.replace("## 9. Final Marker", "READY_FOR_REVIEW\n\n## 9. Final Marker", 1))
    assert "READY_FOR_REVIEW_FORBIDDEN" in run(repo).stdout
