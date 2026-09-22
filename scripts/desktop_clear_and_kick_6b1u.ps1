# CrossBind Desktop: cancel stuck queue except 6B1U, pull, restart uvicorn, kick 6B1U
# Run from elevated-enough PowerShell on Alexander's PC (Cursor agent Shell machineId).
$ErrorActionPreference = "Stop"
$Root = "C:\Users\alexc\Desktop\CrossBind"
$Keep = "20260922_052956_37480faf"
$CancelIds = @(
  "20260922_042613_e229db88",
  "20260922_042552_d065f351",
  "20260922_042452_f260ac40",
  "20260922_042127_42c83f62",
  "20260922_042106_16657bf8"
)
$Note = "Cancelled — cleared queue for 6B1U job"
$Base = "http://127.0.0.1:8787"

Set-Location $Root

function Set-JobCancelled([string]$JobId) {
  $rj = Join-Path $Root "data\jobs\$JobId\result.json"
  if (-not (Test-Path $rj)) { Write-Host "missing $JobId"; return }
  $meta = Get-Content $rj -Raw | ConvertFrom-Json
  $meta.status = "cancelled"
  $meta.error = $Note
  ($meta | ConvertTo-Json -Depth 20) | Set-Content -Path $rj -Encoding UTF8
  $cancelFlag = Join-Path $Root "data\jobs\$JobId\CANCEL"
  Set-Content -Path $cancelFlag -Value "cancel" -Encoding UTF8
  Write-Host "cancelled $JobId"
}

foreach ($id in $CancelIds) { Set-JobCancelled $id }

# Also cancel any other queued jobs except Keep
$jobsDir = Join-Path $Root "data\jobs"
Get-ChildItem $jobsDir -Directory | ForEach-Object {
  if ($_.Name -eq $Keep) { return }
  $rj = Join-Path $_.FullName "result.json"
  if (-not (Test-Path $rj)) { return }
  $meta = Get-Content $rj -Raw | ConvertFrom-Json
  if ($meta.status -eq "queued" -or $meta.status -eq "running") {
    Set-JobCancelled $_.Name
  }
}

git pull --ff-only origin main

# Restart uvicorn carefully — never assign to $PID
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
Start-Sleep -Seconds 2

# Kick 6B1U
try {
  Invoke-RestMethod -Method Post -Uri "$Base/api/job/$Keep/restart" | ConvertTo-Json -Compress
} catch {
  Write-Host "restart API failed, trying manual stamp+note: $_"
}
Start-Sleep -Seconds 2
$st = Invoke-RestMethod -Uri "$Base/api/job/$Keep"
Write-Host "6B1U status=$($st.status) log_bytes=$(( $st.log | Measure-Object -Character).Characters)"
