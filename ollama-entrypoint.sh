#!/bin/sh
# Ollama entrypoint: start server, install CA certs, pull model, then wait.
# This ensures the model is always available on fresh deployments.

set -e

MODEL="${OLLAMA_MODEL:-llama3.2:3b}"

echo "[ollama-entrypoint] Updating CA certificates..."
update-ca-certificates 2>/dev/null || true

echo "[ollama-entrypoint] Starting Ollama server in background..."
ollama serve &
SERVER_PID=$!

# Wait for the server to be ready
echo "[ollama-entrypoint] Waiting for Ollama server to be ready..."
for i in $(seq 1 30); do
  if ollama list >/dev/null 2>&1; then
    echo "[ollama-entrypoint] Ollama server is ready."
    break
  fi
  sleep 1
done

# Pull model if not already present
if ollama list | grep -q "$MODEL"; then
  echo "[ollama-entrypoint] Model '$MODEL' already available."
else
  echo "[ollama-entrypoint] Pulling model '$MODEL' (this may take a few minutes on first run)..."
  ollama pull "$MODEL"
  echo "[ollama-entrypoint] Model '$MODEL' pulled successfully."
fi

echo "[ollama-entrypoint] Ready. Model '$MODEL' is available."

# Keep the server running in the foreground
wait $SERVER_PID
