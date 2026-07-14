from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_v2_req_12_raw_remediation_progress_checkpoint.py"
CHECKPOINT = Path("specs/runtime/raw_remediation/V2_REQ_12_RAW_REMEDIATION_PROGRESS_CHECKPOINT.md")
FILES = (
    CHECKPOINT,
    Path("specs/runtime/V1_SOURCE_RAW_LOGIC_REMEDIATION_PLAN.md"),
    Path("specs/runtime/V1_SOURCE_RAW_LOGIC_COVERAGE_VERIFICATION.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_01_SOURCE_UNCERTAINTY_VERIFICATION.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_VERIFICATION.md"),
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
    path = repo / CHECKPOINT
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_current_checkpoint_passes() -> None:
    result = run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_missing_final_marker_fails(repo_copy: Path) -> None:
    mutate(repo_copy, "V2_REQ_12_RAW_REMEDIATION_PROGRESS_CHECKPOINT_PASS", "")
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVALID_FINAL_PASS_MARKER" in result.stdout


def test_ready_for_review_fails(repo_copy: Path) -> None:
    mutate(repo_copy, "## 11. Final Marker", "READY_FOR_REVIEW\n\n## 11. Final Marker")
    result = run(repo_copy)
    assert result.returncode != 0
    assert "READY_FOR_REVIEW_FORBIDDEN" in result.stdout


def test_completed_checked_total_change_fails(repo_copy: Path) -> None:
    mutate(repo_copy, "Completed checked items: `2,421`", "Completed checked items: `2,420`")
    result = run(repo_copy)
    assert result.returncode != 0
    assert "COMPLETED_CHECKED_INVALID" in result.stdout


def test_completed_resolved_total_change_fails(repo_copy: Path) -> None:
    mutate(repo_copy, "Completed resolved items: `0`", "Completed resolved items: `1`")
    result = run(repo_copy)
    assert result.returncode != 0
    assert "COMPLETED_RESOLVED_INVALID" in result.stdout


def test_total_blocking_scope_change_fails(repo_copy: Path) -> None:
    mutate(repo_copy, "Total blocking scope remains: `6,691`", "Total blocking scope remains: `6,690`")
    result = run(repo_copy)
    assert result.returncode != 0
    assert "TOTAL_BLOCKING_SCOPE_INVALID" in result.stdout


def test_recommended_next_step_change_fails(repo_copy: Path) -> None:
    mutate(
        repo_copy,
        "V2-REQ-13_CREATE_COVERAGE_CLOSURE_PLAN_FROM_RAW_REM_03_TO_05",
        "RAW-REM-06_SCENARIO_CASHFLOW_COMPARISON",
    )
    result = run(repo_copy)
    assert result.returncode != 0
    assert "RECOMMENDED_NEXT_STEP_INVALID" in result.stdout


def test_implementation_recommendation_fails(repo_copy: Path) -> None:
    mutate(repo_copy, "## 8. Explicit Non-Recommendations", "Recommended next step: begin product implementation.\n\n## 8. Explicit Non-Recommendations")
    result = run(repo_copy)
    assert result.returncode != 0
    assert "IMPLEMENTATION_RECOMMENDED" in result.stdout


def test_02m_recommendation_fails(repo_copy: Path) -> None:
    mutate(repo_copy, "## 8. Explicit Non-Recommendations", "Recommended next step: proceed to 02M.\n\n## 8. Explicit Non-Recommendations")
    result = run(repo_copy)
    assert result.returncode != 0
    assert "02M_RECOMMENDED" in result.stdout


def test_02m_not_frozen_fails(repo_copy: Path) -> None:
    mutate(repo_copy, "02M: `FROZEN`", "02M: `UNFROZEN`")
    result = run(repo_copy)
    assert result.returncode != 0
    assert "02M_STATUS_INVALID" in result.stdout


def test_planning_completeness_claim_fails(repo_copy: Path) -> None:
    mutate(repo_copy, "Full planning completeness: `NOT_PROVEN`", "Full planning completeness: `PROVEN`")
    result = run(repo_copy)
    assert result.returncode != 0
    assert "PLANNING_COMPLETENESS" in result.stdout


def test_raw_rem_06_to_10_declared_unnecessary_fails(repo_copy: Path) -> None:
    mutate(
        repo_copy,
        "Do not skip RAW-REM-06..10 permanently; they remain necessary unless a later management decision changes scope.",
        "RAW-REM-06..10 are unnecessary.",
    )
    result = run(repo_copy)
    assert result.returncode != 0
    assert "RAW_REM_06_TO_10" in result.stdout
