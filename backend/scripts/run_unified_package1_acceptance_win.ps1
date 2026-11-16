# RETIRE V2 supervisor 14: one fail-fast local Package 1 acceptance command.
# Run from the repository root:
# powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_unified_package1_acceptance_win.ps1 -ExpectedHead "<COMMIT_SHA>"
# Never points to Neon, Staging or Production; integration uses disposable PG16.
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f]{40}$')]
    [string]$ExpectedHead
)
$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent $PSScriptRoot
$repo = Split-Path -Parent $backend
$python = Join-Path $backend ".venv-py311\Scripts\python.exe"
$originalDatabaseUrl = [Environment]::GetEnvironmentVariable("DATABASE_URL", "Process")
$originalTestUrl = [Environment]::GetEnvironmentVariable("SCENARIO_TEST_POSTGRES_URL", "Process")
$originalAppEnv = [Environment]::GetEnvironmentVariable("APP_ENV", "Process")
$exitCode = 1
try {
    $actualHead = (& git -C $repo rev-parse HEAD)
    if ($LASTEXITCODE -ne 0 -or $actualHead.Trim() -ne $ExpectedHead) {
        throw "HEAD_MISMATCH: expected $ExpectedHead, actual $actualHead"
    }
    Write-Host "PACKAGE1_HEAD_MATCH=$actualHead"
    if (-not (Test-Path $python)) {
        throw "PYTHON311_NOT_FOUND: expected $python"
    }
    & $python -c "import sys; assert sys.version_info[:2] == (3, 11), sys.version"
    if ($LASTEXITCODE -ne 0) { throw "PYTHON311_VERSION_MISMATCH" }

    # Remove accidental production DB credentials from the unit-test process.
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:SCENARIO_TEST_POSTGRES_URL -ErrorAction SilentlyContinue
    $env:APP_ENV = "test"

    Push-Location $backend
    try {
        Write-Host "PACKAGE1_UNIT_START"
        & $python -m pytest -q -ra tests/test_scenario_unified_result.py
        if ($LASTEXITCODE -ne 0) { throw "PACKAGE1_UNIT_FAIL exit=$LASTEXITCODE" }
        Write-Host "PACKAGE1_UNIT_PASS"

        Write-Host "PACKAGE1_COMPATIBILITY_START"
        & $python -m pytest -q -ra @(
            "tests/test_scenario_input_manifest.py",
            "tests/test_scenario_snapshot_candidate.py",
            "tests/test_scenario_draft.py",
            "tests/test_scenario_pension_election_store.py"
        )
        if ($LASTEXITCODE -ne 0) { throw "PACKAGE1_COMPATIBILITY_FAIL exit=$LASTEXITCODE" }
        Write-Host "PACKAGE1_COMPATIBILITY_PASS"

        Write-Host "PACKAGE1_REAL_PG16_START"
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (
            Join-Path $PSScriptRoot "run_stage6_pg_integration_win.ps1"
        )
        if ($LASTEXITCODE -ne 0) { throw "PACKAGE1_REAL_PG16_FAIL exit=$LASTEXITCODE" }
        Write-Host "PACKAGE1_REAL_PG16_PASS"
    }
    finally {
        Pop-Location
    }
    $headAfter = (& git -C $repo rev-parse HEAD)
    if ($LASTEXITCODE -ne 0 -or $headAfter.Trim() -ne $ExpectedHead) {
        throw "HEAD_CHANGED_DURING_TEST: actual $headAfter"
    }
    Write-Host "PACKAGE1_ACCEPTANCE_PASS HEAD=$headAfter"
    $exitCode = 0
}
catch {
    Write-Host "PACKAGE1_ACCEPTANCE_FAIL: $($_.Exception.Message)"
    $exitCode = 1
}
finally {
    [Environment]::SetEnvironmentVariable("DATABASE_URL", $originalDatabaseUrl, "Process")
    [Environment]::SetEnvironmentVariable("SCENARIO_TEST_POSTGRES_URL", $originalTestUrl, "Process")
    [Environment]::SetEnvironmentVariable("APP_ENV", $originalAppEnv, "Process")
}
exit $exitCode
