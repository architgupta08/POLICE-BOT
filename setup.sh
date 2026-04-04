#!/usr/bin/env bash
set -e

echo "========================================================"
echo "   POLICE-BOT Setup Script (Linux / macOS)"
echo "========================================================"
echo

# ── Python check ──────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python 3 not found. Install it first:"
    echo "        Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "        macOS:         brew install python@3.11"
    exit 1
fi
PYVER=$(python3 --version 2>&1)
echo "[OK] $PYVER"

# ── Node.js check ─────────────────────────────────────────────────────────────
if ! command -v node &>/dev/null; then
    echo "[ERROR] Node.js not found. Install it from https://nodejs.org or via nvm."
    exit 1
fi
echo "[OK] Node.js $(node --version)"

# ── Ollama check / hint ───────────────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
    echo
    echo "[WARN] Ollama not found. Install it with:"
    echo "       curl -fsSL https://ollama.ai/install.sh | sh"
    echo "       Then run:  ollama pull mistral"
    echo
else
    echo "[OK] Ollama $(ollama --version 2>/dev/null || echo 'found')"
fi

# ── .env setup ────────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[OK] Created .env from .env.example  (edit it to set your data paths)"
else
    echo "[OK] .env already exists"
fi

# ── Data directories ──────────────────────────────────────────────────────────
mkdir -p data/chroma_db data/case_history logs
echo "[OK] Data directories ready"

# ── Python virtual environment ────────────────────────────────────────────────
if [ ! -d venv ]; then
    echo
    echo "[INFO] Creating Python virtual environment..."
    python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate

echo
echo "[INFO] Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt

echo "[OK] Python dependencies installed"

# ── Frontend dependencies ─────────────────────────────────────────────────────
echo
echo "[INFO] Installing frontend dependencies..."
cd frontend
npm install --legacy-peer-deps
cd ..
echo "[OK] Frontend dependencies installed"

echo
echo "========================================================"
echo "   Setup complete!"
echo "========================================================"
echo
echo "  IMPORTANT: Copy your data files before starting:"
echo "    - chroma_db/            >>  data/chroma_db/"
echo "    - knowledge_graph.json  >>  data/"
echo
echo "  To start the application:"
echo
echo "  1. Start Ollama (separate terminal):"
echo "       ollama serve"
echo "       ollama pull mistral   # first time only"
echo
echo "  2. Start the backend:"
echo "       source venv/bin/activate"
echo "       cd backend"
echo "       uvicorn main:app --reload --port 8000"
echo
echo "  3. Start the frontend (separate terminal):"
echo "       cd frontend"
echo "       npm start"
echo
echo "  Then open: http://localhost:3000"
echo
