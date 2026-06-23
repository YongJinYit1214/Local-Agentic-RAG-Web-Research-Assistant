$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$root\backend\start_backend.ps1`""
Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$root\frontend\start_frontend.ps1`""

Write-Host "Frontend: http://localhost:3000"
Write-Host "Backend:  http://localhost:8000/health"
