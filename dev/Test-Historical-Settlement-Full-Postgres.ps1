# Disposable PostgreSQL migration probe. Never changes the running local stack.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$suffix = [guid]::NewGuid().ToString("N").Substring(0, 12)
$network = "settlement-probe-net-$suffix"
$db = "settlement-probe-db-$suffix"
$image = "retirev2-employment-link-local-test"
Push-Location $root
try {
  & docker build --file "dev/Dockerfile.workspace" --tag $image .
  if ($LASTEXITCODE -ne 0) { throw "Probe image build failed" }
  & docker network create --internal $network
  if ($LASTEXITCODE -ne 0) { throw "Isolated probe network create failed" }
  & docker run -d --name $db --network $network --env POSTGRES_DB=settlement_migration_probe --env POSTGRES_USER=probe_user --env POSTGRES_PASSWORD=probe_local_only --tmpfs /var/lib/postgresql/data postgres:16
  if ($LASTEXITCODE -ne 0) { throw "Probe DB launch failed" }
  $ready = $false
  for ($i = 0; $i -lt 35; $i++) {
    & docker exec $db pg_isready -U probe_user -d settlement_migration_probe *> $null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 1
  }
  if (-not $ready) { throw "Probe PostgreSQL did not become ready" }
  $dbUrl = "postgresql://probe_user:probe_local_only@${db}:5432/settlement_migration_probe"
  & docker run --rm --network $network --env "TEST_DATABASE_URL=$dbUrl" $image python tests/postgres_full_history_settlement_probe.py
  if ($LASTEXITCODE -ne 0) { throw "PostgreSQL migration probe failed" }
  Write-Host "PASS: full-chain PostgreSQL historical-settlement migration. Workspace database untouched."
} finally {
  & docker rm -f $db *> $null
  & docker network rm $network *> $null
  Pop-Location
}
