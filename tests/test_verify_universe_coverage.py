from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER = REPO_ROOT / "scripts" / "verify_universe_coverage.py"
CONTROL_FILES = (
    Path("specs/runtime/V2_REQUIRED_CAPABILITY_UNIVERSE.md"),
    Path("specs/runtime/V1_TO_V2_MECHANICAL_PARITY_LEDGER.md"),
    Path("specs/runtime/V2_FULL_GAP_REGISTER_FROM_PARITY_LEDGER.md"),
    Path("specs/runtime/V2_MASTER_BUILD_SEQUENCE_FULL_SYSTEM.md"),
    Path("specs/runtime/V2_UNIVERSE_COVERAGE_PROOF.md"),
)


def run_verifier(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFIER), "--root", str(root)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@pytest.fixture
def control_copy(tmp_path: Path) -> Path:
    for relative in CONTROL_FILES:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / relative, destination)
    return tmp_path


def mutate(root: Path, relative: Path, old: str, new: str, count: int = 1) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, count), encoding="utf-8")


def assert_fails(root: Path, failure_code: str) -> None:
    result = run_verifier(root)
    assert result.returncode != 0
    assert "MACHINE_UNIVERSE_COVERAGE_VERIFICATION_FAIL" in result.stdout
    assert f"failure_code={failure_code}" in result.stdout


def mutate_first_requirement_status(root: Path, old: str, new: str) -> None:
    universe = CONTROL_FILES[0]
    text = (root / universe).read_text(encoding="utf-8")
    row = next(
        line
        for line in text.splitlines()
        if line.startswith("| REQ-") and f"| {old} |" in line
    )
    mutated = row.replace(f"| {old} |", f"| {new} |", 1)
    mutate(root, universe, row, mutated)


def test_current_repository_passes() -> None:
    result = run_verifier(REPO_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "MACHINE_UNIVERSE_COVERAGE_VERIFICATION_PASS" in result.stdout
    assert "requirements_checked=137" in result.stdout
    assert "failed_requirements=0" in result.stdout


def test_fails_when_req_unmapped_is_introduced(control_copy: Path) -> None:
    mutate_first_requirement_status(control_copy, "REQ_MAPPED_GAP", "REQ_UNMAPPED")
    assert_fails(control_copy, "REQ_STATUS_COUNT_REQ_UNMAPPED")


def test_fails_when_gap_096_is_removed(control_copy: Path) -> None:
    mutate(control_copy, CONTROL_FILES[2], "GAP-096", "GAP-996")
    assert_fails(control_copy, "GAP_096_MISSING")


def test_fails_when_l_009_is_removed(control_copy: Path) -> None:
    mutate(control_copy, CONTROL_FILES[1], "L-009", "L-099")
    assert_fails(control_copy, "LEDGER_L009_MISSING")


def test_fails_when_req_116_loses_gap_096(control_copy: Path) -> None:
    universe = CONTROL_FILES[0]
    text = (control_copy / universe).read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| REQ-116 |"))
    mutated = row.replace("| GAP-096 |", "| None |")
    assert mutated != row
    mutate(control_copy, universe, row, mutated)
    assert_fails(control_copy, "REQ_MAPPED_GAP_MISSING")


def test_fails_when_proof_claims_02m_is_unfrozen(control_copy: Path) -> None:
    proof = CONTROL_FILES[4]
    mutate(
        control_copy,
        proof,
        "UNIVERSE_COVERAGE_PROOF_PASS",
        "02M is unfrozen.\n\nUNIVERSE_COVERAGE_PROOF_PASS",
    )
    assert_fails(control_copy, "PROOF_FALSE_UNFROZEN")


def test_fails_when_requirement_id_is_duplicated(control_copy: Path) -> None:
    mutate(control_copy, CONTROL_FILES[0], "| REQ-002 |", "| REQ-001 |")
    assert_fails(control_copy, "REQ_DUPLICATE")


def test_fails_when_status_counts_do_not_reconcile(control_copy: Path) -> None:
    mutate_first_requirement_status(control_copy, "REQ_MAPPED_GAP", "REQ_MAPPED_UNKNOWN")
    assert_fails(control_copy, "REQ_STATUS_COUNT_REQ_MAPPED_GAP")
