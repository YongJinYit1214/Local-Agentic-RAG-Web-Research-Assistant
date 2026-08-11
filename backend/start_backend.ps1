$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Stop-PortOwner {
    param([int]$Port)

    $owners = netstat -ano |
        Select-String ":$Port\s" |
        ForEach-Object { ($_ -split "\s+")[-1] } |
        Where-Object { $_ -match "^\d+$" -and [int]$_ -ne 0 -and [int]$_ -ne $PID } |
        Select-Object -Unique

    foreach ($owner in $owners) {
        Write-Host "Stopping existing process $owner on port $Port..."
        Stop-Process -Id ([int]$owner) -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
}

.\.venv\Scripts\python -m pip install -r requirements.txt

try {
    $headers = @{ Authorization = "Bearer token-local" }
    Invoke-RestMethod "http://127.0.0.1:8001/v1/models" -Headers $headers | Out-Null
    Invoke-RestMethod "http://127.0.0.1:8002/v1/models" -Headers $headers | Out-Null
}
catch {
    Write-Host ""
    Write-Host "vLLM is not reachable at http://127.0.0.1:8001/v1 or http://127.0.0.1:8002/v1."
    Write-Host "Start the chat and embedding servers, for example:"
    Write-Host "  vllm serve Qwen/Qwen3-4B-Instruct-2507-FP8 --host 127.0.0.1 --port 8001 --api-key token-local --task generate"
    Write-Host "  vllm serve BAAI/bge-small-en-v1.5 --host 127.0.0.1 --port 8002 --api-key token-local --task embed"
    Write-Host ""
}

Stop-PortOwner 8011
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8011
