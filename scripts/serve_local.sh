#!/usr/bin/env bash
# Levanta el LLM local (llama.cpp) con el modelo Qwen2.5-1.5B-Instruct.
# Esperado en http://127.0.0.1:8080/v1 (ver backend/.env → LOCAL_LLM_BASE_URL).
set -euo pipefail

MODEL="${LLAMA_MODEL:-models/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf}"
HOST="${LLAMA_HOST:-0.0.0.0}"
PORT="${LLAMA_PORT:-8080}"

if [ ! -f "$MODEL" ] && [ -f "$HOME/models/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf" ]; then
    MODEL="$HOME/models/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
fi

if [ ! -f "$MODEL" ]; then
    echo "Modelo no encontrado: $MODEL"
    echo "Descarga un GGUF (p. ej. Qwen/Qwen2.5-1.5B-Instruct-GGUF Q4_K_M) y colócalo en models/ o ajusta LLAMA_MODEL."
    exit 1
fi

exec llama-server -m "$MODEL" -c 8192 --host "$HOST" --port "$PORT" -ngl 99 "$@"
