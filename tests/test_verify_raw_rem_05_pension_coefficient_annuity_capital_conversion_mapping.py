from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_raw_rem_05_pension_coefficient_annuity_capital_conversion_mapping.py"
FILES = (
    Path("specs/runtime/V1_SOURCE_RAW_LOGIC_INVENTORY.md"),
    Path("specs/runtime/V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT.md"),
    Path("specs/runtime/V1_SOURCE_RAW_LOGIC_REMEDIATION_PLAN.md"),
    Path("specs/runtime/raw_remediation/RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_MAPPING.md"),
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


def replace_row(text: str, width: int, predicate, change) -> str:
    for line in text.splitlines():
        if line.startswith("| V1LOGIC-"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == width and predicate(cells):
                change(cells)
                return text.replace(line, "| " + " | ".join(cells) + " |", 1)
    raise AssertionError("matching row not found")


def remove_row(text: str, width: int, predicate) -> str:
    for line in text.splitlines():
        if line.startswith("| V1LOGIC-"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == width and predicate(cells):
                return text.replace(line + "\n", "", 1)
    raise AssertionError("matching row not found")


def test_current_raw_rem_05_passes() -> None:
    result = run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_scope_decision_removed_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[4], lambda text: re.sub(r"^\| V1LOGIC-020 \|.*\n", "", text, count=1, flags=re.MULTILINE))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "DECISION_CARDINALITY" in result.stdout


def test_raw_rem_01_decision_added_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[4], lambda text: text.replace("RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_DECISIONS_CREATED", "| V1LOGIC-001 | Clearinghouse intake | PENMAP_NEEDS_MANUAL_SOURCE_REVIEW | YES | Manual review | RAW-REM-05-PATCH | V1 archive source is uncertain. |\n\nRAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_DECISIONS_CREATED"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "RAW_REM_01_ID_IN_DECISIONS" in result.stdout


@pytest.mark.parametrize("logic_id", ["V1LOGIC-006", "V1LOGIC-005", "V1LOGIC-380"])
def test_prior_package_only_decision_added_fails(repo_copy: Path, logic_id: str) -> None:
    mutate(repo_copy, FILES[4], lambda text: text.replace("RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_DECISIONS_CREATED", f"| {logic_id} | Clearinghouse intake | PENMAP_NEEDS_BEHAVIOR_CONTRACT | YES | Behavior contract | RAW-REM-05-PATCH | V1 archive row belongs to a prior package only. |\n\nRAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_DECISIONS_CREATED"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "RAW_REM_02_03_OR_04_ONLY_ID_IN_DECISIONS" in result.stdout


def test_invalid_outcome_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[4], lambda text: replace_row(text, 7, lambda cells: True, lambda cells: cells.__setitem__(2, "INVALID")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVALID_DECISION_OUTCOME" in result.stdout


def test_empty_reason_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[4], lambda text: replace_row(text, 7, lambda cells: True, lambda cells: cells.__setitem__(6, "")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "DECISION_REASON_EMPTY" in result.stdout


def test_needs_outcome_must_block_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[4], lambda text: replace_row(text, 7, lambda cells: cells[2].startswith("PENMAP_NEEDS_"), lambda cells: cells.__setitem__(3, "NO")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "DECISION_NEEDS_OUTCOME_NOT_BLOCKING" in result.stdout


def test_unclassified_fails_pass_package(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[4], lambda text: replace_row(text, 7, lambda cells: True, lambda cells: cells.__setitem__(2, "PENMAP_UNCLASSIFIED_FAIL")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "DECISION_UNCLASSIFIED_IN_PASS_PACKAGE" in result.stdout


def test_coefficient_conversion_inventory_row_removed_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[3], lambda text: remove_row(text, 9, lambda cells: cells[0] == "V1LOGIC-020"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "COEFFICIENT_CONVERSION_INVENTORY_MISSING" in result.stdout


def test_concrete_output_without_source_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[3], lambda text: replace_row(text, 7, lambda cells: cells[1].startswith("RAW05-GOLDEN-"), lambda cells: cells.__setitem__(3, "annuity=123")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "GOLDEN_EXPECTED_OUTPUT_SOURCE_INVALID" in result.stdout


@pytest.mark.parametrize("phrase", ["assumed", "probably", "standard coefficient", "typical pension", "expected annuity"])
def test_unsupported_coefficient_language_fails(repo_copy: Path, phrase: str) -> None:
    mutate(repo_copy, FILES[4], lambda text: replace_row(text, 7, lambda cells: True, lambda cells: cells.__setitem__(6, f"V1 archive evidence is {phrase}.")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "UNSUPPORTED_COEFFICIENT_LANGUAGE" in result.stdout


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
    mutate(repo_copy, FILES[3], lambda text: text.replace("RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_MAPPING_PASS", "RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_MAPPING_FAIL"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVALID_MAPPING_FINAL_MARKER" in result.stdout
