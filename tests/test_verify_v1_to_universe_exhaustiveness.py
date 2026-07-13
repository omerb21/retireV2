from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/verify_v1_to_universe_exhaustiveness.py"
V1_EVIDENCE_ROOT = Path(
    r"C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\Retire V2"
    r"\V1_Source_Verified_Capability_Map_Evidence_2026-07-08"
)
MAP_RELATIVE = Path("specs/runtime/V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP.md")
UNIVERSE_RELATIVE = Path("specs/runtime/V2_REQUIRED_CAPABILITY_UNIVERSE.md")
EVIDENCE_FILES = (
    "routes_output_clean.txt",
    "pytest_collect_output.txt",
    "V1_FULL_SOURCE_VERIFIED_CAPABILITY_MAP.md",
    "V1_RUNTIME_EVIDENCE_ADDENDUM.md",
)


@pytest.fixture()
def verification_copy(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    evidence = tmp_path / "v1_evidence"
    (repo / MAP_RELATIVE.parent).mkdir(parents=True)
    shutil.copy2(REPO_ROOT / MAP_RELATIVE, repo / MAP_RELATIVE)
    shutil.copy2(REPO_ROOT / UNIVERSE_RELATIVE, repo / UNIVERSE_RELATIVE)
    evidence.mkdir()
    for name in EVIDENCE_FILES:
        shutil.copy2(V1_EVIDENCE_ROOT / name, evidence / name)
    return repo, evidence


def run_verifier(repo: Path, evidence: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(repo),
            "--v1-evidence-root",
            str(evidence),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def mutate_map(repo: Path, transform) -> None:
    path = repo / MAP_RELATIVE
    path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")


def first_inventory_line(text: str, status: str) -> tuple[str, list[str]]:
    for line in text.splitlines():
        if line.startswith("| V1ITEM-") and f"| {status} |" in line:
            return line, [cell.strip() for cell in line.strip("|").split("|")]
    raise AssertionError(f"No inventory row found for {status}")


def test_current_repository_map_passes() -> None:
    result = run_verifier(REPO_ROOT, V1_EVIDENCE_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "V1_TO_UNIVERSE_EXHAUSTIVENESS_VERIFICATION_PASS" in result.stdout


def test_unmapped_item_fails(verification_copy: tuple[Path, Path]) -> None:
    repo, evidence = verification_copy

    def transform(text: str) -> str:
        line, cells = first_inventory_line(text, "V1_MAPPED_TO_REQ")
        cells[7] = "V1_UNMAPPED_FAIL"
        return text.replace(line, "| " + " | ".join(cells) + " |", 1)

    mutate_map(repo, transform)
    result = run_verifier(repo, evidence)
    assert result.returncode != 0
    assert "V1_UNMAPPED_FAIL_PRESENT" in result.stdout


def test_unknown_req_fails(verification_copy: tuple[Path, Path]) -> None:
    repo, evidence = verification_copy
    mutate_map(repo, lambda text: re.sub(r"\bREQ-\d{3}\b", "REQ-999", text, count=1))
    result = run_verifier(repo, evidence)
    assert result.returncode != 0
    assert "UNKNOWN_REQ_REFERENCE" in result.stdout


def test_empty_exclusion_reason_fails(verification_copy: tuple[Path, Path]) -> None:
    repo, evidence = verification_copy

    def transform(text: str) -> str:
        line, cells = first_inventory_line(text, "V1_NOT_APPLICABLE_WITH_REASON")
        cells[8] = ""
        return text.replace(line, "| " + " | ".join(cells) + " |", 1)

    mutate_map(repo, transform)
    result = run_verifier(repo, evidence)
    assert result.returncode != 0
    assert "MISSING_CLASSIFICATION_REASON" in result.stdout


def test_replaced_item_without_req_fails(verification_copy: tuple[Path, Path]) -> None:
    repo, evidence = verification_copy

    def transform(text: str) -> str:
        line, cells = first_inventory_line(text, "V1_REPLACED_BY_REQ")
        cells[6] = "None"
        return text.replace(line, "| " + " | ".join(cells) + " |", 1)

    mutate_map(repo, transform)
    result = run_verifier(repo, evidence)
    assert result.returncode != 0
    assert "MISSING_REQ_TARGET" in result.stdout


def test_duplicate_item_id_fails(verification_copy: tuple[Path, Path]) -> None:
    repo, evidence = verification_copy

    def transform(text: str) -> str:
        return text.replace("| V1ITEM-002 |", "| V1ITEM-001 |", 1)

    mutate_map(repo, transform)
    result = run_verifier(repo, evidence)
    assert result.returncode != 0
    assert "DUPLICATE_V1_ITEM_ID" in result.stdout


def test_fail_marker_fails(verification_copy: tuple[Path, Path]) -> None:
    repo, evidence = verification_copy
    mutate_map(
        repo,
        lambda text: text.replace(
            "V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP_PASS",
            "V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP_FAIL",
        ),
    )
    result = run_verifier(repo, evidence)
    assert result.returncode != 0
    assert "INVALID_FINAL_MARKER" in result.stdout


def test_removed_route_fails(verification_copy: tuple[Path, Path]) -> None:
    repo, evidence = verification_copy

    def transform(text: str) -> str:
        for line in text.splitlines():
            if line.startswith("| V1ITEM-") and "| V1_ROUTE |" in line:
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                cells[4] = "REMOVED_ROUTE_REFERENCE"
                return text.replace(line, "| " + " | ".join(cells) + " |", 1)
        raise AssertionError("No V1_ROUTE row found")

    mutate_map(repo, transform)
    result = run_verifier(repo, evidence)
    assert result.returncode != 0
    assert "V1_ROUTE_NOT_EXACTLY_ONCE" in result.stdout
