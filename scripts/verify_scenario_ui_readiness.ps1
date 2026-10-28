# RetireV2 scenario UI preflight: local verification only, never deploys.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
if (!(Test-Path (Join-Path $backend "app/main.py"))) { throw "Canonical backend missing" }
if (!(Test-Path (Join-Path $frontend "package.json"))) { throw "Canonical frontend missing" }
Push-Location $backend
try {
  python -m pytest -q tests/test_scenario_input_manifest.py tests/test_scenario_snapshot_candidate.py tests/test_scenario_allocation_evidence.py tests/test_scenario_allocation_snapshot_service.py tests/test_stage6_internal_api.py
  if ($LASTEXITCODE -ne 0) { throw "Backend tests failed" }
} finally { Pop-Location }
Push-Location $frontend
try {
  if (!(Test-Path "node_modules")) { throw "Frontend dependencies missing; install them from the lockfile" }
  npm test -- src/api/scenarioStage6Api.test.ts src/components/ScenarioStage6Panel.test.tsx
  if ($LASTEXITCODE -ne 0) { throw "Frontend tests failed" }
  $previous = $env:VITE_STAGE6_PREVIEW_ENABLED
  try {
    $env:VITE_STAGE6_PREVIEW_ENABLED = "1"
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
  } finally { $env:VITE_STAGE6_PREVIEW_ENABLED = $previous }
} finally { Pop-Location }
Write-Host "SCENARIO_UI_TEST_GATE=PASS; BROWSER_AND_DATABASE_E2E_NOT_TESTED"
