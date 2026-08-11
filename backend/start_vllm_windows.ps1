$ErrorActionPreference = "Stop"

$chatCommand = @'
source "$HOME/vllm-env/bin/activate"
vllm serve Qwen/Qwen3-4B-Instruct-2507-FP8 \
  --host 127.0.0.1 \
  --port 8001 \
  --api-key token-local \
  --task generate \
  --gpu-memory-utilization 0.95 \
  --max-model-len 1024 \
  --max-num-seqs 1 \
  --enforce-eager
'@

$embedCommand = @'
source "$HOME/vllm-env/bin/activate"
vllm serve BAAI/bge-small-en-v1.5 \
  --host 127.0.0.1 \
  --port 8002 \
  --api-key token-local \
  --task embed \
  --gpu-memory-utilization 0.20 \
  --max-model-len 512
'@

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-Command",
    "wsl -d Ubuntu -- bash -lc '$chatCommand'"
)

Start-Sleep -Seconds 8

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-Command",
    "wsl -d Ubuntu -- bash -lc '$embedCommand'"
)

Write-Host "Opened persistent vLLM windows:"
Write-Host "  Chat:      http://127.0.0.1:8001/v1/models"
Write-Host "  Embedding: http://127.0.0.1:8002/v1/models"
Write-Host "Keep those windows open while using EvidenceDocs."
