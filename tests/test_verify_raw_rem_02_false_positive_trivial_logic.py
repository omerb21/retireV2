from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_raw_rem_02_false_positive_trivial_logic.py"
FILES = (
    Path("specs/runtime/V1_SOURCE_RAW_LOGIC_INVENTORY.md"),
    Path("specs/runtime/V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT.md"),
    Path("specs/runtime/V1_SOURCE_RAW_LOGIC_REMEDIATION_PLAN.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_CLASSIFICATION.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_DECISIONS.md"),
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


def test_current_raw_rem_02_passes() -> None:
    result = run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_scope_decision_removed_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[4], lambda text: re.sub(r"^\| V1LOGIC-006 \|.*\n", "", text, count=1, flags=re.MULTILINE))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "DECISION_CARDINALITY" in result.stdout


def test_source_uncertain_decision_added_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[4], lambda text: text.replace("RAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_DECISIONS_CREATED", "| V1LOGIC-001 | RAWLOGIC_REAL_REQUIRES_MAPPING | YES | RAW-REM-10 | Source-uncertain ID must not enter RAW-REM-02. |\n\nRAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_DECISIONS_CREATED"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "SOURCE_UNCERTAIN_ID_IN_DECISIONS" in result.stdout


def test_invalid_outcome_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[4], lambda text: replace_row(text, 5, lambda cells: True, lambda cells: cells.__setitem__(1, "INVALID_OUTCOME")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVALID_DECISION_OUTCOME" in result.stdout


def test_empty_reason_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[4], lambda text: replace_row(text, 5, lambda cells: True, lambda cells: cells.__setitem__(4, "")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "DECISION_REASON_EMPTY" in result.stdout


def test_real_mapping_requires_package_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[4], lambda text: replace_row(text, 5, lambda cells: cells[1] == "RAWLOGIC_REAL_REQUIRES_MAPPING", lambda cells: cells.__setitem__(3, "")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "DECISION_REAL_MAPPING_PACKAGE_INVALID" in result.stdout


def test_uncertain_classification_must_block_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[4], lambda text: replace_row(text, 5, lambda cells: True, lambda cells: (cells.__setitem__(1, "RAWLOGIC_CLASSIFICATION_UNCERTAIN_BLOCKED"), cells.__setitem__(2, "NO"))))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "DECISION_UNCERTAIN_NOT_BLOCKING" in result.stdout


def test_high_risk_trivial_without_safe_reason_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[3], lambda text: replace_row(text, 13, lambda cells: re.search(r"tax|report|validation|error", " ".join(cells[:6]), re.IGNORECASE) is not None, lambda cells: (cells.__setitem__(6, "RAWLOGIC_TRIVIAL_CRUD_OR_TRANSPORT_WITH_REASON"), cells.__setitem__(7, "Looks simple."), cells.__setitem__(11, "NO"))))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "HIGH_RISK_UNSAFE_CLASSIFICATION" in result.stdout


def test_original_audit_marker_change_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[1], lambda text: text.replace("V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_FAIL", "V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_PASS"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "ORIGINAL_AUDIT_MARKER_CHANGED" in result.stdout


@pytest.mark.parametrize(("status", "failure"), [("V1LOGIC_UNCOVERED_FAIL", "UNCOVERED_BASELINE_CHANGED"), ("V1LOGIC_SOURCE_UNCERTAIN_FAIL", "SOURCE_UNCERTAIN_BASELINE_CHANGED")])
def test_original_count_change_fails(repo_copy: Path, status: str, failure: str) -> None:
    mutate(repo_copy, FILES[1], lambda text: replace_row(text, 13, lambda cells: cells[9] == status, lambda cells: cells.__setitem__(9, "V1LOGIC_COVERED_BY_BEHAVIOR_ONLY_GOLDEN_NOT_REQUIRED")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert failure in result.stdout


def test_fail_marker_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[3], lambda text: text.replace("RAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_CLASSIFICATION_PASS", "RAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_CLASSIFICATION_FAIL"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVALID_CLASSIFICATION_FINAL_MARKER" in result.stdout
