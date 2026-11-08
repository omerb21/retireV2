# RETIRE V2 Supervisor 41 - Windows localhost browser acceptance.
# One command from the existing worktree:
# powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_supervisor41_browser_win.ps1
# Docker Desktop Linux engine, existing backend venv, Node/npm required.
# First run downloads Playwright/Chromium; no remote app or database access.
$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent $PSScriptRoot
$root = Split-Path -Parent $backend
$frontend = Join-Path $root "frontend"
$runId = [Guid]::NewGuid().ToString("N").Substring(0, 14)
$containerName = "retire-v2-supervisor41-" + $runId
$report = Join-Path $env:TEMP ("RETIRE_V2_SUPERVISOR41\" + $runId)
New-Item -ItemType Directory -Path $report -Force | Out-Null
$containerId = $null
$backendProcess = $null
$frontendProcess = $null
$passed = $false
$saved = @{}
$variables = @("DATABASE_URL", "SCENARIO_TEST_POSTGRES_URL", "APP_ENV", "STAGE6_PREVIEW_ENABLED", "RECOVERY_POSTGRES_TEST", "VITE_API_BASE_URL", "PLAYWRIGHT_JSON_OUTPUT_FILE")
foreach ($name in $variables) { $saved[$name] = [Environment]::GetEnvironmentVariable($name, "Process") }

function Invoke-Checked([string]$program, [string[]]$arguments) {
    & $program @arguments
    if ($LASTEXITCODE -ne 0) { throw "SUPERVISOR41_COMMAND_FAILED:$program exit=$LASTEXITCODE" }
}
function Assert-FreeLocalPort([int]$port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $result = $client.BeginConnect("127.0.0.1", $port, $null, $null)
        if ($result.AsyncWaitHandle.WaitOne(350)) {
            try { $client.EndConnect($result) } catch { return }
            throw "SUPERVISOR41_PORT_IN_USE:$port"
        }
    } finally { $client.Close() }
}
function Wait-Http([string]$uri, [System.Diagnostics.Process]$process) {
    for ($i = 0; $i -lt 80; $i++) {
        $process.Refresh()
        if ($process.HasExited) { throw "SUPERVISOR41_SERVER_EXITED:$uri" }
        try {
            $response = Invoke-WebRequest -Uri $uri -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { return }
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    throw "SUPERVISOR41_SERVER_NOT_READY:$uri"
}
try {
    Push-Location $root
    try {
        $head = (& git rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0) { throw "SUPERVISOR41_NOT_GIT_WORKTREE" }
    } finally { Pop-Location }
    foreach ($port in @(8001, 5173)) { Assert-FreeLocalPort $port }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker Desktop missing" }
    Invoke-Checked "docker" @("info", "--format", "{{.ServerVersion}}")
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js missing" }
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw "npm missing" }
    $python = Join-Path $backend ".venv-py311\Scripts\python.exe"
    if (-not (Test-Path $python)) { $python = Join-Path $backend ".venv-py312\Scripts\python.exe" }
    if (-not (Test-Path $python)) { throw "Existing backend Python 3.11/3.12 venv missing" }
    Invoke-Checked $python @("-c", "import fastapi, uvicorn, sqlalchemy, alembic, psycopg2")

    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    try { $listener.Start(); $dbPort = $listener.LocalEndpoint.Port } finally { $listener.Stop() }
    $bytes = New-Object byte[] 24
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    $secret = [BitConverter]::ToString($bytes).Replace("-", "").ToLowerInvariant()
    $env:APP_ENV = "test"
    $env:STAGE6_PREVIEW_ENABLED = "0"
    $env:RECOVERY_POSTGRES_TEST = "0"
    Remove-Item Env:SCENARIO_TEST_POSTGRES_URL -ErrorAction SilentlyContinue
    Remove-Item Env:VITE_API_BASE_URL -ErrorAction SilentlyContinue
    $env:DATABASE_URL = "postgresql+psycopg2://postgres:${secret}@127.0.0.1:${dbPort}/retire_v2_supervisor41_test"
    $dockerArgs = @("run", "--detach", "--rm", "--name", $containerName,
        "--label", "retire-v2.supervisor41=$runId",
        "--publish", "127.0.0.1:${dbPort}:5432",
        "--env", "POSTGRES_PASSWORD=$secret",
        "--env", "POSTGRES_DB=retire_v2_supervisor41_test", "postgres:16-alpine")
    $containerId = (& docker @dockerArgs).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $containerId) { throw "SUPERVISOR41_DOCKER_START_FAILED" }
    $ready = $false
    for ($i = 0; $i -lt 75; $i++) {
        & docker exec $containerId pg_isready -U postgres -d retire_v2_supervisor41_test 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw "SUPERVISOR41_PG16_NOT_READY" }
    Push-Location $backend
    try {
        Invoke-Checked $python @("-m", "alembic", "-c", "alembic.ini", "upgrade", "head")
        Invoke-Checked $python @("scripts/seed_supervisor41_local.py")
    } finally { Pop-Location }
    $backendArgs = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
        "--port", "8001", "--no-access-log")
    $backendProcess = Start-Process -FilePath $python -WorkingDirectory $backend -ArgumentList $backendArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $report "backend.stdout.log") -RedirectStandardError (Join-Path $report "backend.stderr.log")
    Wait-Http "http://127.0.0.1:8001/health" $backendProcess
    Push-Location $frontend
    try {
        if (-not (Test-Path "node_modules/vite/bin/vite.js")) {
            Invoke-Checked "npm.cmd" @("ci", "--ignore-scripts", "--no-audit", "--no-fund")
        }
        if (-not (Test-Path "node_modules/@playwright/test/package.json")) {
            Invoke-Checked "npm.cmd" @("install", "--no-save", "--package-lock=false", "--ignore-scripts",
                "--no-audit", "--no-fund", "@playwright/test@1.56.1")
        }
        $playwright = Join-Path $frontend "node_modules\.bin\playwright.cmd"
        Invoke-Checked $playwright @("install", "chromium")
        $viteArgs = @("node_modules/vite/bin/vite.js", "--mode", "test", "--host",
            "127.0.0.1", "--port", "5173", "--strictPort")
        $frontendProcess = Start-Process -FilePath (Get-Command node).Source -WorkingDirectory $frontend -ArgumentList $viteArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $report "frontend.stdout.log") -RedirectStandardError (Join-Path $report "frontend.stderr.log")
        Wait-Http "http://127.0.0.1:5173/" $frontendProcess
        $env:PLAYWRIGHT_JSON_OUTPUT_FILE = Join-Path $report "playwright-report.json"
        $testArgs = @("test", "e2e/supervisor41.spec.ts", "--browser=chromium",
            "--workers=1", "--reporter=line,json", "--trace=on",
            "--output", (Join-Path $report "screenshots"))
        & $playwright @testArgs *> (Join-Path $report "playwright-console.log")
        if ($LASTEXITCODE -ne 0) { throw "SUPERVISOR41_PLAYWRIGHT_FAILED:$LASTEXITCODE" }
        $passed = $true
    } finally { Pop-Location }
}
catch {
    $reason = $_.Exception.Message
    Write-Host ("SUPERVISOR41_BLOCKED: " + $reason)
    Set-Content -Path (Join-Path $report "failure.txt") -Value $reason -Encoding UTF8
}
finally {
    foreach ($proc in @($frontendProcess, $backendProcess)) {
        if ($null -ne $proc) {
            try {
                $proc.Refresh()
                if (-not $proc.HasExited) {
                    Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                    $proc.WaitForExit(10000) | Out-Null
                }
            } catch { Write-Host ("SUPERVISOR41_PROCESS_CLEANUP_WARNING:" + $_.Exception.Message) }
        }
    }
    if ($containerId) {
        try {
            $details = @((& docker inspect $containerId 2>$null | ConvertFrom-Json))
            if ($LASTEXITCODE -eq 0 -and $details.Count -eq 1 -and
                $details[0].Id -eq $containerId -and
                $details[0].Config.Labels.'retire-v2.supervisor41' -eq $runId) {
                & docker rm --force $containerId 2>$null | Out-Null
            } else { Write-Host "SUPERVISOR41_CONTAINER_IDENTITY_NOT_VERIFIED" }
        } catch { Write-Host ("SUPERVISOR41_DOCKER_CLEANUP_WARNING:" + $_.Exception.Message) }
    }
    foreach ($name in $variables) {
        [Environment]::SetEnvironmentVariable($name, $saved[$name], "Process")
    }
    $status = if ($passed) { "PASS" } else { "BLOCKED_OR_FAILED" }
    Set-Content -Path (Join-Path $report "summary.txt") -Encoding UTF8 -Value @(
        "SUPERVISOR41_STATUS=$status",
        "HEAD=$head",
        "RESULTS=$report",
        "SYNTHETIC_ONLY=True",
        "CONTAINER_ID=$containerId"
    )
    Write-Host "SUPERVISOR41_STATUS=$status"
    Write-Host "SUPERVISOR41_EVIDENCE_DIR=$report"
}
if (-not $passed) { exit 1 }
exit 0
