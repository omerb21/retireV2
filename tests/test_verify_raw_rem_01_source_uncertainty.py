from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_raw_rem_01_source_uncertainty.py"
FILES = (
    Path("specs/runtime/V1_SOURCE_RAW_LOGIC_INVENTORY.md"),
    Path("specs/runtime/V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_01_SOURCE_UNCERTAINTY_TRIAGE.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_01_SOURCE_UNCERTAINTY_DECISIONS.md"),
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


def replace_row(text: str, width: int, predicate, change) -> str:
    for line in text.splitlines():
        if line.startswith("| V1LOGIC-"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == width and predicate(cells):
                change(cells)
                return text.replace(line, "| " + " | ".join(cells) + " |", 1)
    raise AssertionError("matching row not found")


def test_current_raw_rem_01_passes() -> None:
    result = run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_source_uncertain_decision_removed_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[3], lambda text: re.sub(r"^\| V1LOGIC-001 \|.*\n", "", text, count=1, flags=re.MULTILINE))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "DECISION_CARDINALITY" in result.stdout


def test_non_source_uncertain_decision_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[3], lambda text: text.replace("RAW_REM_01_SOURCE_UNCERTAINTY_DECISIONS_CREATED", "| V1LOGIC-004 | SOURCE_REQUIRES_MANUAL_ARCHIVE_REVIEW | YES | MANUAL_ARCHIVE_REVIEW_REQUIRED | Not an original source-uncertain row. |\n\nRAW_REM_01_SOURCE_UNCERTAINTY_DECISIONS_CREATED"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "NON_SOURCE_UNCERTAIN_DECISION" in result.stdout


def test_invalid_outcome_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[3], lambda text: replace_row(text, 5, lambda cells: True, lambda cells: cells.__setitem__(1, "INVALID_OUTCOME")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVALID_DECISION_OUTCOME" in result.stdout


def test_empty_reason_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[3], lambda text: replace_row(text, 5, lambda cells: True, lambda cells: cells.__setitem__(4, "")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "DECISION_SUMMARY_REASON_EMPTY" in result.stdout


def test_manual_review_must_block_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[3], lambda text: replace_row(text, 5, lambda cells: cells[1] == "SOURCE_REQUIRES_MANUAL_ARCHIVE_REVIEW", lambda cells: cells.__setitem__(2, "NO")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "DECISION_BLOCKING_OUTCOME_NOT_BLOCKING" in result.stdout


def test_confirmed_mapping_requires_future_package(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[3], lambda text: replace_row(text, 5, lambda cells: True, lambda cells: (cells.__setitem__(1, "SOURCE_CONFIRMED_FOR_FUTURE_MAPPING"), cells.__setitem__(3, ""))))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "DECISION_CONFIRMED_PACKAGE_INVALID" in result.stdout


def test_original_audit_marker_change_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[1], lambda text: text.replace("V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_FAIL", "V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_PASS"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "ORIGINAL_AUDIT_MARKER_CHANGED" in result.stdout


def test_original_source_uncertain_count_change_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[1], lambda text: replace_row(text, 13, lambda cells: cells[9] == "V1LOGIC_SOURCE_UNCERTAIN_FAIL", lambda cells: cells.__setitem__(9, "V1LOGIC_COVERED_BY_BEHAVIOR_ONLY_GOLDEN_NOT_REQUIRED")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "SOURCE_UNCERTAIN_BASELINE_CHANGED" in result.stdout


def test_fail_marker_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[2], lambda text: text.replace("RAW_REM_01_SOURCE_UNCERTAINTY_TRIAGE_PASS", "RAW_REM_01_SOURCE_UNCERTAINTY_TRIAGE_FAIL"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVALID_TRIAGE_FINAL_MARKER" in result.stdout
