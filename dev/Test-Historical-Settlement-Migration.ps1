# Local isolated migration regression; does not modify the running workspace stack.
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$image = "retirev2-employment-link-local-test"
Push-Location $repo
try {
  & docker build --file "dev/Dockerfile.workspace" --tag $image .
  if ($LASTEXITCODE -ne 0) { throw "Backend image build failed." }
  & docker run --rm --network none --env "APP_ENV=development" $image python -m pytest tests/test_historical_settlement_migration.py -q
  if ($LASTEXITCODE -ne 0) { throw "Historical settlement migration regression failed." }
  Write-Host "PASS: legacy duplicate-safe migration in disposable database; active PostgreSQL untouched."
} finally {
  Pop-Location
}
