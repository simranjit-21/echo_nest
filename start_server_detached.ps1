$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $projectRoot "server.pid"

Set-Location $projectRoot

if (Test-Path $pidFile) {
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

$process = Start-Process -FilePath "powershell" `
    -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $projectRoot "start_server.ps1") `
    -WorkingDirectory $projectRoot `
    -PassThru

$process.Id | Set-Content -Path $pidFile
$hostAddress = if ($env:HOST) { $env:HOST } else { "127.0.0.1" }
$portNumber = if ($env:PORT) { $env:PORT } else { "5000" }
Write-Host "Echo_Nest server window launched for http://$hostAddress`:$portNumber (PID $($process.Id))"
