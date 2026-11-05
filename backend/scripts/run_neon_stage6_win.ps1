# Run isolated Neon Stage 6 validation with a Python version compatible
# with the pinned application dependencies. Run from any directory:
# powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_neon_stage6_win.ps1

$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent $PSScriptRoot
Push-Location $backend
try {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        Write-Host "STOP: Windows Python launcher is missing."
        exit 2
    }

    $selected = $null
    foreach ($candidate in @("3.11", "3.12")) {
        & py "-$candidate" -c "import sys; print(sys.version.split()[0])" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $selected = $candidate
            break
        }
    }
    if (-not $selected) {
        Write-Host "STOP: Python 3.11 or 3.12 is required for SQLAlchemy 2.0.36."
        Write-Host "Install Python 3.11 from python.org, reopen PowerShell and run this script again."
        exit 2
    }

    Write-Host "Using Python $selected for the isolated Neon migration."
    $venvName = ".venv-py" + $selected.Replace(".", "")
    $venvPath = Join-Path $backend $venvName
    $python = Join-Path $venvPath "Scripts\python.exe"

    if (-not (Test-Path $python)) {
        & py "-$selected" -m venv $venvPath
        if ($LASTEXITCODE -ne 0) {
            Write-Host "STOP: Could not create the isolated Python environment."
            exit 2
        }
    }

    & $python -m pip install --disable-pip-version-check -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "STOP: Installing the pinned dependencies failed."
        exit 2
    }

    & $python -m pytest -q tests/test_db_connection_pool_recovery.py tests/test_neon_stage6_bootstrap.py tests/test_neon_migration_diagnostics.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "STOP: Unit tests failed; migrations were not attempted."
        exit 2
    }

    & $python scripts/safe_neon_stage6_runner.py --apply
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
