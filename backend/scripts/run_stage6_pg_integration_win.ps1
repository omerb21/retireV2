# RETIRE V2 Stage 6 - isolated PostgreSQL 16 integration runner.
# Requires Docker Desktop with a running Linux engine and the existing Python 3.11 venv.
# Run from backend:
# powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_stage6_pg_integration_win.ps1
#
# A disposable container binds only 127.0.0.1, and is removed after the tests.
# No production, Neon or Render credentials are used.
$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent $PSScriptRoot
$containerName = "retire-v2-stage6-test-" + [Guid]::NewGuid().ToString("N").Substring(0, 12)
$started = $false
$exitCode = 2
$savedDatabaseUrl = [Environment]::GetEnvironmentVariable("DATABASE_URL", "Process")
$savedTestUrl = [Environment]::GetEnvironmentVariable("SCENARIO_TEST_POSTGRES_URL", "Process")
$savedAppEnv = [Environment]::GetEnvironmentVariable("APP_ENV", "Process")
$savedPreview = [Environment]::GetEnvironmentVariable("STAGE6_PREVIEW_ENABLED", "Process")

function Restore-ProcessEnv([string]$name, [AllowNull()][string]$value) {
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
}

Push-Location $backend
try {
    $python = Join-Path $backend ".venv-py311\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $python = Join-Path $backend ".venv-py312\Scripts\python.exe"
    }
    if (-not (Test-Path $python)) {
        throw "Python 3.11/3.12 environment missing; first run run_neon_stage6_win.ps1"
    }
    & $python -c "import sys; assert sys.version_info[:2] in ((3,11),(3,12))"
    if ($LASTEXITCODE -ne 0) { throw "Incompatible Python interpreter" }

    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker Desktop is not installed. This test requires Docker Desktop."
    }
    try {
        & docker info --format "{{.ServerVersion}}" 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Docker engine not running" }
    }
    catch {
        throw "Docker Desktop Linux engine is not running. Start it and retry."
    }

    $listener = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Loopback, 0
    )
    try {
        $listener.Start()
        $port = $listener.LocalEndpoint.Port
    }
    finally {
        $listener.Stop()
    }

    $bytes = New-Object byte[] 24
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    }
    finally {
        $rng.Dispose()
    }
    $secret = [BitConverter]::ToString($bytes).Replace("-", "").ToLowerInvariant()
    $binding = "127.0.0.1:{0}:5432" -f $port

    Write-Host "STAGE6_PG16_LOCAL_CONTAINER_START"
    $dockerArgs = @(
        "run", "--detach", "--rm", "--name", $containerName,
        "-p", $binding,
        "-e", ("POSTGRES_PASSWORD=" + $secret),
        "-e", "POSTGRES_DB=retire_v2_scenario_test",
        "postgres:16-alpine"
    )
    & docker @dockerArgs | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Could not start disposable PostgreSQL container" }
    $started = $true

    $ready = $false
    for ($i = 0; $i -lt 45; $i++) {
        & docker exec $containerName pg_isready -U postgres -d retire_v2_scenario_test 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw "PostgreSQL container did not become ready" }

    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    $env:SCENARIO_TEST_POSTGRES_URL = "postgresql+psycopg2://postgres:${secret}@127.0.0.1:${port}/retire_v2_scenario_test"
    $env:APP_ENV = "test"
    $env:STAGE6_PREVIEW_ENABLED = "0"

    $suite = @(
        "tests/test_stage6_p1b_postgresql.py",
        "tests/test_stage6_p1c_postgresql.py",
        "tests/test_stage6_p1d_postgresql.py",
        "tests/test_scenario_pension_election_store_real_postgresql.py",
        "tests/test_scenario_professional_review_store_real_postgresql.py",
        "tests/test_scenario_coefficient_input_inventory_real_postgresql.py",
        "tests/test_scenario_snapshot_candidate_postgresql.py",
        "tests/test_scenario_admission_postgresql_isolation.py",
        "tests/test_scenario_admission_postgresql_tables.py"
    )

    Write-Host "STAGE6_PG16_LOCAL_READY"
    Write-Host "STAGE6_PG_INTEGRATION_START (localhost only)"
    & $python -m pytest -q -ra @suite
    $exitCode = $LASTEXITCODE
}
catch {
    Write-Host ("STAGE6_PG_INTEGRATION_STOP: " + $_.Exception.Message)
    if ($exitCode -eq 0) { $exitCode = 2 }
}
finally {
    if ($started) {
        & docker rm --force $containerName 2>$null | Out-Null
        Write-Host "STAGE6_PG16_LOCAL_CONTAINER_REMOVED"
    }
    Restore-ProcessEnv "DATABASE_URL" $savedDatabaseUrl
    Restore-ProcessEnv "SCENARIO_TEST_POSTGRES_URL" $savedTestUrl
    Restore-ProcessEnv "APP_ENV" $savedAppEnv
    Restore-ProcessEnv "STAGE6_PREVIEW_ENABLED" $savedPreview
    Pop-Location
}
Write-Host "STAGE6_PG_INTEGRATION_EXIT_CODE=$exitCode"
exit $exitCode
