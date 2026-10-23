# Read-only Alembic ancestry audit. Uses disposable local Docker image, no DB/network.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
  & docker build --file dev/Dockerfile.workspace --tag retirev2-employment-link-local-test .
  if ($LASTEXITCODE -ne 0) { throw "Backend image build failed" }
  & docker run --rm --network none --env "APP_ENV=development" retirev2-employment-link-local-test python -m alembic heads --verbose
  if ($LASTEXITCODE -ne 0) { throw "Could not determine Alembic heads" }
  & docker run --rm --network none --env "APP_ENV=development" retirev2-employment-link-local-test python -m alembic history -r -3:heads
  if ($LASTEXITCODE -ne 0) { throw "Could not inspect Alembic lineage" }
} finally {
  Pop-Location
}
