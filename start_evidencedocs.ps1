$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Start-EvidenceDocsWindow {
    param(
        [string]$Title,
        [string]$Command
    )

    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
    & cmd.exe /c start "`"$Title`"" powershell.exe -NoExit -NoProfile -ExecutionPolicy Bypass -EncodedCommand $encoded
}

Start-EvidenceDocsWindow "EvidenceDocs vLLM" "& '$root\backend\start_vllm_windows.ps1'"
Start-Sleep -Seconds 10
Start-EvidenceDocsWindow "EvidenceDocs Backend" "& '$root\backend\start_backend.ps1'"
Start-EvidenceDocsWindow "EvidenceDocs Frontend" "& '$root\frontend\start_frontend.ps1'"

Write-Host "vLLM:     http://localhost:8011/health/vllm"
Write-Host "Frontend: http://localhost:3000"
Write-Host "Backend:  http://localhost:8011/health"
