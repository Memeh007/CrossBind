# ddOS Desktop: pull ligand-aware pockets (v1.3.1), restart uvicorn, hit /api/health
$ErrorActionPreference = "Stop"
$Root = "C:\Users\alexc\Desktop\CrossBind"
$Base = "http://127.0.0.1:8787"

Set-Location $Root
git fetch origin
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
$h = Invoke-RestMethod -Uri "$Base/api/health"
Write-Host ("health app={0} version={1} p2rank_ok={2} vina_ok={3}" -f $h.app, $h.version, $h.p2rank_ok, $h.vina_ok)
