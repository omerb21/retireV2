# Local backend API regression suite. Offline, leaves the running dev stack untouched.
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$image = "retirev2-employment-link-local-test"
Push-Location $repo
try {
  & docker build --file "dev/Dockerfile.workspace" --tag $image .
  if ($LASTEXITCODE -ne 0) { throw "Local backend test image build failed." }
  # Pytest fixture migrates a disposable SQLite database in a temp directory.
  # No ports, network access or Railway configuration is used.
  & docker run --rm --network none --env "APP_ENV=development" $image python -m pytest tests/test_employment_grant_link_api.py -q
  if ($LASTEXITCODE -ne 0) { throw "Employment/grant link backend tests failed." }
  Write-Host "PASS: isolated backend link tests; existing localhost servers untouched."
} finally {
  Pop-Location
}
