#!/usr/bin/env bash
set -euo pipefail

source "$HOME/vllm-env/bin/activate"

LOG_DIR="/mnt/c/Users/jinyi/OneDrive/Desktop/stock research/backend/data"
mkdir -p "$LOG_DIR"

if [[ -f "$LOG_DIR/vllm_embed.pid" ]]; then
  kill "$(cat "$LOG_DIR/vllm_embed.pid")" 2>/dev/null || true
fi

nohup vllm serve BAAI/bge-small-en-v1.5 \
  --host 127.0.0.1 \
  --port 8002 \
  --api-key token-local \
  --task embed \
  --gpu-memory-utilization 0.20 \
  --max-model-len 512 \
  > "$LOG_DIR/vllm_embed.log" 2>&1 &
echo "$!" > "$LOG_DIR/vllm_embed.pid"
EMBED_PID="$(cat "$LOG_DIR/vllm_embed.pid")"

echo "Started vLLM embedding server."
echo "Keep this WSL terminal open. Press Ctrl+C to stop the server."

trap 'kill "$EMBED_PID" 2>/dev/null || true; exit 0' INT TERM
wait "$EMBED_PID"
