#!/usr/bin/env bash
set -euo pipefail

source "$HOME/vllm-env/bin/activate"

LOG_DIR="/mnt/c/Users/jinyi/OneDrive/Desktop/stock research/backend/data"
mkdir -p "$LOG_DIR"

if [[ -f "$LOG_DIR/vllm_chat.pid" ]]; then
  kill "$(cat "$LOG_DIR/vllm_chat.pid")" 2>/dev/null || true
fi

nohup vllm serve Qwen/Qwen3-4B-Instruct-2507-FP8 \
  --host 127.0.0.1 \
  --port 8001 \
  --api-key token-local \
  --task generate \
  --gpu-memory-utilization 0.95 \
  --max-model-len 4096 \
  --max-num-seqs 1 \
  --enforce-eager \
  > "$LOG_DIR/vllm_chat.log" 2>&1 &
echo "$!" > "$LOG_DIR/vllm_chat.pid"
CHAT_PID="$(cat "$LOG_DIR/vllm_chat.pid")"

echo "Started vLLM chat server."
echo "Keep this WSL terminal open. Press Ctrl+C to stop the server."

trap 'kill "$CHAT_PID" 2>/dev/null || true; exit 0' INT TERM
wait "$CHAT_PID"
