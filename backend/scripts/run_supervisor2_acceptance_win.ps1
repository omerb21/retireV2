# RETIRE V2 supervisor 2: both offline gates, no deployment or Neon writes.
# Run from backend after git pull --ff-only:
# powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_supervisor2_acceptance_win.ps1
$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent $PSScriptRoot
$expected = "feature/neon-stage6-db-reconnect-20261105"
$branch = (& git -C $backend branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $branch -ne $expected) {
    Write-Host "SUPERVISOR2_STOP_WRONG_BRANCH: $branch"
    exit 2
}
$steps = @(
    "run_supervisor1_offline_acceptance_win.ps1",
    "run_stage6_pg_integration_win.ps1"
)
foreach ($step in $steps) {
    $script = Join-Path $PSScriptRoot $step
    if (-not (Test-Path $script)) {
        Write-Host "SUPERVISOR2_STOP_MISSING_SCRIPT: $script"
        exit 2
    }
    Write-Host "SUPERVISOR2_STEP_START: $step"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $script
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        Write-Host "SUPERVISOR2_STEP_FAIL: $step (exit $code)"
        exit $code
    }
    Write-Host "SUPERVISOR2_STEP_PASS: $step"
}
Write-Host "SUPERVISOR2_ACCEPTANCE_PASS"
exit 0
