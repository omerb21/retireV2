# Guarded local-only deployment of historical settlement schema to existing synthetic stack.
# Never uses compose down or recreates the tmpfs-backed database container.
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$project = "rtdir-ux-20261022135623"
$backend = "$project-backend-1"
$db = "$project-db-1"
$backupDir = Join-Path $repo "dev-local-backups"
Push-Location $repo
try {
  $dbRunning = & docker inspect --format '{{.State.Running}}' $db 2>$null
  if ($LASTEXITCODE -ne 0 -or $dbRunning -ne "true") {
    throw "Expected synthetic DB container is not running. Refusing any changes."
  }
  $actualDb = & docker exec $db printenv POSTGRES_DB
  if ($LASTEXITCODE -ne 0 -or $actualDb.Trim() -ne "retirement_v2_synthetic") {
    throw "The target database is not the expected synthetic database. Refusing any changes."
  }
  $actualUser = & docker exec $db printenv POSTGRES_USER
  if ($LASTEXITCODE -ne 0 -or $actualUser.Trim() -ne "synthetic_planner") {
    throw "The target database user does not match. Refusing any changes."
  }
  New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $backup = Join-Path $backupDir "retirement_v2_synthetic-$stamp.dump"
  # Powershell 5 native output redirection may alter bytes; use docker cp instead.
  & docker exec $db pg_dump -U synthetic_planner -d retirement_v2_synthetic -Fc -f /tmp/settlement_pre_migration.dump
  if ($LASTEXITCODE -ne 0) { throw "pg_dump failed: backend unchanged" }
  & docker cp "${db}:/tmp/settlement_pre_migration.dump" $backup
  if ($LASTEXITCODE -ne 0 -or !(Test-Path $backup)) { throw "Could not copy backup: backend unchanged" }
  if ((Get-Item $backup).Length -lt 1024) { throw "Backup file unexpectedly small: backend unchanged" }
  & docker exec $db pg_restore --list /tmp/settlement_pre_migration.dump *> $null
  if ($LASTEXITCODE -ne 0) { throw "Backup archive validation failed: backend unchanged" }
  Write-Host "BACKUP OK: $backup"
  $backendRunning = & docker inspect --format '{{.State.Running}}' $backend 2>$null
  if ($LASTEXITCODE -ne 0 -or $backendRunning -ne "true") { throw "Expected backend is not running. Refusing replacement." }
  & docker compose -p $project -f "dev/compose.workspace.yml" up -d --no-deps --build backend
  if ($LASTEXITCODE -ne 0) { throw "Backend replacement failed; saved backup: $backup" }
  $healthy = $false
  for ($i = 0; $i -lt 35; $i++) {
    $status = & docker inspect --format '{{.State.Health.Status}}' $backend 2>$null
    if ($LASTEXITCODE -eq 0 -and $status -eq "healthy") { $healthy = $true; break }
    Start-Sleep -Seconds 2
  }
  if (-not $healthy) { throw "Backend not healthy; preserve backup: $backup" }
  $revision = & docker exec --env "DATABASE_URL=postgresql://synthetic_planner:synthetic_only_local_password@db:5432/retirement_v2_synthetic" $backend python -m alembic current 2>&1
  if ($LASTEXITCODE -ne 0) { throw "Could not verify schema revision: $revision" }
  Write-Host $revision
  if (($revision | Out-String) -notmatch "d2c4e6a8b031") {
    throw "Unexpected Alembic revision; retain backup: $backup"
  }
  & docker exec $db psql -U synthetic_planner -d retirement_v2_synthetic -v ON_ERROR_STOP=1 -tAc "SELECT exempt_grant_status || ':' || COUNT(*) FROM employment_records WHERE NOT is_current GROUP BY exempt_grant_status ORDER BY exempt_grant_status;"
  if ($LASTEXITCODE -ne 0) { throw "Schema updated but unable to review settlement statuses" }
  Write-Host "PASS: local synthetic database migration and backend health verified; DB container unchanged."
  Write-Host "Backup: $backup"
} finally {
  Pop-Location
}
