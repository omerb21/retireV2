from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_v2_req_13_coverage_closure_plan.py"
PLAN = Path("specs/runtime/raw_remediation/V2_REQ_13_COVERAGE_CLOSURE_PLAN_FROM_RAW_REM_03_TO_05.md")
FILES = (
    PLAN,
    Path("specs/runtime/raw_remediation/V2_REQ_12_RAW_REMEDIATION_PROGRESS_CHECKPOINT.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_VERIFICATION.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_04_CLEARINGHOUSE_PARSER_BALANCE_LEDGER_VERIFICATION.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_VERIFICATION.md"),
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


def mutate(repo: Path, old: str, new: str) -> None:
    path = repo / PLAN
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_current_plan_passes() -> None:
    result = run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_missing_final_marker_fails(repo_copy: Path) -> None:
    mutate(repo_copy, "V2_REQ_13_COVERAGE_CLOSURE_PLAN_FROM_RAW_REM_03_TO_05_PASS", "")
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVALID_FINAL_MARKER" in result.stdout


def test_ready_for_review_fails(repo_copy: Path) -> None:
    mutate(repo_copy, "## 12. Final Marker", "READY_FOR_REVIEW\n\n## 12. Final Marker")
    result = run(repo_copy)
    assert result.returncode != 0
    assert "READY_FOR_REVIEW_FORBIDDEN" in result.stdout


@pytest.mark.parametrize(
    ("old", "new", "failure"),
    [
        ("Closure-scope items: `1,455`", "Closure-scope items: `1,454`", "CLOSURE_SCOPE_INVALID"),
        ("Closure-scope resolved: `0`", "Closure-scope resolved: `1`", "CLOSURE_RESOLVED_INVALID"),
        ("Closure-scope remaining blocking: `1,455`", "Closure-scope remaining blocking: `1,454`", "CLOSURE_BLOCKING_INVALID"),
        ("Golden candidate total: `1,107`", "Golden candidate total: `1,106`", "GOLDEN_TOTAL_INVALID"),
    ],
)
def test_required_total_change_fails(repo_copy: Path, old: str, new: str, failure: str) -> None:
    mutate(repo_copy, old, new)
    result = run(repo_copy)
    assert result.returncode != 0
    assert failure in result.stdout


def test_required_package_missing_fails(repo_copy: Path) -> None:
    path = repo_copy / PLAN
    lines = path.read_text(encoding="utf-8").splitlines()
    lines = [line for line in lines if not line.startswith("| CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS |")]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = run(repo_copy)
    assert result.returncode != 0
    assert "PACKAGE_TABLE_CARDINALITY" in result.stdout


def test_closure_int_01_not_first_fails(repo_copy: Path) -> None:
    mutate(
        repo_copy,
        "1. `CLOSURE-INT-01_RAWLOGIC_TO_CORE_MAP_TRACEABILITY_INDEX`",
        "1. `CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS`",
    )
    result = run(repo_copy)
    assert result.returncode != 0
    assert "RECOMMENDED_FIRST_INVALID" in result.stdout


def test_closure_int_03_not_last_fails(repo_copy: Path) -> None:
    mutate(
        repo_copy,
        "17. `CLOSURE-INT-03_REGRESSION_AND_FAILURE_COUNT_REBASE`",
        "17. `CLOSURE-INT-02_RAWLOGIC_CLOSURE_VERIFIER_UPDATE`",
    )
    result = run(repo_copy)
    assert result.returncode != 0
    assert "RECOMMENDED_LAST_INVALID" in result.stdout


def test_implementation_recommendation_fails(repo_copy: Path) -> None:
    mutate(repo_copy, "## 8. Closure vs Implementation Boundary", "Recommended next step: begin product implementation.\n\n## 8. Closure vs Implementation Boundary")
    result = run(repo_copy)
    assert result.returncode != 0
    assert "IMPLEMENTATION_RECOMMENDED" in result.stdout


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("## 8. Closure vs Implementation Boundary", "Recommended next step: proceed to 02M.\n\n## 8. Closure vs Implementation Boundary"),
        ("02M: `FROZEN`", "02M: `UNFROZEN`"),
    ],
)
def test_02m_recommendation_or_unfreeze_fails(repo_copy: Path, old: str, new: str) -> None:
    mutate(repo_copy, old, new)
    result = run(repo_copy)
    assert result.returncode != 0
    assert "02M_" in result.stdout


def test_planning_completeness_claim_fails(repo_copy: Path) -> None:
    mutate(repo_copy, "Full planning completeness: `NOT_PROVEN`", "Full planning completeness: `PROVEN`")
    result = run(repo_copy)
    assert result.returncode != 0
    assert "PLANNING_COMPLETENESS" in result.stdout


def test_raw_rem_06_to_10_declared_unnecessary_fails(repo_copy: Path) -> None:
    mutate(
        repo_copy,
        "RAW-REM-06..10 remain necessary unless a later scope decision changes them.",
        "RAW-REM-06..10 are unnecessary.",
    )
    result = run(repo_copy)
    assert result.returncode != 0
    assert "RAW_REM_06_TO_10" in result.stdout


def test_closure_already_happened_claim_fails(repo_copy: Path) -> None:
    mutate(repo_copy, "No closure is completed by this plan.", "Closure has already happened.")
    result = run(repo_copy)
    assert result.returncode != 0
    assert "CLOSURE_ALREADY_CLAIMED" in result.stdout
