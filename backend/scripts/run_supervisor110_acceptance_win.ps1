# RETIRE V2 Supervisor 110 - Windows localhost fixation admission controls acceptance.
# One command from the existing worktree:
# powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_supervisor110_acceptance_win.ps1 -ExpectedHead <40-character-commit-SHA>
# Docker Desktop Linux engine, existing backend venv, Node/npm required.
# Reuses the previously accepted Supervisor 41 synthetic seed; no remote app or database access.
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[0-9a-fA-F]{40}$")]
    [string]$ExpectedHead
)
$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent $PSScriptRoot
$root = Split-Path -Parent $backend
$frontend = Join-Path $root "frontend"
$runId = [Guid]::NewGuid().ToString("N").Substring(0, 14)
$containerName = "retire-v2-supervisor110-" + $runId
$report = Join-Path $env:TEMP ("RETIRE_V2_SUPERVISOR110\" + $runId)
New-Item -ItemType Directory -Path $report -Force | Out-Null
$containerId = $null
$backendProcess = $null
$frontendProcess = $null
$passed = $false
$stages = [ordered]@{ PostgreSQL='NOT_RUN'; Frontend='NOT_RUN'; TypeScript='NOT_RUN'; Chromium='NOT_RUN' }
$counts = [ordered]@{}
$cleanupOk = $true
$saved = @{}
$variables = @("DATABASE_URL", "SCENARIO_TEST_POSTGRES_URL", "APP_ENV", "STAGE6_PREVIEW_ENABLED", "RECOVERY_POSTGRES_TEST", "VITE_API_BASE_URL", "PLAYWRIGHT_JSON_OUTPUT_FILE", "CRTISBA_APPLICATION_DB_ROLE")
foreach ($name in $variables) { $saved[$name] = [Environment]::GetEnvironmentVariable($name, "Process") }

function Invoke-Checked([string]$program, [string[]]$arguments) {
    & $program @arguments
    if ($LASTEXITCODE -ne 0) { throw "SUPERVISOR110_COMMAND_FAILED:$program exit=$LASTEXITCODE" }
}
function Assert-FreeLocalPort([int]$port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $result = $client.BeginConnect("127.0.0.1", $port, $null, $null)
        if ($result.AsyncWaitHandle.WaitOne(350)) {
            try { $client.EndConnect($result) } catch { return }
            throw "SUPERVISOR110_PORT_IN_USE:$port"
        }
    } finally { $client.Close() }
}
function Wait-Http([string]$uri, [System.Diagnostics.Process]$process) {
    for ($i = 0; $i -lt 80; $i++) {
        $process.Refresh()
        if ($process.HasExited) { throw "SUPERVISOR110_SERVER_EXITED:$uri" }
        try {
            $response = Invoke-WebRequest -Uri $uri -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { return }
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    throw "SUPERVISOR110_SERVER_NOT_READY:$uri"
}
try {
    Push-Location $root
    try {
        $head = (& git rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0) { throw "SUPERVISOR110_NOT_GIT_WORKTREE" }
    } finally { Pop-Location }
    # Commit identity is authoritative. Detached HEAD is deliberately supported.
    # Use explicit -C so invocation does not depend on the caller's directory.
    if ($head -cne $ExpectedHead.ToLowerInvariant()) {
        throw "SUPERVISOR110_HEAD_MISMATCH:expected=$ExpectedHead;actual=$head"
    }
    $dirty = & git -C $root status --porcelain --untracked-files=all
    if ($LASTEXITCODE -ne 0) { throw "SUPERVISOR110_GIT_STATUS_FAILED" }
    if ($dirty) { throw "SUPERVISOR110_WORKTREE_NOT_CLEAN" }
    Set-Content (Join-Path $report "head.txt") @("HEAD=$head", "EXPECTED_HEAD=$ExpectedHead")
    foreach ($port in @(8001, 5174)) { Assert-FreeLocalPort $port }
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
    # A unique role for this one disposable localhost PG16 container.
    $env:CRTISBA_APPLICATION_DB_ROLE = "supervisor110_app_$runId"
    $env:DATABASE_URL = "postgresql+psycopg2://postgres:${secret}@127.0.0.1:${dbPort}/retire_v2_supervisor41_test"
    $dockerArgs = @("run", "--detach", "--rm", "--name", $containerName,
        "--label", "retire-v2.supervisor110=$runId",
        "--publish", "127.0.0.1:${dbPort}:5432",
        "--env", "POSTGRES_PASSWORD=$secret",
        "--env", "POSTGRES_DB=retire_v2_supervisor41_test", "postgres:16-alpine")
    $containerId = (& docker @dockerArgs).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $containerId) { throw "SUPERVISOR110_DOCKER_START_FAILED" }
    # The official postgres image may start a bootstrap server on its Unix
    # socket, stop it, and only then start the permanent TCP listener.
    # Docker-internal pg_isready without -h can report the bootstrap server.
    # Require two successful TCP SQL probes to the *final* listener.
    $deadline = [DateTime]::UtcNow.AddSeconds(120)
    $consecutive = 0
    $ready = $false
    while ([DateTime]::UtcNow -lt $deadline) {
        # A stopped container is never an acceptable readiness outcome.
        $running = (& docker inspect --format "{{.State.Running}}" $containerId 2>$null)
        if ($LASTEXITCODE -ne 0 -or "$running".Trim() -ne "true") {
            throw "SUPERVISOR110_PG16_CONTAINER_STOPPED"
        }
        & docker exec $containerId pg_isready -h 127.0.0.1 -p 5432 -U postgres -d retire_v2_supervisor41_test -t 2 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $consecutive = 0
            Start-Sleep -Seconds 1
            continue
        }
        # SQL proves that the TCP endpoint accepts actual authenticated
        # connections, rather than just advertising readiness.
        $probe = & docker exec -e "PGPASSWORD=$secret" $containerId psql -X -w -h 127.0.0.1 -p 5432 -U postgres -d retire_v2_supervisor41_test -t -A -v ON_ERROR_STOP=1 -c "SELECT CASE WHEN pg_is_in_recovery() THEN 'recovery' ELSE 'primary' END" 2>&1
        if ($LASTEXITCODE -ne 0) {
            $detail = ($probe | Out-String).Trim()
            if ($detail -match '(?i)database system is (starting up|shutting down)|connection refused|server closed the connection unexpectedly|the database system is in recovery mode') {
                $consecutive = 0
                Start-Sleep -Seconds 1
                continue
            }
            throw "SUPERVISOR110_PG16_SQL_PROBE_FAILED:$detail"
        }
        if (($probe | Out-String).Trim() -ne "primary") {
            throw "SUPERVISOR110_PG16_UNEXPECTED_SERVER_STATE"
        }
        $consecutive += 1
        if ($consecutive -ge 2) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw "SUPERVISOR110_PG16_TCP_STARTUP_TIMEOUT" }

    # This role is created only inside the uniquely identified disposable
    # container. Alembic still performs its original privilege checks.
    $role = $env:CRTISBA_APPLICATION_DB_ROLE
    if ($role -cnotmatch '^supervisor110_app_[0-9a-f]{14}$') {
        throw "SUPERVISOR110_APPLICATION_ROLE_NAME_INVALID"
    }
    # A short bounded retry covers an exceptional shutdown/startup transition
    # after readiness. Any other SQL error is surfaced immediately.
    $roleCreated = $false
    for ($attempt = 0; $attempt -lt 5; $attempt++) {
        $createOutput = & docker exec -e "PGPASSWORD=$secret" $containerId psql -X -w -h 127.0.0.1 -p 5432 -v ON_ERROR_STOP=1 -U postgres -d retire_v2_supervisor41_test -c "CREATE ROLE $role NOLOGIN" 2>&1
        if ($LASTEXITCODE -eq 0) {
            if (($createOutput | Out-String) -notmatch 'CREATE ROLE') {
                throw "SUPERVISOR110_APPLICATION_ROLE_CREATE_UNEXPECTED_OUTPUT"
            }
            $roleCreated = $true
            break
        }
        $createError = ($createOutput | Out-String).Trim()
        if ($createError -notmatch '(?i)database system is (starting up|shutting down)|connection refused|server closed the connection unexpectedly|the database system is in recovery mode') {
            throw "SUPERVISOR110_APPLICATION_ROLE_CREATE_FAILED:$createError"
        }
        if ($attempt -eq 4 -or [DateTime]::UtcNow -ge $deadline) { break }
        Start-Sleep -Seconds 1
    }
    if (-not $roleCreated) { throw "SUPERVISOR110_APPLICATION_ROLE_STARTUP_TIMEOUT" }
    $roleExists = (& docker exec -e "PGPASSWORD=$secret" $containerId psql -X -w -h 127.0.0.1 -p 5432 -v ON_ERROR_STOP=1 -U postgres -d retire_v2_supervisor41_test -t -A -c "SELECT count(*) FROM pg_roles WHERE rolname = '$role'").Trim()
    if ($LASTEXITCODE -ne 0 -or $roleExists -ne "1") {
        throw "SUPERVISOR110_APPLICATION_ROLE_NOT_VERIFIED"
    }
    # The existing integration fixture requires its own fixed-name localhost DB.
    & docker exec -e "PGPASSWORD=$secret" $containerId psql -X -w -h 127.0.0.1 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE retire_v2_scenario_test" *> (Join-Path $report "pg-test-db.log")
    if ($LASTEXITCODE -ne 0) { throw "SUPERVISOR110_TEST_DB_CREATE_FAILED" }
    $env:SCENARIO_TEST_POSTGRES_URL = "postgresql+psycopg2://postgres:${secret}@127.0.0.1:${dbPort}/retire_v2_scenario_test"
    Push-Location $backend
    try {
        $pgOutput = Join-Path $report "postgresql.log"
        & $python -m pytest -q -ra --junitxml (Join-Path $report "postgresql-junit.xml") tests/test_scenario_internal_fixation_approval_postgresql.py tests/test_internal_fixation_approval_migration_postgresql.py tests/test_supervisor110_source_race_postgresql.py *> $pgOutput
        $pgExit = $LASTEXITCODE
        Add-Content $pgOutput "EXIT_CODE=$pgExit"
        if ($pgExit -ne 0) { throw "SUPERVISOR110_POSTGRESQL_FAILED:$pgExit" }
        $junit = [xml](Get-Content (Join-Path $report "postgresql-junit.xml") -Raw)
        $suite = $junit.testsuites.testsuite
        if ($null -eq $suite) { $suite = $junit.testsuite }
        if ([int]$suite.tests -lt 3 -or [int]$suite.failures -ne 0 -or [int]$suite.errors -ne 0 -or [int]$suite.skipped -ne 0) { throw "SUPERVISOR110_POSTGRESQL_INCOMPLETE" }
        $counts.PostgreSQL = @{ Tests=[int]$suite.tests; Failures=[int]$suite.failures; Errors=[int]$suite.errors; Skipped=[int]$suite.skipped; Exit=$pgExit }
        $stages.PostgreSQL = 'PASS'
    } finally { Pop-Location }

    Push-Location $frontend
    try {
        if (-not (Test-Path "node_modules/vite/bin/vite.js")) {
            Invoke-Checked "npm.cmd" @("ci", "--ignore-scripts", "--no-audit", "--no-fund")
        }
        $vitest = Join-Path $frontend "node_modules\.bin\vitest.cmd"
        $ftOutput = Join-Path $report "frontend.log"
        $frontendJunit = Join-Path $report "frontend-junit.xml"
        & $vitest run src/components/ScenarioFixationProfessionalReviewPanel.test.tsx --reporter=verbose --reporter=junit "--outputFile.junit=$frontendJunit" *> $ftOutput
        $ftExit = $LASTEXITCODE
        Add-Content $ftOutput "EXIT_CODE=$ftExit"
        if ($ftExit -ne 0) { throw "SUPERVISOR110_FRONTEND_FAILED:$ftExit" }
        $ftXml = [xml](Get-Content (Join-Path $report "frontend-junit.xml") -Raw)
        $ftSuite = $ftXml.testsuites.testsuite
        if ($null -eq $ftSuite) { $ftSuite = $ftXml.testsuite }
        if ([int]$ftSuite.tests -lt 1 -or [int]$ftSuite.failures -ne 0 -or [int]$ftSuite.errors -ne 0 -or [int]$ftSuite.skipped -ne 0) { throw "SUPERVISOR110_FRONTEND_INCOMPLETE" }
        $counts.Frontend = @{ Tests=[int]$ftSuite.tests; Failures=[int]$ftSuite.failures; Errors=[int]$ftSuite.errors; Skipped=[int]$ftSuite.skipped; Exit=$ftExit }
        $stages.Frontend = 'PASS'

        $tsOutput = Join-Path $report "typescript.log"
        & (Join-Path $frontend "node_modules\.bin\tsc.cmd") -b --pretty false *> $tsOutput
        $tsExit = $LASTEXITCODE
        Add-Content $tsOutput "EXIT_CODE=$tsExit"
        if ($tsExit -ne 0) { throw "SUPERVISOR110_TYPESCRIPT_FAILED:$tsExit" }
        $counts.TypeScript = @{ Tests=1; Failures=0; Errors=0; Skipped=0; Exit=$tsExit }
        $stages.TypeScript = 'PASS'
    } finally { Pop-Location }

    Remove-Item Env:SCENARIO_TEST_POSTGRES_URL -ErrorAction SilentlyContinue
    Push-Location $backend
    try {
        Invoke-Checked $python @("-m", "alembic", "-c", "alembic.ini", "upgrade", "head")
        Invoke-Checked $python @("-m", "scripts.seed_supervisor41_local")
    } finally { Pop-Location }
    $backendArgs = @("-m", "uvicorn", "scripts.supervisor65_test_app:app", "--host", "127.0.0.1",
        "--port", "8001", "--no-access-log")
    $backendProcess = Start-Process -FilePath $python -WorkingDirectory $backend -ArgumentList $backendArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $report "backend.stdout.log") -RedirectStandardError (Join-Path $report "backend.stderr.log")
    Wait-Http "http://127.0.0.1:8001/health" $backendProcess
    # Reject a foreign service on 8001 even when its /health returns HTTP 200.
    $backendIdentity = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8001/__retire_v2_test_identity" -TimeoutSec 5
    if ($backendIdentity.service -cne "RETIRE_V2_BACKEND" -or
        $backendIdentity.environment -cne "test" -or
        $backendIdentity.database -cne "retire_v2_supervisor41_test" -or
        $backendIdentity.port -ne 8001) {
        throw "SUPERVISOR110_BACKEND_IDENTITY_MISMATCH"
    }
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
            "127.0.0.1", "--port", "5174", "--strictPort")
        $frontendProcess = Start-Process -FilePath (Get-Command node).Source -WorkingDirectory $frontend -ArgumentList $viteArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $report "frontend.stdout.log") -RedirectStandardError (Join-Path $report "frontend.stderr.log")
        Wait-Http "http://127.0.0.1:5174/" $frontendProcess
        # Vite identity is only served in --mode test and on localhost:5174.
        $frontendIdentity = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:5174/__retire_v2_test_identity" -TimeoutSec 5
        if ($frontendIdentity.service -cne "RETIRE_V2_FRONTEND" -or
            $frontendIdentity.mode -cne "test" -or $frontendIdentity.port -ne 5174) {
            throw "SUPERVISOR110_FRONTEND_IDENTITY_MISMATCH"
        }
        # Confirm Vite's /api proxy reaches the seeded RETIRE V2 backend, not
        # a CRM listener. A 401/404 is a preflight failure, not a test pass.
        $prepared = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:5174/api/clients/410078/scenario-drafts/supervisor78-scenario-a/fixation-admission-preparation" -TimeoutSec 15
        if ($prepared.contract -cne "SCENARIO_FIXATION_ADMISSION_PREPARATION_V1" -or
            $prepared.client_id -ne 410078 -or
            $prepared.scenario_id -cne "supervisor78-scenario-a" -or
            $prepared.state -cne "PREPARED" -or
            $prepared.professional_authority -cne $false -or
            $prepared.execution_allowed -cne $false) {
            throw "SUPERVISOR110_API_PROXY_IDENTITY_MISMATCH"
        }
        $env:PLAYWRIGHT_JSON_OUTPUT_FILE = Join-Path $report "playwright-report.json"
        $testArgs = @("test", "e2e/supervisor110.spec.ts", "--browser=chromium", "--workers=1", "--reporter=line,json", "--trace=on",
            "--output", (Join-Path $report "screenshots"))
        & $playwright @testArgs *> (Join-Path $report "playwright-console.log")
        $browserExit = $LASTEXITCODE
        Add-Content (Join-Path $report "playwright-console.log") "EXIT_CODE=$browserExit"
        if ($browserExit -ne 0) { throw "SUPERVISOR110_PLAYWRIGHT_FAILED:$browserExit" }
        $jsonPath = Join-Path $report "playwright-report.json"
        if (-not (Test-Path $jsonPath)) { throw "SUPERVISOR110_BROWSER_JSON_MISSING" }
        $pw = Get-Content $jsonPath -Raw | ConvertFrom-Json
        if ([int]$pw.stats.expected -lt 1 -or [int]$pw.stats.unexpected -ne 0 -or [int]$pw.stats.skipped -ne 0 -or [int]$pw.stats.flaky -ne 0) { throw "SUPERVISOR110_BROWSER_RESULTS_INCOMPLETE" }
        $counts.Chromium = @{ Tests=[int]$pw.stats.expected; Failures=[int]$pw.stats.unexpected; Errors=0; Skipped=[int]$pw.stats.skipped; Exit=$browserExit }
        $stages.Chromium = 'PASS'
        $passed = $true
    } finally { Pop-Location }
}
catch {
    $reason = $_.Exception.Message
    Write-Host ("SUPERVISOR110_BLOCKED: " + $reason)
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
            } catch {
                $cleanupOk = $false
                Write-Host ("SUPERVISOR110_PROCESS_CLEANUP_WARNING:" + $_.Exception.Message)
            }
        }
    }
    if ($containerId) {
        try {
            $details = @((& docker inspect $containerId 2>$null | ConvertFrom-Json))
            if ($LASTEXITCODE -eq 0 -and $details.Count -eq 1 -and
                $details[0].Id -eq $containerId -and
                $details[0].Config.Labels.'retire-v2.supervisor110' -eq $runId) {
                & docker rm --force $containerId 2>$null | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    $cleanupOk = $false
                    Write-Host "SUPERVISOR110_CONTAINER_REMOVE_FAILED"
                }
            } else {
                $cleanupOk = $false
                Write-Host "SUPERVISOR110_CONTAINER_IDENTITY_NOT_VERIFIED"
            }
        } catch {
            $cleanupOk = $false
            Write-Host ("SUPERVISOR110_DOCKER_CLEANUP_WARNING:" + $_.Exception.Message)
        }
    }
    foreach ($name in $variables) {
        [Environment]::SetEnvironmentVariable($name, $saved[$name], "Process")
    }
    $status = if ($passed -and $cleanupOk -and @($stages.Values | Where-Object { $_ -ne 'PASS' }).Count -eq 0) { "PASS" } else { "BLOCKED_OR_FAILED" }
    @{ Status=$status; Head=$head; Stages=$stages; Counts=$counts; Cleanup=$cleanupOk; Evidence=$report } | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $report "summary.json") -Encoding UTF8
    Set-Content -Path (Join-Path $report "summary.txt") -Encoding UTF8 -Value @(
        "SUPERVISOR110_STATUS=$status",
        "HEAD=$head",
        "RESULTS=$report",
        "SYNTHETIC_ONLY=True",
        "CLEANUP_CONFIRMED=$cleanupOk",
        "CONTAINER_ID=$containerId"
    )
    Write-Host "SUPERVISOR110_STATUS=$status"
    Write-Host "SUPERVISOR110_EVIDENCE_DIR=$report"
}
if (-not $passed -or -not $cleanupOk) { exit 1 }
exit 0
