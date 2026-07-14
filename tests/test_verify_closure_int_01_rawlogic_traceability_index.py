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
FILES = (
    PLAN,
    INDEX,
    Path("specs/runtime/raw_remediation/V2_REQ_13_COVERAGE_CLOSURE_PLAN_FROM_RAW_REM_03_TO_05.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_DECISIONS.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_04_CLEARINGHOUSE_PARSER_BALANCE_LEDGER_DECISIONS.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_DECISIONS.md"),
    Path("specs/runtime/raw_remediation/closure/CLOSURE_03A_TAX_BEHAVIOR_CONTRACTS.md"),
    Path("specs/runtime/raw_remediation/closure/CLOSURE_03B_TAX_FORMULA_RULE_CONTRACTS.md"),
    Path("specs/runtime/V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP.md"),
)


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


def replace_index_row(text: str, predicate, updates: dict[int, str]) -> str:
    for line in text.splitlines():
        if line.startswith("| V1LOGIC-"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == 11 and predicate(cells):
                for index, value in updates.items():
                    cells[index] = value
                return text.replace(line, "| " + " | ".join(cells) + " |", 1)
    raise AssertionError("matching index row not found")


def test_current_index_passes_with_136_verified_closures() -> None:
    result = run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "closed_rows=136" in result.stdout
    assert "closure_03a_closed_rows=91" in result.stdout
    assert "closure_03b_closed_rows=45" in result.stdout
    assert "invalid_closed_rows=0" in result.stdout


@pytest.mark.parametrize(
    ("package", "failure_code"),
    [
        ("CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS", "CLOSED_EVIDENCE_MISSING"),
        ("CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS", "CLOSED_EVIDENCE_MISSING"),
    ],
)
def test_closure_evidence_without_contract_id_fails(repo: Path, package: str, failure_code: str) -> None:
    mutate(
        repo,
        INDEX,
        lambda text: replace_index_row(text, lambda cells: cells[9].startswith(package + ":"), {9: package}),
    )
    result = run(repo)
    assert result.returncode != 0
    assert failure_code in result.stdout


@pytest.mark.parametrize("source", ["RAW-REM-04", "RAW-REM-05"])
def test_non_tax_row_closed_fails(repo: Path, source: str) -> None:
    mutate(
        repo,
        INDEX,
        lambda text: replace_index_row(
            text,
            lambda cells: cells[1] == source,
            {8: "CLOSED_BY_FUTURE_PATCH", 9: "UNKNOWN-CLOSURE:FAKE"},
        ),
    )
    result = run(repo)
    assert result.returncode != 0
    assert "CLOSED_SOURCE_NOT_ALLOWED" in result.stdout


def test_raw_rem_03_outside_03a_03b_closed_fails(repo: Path) -> None:
    mutate(
        repo,
        INDEX,
        lambda text: replace_index_row(
            text,
            lambda cells: cells[1] == "RAW-REM-03" and cells[3] == "TAXMAP_NEEDS_BEHAVIOR_AND_GOLDEN",
            {8: "CLOSED_BY_FUTURE_PATCH", 9: "UNKNOWN-CLOSURE:FAKE"},
        ),
    )
    result = run(repo)
    assert result.returncode != 0
    assert "UNKNOWN_CLOSURE_PACKAGE" in result.stdout


def test_unknown_closure_package_fails(repo: Path) -> None:
    mutate(
        repo,
        INDEX,
        lambda text: replace_index_row(
            text,
            lambda cells: cells[9].startswith("CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS:"),
            {9: "UNKNOWN-CLOSURE-PACKAGE:C03B-FR-001"},
        ),
    )
    assert "UNKNOWN_CLOSURE_PACKAGE" in run(repo).stdout


def test_closed_row_with_empty_evidence_fails(repo: Path) -> None:
    mutate(
        repo,
        INDEX,
        lambda text: replace_index_row(
            text,
            lambda cells: cells[8] == "CLOSED_BY_FUTURE_PATCH",
            {9: "EMPTY_NOT_CLOSED"},
        ),
    )
    assert "CLOSED_EVIDENCE_MISSING" in run(repo).stdout


def test_total_closed_count_not_136_fails(repo: Path) -> None:
    mutate(
        repo,
        INDEX,
        lambda text: replace_index_row(
            text,
            lambda cells: cells[9].startswith("CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS:"),
            {8: "NOT_CLOSED", 9: "EMPTY_NOT_CLOSED"},
        ),
    )
    assert "CLOSED_ROW_COUNT_INVALID" in run(repo).stdout


def test_closure_03a_count_not_91_fails(repo: Path) -> None:
    mutate(
        repo,
        INDEX,
        lambda text: replace_index_row(
            text,
            lambda cells: cells[9].startswith("CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS:"),
            {8: "NOT_CLOSED", 9: "EMPTY_NOT_CLOSED"},
        ),
    )
    assert "CLOSURE_03A_VALID_ROW_COUNT_INVALID" in run(repo).stdout


def test_closure_03b_count_not_45_fails(repo: Path) -> None:
    mutate(
        repo,
        INDEX,
        lambda text: replace_index_row(
            text,
            lambda cells: cells[9].startswith("CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS:"),
            {8: "NOT_CLOSED", 9: "EMPTY_NOT_CLOSED"},
        ),
    )
    assert "CLOSURE_03B_VALID_ROW_COUNT_INVALID" in run(repo).stdout


def test_final_marker_missing_fails(repo: Path) -> None:
    mutate(repo, PLAN, lambda text: text.replace("CLOSURE_INT_01_RAWLOGIC_TO_CORE_MAP_TRACEABILITY_INDEX_PASS", ""))
    assert "INVALID_PLAN_MARKER" in run(repo).stdout


def test_ready_for_review_fails(repo: Path) -> None:
    mutate(repo, PLAN, lambda text: text.replace("## 12. Final Marker", "READY_FOR_REVIEW\n\n## 12. Final Marker"))
    assert "READY_FOR_REVIEW_FORBIDDEN" in run(repo).stdout


@pytest.mark.parametrize(
    ("claim", "failure_code"),
    [
        ("Implementation: READY", "INDEX_IMPLEMENTATION_READINESS_CLAIM"),
        ("Full planning completeness: PROVEN", "INDEX_FULL_PLANNING_COMPLETENESS_CLAIM"),
        ("02M is UNFROZEN", "INDEX_02M_UNFROZEN"),
    ],
)
def test_index_governance_claims_fail(repo: Path, claim: str, failure_code: str) -> None:
    mutate(
        repo,
        INDEX,
        lambda text: text.replace(
            "CLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX_CREATED",
            claim + "\n\nCLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX_CREATED",
        ),
    )
    assert failure_code in run(repo).stdout
