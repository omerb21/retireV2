# Local synthetic stack only. No Railway / real customer credentials.
# Run while dev/Start-Workspace-Local.ps1 is serving on 127.0.0.1:18080.
$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:18080/api"
function Request([string]$method, [string]$path, $body = $null) {
  $params = @{ Uri = $base + $path; Method = $method; TimeoutSec = 15; UseBasicParsing = $true }
  if ($null -ne $body) {
    $json = ConvertTo-Json -InputObject $body -Compress -Depth 10
    $params.Body = [System.Text.Encoding]::UTF8.GetBytes($json)
    $params.ContentType = "application/json; charset=utf-8"
  }
  $response = Invoke-WebRequest @params
  $stream = $response.RawContentStream
  if ($stream.CanSeek) { $stream.Position = 0 }
  $reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::UTF8)
  try { $text = $reader.ReadToEnd() } finally { $reader.Dispose() }
  return ConvertFrom-Json -InputObject $text
}
function Assert([bool]$ok, [string]$why) {
  if (-not $ok) { throw "SMOKE FAILED: $why" }
}
$clientsRaw = Request "GET" "/clients"
# PowerShell 5.1 may preserve the top-level JSON list as a nested array.
$clients = @($clientsRaw)
while ($clients.Count -eq 1 -and $clients[0] -is [array]) {
  $clients = @($clients[0] | ForEach-Object { $_ })
}
$aMatches = @($clients | Where-Object { $_.full_name -eq "Synthetic Retirement Client A" })
$bMatches = @($clients | Where-Object { $_.full_name -eq "Synthetic Retirement Client B" })
Assert ($aMatches.Count -eq 1 -and $bMatches.Count -eq 1) "Exactly one synthetic client A and B must exist."
Assert ($aMatches[0].client_id -isnot [array] -and $bMatches[0].client_id -isnot [array]) "Unexpected array-valued client ID."
$idA = [int]$aMatches[0].client_id
$idB = [int]$bMatches[0].client_id
Assert ($idA -ne $idB) "Client isolation precondition failed."
$employment = @{
  employer_name = "Synthetic Employer Before"
  work_start_date = "2012-01-01"
  work_end_date = "2020-12-31"
  is_current = $false
  notes = "synthetic only"
}
$createdEmp = Request "POST" "/clients/$idA/employment-records" $employment
Assert ($createdEmp.client_id -eq $idA) "Employment POST owner."
$employment.employer_name = "Synthetic Employer After"
$updatedEmp = Request "PUT" "/clients/$idA/employment-records/$($createdEmp.employment_record_id)" $employment
Assert ($updatedEmp.client_id -eq $idA -and $updatedEmp.employment_record_id -eq $createdEmp.employment_record_id) "Employment PUT identity."
$reloadedEmp = @(Request "GET" "/clients/$idA/employment-records")
Assert (@($reloadedEmp | Where-Object { $_.employment_record_id -eq $createdEmp.employment_record_id -and $_.employer_name -eq "Synthetic Employer After" }).Count -eq 1) "Employment persisted after GET."
Write-Host "PASS: employment POST / PUT / independent GET."
$grant = @{
  employer_name = "Synthetic Employer Grant"
  employer_withholding_file_number = "999999999"
  employment_start_date = "2012-01-01"
  employment_end_date = "2020-12-31"
  grant_receipt_date = "2021-01-15"
  exempt_grant_amount = "1000.00"
}
$createdGrant = Request "POST" "/clients/$idA/grants" $grant
Assert ($createdGrant.client_id -eq $idA) "Grant POST owner."
$grant.exempt_grant_amount = "1200.00"
$updatedGrant = Request "PUT" "/clients/$idA/grants/$($createdGrant.grant_id)" $grant
Assert ($updatedGrant.client_id -eq $idA -and $updatedGrant.grant_id -eq $createdGrant.grant_id) "Grant PUT identity."
$reloadedGrant = @(Request "GET" "/clients/$idA/grants")
Assert (@($reloadedGrant | Where-Object { $_.grant_id -eq $createdGrant.grant_id -and [decimal]$_.exempt_grant_amount -eq [decimal]1200 }).Count -eq 1) "Grant persisted after GET."
Write-Host "PASS: grant POST / PUT / independent GET."
$otherEmp = @(Request "GET" "/clients/$idB/employment-records")
$otherGrant = @(Request "GET" "/clients/$idB/grants")
Assert (@($otherEmp | Where-Object { $_.employment_record_id -eq $createdEmp.employment_record_id }).Count -eq 0) "Employment leaked to client B."
Assert (@($otherGrant | Where-Object { $_.grant_id -eq $createdGrant.grant_id }).Count -eq 0) "Grant leaked to client B."
Write-Host "PASS: client B lists exclude A employment and grant IDs."
Write-Host "LOCAL SYNTHETIC API SMOKE PASSED. A=$idA B=$idB. Temporary database only."
