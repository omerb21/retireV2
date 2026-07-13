from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_v1_source_raw_logic_coverage.py"
FILES = (
    Path("specs/runtime/V1_SOURCE_RAW_LOGIC_INVENTORY.md"),
    Path("specs/runtime/V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT.md"),
    Path("specs/runtime/V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP.md"),
    Path("specs/runtime/V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP.md"),
    Path("specs/runtime/V1_GOLDEN_MASTER_EXPECTED_OUTPUT_CASES.md"),
    Path("specs/runtime/V2_REQUIRED_CAPABILITY_UNIVERSE.md"),
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


def replace_audit_row(text: str, predicate, change) -> str:
    for line in text.splitlines():
        if line.startswith("| V1LOGIC-"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == 13 and predicate(cells):
                change(cells)
                return text.replace(line, "| " + " | ".join(cells) + " |", 1)
    raise AssertionError("Audit row not found")


def test_current_repository_result_matches_audit_marker() -> None:
    result = run(ROOT)
    audit = (ROOT / FILES[1]).read_text(encoding="utf-8")
    if "V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_PASS" in audit:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0
        assert "V1_SOURCE_RAW_LOGIC_COVERAGE_VERIFICATION_FAIL" in result.stdout


@pytest.mark.parametrize(("status", "failure"), [
    ("V1LOGIC_UNCOVERED_FAIL", "UNCOVERED_FAIL_PRESENT"),
    ("V1LOGIC_SOURCE_UNCERTAIN_FAIL", "SOURCE_UNCERTAIN_FAIL_PRESENT"),
])
def test_blocking_status_fails(repo_copy: Path, status: str, failure: str) -> None:
    mutate(repo_copy, FILES[1], lambda text: replace_audit_row(text, lambda cells: True, lambda cells: cells.__setitem__(9, status)))
    result = run(repo_copy)
    assert result.returncode != 0
    assert failure in result.stdout


@pytest.mark.parametrize(("index", "replacement", "failure"), [
    (6, "V1BEHAVIOR-999", "UNKNOWN_BEHAVIOR_REFERENCE"),
    (7, "V1GOLDEN-999", "UNKNOWN_GOLDEN_REFERENCE"),
    (8, "REQ-999", "UNKNOWN_REQ_REFERENCE"),
    (5, "V1ITEM-999", "UNKNOWN_ITEM_REFERENCE"),
])
def test_unknown_reference_fails(repo_copy: Path, index: int, replacement: str, failure: str) -> None:
    mutate(repo_copy, FILES[1], lambda text: replace_audit_row(text, lambda cells: True, lambda cells: cells.__setitem__(index, replacement)))
    result = run(repo_copy)
    assert result.returncode != 0
    assert failure in result.stdout


def test_required_golden_empty_fails(repo_copy: Path) -> None:
    required = {"V1LOGIC_FORMULA", "V1LOGIC_TAX_PARAMETER", "V1LOGIC_INDEXATION_CPI", "V1LOGIC_SCENARIO_CASHFLOW_RULE", "V1LOGIC_REPORT_OUTPUT_FIELD"}
    mutate(repo_copy, FILES[1], lambda text: replace_audit_row(text, lambda cells: cells[1] in required, lambda cells: (cells.__setitem__(7, ""), cells.__setitem__(9, "V1LOGIC_COVERED_BY_BEHAVIOR_AND_GOLDEN"))))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "MISSING_REQUIRED_GOLDEN" in result.stdout


def test_high_risk_domain_removed_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[1], lambda text: re.sub(r"^\| Retirement age by gender/date/year \|.*\n", "", text, count=1, flags=re.MULTILINE))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "HIGH_RISK_DOMAIN_MISSING" in result.stdout


def test_user_challenge_removed_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[1], lambda text: re.sub(r"^\| retirement age by gender \|.*\n", "", text, count=1, flags=re.MULTILINE))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "USER_EXAMPLE_CHALLENGE_MISSING" in result.stdout


def test_fail_marker_prevents_pass(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[1], lambda text: text.replace("V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_FAIL", "V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_PASS"))
    pass_marked = run(repo_copy)
    assert pass_marked.returncode != 0
    assert "UNCOVERED_FAIL_PRESENT" in pass_marked.stdout
    mutate(repo_copy, FILES[1], lambda text: text.replace("V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_PASS", "V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_FAIL"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVALID_AUDIT_FINAL_MARKER" in result.stdout


def test_duplicate_logic_id_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[0], lambda text: text.replace("| V1LOGIC-002 |", "| V1LOGIC-001 |", 1))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "DUPLICATE_V1LOGIC_ID" in result.stdout


def test_inventory_item_missing_from_audit_fails(repo_copy: Path) -> None:
    mutate(repo_copy, FILES[1], lambda text: re.sub(r"^\| V1LOGIC-001 \|.*\n", "", text, count=1, flags=re.MULTILINE))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVENTORY_AUDIT_CARDINALITY" in result.stdout
