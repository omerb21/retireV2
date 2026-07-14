from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_closure_03a_tax_behavior_contracts.py"
BEHAVIOR = Path("specs/runtime/V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP.md")
TRACE = Path("specs/runtime/raw_remediation/closure/CLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX.md")
REPORT_03A = Path("specs/runtime/raw_remediation/closure/CLOSURE_03A_TAX_BEHAVIOR_CONTRACTS.md")
REPORT_03B = Path("specs/runtime/raw_remediation/closure/CLOSURE_03B_TAX_FORMULA_RULE_CONTRACTS.md")
DECISIONS = Path("specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_DECISIONS.md")
FILES = (BEHAVIOR, TRACE, REPORT_03A, REPORT_03B, DECISIONS)


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


def replace_row(text: str, prefix: str, width: int, predicate, updates: dict[int, str]) -> str:
    for line in text.splitlines():
        if line.startswith(f"| {prefix}"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == width and predicate(cells):
                for index, value in updates.items():
                    cells[index] = value
                return text.replace(line, "| " + " | ".join(cells) + " |", 1)
    raise AssertionError("matching row not found")


def remove_row(text: str, prefix: str, width: int, predicate) -> str:
    for line in text.splitlines():
        if line.startswith(f"| {prefix}"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == width and predicate(cells):
                return text.replace(line + "\n", "", 1)
    raise AssertionError("matching row not found")


def close_trace_row(text: str, source: str, outcome=None) -> str:
    return replace_row(
        text,
        "V1LOGIC-",
        11,
        lambda cells: cells[1] == source and (outcome is None or cells[3] == outcome),
        {8: "CLOSED_BY_FUTURE_PATCH", 9: "UNKNOWN-CLOSURE:FAKE"},
    )


def test_current_state_passes_with_later_03b_closures() -> None:
    result = run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "traceability_rows_closed_by_03a=91" in result.stdout
    assert "later_valid_closure_03b_rows=45" in result.stdout
    assert "total_traceability_closed_rows=136" in result.stdout


def test_selected_closure_03a_contract_missing_fails(repo: Path) -> None:
    mutate(repo, BEHAVIOR, lambda text: remove_row(text, "C03A-BEH-", 13, lambda cells: True))
    assert "BEHAVIOR_CONTRACT" in run(repo).stdout


def test_selected_closure_03a_row_not_closed_fails(repo: Path) -> None:
    mutate(
        repo,
        TRACE,
        lambda text: replace_row(
            text,
            "V1LOGIC-",
            11,
            lambda cells: cells[9].startswith("CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS:"),
            {8: "NOT_CLOSED", 9: "EMPTY_NOT_CLOSED"},
        ),
    )
    assert "TRACE_SELECTED_NOT_CLOSED" in run(repo).stdout


def test_closure_03a_evidence_reference_missing_fails(repo: Path) -> None:
    mutate(
        repo,
        TRACE,
        lambda text: replace_row(
            text,
            "V1LOGIC-",
            11,
            lambda cells: cells[9].startswith("CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS:"),
            {9: "CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS"},
        ),
    )
    assert "TRACE_EVIDENCE_INVALID" in run(repo).stdout


@pytest.mark.parametrize("source", ["RAW-REM-04", "RAW-REM-05"])
def test_non_tax_row_closed_fails(repo: Path, source: str) -> None:
    mutate(repo, TRACE, lambda text: close_trace_row(text, source))
    assert "NON_TAX_ROW_CLOSED" in run(repo).stdout


def test_raw_rem_03_outside_valid_03a_03b_closed_fails(repo: Path) -> None:
    mutate(repo, TRACE, lambda text: close_trace_row(text, "RAW-REM-03", "TAXMAP_NEEDS_BEHAVIOR_AND_GOLDEN"))
    assert "EXTRA_ROW_CLOSED" in run(repo).stdout


def test_unknown_closure_package_fails(repo: Path) -> None:
    mutate(repo, TRACE, lambda text: close_trace_row(text, "RAW-REM-03", "TAXMAP_NEEDS_BEHAVIOR_AND_GOLDEN"))
    assert "EXTRA_ROW_CLOSED" in run(repo).stdout


def test_total_closed_count_not_136_fails(repo: Path) -> None:
    mutate(
        repo,
        TRACE,
        lambda text: replace_row(
            text,
            "V1LOGIC-",
            11,
            lambda cells: cells[9].startswith("CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS:"),
            {8: "NOT_CLOSED", 9: "EMPTY_NOT_CLOSED"},
        ),
    )
    assert "TOTAL_CLOSED_COUNT" in run(repo).stdout


def test_later_valid_closure_03b_count_not_45_fails(repo: Path) -> None:
    mutate(
        repo,
        TRACE,
        lambda text: replace_row(
            text,
            "V1LOGIC-",
            11,
            lambda cells: cells[9].startswith("CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS:"),
            {9: "UNKNOWN-CLOSURE:C03B-FR-001"},
        ),
    )
    assert "LATER_CLOSURE_03B_COUNT" in run(repo).stdout


def test_implementation_recommendation_fails(repo: Path) -> None:
    mutate(
        repo,
        REPORT_03A,
        lambda text: text.replace("## 5. Effect on Raw Coverage", "Recommended next step: implementation ready\n\n## 5. Effect on Raw Coverage"),
    )
    assert "FORBIDDEN_CONTENT" in run(repo).stdout


def test_02m_unfrozen_fails(repo: Path) -> None:
    mutate(repo, REPORT_03A, lambda text: text.replace("02M: FROZEN", "02M: UNFROZEN", 1))
    result = run(repo)
    assert "02M_STATUS" in result.stdout or "FORBIDDEN_CONTENT" in result.stdout


def test_full_planning_completeness_proven_fails(repo: Path) -> None:
    mutate(
        repo,
        REPORT_03A,
        lambda text: text.replace("Full planning completeness: NOT_PROVEN", "Full planning completeness proven", 1),
    )
    result = run(repo)
    assert "PLANNING_STATUS" in result.stdout or "FORBIDDEN_CONTENT" in result.stdout


def test_final_marker_missing_fails(repo: Path) -> None:
    mutate(repo, REPORT_03A, lambda text: text.replace("CLOSURE_03A_TAX_BEHAVIOR_CONTRACTS_PASS", ""))
    assert "FINAL_MARKER_INVALID" in run(repo).stdout


def test_ready_for_review_fails(repo: Path) -> None:
    mutate(repo, REPORT_03A, lambda text: text.replace("## 7. Final Marker", "READY_FOR_REVIEW\n\n## 7. Final Marker"))
    assert "READY_FOR_REVIEW_FORBIDDEN" in run(repo).stdout
