# Stage 6 functional/unit regression suite. No remote database or deployment.
# Run from backend: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_stage6_unit_acceptance_win.ps1

$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent $PSScriptRoot
Push-Location $backend
try {
    $python = Join-Path $backend ".venv-py311\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $python = Join-Path $backend ".venv-py312\Scripts\python.exe"
    }
    if (-not (Test-Path $python)) {
        Write-Host "STOP: compatible Python environment missing. Run run_neon_stage6_win.ps1 first."
        exit 2
    }
    # Never allow a local unit suite to write to Render or Neon by accident.
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:SCENARIO_TEST_POSTGRES_URL -ErrorAction SilentlyContinue
    $env:APP_ENV = "test"
    $env:STAGE6_PREVIEW_ENABLED = "0"

    $suite = @(
        "tests/test_db_connection_pool_recovery.py",
        "tests/test_neon_stage6_bootstrap.py",
        "tests/test_neon_migration_diagnostics.py",
        "tests/test_stage6_internal_api.py",
        "tests/test_stage6_internal_election_api.py",
        "tests/test_stage6_factor_admission_api.py",
        "tests/test_stage6_factor_revision_api.py",
        "tests/test_stage6_monthly_cashflow.py",
        "tests/test_stage6_monthly_comparison.py",
        "tests/test_stage6_p1a_permission_admission.py",
        "tests/test_stage6_p1b_admission_model.py",
        "tests/test_stage6_p1b_admission_read_service.py",
        "tests/test_stage6_p1b_admission_write_service.py",
        "tests/test_stage6_p1b_factor_contract.py",
        "tests/test_stage6_p1b_migration.py",
        "tests/test_stage6_p1c_canonical_identity.py",
        "tests/test_stage6_p1c_snapshot_contract.py",
        "tests/test_stage6_p1d_estimate.py",
        "tests/test_stage6_p1d_pte_kind.py",
        "tests/test_render_runtime.py"
    )

    & $python -c "import sys; assert sys.version_info[:2] in ((3,11),(3,12)), 'Python 3.11/3.12 required'; print('PYTHON', sys.version.split()[0])"
    if ($LASTEXITCODE -ne 0) { exit 2 }
    Write-Host "STAGE6_UNIT_ACCEPTANCE_START - remote databases disabled"
    & $python -m pytest -q -ra @suite
    $code = $LASTEXITCODE
    Write-Host "STAGE6_UNIT_ACCEPTANCE_EXIT_CODE=$code"
    exit $code
}
finally {
    Pop-Location
}
