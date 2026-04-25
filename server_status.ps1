$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $projectRoot "server.pid"

if (-not (Test-Path $pidFile)) {
    Write-Host "Echo_Nest is not tracked as running."
    exit 0
}

$serverPid = Get-Content $pidFile | Select-Object -First 1
$process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
if ($process) {
    Write-Host "Echo_Nest is running with PID $serverPid."
} else {
    Write-Host "Echo_Nest is not running, but server.pid exists."
}
