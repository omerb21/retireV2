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
)


@pytest.fixture()
def repo_copy(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for relative in FILES:
        (repo / relative.parent).mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, repo / relative)
    return repo


def run(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), "--repo-root", str(repo)], capture_output=True, text=True, check=False)


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


def remove_source_row(text: str, source: str) -> str:
    for line in text.splitlines():
        if line.startswith("| V1LOGIC-"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == 11 and cells[1] == source:
                return text.replace(line + "\n", "", 1)
    raise AssertionError("matching source row not found")


def test_current_index_passes() -> None:
    result = run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("source", ["RAW-REM-03", "RAW-REM-04", "RAW-REM-05"])
def test_source_row_removed_fails(repo_copy: Path, source: str) -> None:
    mutate(repo_copy, INDEX, lambda text: remove_source_row(text, source))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INDEX_CARDINALITY" in result.stdout


def test_duplicate_logic_id_fails(repo_copy: Path) -> None:
    mutate(repo_copy, INDEX, lambda text: text.replace("CLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX_CREATED", next(line for line in text.splitlines() if line.startswith("| V1LOGIC-")) + "\n\nCLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX_CREATED"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INDEX_CARDINALITY" in result.stdout


def test_extra_logic_id_fails(repo_copy: Path) -> None:
    extra = "| V1LOGIC-999999 | RAW-REM-03 | specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_DECISIONS.md | TAXMAP_NEEDS_BEHAVIOR_CONTRACT | Extra | CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS | BEHAVIOR_FORMULA_RULE_PARITY_MAP | NONE | NOT_CLOSED | EMPTY_NOT_CLOSED | Invalid extra row. |"
    mutate(repo_copy, INDEX, lambda text: text.replace("CLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX_CREATED", extra + "\n\nCLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX_CREATED"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "EXTRA_INDEX_LOGIC_ID" in result.stdout


def test_closed_status_fails(repo_copy: Path) -> None:
    mutate(repo_copy, INDEX, lambda text: replace_index_row(text, lambda cells: True, lambda cells: cells.__setitem__(8, "CLOSED_BY_FUTURE_PATCH")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVALID_CLOSURE_STATUS" in result.stdout


def test_nonempty_closure_evidence_fails(repo_copy: Path) -> None:
    mutate(repo_copy, INDEX, lambda text: replace_index_row(text, lambda cells: True, lambda cells: cells.__setitem__(9, "fake-evidence")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVALID_CLOSURE_EVIDENCE" in result.stdout


def test_future_package_empty_fails(repo_copy: Path) -> None:
    mutate(repo_copy, INDEX, lambda text: replace_index_row(text, lambda cells: True, lambda cells: cells.__setitem__(5, "")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "FUTURE_PACKAGE_EMPTY" in result.stdout


def test_invalid_target_artifact_fails(repo_copy: Path) -> None:
    mutate(repo_copy, INDEX, lambda text: replace_index_row(text, lambda cells: True, lambda cells: cells.__setitem__(6, "INVALID_ARTIFACT")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVALID_TARGET_ARTIFACT_TYPE" in result.stdout


def test_plan_claims_raw_coverage_fixed_fails(repo_copy: Path) -> None:
    mutate(repo_copy, PLAN, lambda text: text.replace("Raw V1 source logic coverage: `FAIL`", "Raw V1 source logic coverage: `FIXED`", 1))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "RAW_COVERAGE" in result.stdout


def test_plan_recommends_implementation_fails(repo_copy: Path) -> None:
    mutate(repo_copy, PLAN, lambda text: text.replace("## 10. Effect on Baseline", "Recommended next step: begin product implementation.\n\n## 10. Effect on Baseline"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "IMPLEMENTATION_RECOMMENDED" in result.stdout


def test_plan_unfreezes_02m_fails(repo_copy: Path) -> None:
    mutate(repo_copy, PLAN, lambda text: text.replace("02M: `FROZEN`", "02M: `UNFROZEN`", 1))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "02M_" in result.stdout


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
