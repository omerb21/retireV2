from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/summarize_v1_source_raw_logic_failures.py"
INVENTORY = Path("specs/runtime/V1_SOURCE_RAW_LOGIC_INVENTORY.md")
AUDIT = Path("specs/runtime/V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT.md")


@pytest.fixture()
def repo_copy(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for relative in (INVENTORY, AUDIT):
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


def test_current_failure_baseline_passes() -> None:
    result = run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "v1logic_items_total=6736" in result.stdout
    assert "uncovered_fail=6457" in result.stdout
    assert "source_uncertain_fail=234" in result.stdout


def test_pass_marker_fails(repo_copy: Path) -> None:
    mutate(repo_copy, AUDIT, lambda text: text.replace("V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_FAIL", "V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_PASS"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "AUDIT_FINAL_MARKER_INVALID" in result.stdout


@pytest.mark.parametrize("status", ["V1LOGIC_UNCOVERED_FAIL", "V1LOGIC_SOURCE_UNCERTAIN_FAIL"])
def test_zero_failure_count_without_updated_baseline_fails(repo_copy: Path, status: str) -> None:
    mutate(repo_copy, AUDIT, lambda text: text.replace(f"| {status} |", "| V1LOGIC_COVERED_BY_BEHAVIOR_ONLY_GOLDEN_NOT_REQUIRED |"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "UNAUTHORIZED_BASELINE_DRIFT" in result.stdout


def test_required_high_risk_domain_removed_fails(repo_copy: Path) -> None:
    mutate(repo_copy, AUDIT, lambda text: re.sub(r"^\| Retirement age by gender/date/year \|.*\n", "", text, count=1, flags=re.MULTILINE))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "HIGH_RISK_DOMAIN_MISSING" in result.stdout


def test_inventory_marker_missing_fails(repo_copy: Path) -> None:
    mutate(repo_copy, INVENTORY, lambda text: text.replace("V1_SOURCE_RAW_LOGIC_INVENTORY_CREATED", ""))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVENTORY_MARKER_INVALID" in result.stdout


def test_audit_file_missing_fails(repo_copy: Path) -> None:
    (repo_copy / AUDIT).unlink()
    result = run(repo_copy)
    assert result.returncode != 0
    assert "AUDIT_FILE_MISSING" in result.stdout


def test_unparseable_counts_fail(repo_copy: Path) -> None:
    mutate(repo_copy, AUDIT, lambda text: re.sub(r"^\| V1LOGIC-\d{3,} \|.*\n", "", text, flags=re.MULTILINE))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "COUNTS_CANNOT_BE_PARSED" in result.stdout
