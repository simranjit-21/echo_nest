$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "Virtual environment Python not found at $python"
}

Set-Location $projectRoot

if (-not $env:SECRET_KEY) {
    $env:SECRET_KEY = "dev-secret"
}

if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "sqlite:///echo_nest.db"
}

Write-Host "Starting Echo_Nest at http://127.0.0.1:5000"
& $python run.py
