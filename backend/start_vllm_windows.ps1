$ErrorActionPreference = "Stop"

function Convert-ToWslPath {
    param([string]$WindowsPath)

    $fullPath = [System.IO.Path]::GetFullPath($WindowsPath)
    $drive = $fullPath.Substring(0, 1).ToLowerInvariant()
    $rest = $fullPath.Substring(2).Replace("\", "/")
    return "/mnt/$drive$rest"
}

$backendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$wslScript = "$(Convert-ToWslPath $backendDir)/start_vllm_servers.sh"
$escapedScript = $wslScript.Replace("'", "'\''")

Write-Host "Starting vLLM chat and embedding servers through WSL..."
Write-Host "Chat:      http://127.0.0.1:8001/v1/models"
Write-Host "Embedding: http://127.0.0.1:8002/v1/models"
Write-Host "Keep this terminal open while using EvidenceDocs."
Write-Host ""

wsl -d Ubuntu -- bash -lc "bash '$escapedScript'"
