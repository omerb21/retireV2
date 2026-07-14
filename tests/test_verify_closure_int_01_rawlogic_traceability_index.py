from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_closure_int_01_rawlogic_traceability_index.py"
PLAN = Path("specs/runtime/raw_remediation/closure/CLOSURE_INT_01_RAWLOGIC_TO_CORE_MAP_TRACEABILITY_INDEX.md")
INDEX = Path("specs/runtime/raw_remediation/closure/CLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX.md")
CLOSURE_03A = Path("specs/runtime/raw_remediation/closure/CLOSURE_03A_TAX_BEHAVIOR_CONTRACTS.md")
BEHAVIOR_MAP = Path("specs/runtime/V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP.md")
FILES = (
    PLAN,
    INDEX,
    CLOSURE_03A,
    BEHAVIOR_MAP,
    Path("specs/runtime/raw_remediation/V2_REQ_13_COVERAGE_CLOSURE_PLAN_FROM_RAW_REM_03_TO_05.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_DECISIONS.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_04_CLEARINGHOUSE_PARSER_BALANCE_LEDGER_DECISIONS.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_DECISIONS.md"),
)


@pytest.fixture()
def repo_copy(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for relative in FILES:
        (repo / relative.parent).mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, repo / relative)
    return repo


def run(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo)],
        capture_output=True,
        text=True,
        check=False,
    )


def mutate(repo: Path, relative: Path, transform) -> None:
    path = repo / relative
    path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")


