from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_v1_golden_master_expected_outputs.py"
FILES = (
    Path("specs/runtime/V1_GOLDEN_MASTER_EXPECTED_OUTPUT_CASES.md"),
    Path("specs/runtime/V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP.md"),
    Path("specs/runtime/V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP.md"),
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


def mutate(repo: Path, transform) -> None:
    path = repo / FILES[0]
    path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")


def replace_row(text: str, predicate, change) -> str:
    for line in text.splitlines():
        if line.startswith("| V1GOLDEN-"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == 21 and predicate(cells):
                change(cells)
                return text.replace(line, "| " + " | ".join(cells) + " |", 1)
    raise AssertionError("Golden row not found")


def test_current_repository_passes() -> None:
    result = run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("status", "failure"),
    [
        ("GOLDEN_CASE_MISSING_FAIL", "GOLDEN_CASE_MISSING_FAIL_PRESENT"),
        ("GOLDEN_CASE_MANUAL_DOMAIN_DECISION_REQUIRED", "MANUAL_DOMAIN_DECISION_PRESENT"),
    ],
)
def test_blocking_status_fails(repo_copy: Path, status: str, failure: str) -> None:
    mutate(repo_copy, lambda text: replace_row(text, lambda cells: cells[17] == "GOLDEN_CASE_READY", lambda cells: cells.__setitem__(17, status)))
    result = run(repo_copy)
    assert result.returncode != 0
    assert failure in result.stdout


@pytest.mark.parametrize(
    ("pattern", "replacement", "failure"),
    [
        (r"\bREQ-\d{3}\b", "REQ-999", "UNKNOWN_REQ_REFERENCE"),
        (r"\bV1BEHAVIOR-\d{3}\b", "V1BEHAVIOR-999", "UNKNOWN_BEHAVIOR_REFERENCE"),
        (r"\bV1ITEM-\d{3}\b", "V1ITEM-999", "UNKNOWN_V1ITEM_REFERENCE"),
    ],
)
def test_unknown_reference_fails(repo_copy: Path, pattern: str, replacement: str, failure: str) -> None:
    mutate(repo_copy, lambda text: re.sub(pattern, replacement, text, count=1))
    result = run(repo_copy)
    assert result.returncode != 0
    assert failure in result.stdout


@pytest.mark.parametrize("field_index", [8, 9, 15])
def test_ready_required_field_empty_fails(repo_copy: Path, field_index: int) -> None:
    mutate(repo_copy, lambda text: replace_row(text, lambda cells: cells[17] == "GOLDEN_CASE_READY", lambda cells: cells.__setitem__(field_index, "")))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "READY_CASE_FIELD_MISSING" in result.stdout


def test_required_behavior_without_coverage_fails(repo_copy: Path) -> None:
    def remove_first(text: str) -> str:
        return re.sub(r"^\| V1GOLDEN-001 \|.*\n", "", text, count=1, flags=re.MULTILINE)
    mutate(repo_copy, remove_first)
    result = run(repo_copy)
    assert result.returncode != 0
    assert "REQUIRED_BEHAVIOR_GOLDEN_CASE_MISSING" in result.stdout


def test_missing_domain_fails(repo_copy: Path) -> None:
    mutate(repo_copy, lambda text: re.sub(r"^\| Fixation rights / 161D \|.*\n", "", text, count=1, flags=re.MULTILINE))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "HIGH_RISK_DOMAIN_MISSING" in result.stdout


def test_fail_marker_fails(repo_copy: Path) -> None:
    mutate(repo_copy, lambda text: text.replace("V1_GOLDEN_MASTER_EXPECTED_OUTPUT_CASES_PASS", "V1_GOLDEN_MASTER_EXPECTED_OUTPUT_CASES_FAIL"))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "INVALID_FINAL_MARKER" in result.stdout


def test_duplicate_id_fails(repo_copy: Path) -> None:
    mutate(repo_copy, lambda text: text.replace("| V1GOLDEN-002 |", "| V1GOLDEN-001 |", 1))
    result = run(repo_copy)
    assert result.returncode != 0
    assert "DUPLICATE_GOLDEN_CASE_ID" in result.stdout
