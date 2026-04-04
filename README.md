# 🚔 POLICE-BOT — NDPS Legal Guidance System

A fully-functional AI-powered web application that provides **real-time legal guidance** to police officers on the **Narcotic Drugs and Psychotropic Substances (NDPS) Act** of India.  The system supports both local (Ollama) and cloud (Hugging Face) LLM backends, JWT-based user authentication, and one-click deployment to **Render + Vercel**.

---

## ✨ Features

| Feature | Description |
|---|---|
| 💬 **Conversational Chat** | Ask questions in plain language and get structured, legal answers |
| 📚 **RAG Pipeline** | Retrieves the most relevant NDPS documents from your knowledge base before answering |
| 🧠 **Dual LLM Backend** | Local Ollama (offline) **or** Hugging Face Inference API (cloud) |
| 🔐 **JWT Authentication** | User signup/login with bcrypt password hashing and JWT sessions |
| 📋 **Case History** | All sessions are saved automatically; switch between them from the sidebar |
| 📄 **PDF Export** | Export any conversation as a formatted PDF for official records |
| 🔗 **Source Citations** | Every answer shows which knowledge-base document was used |
| ☁️ **Cloud Deployable** | Ready to deploy on Render (backend) + Vercel (frontend) |

---

## 🗂️ Project Structure

```
POLICE-BOT/
├── backend/
│   ├── main.py            # FastAPI application + API routes
│   ├── auth.py            # JWT utilities + FastAPI dependency
│   ├── database.py        # SQLite user database
│   ├── hf_handler.py      # Hugging Face Inference API LLM handler
│   ├── llm_handler.py     # Ollama / Mistral 7B handler (local)
│   ├── rag_pipeline.py    # RAG logic: Chroma DB + knowledge-graph retrieval
│   ├── config.py          # All configuration (reads from .env)
│   └── utils.py           # PDF export, session helpers, logging
├── frontend/
│   ├── src/
│   │   ├── App.jsx                      # Root component + routing
│   │   ├── context/
│   │   │   └── AuthContext.jsx          # Auth state (login/signup/logout)
│   │   ├── components/
│   │   │   ├── LoginPage.jsx            # Login form
│   │   │   ├── SignupPage.jsx           # Signup form
│   │   │   ├── ChatWindow.jsx           # Main chat UI
│   │   │   ├── ChatHistory.jsx          # Session sidebar
│   │   │   ├── SourceCitations.jsx      # Source tags below bot answers
│   │   │   └── ExportPDF.jsx            # PDF export button
│   │   ├── services/
│   │   │   └── api.js                   # Axios wrapper (with Auth header)
│   │   └── styles/main.css
│   ├── vercel.json                      # Vercel deployment config
│   └── package.json
├── data/
│   ├── chroma_db/          # ← Copy your Chroma DB here
│   └── knowledge_graph.json # ← Copy your knowledge graph here
├── requirements.txt
├── render.yaml             # Render deployment config
├── .env.example
└── README.md
```

---

## 🚀 Quick Start (Local)

### Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.10 + | https://python.org |
| Node.js | 18 + | https://nodejs.org |
| Ollama | latest (optional) | https://ollama.ai/download |

### Step 1 — Copy your data files

```bash
# Linux / macOS
cp -r "/path/to/chroma_db" data/
cp "/path/to/knowledge_graph.json" data/

# Windows
xcopy /E /I "D:\POLICE BOT\chroma_db" "data\chroma_db"
copy "D:\POLICE BOT\knowledge_graph.json" "data\knowledge_graph.json"
```

### Step 2 — Configure environment

```bash
cp .env.example .env
# Edit .env — set LLM_BACKEND, JWT_SECRET_KEY, and optionally HF_API_TOKEN
```

### Step 3 — Run setup

**Windows:** `setup.bat`  
**Linux / macOS:** `chmod +x setup.sh && ./setup.sh`

### Step 4 — Start services

**Terminal 1 — Backend:**
```bash
source venv/bin/activate   # Windows: venv\Scripts\activate
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm start
```

Open **http://localhost:3000** — sign up for an account to start chatting. 🎉

> **Dev mode:** `DEV_MODE=true` (the default) makes authentication optional so you can test without signing up.

---

