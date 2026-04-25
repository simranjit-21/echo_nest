$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $projectRoot "server.pid"

if (-not (Test-Path $pidFile)) {
    Write-Host "No server.pid file found."
    exit 0
}

$serverPid = Get-Content $pidFile | Select-Object -First 1
if (-not $serverPid) {
    Remove-Item $pidFile -ErrorAction SilentlyContinue
    Write-Host "server.pid was empty."
    exit 0
}

$process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
if ($process) {
    Stop-Process -Id $serverPid -Force
    Write-Host "Stopped Echo_Nest process $serverPid."
} else {
    Write-Host "Process $serverPid was not running."
}

Remove-Item $pidFile -ErrorAction SilentlyContinue