def replace_index_row(text: str, predicate, change) -> str:
    for line in text.splitlines():
        if line.startswith("| V1LOGIC-"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == 11 and predicate(cells):
                change(cells)
                return text.replace(line, "| " + " | ".join(cells) + " |", 1)
    raise AssertionError("matching index row not found")


def remove_index_row(text: str, predicate) -> str:
    for line in text.splitlines():
        if line.startswith("| V1LOGIC-"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == 11 and predicate(cells):
                return text.replace(line + "\n", "", 1)
    raise AssertionError("matching index row not found")


def first_closed(text: str) -> list[str]:
    for line in text.splitlines():
        if line.startswith("| V1LOGIC-"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == 11 and cells[8] == "CLOSED_BY_FUTURE_PATCH":
                return cells
    raise AssertionError("closed index row not found")


def close_with_evidence(cells: list[str], evidence: str) -> None:
    cells[8] = "CLOSED_BY_FUTURE_PATCH"
    cells[9] = evidence


def remove_table_row(text: str, predicate, width: int) -> str:
    for line in text.splitlines():
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == width and predicate(cells):
                return text.replace(line + "\n", "", 1)
    raise AssertionError("matching table row not found")


def test_current_index_passes_with_91_verified_closures() -> None:
    result = run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "closed_rows=91" in result.stdout
    assert "closure_03a_closed_rows=91" in result.stdout
    assert "invalid_closed_rows=0" in result.stdout


def test_valid_closure_evidence_contract_reference_removed_fails(repo_copy: Path) -> None:
    mutate(
        repo_copy,
        INDEX,
        lambda text: replace_index_row(
            text,
            lambda cells: cells[8] == "CLOSED_BY_FUTURE_PATCH",
            lambda cells: cells.__setitem__(9, "CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS"),
        ),
    )
    result = run(repo_copy)
    assert result.returncode != 0
    assert "CLOSED_EVIDENCE_MISSING" in result.stdout


def test_closed_row_with_empty_evidence_fails(repo_copy: Path) -> None:
    mutate(
        repo_copy,
        INDEX,
        lambda text: replace_index_row(
            text,
            lambda cells: cells[8] == "CLOSED_BY_FUTURE_PATCH",
            lambda cells: cells.__setitem__(9, "EMPTY_NOT_CLOSED"),
        ),
    )
    result = run(repo_copy)
    assert result.returncode != 0
    assert "CLOSED_EVIDENCE_MISSING" in result.stdout


@pytest.mark.parametrize("source", ["RAW-REM-04", "RAW-REM-05"])
def test_non_tax_source_cannot_be_closed(repo_copy: Path, source: str) -> None:
    evidence = first_closed((repo_copy / INDEX).read_text(encoding="utf-8"))[9]
    mutate(
        repo_copy,
        INDEX,
        lambda text: replace_index_row(
            text,
            lambda cells: cells[1] == source,
            lambda cells: close_with_evidence(cells, evidence),
        ),
    )
    result = run(repo_copy)
    assert result.returncode != 0
    assert "CLOSED_SOURCE_NOT_ALLOWED" in result.stdout


def test_raw_rem_03_nonselected_row_cannot_be_closed(repo_copy: Path) -> None:
    evidence = first_closed((repo_copy / INDEX).read_text(encoding="utf-8"))[9]
    mutate(
        repo_copy,
        INDEX,
        lambda text: replace_index_row(
            text,
            lambda cells: cells[1] == "RAW-REM-03" and cells[3] != "TAXMAP_NEEDS_BEHAVIOR_CONTRACT",
            lambda cells: close_with_evidence(cells, evidence),
        ),
    )
    result = run(repo_copy)
    assert result.returncode != 0
    assert "CLOSED_OUTCOME_NOT_SELECTED" in result.stdout


def test_unknown_closure_package_fails(repo_copy: Path) -> None:
    mutate(
        repo_copy,
        INDEX,
        lambda text: replace_index_row(
            text,
            lambda cells: cells[8] == "CLOSED_BY_FUTURE_PATCH",
            lambda cells: cells.__setitem__(9, cells[9].replace("CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS", "UNKNOWN-CLOSURE-PACKAGE")),
        ),
    )
    result = run(repo_copy)
    assert result.returncode != 0
    assert "UNKNOWN_CLOSURE_PACKAGE" in result.stdout


def test_closed_row_missing_from_closure_report_fails(repo_copy: Path) -> None:
    logic_id = first_closed((repo_copy / INDEX).read_text(encoding="utf-8"))[0]
    mutate(repo_copy, CLOSURE_03A, lambda text: remove_table_row(text, lambda cells: cells[0] == logic_id, 9))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "CLOSURE_03A_REPORT_CARDINALITY" in result.stdout


def test_closed_row_missing_from_behavior_map_fails(repo_copy: Path) -> None:
    logic_id = first_closed((repo_copy / INDEX).read_text(encoding="utf-8"))[0]
    mutate(repo_copy, BEHAVIOR_MAP, lambda text: remove_table_row(text, lambda cells: cells[1] == logic_id, 13))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "CLOSURE_03A_BEHAVIOR_MAP_CARDINALITY" in result.stdout


def test_total_row_count_1454_fails(repo_copy: Path) -> None:
    mutate(repo_copy, INDEX, lambda text: remove_index_row(text, lambda cells: cells[8] != "CLOSED_BY_FUTURE_PATCH"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "TOTAL_ROW_COUNT_INVALID" in result.stdout


def test_final_marker_missing_fails(repo_copy: Path) -> None:
    mutate(repo_copy, PLAN, lambda text: text.replace("CLOSURE_INT_01_RAWLOGIC_TO_CORE_MAP_TRACEABILITY_INDEX_PASS", ""))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVALID_PLAN_MARKER" in result.stdout


def test_ready_for_review_fails(repo_copy: Path) -> None:
    mutate(repo_copy, PLAN, lambda text: text.replace("## 12. Final Marker", "READY_FOR_REVIEW\n\n## 12. Final Marker"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "READY_FOR_REVIEW_FORBIDDEN" in result.stdout


@pytest.mark.parametrize(
    ("claim", "failure_code"),
    [
        ("Implementation: READY", "INDEX_IMPLEMENTATION_READINESS_CLAIM"),
        ("Full planning completeness: PROVEN", "INDEX_FULL_PLANNING_COMPLETENESS_CLAIM"),
        ("02M is UNFROZEN", "INDEX_02M_UNFROZEN"),
    ],
)
def test_index_governance_claims_fail(repo_copy: Path, claim: str, failure_code: str) -> None:
    mutate(repo_copy, INDEX, lambda text: text.replace("CLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX_CREATED", claim + "\n\nCLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX_CREATED"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert failure_code in result.stdout
