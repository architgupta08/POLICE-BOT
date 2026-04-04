#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Render / production startup script for POLICE-BOT backend.
#
# 1. Installs Ollama if not already present.
# 2. Starts the Ollama server in the background.
# 3. Waits until the server is ready.
# 4. Pulls the configured model (default: mistral) if it is not yet cached.
# 5. Launches the FastAPI server with uvicorn.
# ---------------------------------------------------------------------------
set -e

OLLAMA_MODEL="${OLLAMA_MODEL:-mistral}"

# ── 1. Install Ollama ────────────────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
    echo "[start.sh] Ollama not found — installing..."
    curl -fsSL https://ollama.ai/install.sh | sh
    echo "[start.sh] Ollama installed."
else
    echo "[start.sh] Ollama already installed: $(ollama --version 2>/dev/null || echo 'unknown version')"
fi

# ── 2. Start Ollama server in background ────────────────────────────────────
echo "[start.sh] Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# ── 3. Wait for Ollama to be ready (up to 60 seconds) ───────────────────────
echo "[start.sh] Waiting for Ollama to be ready..."
READY=0
for i in $(seq 1 30); do
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "[start.sh] Ollama is ready."
        READY=1
        break
    fi
    sleep 2
done

if [ "$READY" -eq 0 ]; then
    echo "[start.sh] WARNING: Ollama did not become ready in 60 seconds — continuing anyway."
fi

# ── 4. Pull model if not already cached ─────────────────────────────────────
echo "[start.sh] Pulling model '${OLLAMA_MODEL}' (skipped if already cached)..."
ollama pull "${OLLAMA_MODEL}"
echo "[start.sh] Model '${OLLAMA_MODEL}' is ready."

# ── 5. Start the FastAPI server ──────────────────────────────────────────────
echo "[start.sh] Starting POLICE-BOT API on port ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
