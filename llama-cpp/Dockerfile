FROM ghcr.io/ggml-org/llama.cpp:server

ENV MODEL_PATH=/models/Qwen3.5-4B-Q4_K_M.gguf
ENV LLAMA_PORT=8080
ENV LLAMA_CTX=8192
ENV LLAMA_THREADS=8

# Nota: LLAMA_ARG_REASONING=on se deshabilita porque el modo think de Qwen
# con budget reducido interfiere con el function calling y hace que el modelo
# ignore las instrucciones del sistema. Se usa --jinja para que llama-cpp
# aplique el chat template nativo del modelo (mejor soporte de tools).

EXPOSE 8080

ENTRYPOINT ["/bin/sh", "-c", \
  "/app/llama-server -m ${MODEL_PATH} --port ${LLAMA_PORT} \
   --ctx-size ${LLAMA_CTX} --threads ${LLAMA_THREADS} \
   --jinja \
   --host 0.0.0.0 \"$@\"", "--"]
