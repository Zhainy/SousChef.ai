FROM ghcr.io/ggml-org/llama.cpp:server

# Modelo por defecto: Qwen 2.5-1.5B-Instruct Q4_K_M
# (~1 GB, 15-20 t/s en ARM Neoverse-N1, excelente function calling y español)
ENV MODEL_PATH=/models/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf
ENV LLAMA_PORT=8080
ENV LLAMA_CTX=2048
ENV LLAMA_THREADS=2

# Nota: LLAMA_ARG_REASONING=on se deshabilita porque interfiere con function calling.
# Se usa --jinja para aplicar el template nativo y --cache-reuse para acelerar prompts.

EXPOSE 8080

ENTRYPOINT ["/bin/sh", "-c", \
  "/app/llama-server -m ${MODEL_PATH} --port ${LLAMA_PORT} \
   --ctx-size ${LLAMA_CTX} --threads ${LLAMA_THREADS} \
   --cache-reuse 256 --batch-size 512 --ubatch-size 256 \
   --jinja \
   --host 0.0.0.0 \"$@\"", "--"]
