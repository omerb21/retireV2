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
APPROVED_SLICE_1_MIGRATION_PATH = (
    "backend/alembic/versions/7c1d9e4a2b83_slice_1_actual_capitalization_metadata.py"
)
APPROVED_LOCAL_UNTRACKED_PATHS = {
    "CURRENT_PROJECT_STATE.md",
    "_evidence/",
    "specs/bootstraps/",
}
APPROVED_PACKAGE_1_PATHS = {
    "backend/app/api/fixation_routes.py",
    "backend/app/schemas/fixation_contracts.py",
    "backend/app/schemas/fixation_review.py",
    "backend/tests/test_fixation_contracts.py",
    "backend/tests/test_phase10_api_behavior.py",
    "backend/tests/test_governance_baseline.py",
}
APPROVED_PACKAGE_2_PATHS = {
    "backend/app/api/fixation_routes.py",
    "backend/app/schemas/fixation_review.py",
    "backend/tests/test_phase10_api_behavior.py",
    "backend/tests/test_governance_baseline.py",
    "frontend/src/api/fixationApi.ts",
    "frontend/src/pages/FixationInputScreen.tsx",
    "frontend/src/pages/FixationInputScreen.test.tsx",
}
APPROVED_PKG_001_PATHS = {
    "backend/alembic/versions/b7e4c2d9a105_pkg001_fixation_run_statuses.py",
    "backend/app/api/fixation_routes.py",
    "backend/app/engines/fixation_engine.py",
    "backend/app/models/fixation_run.py",
    "backend/app/schemas/fixation_admissibility.py",
    "backend/app/schemas/fixation_contracts.py",
    "backend/app/schemas/fixation_review.py",
    "backend/app/services/fixation_admission_service.py",
    "backend/app/services/fixation_service.py",
    "backend/tests/test_fixation_contracts.py",
    "backend/tests/test_fixation_engine.py",
    "backend/tests/test_fixation_engine_golden.py",
    "backend/tests/test_governance_baseline.py",
    "backend/tests/test_phase10_api_behavior.py",
    "backend/tests/test_phase7_persistence.py",
    "backend/tests/test_phase8_service.py",
    "backend/tests/test_phase9_api.py",
    "backend/tests/test_pkg001_admissible_foundation.py",
    "frontend/src/api/fixationApi.ts",
    "frontend/src/pages/CalculationResultScreen.tsx",
    "frontend/src/pages/CalculationResultScreen.test.tsx",
    "frontend/src/pages/RunDetailScreen.tsx",
}


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


def _allowed_untracked_paths() -> set[str]:
    return {
        *APPROVED_LOCAL_UNTRACKED_PATHS,
        APPROVED_SLICE_1_MIGRATION_PATH,
        "backend/app/schemas/fixation_review.py",
        "backend/app/schemas/fixation_admissibility.py",
        "backend/app/services/fixation_admission_service.py",
        "backend/tests/test_pkg001_admissible_foundation.py",
        "backend/alembic/versions/b7e4c2d9a105_pkg001_fixation_run_statuses.py",
    }


def _unapproved_untracked(status_lines: list[str]) -> list[str]:
    allowed_untracked = _allowed_untracked_paths()
    return [
        line
        for line in status_lines
        if line.startswith("?? ") and _status_path(line) not in allowed_untracked
    ]


def _approved_tracked_change_paths() -> set[str]:
    return {
        APPROVED_SLICE_1_MIGRATION_PATH,
        *APPROVED_PACKAGE_1_PATHS,
        *APPROVED_PACKAGE_2_PATHS,
        *APPROVED_PKG_001_PATHS,
        "backend/app/api/clients_routes.py",
        "backend/app/models/actual_capitalization.py",
        "backend/app/models/client.py",
        "backend/app/models/client_profile.py",
        "backend/app/models/grant.py",
        "backend/tests/test_phase9_api.py",
        "frontend/src/api/clientsApi.ts",
        "frontend/src/pages/ActualCapitalizationsScreen.test.tsx",
        "frontend/src/pages/ActualCapitalizationsScreen.tsx",
        "frontend/src/pages/ClientDetailScreen.test.tsx",
        "frontend/src/pages/ClientDetailScreen.tsx",
        "frontend/src/pages/GrantsScreen.test.tsx",
        "frontend/src/pages/GrantsScreen.tsx",
    }


