#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="/mnt/c/Users/jinyi/OneDrive/Desktop/stock research/backend/data"

for pid_file in "$LOG_DIR/vllm_chat.pid" "$LOG_DIR/vllm_embed.pid"; do
  if [[ -f "$pid_file" ]]; then
    kill "$(cat "$pid_file")" 2>/dev/null || true
  fi
done

pkill -f "vllm serve" 2>/dev/null || true
pkill -f "multiprocessing.spawn" 2>/dev/null || true
sleep 2
pkill -9 -f "vllm serve" 2>/dev/null || true
pkill -9 -f "multiprocessing.spawn" 2>/dev/null || true
rm -f "$LOG_DIR/vllm_chat.pid" "$LOG_DIR/vllm_embed.pid"

echo "Stopped vLLM servers."
