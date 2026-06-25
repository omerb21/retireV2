"""
This file implements minimal governance participation only.
It does not prove architecture correctness or governance completeness.

What this gate explicitly does NOT enforce
- formula correctness
- Golden output correctness
- API response strategy correctness
- DB/persistence correctness
- service business behavior correctness
- architecture compliance proof
- AST/import graph analysis
- drift resolution
- deferred architecture decisions
- Supervisor review replacement
- targeted test replacement
"""

from __future__ import annotations

from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_git_status_porcelain() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _status_path(line: str) -> str:
    path_part = line[3:]
    if " -> " in path_part:
        return path_part.split(" -> ", 1)[1]
    return path_part


def test_governance_artifacts_exist() -> None:
    required_files = [
        REPO_ROOT / "specs/phase5a/service_assembly_policy.md",
        REPO_ROOT / "specs/governance/drift_register.md",
        REPO_ROOT / "specs/governance/enforcement_categories.md",
        REPO_ROOT / "specs/governance/executable_governance_gate_plan.md",
        REPO_ROOT / "specs/governance/phase_closure_checklist.md",
    ]

    missing = [str(path.relative_to(REPO_ROOT)) for path in required_files if not path.exists()]
    assert not missing, f"missing required governance artifacts: {missing}"


def test_required_drift_ids_exist() -> None:
    drift_register_path = REPO_ROOT / "specs/governance/drift_register.md"
    content = drift_register_path.read_text(encoding="utf-8")

    required_ids = [
        "DRIFT-001",
        "DRIFT-002",
        "DRIFT-003",
        "DRIFT-004",
        "DRIFT-005",
        "DRIFT-006",
        "DRIFT-007",
    ]

    missing_ids = [drift_id for drift_id in required_ids if drift_id not in content]
    assert not missing_ids, f"missing required drift identifiers: {missing_ids}"


def test_repository_has_no_untracked_files_for_governance_gate() -> None:
    status_lines = _run_git_status_porcelain()
    allowed_bootstrap_untracked = {
        "backend/alembic/versions/3d2f8a7b4c19_phase_a_file_foundation.py",
        "backend/tests/test_governance_baseline.py",
    }
    untracked = [
        line
        for line in status_lines
        if line.startswith("?? ") and _status_path(line) not in allowed_bootstrap_untracked
    ]
    assert not untracked, f"untracked files detected: {untracked}"


def test_forbidden_paths_not_modified() -> None:
    status_lines = _run_git_status_porcelain()
    modified_paths = [_status_path(line) for line in status_lines if not line.startswith("?? ")]
    authorized_contract_alignment_paths = {
        "backend/alembic/versions/9a6f3b8c21de_stage_c_cutover_integer_ids.py",
        "backend/alembic/versions/eb25e18b9fcd_align_phase_1_ids_for_api.py",
        "backend/app/api/clients_routes.py",
        "backend/app/api/fixation_routes.py",
        "backend/app/models/client.py",
        "backend/app/models/client_profile.py",
        "backend/app/schemas/fixation_contracts.py",
        "backend/tests/test_governance_baseline.py",
        "frontend/src/App.test.tsx",
        "frontend/src/api/clientsApi.ts",
        "frontend/src/pages/ActualCapitalizationsScreen.test.tsx",
        "frontend/src/pages/ActualCapitalizationsScreen.tsx",
        "frontend/src/pages/ClientDetailScreen.test.tsx",
        "frontend/src/pages/ClientDetailScreen.tsx",
        "frontend/src/pages/ClientListScreen.test.tsx",
        "frontend/src/pages/ClientListScreen.tsx",
        "frontend/src/pages/CreateClientScreen.test.tsx",
        "frontend/src/pages/CreateClientScreen.tsx",
        "frontend/src/pages/EmploymentHistoryScreen.test.tsx",
        "frontend/src/pages/EmploymentHistoryScreen.tsx",
        "frontend/src/pages/GrantsScreen.test.tsx",
        "frontend/src/pages/GrantsScreen.tsx",
    }

    forbidden_prefixes = (
        "backend/app/engines/",
        "backend/app/schemas/",
        "backend/app/api/",
        "backend/app/models/",
        "frontend/",
        "backend/alembic/",
        "specs/phase4/",
    )
    forbidden_exact_paths = {
        "specs/phase4/formula_lock.md",
        "specs/phase4/corrected_golden_calculation_lock.md",
        "specs/phase4/final_golden_validation_payload_set.md",
    }

    forbidden_modified = [
        path
        for path in modified_paths
        if path not in authorized_contract_alignment_paths
        and (path in forbidden_exact_paths or path.startswith(forbidden_prefixes))
    ]
    assert not forbidden_modified, f"forbidden paths modified: {forbidden_modified}"


def test_phase_closure_checklist_exists() -> None:
    checklist_path = REPO_ROOT / "specs/governance/phase_closure_checklist.md"
    assert checklist_path.exists(), "missing required phase closure checklist"