## ☁️ Cloud Deployment (Render + Vercel)

### Backend → Render

1. Create a free account at https://render.com and link your GitHub repo.
2. Render will auto-detect `render.yaml` and create the service.
3. In the Render dashboard → **Environment** tab, add:
   - `HF_API_TOKEN` — your Hugging Face token (https://huggingface.co/settings/tokens)
4. Your backend URL will be: `https://police-bot-backend.onrender.com`

### Frontend → Vercel

1. Create a free account at https://vercel.com and import the GitHub repo.
2. Set the **Root Directory** to `frontend`.
3. Add environment variable in the Vercel dashboard:
   - `REACT_APP_API_URL` → `https://police-bot-backend.onrender.com`
4. Your frontend URL will be: `https://police-bot.vercel.app`

### After both are deployed

Update `render.yaml` → `CORS_ORIGINS` to your Vercel URL, then redeploy the backend.

---

## 🔌 API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/health` | No | Server + LLM + RAG status |
| POST | `/auth/signup` | No | Register a new user, returns JWT |
| POST | `/auth/login` | No | Login, returns JWT |
| POST | `/auth/logout` | No | Logout (client clears token) |
| GET | `/auth/me` | JWT | Current user profile |
| POST | `/api/chat` | JWT* | Send a message, get an answer |
| GET | `/api/sessions` | JWT* | List saved chat sessions |
| GET | `/api/sessions/{id}` | JWT* | Full message history |
| DELETE | `/api/sessions/{id}` | JWT* | Delete a session |
| GET | `/api/sessions/{id}/export/pdf` | JWT* | Download session as PDF |

*JWT required unless `DEV_MODE=true`.

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `LLM_BACKEND` | `ollama` | `ollama` (local) or `huggingface` (cloud) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `mistral` | Ollama model name |
| `HF_API_TOKEN` | *(empty)* | Hugging Face API token (cloud) |
| `HF_MODEL` | `mistralai/Mistral-7B-Instruct-v0.2` | HF model ID |
| `JWT_SECRET_KEY` | auto-generated | Secret for signing JWT tokens |
| `JWT_EXPIRE_MINUTES` | `60` | Token expiry in minutes |
| `DEV_MODE` | `true` | If `true`, auth is optional (local dev only) |
| `DATABASE_PATH` | `./data/police_bot.db` | SQLite database file |
| `CHROMA_DB_PATH` | `./data/chroma_db` | Path to Chroma DB folder |
| `KNOWLEDGE_GRAPH_PATH` | `./data/knowledge_graph.json` | Path to knowledge graph JSON |
| `CASE_HISTORY_DIR` | `./data/case_history` | Where session JSON files are stored |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins (comma-separated) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## 🔧 Troubleshooting

### "Ollama server is not running"
Start it: `ollama serve`

### "HF_API_TOKEN is not set"
Add your Hugging Face token to `.env` or to Render's environment variables.

### Backend shows "0 documents in Chroma DB"
- Make sure you copied the `chroma_db` folder correctly.
- Check `CHROMA_DB_PATH` in `.env` — use the full absolute path if needed.

### Frontend can't reach the backend
- Backend must be running on port 8000 locally.
- In production, set `REACT_APP_API_URL` in Vercel to your Render backend URL.
- Check `CORS_ORIGINS` includes your frontend URL.

### Slow responses (8 GB RAM + Ollama)
- Mistral 7B uses ≈5–6 GB RAM; close other applications.
- Or switch to `LLM_BACKEND=huggingface` for serverless inference.

---

## 🏗️ Architecture

```
  Browser (React + Auth)
       │  HTTP + Bearer JWT
       ▼
  FastAPI Backend (port 8000)
       │      │          │
       │      │          ▼
       │      │     Auth (JWT/bcrypt)
       │      │     SQLite users DB
       │      │
       │      ▼
       │   RAG Pipeline
       │     ├── Chroma DB (vector search)
       │     └── Knowledge Graph JSON
       │
       ▼
  LLM Backend (choose one)
       ├── Ollama (local, port 11434)  — offline
       └── Hugging Face API (cloud)   — serverless
```

---

## 📜 License

This project is for official law enforcement use. All NDPS legal content is sourced from publicly available government publications.