$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
}

.\.venv\Scripts\python -m pip install -r requirements.txt

try {
    Invoke-RestMethod "http://127.0.0.1:11434/api/tags" | Out-Null
}
catch {
    Write-Host ""
    Write-Host "Ollama is not reachable at http://127.0.0.1:11434."
    Write-Host "Install/start Ollama, then run:"
    Write-Host "  ollama pull llama3.1:8b"
    Write-Host "  ollama pull nomic-embed-text"
    Write-Host ""
}

.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
