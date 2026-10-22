# ASCII-only file: compatible with Windows PowerShell 5.1 encoding defaults.
# Synthetic V2 workspace integration. Uses only local loopback and ephemeral Docker storage.
# Execute from the cloned feature branch. Ctrl+C stops the frontend and removes the test stack.
param([switch]$SkipSeed)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $repo "frontend"
$composeFile = Join-Path $PSScriptRoot "compose.workspace.yml"
$project = ("rtdir-ux-" + (Get-Date -Format "yyyyMMddHHmmss")).ToLowerInvariant()
$base = "http://127.0.0.1:18080"
$composeStarted = $false

function Assert-Command([string]$name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw ("Required tool is missing: " + $name)
  }
}
function Request-Json([string]$method, [string]$path, $data = $null) {
  $args = @{ Uri = ($base + $path); Method = $method; TimeoutSec = 20 }
  if ($null -ne $data) {
    $json = ConvertTo-Json -InputObject $data -Depth 24 -Compress
    $args["Body"] = [System.Text.Encoding]::UTF8.GetBytes($json)
    $args["ContentType"] = "application/json; charset=utf-8"
  }
  $response = Invoke-WebRequest @args -UseBasicParsing
  $response.RawContentStream.Position = 0
  $reader = New-Object System.IO.StreamReader($response.RawContentStream, [System.Text.Encoding]::UTF8)
  try { $responseJson = $reader.ReadToEnd() } finally { $reader.Dispose() }
  return ConvertFrom-Json -InputObject $responseJson
}
function Add-SyntheticProduct([int]$client, [string]$name, [string]$account,
    [string]$reported, [string[]]$allocations) {
  $metadata = @{
    product_name = $name
    product_type = "Synthetic Pension Product"
    provider_name = "Synthetic Pension Provider"
    provider_identifier = $null
    account_reference = $account
    start_date = "2001-01-01"
    statement_date = "2026-09-30"
    historical_employers = @()
    reported_product_total = $reported
    reported_rewards_total = $null
    reported_severance_total = $null
  }
  $created = Request-Json "POST" ("/api/clients/" + $client + "/pension-products") $metadata
  $components = @{}
  $codes = @($created.components.PSObject.Properties.Name)
  if ($codes.Count -ne 11) {
    throw ("Expected 11 canonical monetary components; got " + $codes.Count)
  }
  foreach ($code in $codes) { $components[$code] = "0.00" }
  for ($i = 0; $i -lt $allocations.Count; $i++) {
    $components[$codes[$i]] = $allocations[$i]
  }
  $body = @{}
  foreach ($key in $metadata.Keys) { $body[$key] = $metadata[$key] }
  $body["components"] = $components
  $body["expected_version"] = $created.version
  $saved = Request-Json "PUT" ("/api/clients/" + $client +
     "/pension-products/" + $created.product_id) $body
  if ($saved.version -ne ($created.version + 1)) {
    throw "The synthetic product write did not advance its version."
  }
  Write-Host ("Seeded " + $name + " (" + $account + ")")
}

Assert-Command "docker"
Assert-Command "npm.cmd"
try {
  & docker info --format "{{.ServerVersion}}" | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Docker Desktop is not running." }
  & docker compose version | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Docker Compose v2 is required." }
  if (-not (Test-Path $composeFile)) { throw "Missing local Compose file." }
  if (-not (Test-Path (Join-Path $frontend "package-lock.json"))) {
    throw "Frontend dependencies are missing from the checkout."
  }

  Write-Host ""
  Write-Host "Starting isolated PostgreSQL 16 + FastAPI; no Railway credentials are used."
  Write-Host ("Compose project: " + $project)
  $composeStarted = $true
  & docker compose -p $project -f $composeFile up --build -d
  if ($LASTEXITCODE -ne 0) { throw "Could not start the isolated Docker stack." }

  $ready = $false
  for ($i=0; $i -lt 90; $i++) {
    try {
      $health = Invoke-RestMethod -Uri ($base + "/health") -TimeoutSec 2
      if ($health.status -eq "ok") { $ready = $true; break }
    } catch {}
    # Fail immediately on a crashed migration; avoid a lengthy health wait.
    $backendId = (& docker compose -p $project -f $composeFile ps -a -q backend |
      Select-Object -First 1)
    if ($backendId) {
      $backendState = (& docker inspect --format "{{.State.Status}}" $backendId)
      if ($backendState -eq "exited" -or $backendState -eq "dead") {
        throw "Local FastAPI container exited. See the logs below for the exact migration or server error."
      }
    }
    Start-Sleep -Seconds 2
  }
  if (-not $ready) { throw "Local FastAPI health endpoint did not become ready." }

  if (-not $SkipSeed) {
    $primary = Request-Json "POST" "/api/clients" @{
      full_name = "Synthetic Retirement Client A"
      id_number = "900000101"
      birth_date = "1963-04-17"
    }
    Add-SyntheticProduct $primary.client_id "Synthetic Pension Fund A" "SYN-A-001" "350000.00" @("50000.00", "100000.00", "200000.00")
    Add-SyntheticProduct $primary.client_id "Synthetic Provident Fund B" "SYN-B-002" "250000.00" @("70000.00", "180000.00")
    Add-SyntheticProduct $primary.client_id "Synthetic Policy C" "SYN-C-003" "410000.00" @("410000.00")
    Add-SyntheticProduct $primary.client_id "Synthetic Balance Review D" "SYN-D-004" "121000.00" @("120000.00")
    $secondary = Request-Json "POST" "/api/clients" @{
      full_name = "Synthetic Retirement Client B"
      id_number = "900000102"
      birth_date = "1960-03-21"
    }
    Add-SyntheticProduct $secondary.client_id "Synthetic Other Client Fund" "SYN-E-005" "75000.00" @("75000.00")
    $openUrl = "http://127.0.0.1:5173/clients/" + $primary.client_id + "/workspace"
    $list = Request-Json "GET" ("/api/clients/" + $primary.client_id + "/pension-products")
    if (@($list).Count -ne 4) { throw "Synthetic product verification failed." }
    Write-Host ("Verified " + @($list).Count + " isolated products for client A.")
  } else {
    $openUrl = "http://127.0.0.1:5173/clients"
  }

  Push-Location $frontend
  try {
    if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
      Write-Host "Installing locked frontend dependencies..."
      & npm.cmd ci
      if ($LASTEXITCODE -ne 0) { throw "npm ci failed." }
    }
    $env:VITE_API_BASE_URL = $base + "/api"
    Write-Host ""
    Write-Host "The React frontend will connect only to the isolated local FastAPI backend."
    Write-Host ("Open in your browser: " + $openUrl)
    Write-Host "Ctrl+C ends the trial and destroys the temporary synthetic database."
    Start-Job -ArgumentList $openUrl -ScriptBlock {
      param($url)
      Start-Sleep -Seconds 6
      Start-Process $url
    } | Out-Null
    & npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
  } finally {
    Pop-Location
  }
} catch {
  Write-Host ("LOCAL TRIAL FAILED: " + $_.Exception.Message) -ForegroundColor Red
  if ($composeStarted) {
    Write-Host "Recent isolated backend logs:"
    & docker compose -p $project -f $composeFile logs --tail 50 backend
  }
  throw
} finally {
  if ($composeStarted) {
    Write-Host ""
    Write-Host "Removing isolated containers, networks and temporary database..."
    & docker compose -p $project -f $composeFile down --volumes --remove-orphans
  }
}