def _tracked_status_lines(status_lines: list[str]) -> list[str]:
    return [line for line in status_lines if not line.startswith("?? ")]


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
    untracked = _unapproved_untracked(status_lines)
    assert not untracked, f"untracked files detected: {untracked}"


def test_governance_allows_only_approved_local_untracked_paths() -> None:
    status_lines = [
        "?? CURRENT_PROJECT_STATE.md",
        "?? _evidence/",
        "?? specs/bootstraps/",
    ]
    assert _unapproved_untracked(status_lines) == []
    assert _unapproved_untracked([*status_lines, "?? scratch.txt"]) == ["?? scratch.txt"]


def test_slice_1_governance_allows_only_exact_approved_migration_path() -> None:
    approved = f"?? {APPROVED_SLICE_1_MIGRATION_PATH}"
    rejected = "?? backend/alembic/versions/7c1d9e4a2b84_other_migration.py"
    assert _unapproved_untracked([approved]) == []
    assert _unapproved_untracked([rejected]) == [rejected]


def test_package_1_governance_allows_only_exact_review_schema_module() -> None:
    approved = "?? backend/app/schemas/fixation_review.py"
    rejected = "?? backend/app/schemas/other_review.py"
    assert _unapproved_untracked([approved]) == []
    assert _unapproved_untracked([rejected]) == [rejected]


def test_package_1_governance_rejects_unapproved_api_and_test_changes() -> None:
    approved_api = " M backend/app/api/fixation_routes.py"
    rejected_api = " M backend/app/api/clients_routes_extra.py"
    approved_test = " M backend/tests/test_fixation_contracts.py"
    rejected_test = " M backend/tests/test_other_package.py"

    assert [
        line
        for line in _tracked_status_lines([approved_api, approved_test])
        if _status_path(line) not in _approved_tracked_change_paths()
    ] == []
    assert [
        line
        for line in _tracked_status_lines([rejected_api, rejected_test])
        if _status_path(line) not in _approved_tracked_change_paths()
    ] == [rejected_api, rejected_test]


def test_package_2_governance_rejects_unapproved_frontend_changes() -> None:
    approved_api = " M frontend/src/api/fixationApi.ts"
    approved_screen = " M frontend/src/pages/FixationInputScreen.tsx"
    approved_test = " M frontend/src/pages/FixationInputScreen.test.tsx"
    rejected_api = " M frontend/src/api/otherApi.ts"
    pkg_001_screen = " M frontend/src/pages/CalculationResultScreen.tsx"
    rejected_test = " M frontend/src/pages/OtherScreen.test.tsx"

    assert [
        line
        for line in _tracked_status_lines([approved_api, approved_screen, approved_test, pkg_001_screen])
        if _status_path(line) not in _approved_tracked_change_paths()
    ] == []
    assert [
        line
        for line in _tracked_status_lines([rejected_api, rejected_test])
        if _status_path(line) not in _approved_tracked_change_paths()
    ] == [rejected_api, rejected_test]


def test_repository_has_no_staged_files_for_governance_gate() -> None:
    status_lines = _run_git_status_porcelain()
    staged = [
        line
        for line in _tracked_status_lines(status_lines)
        if line[0] != " "
    ]
    assert not staged, f"staged files detected: {staged}"


def test_repository_has_no_tracked_deletions_for_governance_gate() -> None:
    status_lines = _run_git_status_porcelain()
    deleted = [
        line
        for line in _tracked_status_lines(status_lines)
        if line[:2] in {" D", "D ", "DD"}
    ]
    assert not deleted, f"tracked deletions detected: {deleted}"


def test_repository_has_only_approved_tracked_changes_for_governance_gate() -> None:
    status_lines = _run_git_status_porcelain()
    approved_paths = _approved_tracked_change_paths()
    unapproved = [
        line
        for line in _tracked_status_lines(status_lines)
        if _status_path(line) not in approved_paths
    ]
    assert not unapproved, f"unapproved tracked changes detected: {unapproved}"


def test_forbidden_paths_not_modified() -> None:
    status_lines = _run_git_status_porcelain()
    modified_paths = [_status_path(line) for line in status_lines if not line.startswith("?? ")]
    authorized_contract_alignment_paths = _approved_tracked_change_paths()

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
