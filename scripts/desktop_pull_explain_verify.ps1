# CrossBind Desktop: pull main, restart uvicorn, rebuild explanation for 6B1U job, verify page
$ErrorActionPreference = "Stop"
$Root = "C:\Users\alexc\Desktop\CrossBind"
$Keep = "20260922_052956_37480faf"
$Base = "http://127.0.0.1:8787"

Set-Location $Root
git pull --ff-only origin main

$listen = Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue |
  Select-Object -First 1
if ($listen) {
  $listenPid = $listen.OwningProcess
  Write-Host "Stopping uvicorn pid=$listenPid"
  Stop-Process -Id $listenPid -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 1
}

$py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$env:PYTHONPATH = $Root
Start-Process -FilePath $py -ArgumentList "-m","uvicorn","crossbind.app:app","--host","127.0.0.1","--port","8787" -WorkingDirectory $Root -WindowStyle Hidden
Start-Sleep -Seconds 3

# Rebuild explanation from current result.json (keeps Desktop's real ASP88 contacts)
try {
  $ex = Invoke-RestMethod -Method Post -Uri "$Base/api/job/$Keep/explain"
  Write-Host "explain ok chars=$($ex.explanation.Length)"
} catch {
  Write-Host "explain failed: $_"
}

$page = Invoke-WebRequest -Uri "$Base/job/$Keep" -UseBasicParsing
Write-Host "job page status=$($page.StatusCode) len=$($page.Content.Length)"
if ($page.Content -match "ASP88") { Write-Host "OK: ASP88 visible on job page" } else { Write-Host "WARN: ASP88 not found in HTML" }
if ($page.Content -match "Evidence summary") { Write-Host "OK: Evidence summary box present" } else { Write-Host "WARN: Evidence summary missing" }
if ($page.Content -match "Residue binding proof") { Write-Host "OK: Residue binding proof heading" } else { Write-Host "WARN: proof heading missing" }

$api = Invoke-RestMethod -Uri "$Base/api/job/$Keep"
Write-Host "api status=$($api.status) contacts=$($api.interactions.contact_residues -join ',')"
