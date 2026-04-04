@echo off
setlocal EnableDelayedExpansion

echo ========================================================
echo   POLICE-BOT Setup Script (Windows)
echo ========================================================
echo.

:: ── Python check ─────────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ from https://python.org
    pause & exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% found

:: ── Node.js check ────────────────────────────────────────────────────────────
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install from https://nodejs.org
    pause & exit /b 1
)
for /f "tokens=1" %%v in ('node --version') do set NODEVER=%%v
echo [OK] Node.js %NODEVER% found

:: ── Ollama check / install hint ───────────────────────────────────────────────
where ollama >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARN] Ollama not found.
    echo        Please download and install it from: https://ollama.ai/download
    echo        After installing, run in a new terminal:  ollama pull mistral
    echo.
) else (
    echo [OK] Ollama found
)

:: ── .env setup ────────────────────────────────────────────────────────────────
if not exist .env (
    copy .env.example .env >nul
    echo [OK] Created .env from .env.example  ^(edit it to set your data paths^)
) else (
    echo [OK] .env already exists
)

:: ── Data directories ──────────────────────────────────────────────────────────
if not exist data\chroma_db  mkdir data\chroma_db
if not exist data\case_history mkdir data\case_history
if not exist logs mkdir logs
echo [OK] Data directories ready

:: ── Python virtual environment ────────────────────────────────────────────────
if not exist venv (
    echo.
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat

echo.
echo [INFO] Installing Python dependencies...
pip install --upgrade pip -q
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed. Check requirements.txt and your internet connection.
    pause & exit /b 1
)
echo [OK] Python dependencies installed

:: ── Frontend dependencies ─────────────────────────────────────────────────────
echo.
echo [INFO] Installing frontend dependencies...
cd frontend
call npm install --legacy-peer-deps
if errorlevel 1 (
    echo [ERROR] npm install failed.
    pause & exit /b 1
)
cd ..
echo [OK] Frontend dependencies installed

echo.
echo ========================================================
echo   Setup complete!
echo ========================================================
echo.
echo  IMPORTANT: Copy your data files before starting:
echo    - chroma_db/  ^>^>  data\chroma_db\
echo    - knowledge_graph.json  ^>^>  data\
echo.
echo  To start the application:
echo.
echo  1. Start Ollama (in a separate terminal):
echo       ollama serve
echo       ollama pull mistral   ^(first time only^)
echo.
echo  2. Start the backend (in this terminal):
echo       venv\Scripts\activate.bat
echo       cd backend
echo       uvicorn main:app --reload --port 8000
echo.
echo  3. Start the frontend (in another terminal):
echo       cd frontend
echo       npm start
echo.
echo  Then open: http://localhost:3000
echo.
pause
