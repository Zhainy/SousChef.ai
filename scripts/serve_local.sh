#!/usr/bin/env bash
# Levanta el LLM local (llama.cpp) con el modelo Qwen3.5-4B.
# Esperado en http://127.0.0.1:8080/v1 (ver backend/.env → LOCAL_LLM_BASE_URL).
set -euo pipefail

MODEL="${LLAMA_MODEL:-$HOME/models/Qwen3.5-4B-Q4_K_M.gguf}"
HOST="${LLAMA_HOST:-0.0.0.0}"
PORT="${LLAMA_PORT:-8080}"
BUDGET="${LLAMA_REASONING_BUDGET:-128}"

if [ ! -f "$MODEL" ]; then
    echo "Modelo no encontrado: $MODEL"
    echo "Descarga un GGUF (p. ej. Qwen/Qwen3.5-4B-GGUF Q4_K_M) y ajusta LLAMA_MODEL."
    exit 1
fi

# Qwen3.5 es un modelo de razonamiento: con --reasoning off deja de emitir el
# bloque ```json que el backend espera (ver agent/llm.py SYSTEM_INSTRUCTION).
exec llama-server -m "$MODEL" -c 8192 --host "$HOST" --port "$PORT" -ngl 99 \
    --reasoning on --reasoning-budget "$BUDGET" "$@"
