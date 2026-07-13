from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/verify_v1_behavior_formula_rule_parity.py"
MAP_RELATIVE = Path("specs/runtime/V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP.md")
V1ITEM_RELATIVE = Path("specs/runtime/V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP.md")
UNIVERSE_RELATIVE = Path("specs/runtime/V2_REQUIRED_CAPABILITY_UNIVERSE.md")


@pytest.fixture()
def verification_copy(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / MAP_RELATIVE.parent).mkdir(parents=True)
    for relative in (MAP_RELATIVE, V1ITEM_RELATIVE, UNIVERSE_RELATIVE):
        shutil.copy2(REPO_ROOT / relative, repo / relative)
    return repo


def run_verifier(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo)],
        check=False,
        capture_output=True,
        text=True,
    )


def mutate_map(repo: Path, transform) -> None:
    path = repo / MAP_RELATIVE
    path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")


def first_row(text: str, predicate) -> tuple[str, list[str]]:
    for line in text.splitlines():
        if line.startswith("| V1BEHAVIOR-"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == 25 and predicate(cells):
                return line, cells
    raise AssertionError("Required behavior row not found")


def replace_row(text: str, predicate, mutate) -> str:
    line, cells = first_row(text, predicate)
    mutate(cells)
    return text.replace(line, "| " + " | ".join(cells) + " |", 1)


def test_current_repository_map_passes() -> None:
    result = run_verifier(REPO_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "V1_BEHAVIOR_FORMULA_RULE_PARITY_VERIFICATION_PASS" in result.stdout


def test_unmapped_behavior_fails(verification_copy: Path) -> None:
    mutate_map(
        verification_copy,
        lambda text: replace_row(
            text,
            lambda cells: cells[22] == "BEHAVIOR_EXACT_MATCH_REQUIRED",
            lambda cells: (cells.__setitem__(16, "BEHAVIOR_UNMAPPED_FAIL"), cells.__setitem__(22, "BEHAVIOR_UNMAPPED_FAIL")),
        ),
    )
    result = run_verifier(verification_copy)
    assert result.returncode != 0
    assert "BEHAVIOR_UNMAPPED_FAIL_PRESENT" in result.stdout


def test_unknown_req_fails(verification_copy: Path) -> None:
    mutate_map(verification_copy, lambda text: re.sub(r"\bREQ-\d{3}\b", "REQ-999", text, count=1))
    result = run_verifier(verification_copy)
    assert result.returncode != 0
    assert "UNKNOWN_REQ_REFERENCE" in result.stdout


def test_unknown_v1item_fails(verification_copy: Path) -> None:
    mutate_map(verification_copy, lambda text: re.sub(r"\bV1ITEM-\d{3}\b", "V1ITEM-999", text, count=1))
    result = run_verifier(verification_copy)
    assert result.returncode != 0
    assert "UNKNOWN_V1ITEM_REFERENCE" in result.stdout


def test_empty_required_v2_behavior_fails(verification_copy: Path) -> None:
    mutate_map(
        verification_copy,
        lambda text: replace_row(text, lambda cells: True, lambda cells: cells.__setitem__(15, "")),
    )
    result = run_verifier(verification_copy)
    assert result.returncode != 0
    assert "MISSING_REQUIRED_BEHAVIOR_FIELD" in result.stdout


@pytest.mark.parametrize("field_index", [7, 8, 9])
def test_formula_row_missing_required_field_fails(verification_copy: Path, field_index: int) -> None:
    def clear_field(cells: list[str]) -> None:
        cells[field_index] = ""
        if field_index == 9:
            cells[10] = ""

    mutate_map(
        verification_copy,
        lambda text: replace_row(
            text,
            lambda cells: cells[3] == "V1_FORMULA_BEHAVIOR",
            clear_field,
        ),
    )
    result = run_verifier(verification_copy)
    assert result.returncode != 0
    assert "FORMULA_ROW_FIELD_MISSING" in result.stdout


def test_formula_row_without_golden_test_fails(verification_copy: Path) -> None:
    mutate_map(
        verification_copy,
        lambda text: replace_row(
            text,
            lambda cells: cells[3] == "V1_FORMULA_BEHAVIOR",
            lambda cells: cells.__setitem__(18, "NO"),
        ),
    )
    result = run_verifier(verification_copy)
    assert result.returncode != 0
    assert "FORMULA_ROW_GOLDEN_TEST_REQUIRED" in result.stdout


def test_numeric_tolerance_missing_fails(verification_copy: Path) -> None:
    mutate_map(
        verification_copy,
        lambda text: replace_row(
            text,
            lambda cells: cells[22] == "BEHAVIOR_NUMERIC_TOLERANCE_ALLOWED",
            lambda cells: cells.__setitem__(17, ""),
        ),
    )
    result = run_verifier(verification_copy)
    assert result.returncode != 0
    assert "NUMERIC_TOLERANCE_MISSING" in result.stdout


def test_intentional_change_requires_reason_and_review(verification_copy: Path) -> None:
    mutate_map(
        verification_copy,
        lambda text: replace_row(
            text,
            lambda cells: cells[22] == "BEHAVIOR_INTENTIONAL_CHANGE_REQUIRED",
            lambda cells: (cells.__setitem__(23, "NO"), cells.__setitem__(24, "")),
        ),
    )
    result = run_verifier(verification_copy)
    assert result.returncode != 0
    assert "INTENTIONAL_CHANGE_REASON_MISSING" in result.stdout
    assert "INTENTIONAL_CHANGE_REVIEW_REQUIRED" in result.stdout


def test_missing_high_risk_domain_fails(verification_copy: Path) -> None:
    mutate_map(
        verification_copy,
        lambda text: re.sub(r"^\| Fixation rights / 161D \|.*\n", "", text, count=1, flags=re.MULTILINE),
    )
    result = run_verifier(verification_copy)
    assert result.returncode != 0
    assert "HIGH_RISK_DOMAIN_MISSING" in result.stdout


def test_fail_marker_fails(verification_copy: Path) -> None:
    mutate_map(
        verification_copy,
        lambda text: text.replace(
            "V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP_PASS",
            "V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP_FAIL",
        ),
    )
    result = run_verifier(verification_copy)
    assert result.returncode != 0
    assert "INVALID_FINAL_MARKER" in result.stdout


def test_duplicate_behavior_id_fails(verification_copy: Path) -> None:
    mutate_map(verification_copy, lambda text: text.replace("| V1BEHAVIOR-002 |", "| V1BEHAVIOR-001 |", 1))
    result = run_verifier(verification_copy)
    assert result.returncode != 0
    assert "DUPLICATE_BEHAVIOR_ID" in result.stdout
