# Supervisor instruction 1 - offline acceptance, never deploy or access external DBs.
# Run from backend:
# powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_supervisor1_offline_acceptance_win.ps1
$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $backend
$python = Join-Path $backend ".venv-py311\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "STOP: Python 3.11 environment missing; refusing another interpreter."
    exit 2
}
$saved = @{}
foreach ($key in @("DATABASE_URL", "SCENARIO_TEST_POSTGRES_URL", "APP_ENV", "STAGE6_PREVIEW_ENABLED")) {
    $saved[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
}
try {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:SCENARIO_TEST_POSTGRES_URL -ErrorAction SilentlyContinue
    $env:APP_ENV = "test"
    $env:STAGE6_PREVIEW_ENABLED = "0"
    Push-Location $backend
    try {
        $suite = @(
            "tests/test_scenario_draft.py",
            "tests/test_scenario_pension_election_store.py",
            "tests/test_scenario_calculation_admission.py",
            "tests/test_scenario_draft_readiness.py",
            "tests/test_stage6_internal_api.py",
            "tests/test_stage6_internal_election_api.py",
            "tests/test_stage6_factor_admission_api.py",
            "tests/test_stage6_factor_revision_api.py"
        )
        Write-Host "SUPERVISOR1_BACKEND_TESTS_START"
        & $python -m pytest -q -ra @suite
        $backendCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
    if ($backendCode -ne 0) {
        Write-Host "SUPERVISOR1_BACKEND_TESTS_FAIL=$backendCode"
        exit $backendCode
    }
    Push-Location (Join-Path $repoRoot "frontend")
    try {
        Write-Host "SUPERVISOR1_FRONTEND_TESTS_START"
        & npm test -- --reporter=dot
        $frontendCode = $LASTEXITCODE
        if ($frontendCode -eq 0) {
            & npm run build
            $frontendCode = $LASTEXITCODE
        }
    }
    finally {
        Pop-Location
    }
    if ($frontendCode -ne 0) {
        Write-Host "SUPERVISOR1_FRONTEND_TESTS_FAIL=$frontendCode"
        exit $frontendCode
    }
    Write-Host "SUPERVISOR1_OFFLINE_ACCEPTANCE_PASS"
    exit 0
}
finally {
    foreach ($key in $saved.Keys) {
        [Environment]::SetEnvironmentVariable($key, $saved[$key], "Process")
    }
}
