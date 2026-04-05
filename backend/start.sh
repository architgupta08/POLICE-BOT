#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Render / production startup script for POLICE-BOT backend.
#
# Starts the FastAPI server with uvicorn.
# The backend uses Ollama exclusively for LLM inference.
# Configure OLLAMA_BASE_URL and OLLAMA_MODEL via environment variables.
# ---------------------------------------------------------------------------

# Change to the backend directory so Python imports resolve correctly
cd "$(dirname "$0")"

echo "[start.sh] Starting POLICE-BOT API on port ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
