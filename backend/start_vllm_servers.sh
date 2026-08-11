#!/usr/bin/env bash
set -euo pipefail

source "$HOME/vllm-env/bin/activate"

LOG_DIR="/mnt/c/Users/jinyi/OneDrive/Desktop/stock research/backend/data"
mkdir -p "$LOG_DIR"

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

echo "Started vLLM chat and embedding servers."
echo "Keep this WSL terminal open. Press Ctrl+C to stop both servers."

trap 'kill "$CHAT_PID" "$EMBED_PID" 2>/dev/null || true; exit 0' INT TERM
wait "$CHAT_PID" "$EMBED_PID"
