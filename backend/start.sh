#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Render / production startup script for POLICE-BOT backend.
#
# 1. Installs Ollama if not already present.
# 2. Starts the Ollama server in the background.
# 3. Waits until the server is ready (up to 120 seconds).
# 4. Pulls the configured model (default: tinyllama) in the background.
# 5. Launches the FastAPI server with uvicorn.
#
# The backend starts even if Ollama is not yet ready — requests made before
# the model is pulled will return a clear error message.
# ---------------------------------------------------------------------------

OLLAMA_MODEL="${OLLAMA_MODEL:-tinyllama}"

# ── 1. Install Ollama ────────────────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
    echo "[start.sh] Ollama not found — installing..."
    if curl -fsSL https://ollama.ai/install.sh | sh; then
        echo "[start.sh] Ollama installed."
    else
        echo "[start.sh] WARNING: Ollama installation failed — LLM features will be unavailable."
    fi
else
    echo "[start.sh] Ollama already installed: $(ollama --version 2>/dev/null || echo 'unknown version')"
fi

# ── 2. Start Ollama server in background ────────────────────────────────────
if command -v ollama &>/dev/null; then
    echo "[start.sh] Starting Ollama server..."
    ollama serve &
    OLLAMA_PID=$!

    # ── 3. Wait for Ollama to be ready (up to 120 seconds) ──────────────────
    echo "[start.sh] Waiting for Ollama to be ready (up to 120 s)..."
    READY=0
    for i in $(seq 1 60); do
        if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
            echo "[start.sh] Ollama is ready (attempt ${i})."
            READY=1
            break
        fi
        sleep 2
    done

    if [ "$READY" -eq 0 ]; then
        echo "[start.sh] WARNING: Ollama did not become ready in 120 seconds — continuing anyway."
    else
        # ── 4. Pull model in the background so the API can start sooner ─────
        echo "[start.sh] Pulling model '${OLLAMA_MODEL}' in the background..."
        (
            if ollama pull "${OLLAMA_MODEL}"; then
                echo "[start.sh] Model '${OLLAMA_MODEL}' pulled successfully."
            else
                echo "[start.sh] WARNING: Could not pull model '${OLLAMA_MODEL}'. Check disk space and model name."
            fi
        ) &
    fi
else
    echo "[start.sh] WARNING: Ollama is not installed — LLM features will be unavailable."
fi

# ── 5. Start the FastAPI server ──────────────────────────────────────────────
echo "[start.sh] Starting POLICE-BOT API on port ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
