FROM ghcr.io/ggml-org/llama.cpp:server

ENV MODEL_PATH=/models/Qwen3.5-4B-Q4_K_M.gguf
ENV LLAMA_PORT=8080
ENV LLAMA_CTX=8192
ENV LLAMA_THREADS=8
ENV LLAMA_ARG_REASONING=on
ENV LLAMA_ARG_THINK_BUDGET=128

EXPOSE 8080

ENTRYPOINT ["/bin/sh", "-c", \
  "/app/llama-server -m ${MODEL_PATH} --port ${LLAMA_PORT} \
   --ctx-size ${LLAMA_CTX} --threads ${LLAMA_THREADS} \
   --host 0.0.0.0 \"$@\"", "--"]
