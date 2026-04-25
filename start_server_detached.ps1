$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pidFile = Join-Path $projectRoot "server.pid"
$stdoutFile = Join-Path $projectRoot "server.out.log"
$stderrFile = Join-Path $projectRoot "server.err.log"

if (-not (Test-Path $python)) {
    Write-Error "Virtual environment Python not found at $python"
}

Set-Location $projectRoot

if (Test-Path $pidFile) {
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

$process = Start-Process -FilePath $python `
    -ArgumentList "run.py" `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $stdoutFile `
    -RedirectStandardError $stderrFile `
    -PassThru

$process.Id | Set-Content -Path $pidFile
Write-Host "Echo_Nest started in the background on http://127.0.0.1:5000 (PID $($process.Id))"
