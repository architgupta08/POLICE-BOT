#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Render / production startup script for POLICE-BOT backend.
#
# Starts the FastAPI server with uvicorn.
# The LLM backend is configured via the LLM_BACKEND environment variable:
#   - "groq"        (default) — Groq Cloud API, requires GROQ_API_KEY
#   - "huggingface" — Hugging Face Inference API, requires HF_API_TOKEN
#   - "ollama"      — Local Ollama server (for local development only)
# ---------------------------------------------------------------------------

# Change to the backend directory so Python imports resolve correctly
cd "$(dirname "$0")"

echo "[start.sh] Starting POLICE-BOT API on port ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
