$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
}

.\.venv\Scripts\python -m pip install -r requirements.txt

try {
    Invoke-RestMethod "http://127.0.0.1:8001/v1/models" | Out-Null
    Invoke-RestMethod "http://127.0.0.1:8002/v1/models" | Out-Null
}
catch {
    Write-Host ""
    Write-Host "vLLM is not reachable at http://127.0.0.1:8001/v1 or http://127.0.0.1:8002/v1."
    Write-Host "Start the chat and embedding servers, for example:"
    Write-Host "  vllm serve Qwen/Qwen3-4B-Instruct-2507-FP8 --host 127.0.0.1 --port 8001 --api-key token-local --task generate"
    Write-Host "  vllm serve BAAI/bge-small-en-v1.5 --host 127.0.0.1 --port 8002 --api-key token-local --task embed"
    Write-Host ""
}

.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
