# 🚔 POLICE-BOT — NDPS Legal Guidance System

A fully-functional AI-powered web application that provides **real-time legal guidance** to police officers on the **Narcotic Drugs and Psychotropic Substances (NDPS) Act** of India.  The system uses a local LLM (Mistral 7B via Ollama) combined with Retrieval-Augmented Generation (RAG) over your existing **Chroma DB** and **knowledge-graph JSON**.

---

## ✨ Features

| Feature | Description |
|---|---|
| 💬 **Conversational Chat** | Ask questions in plain language and get structured, legal answers |
| 📚 **RAG Pipeline** | Retrieves the most relevant NDPS documents from your knowledge base before answering |
| 🧠 **Local LLM** | Mistral 7B via Ollama — fully offline, no API keys, no data leaves your machine |
| 📋 **Case History** | All sessions are saved automatically; switch between them from the sidebar |
| 📄 **PDF Export** | Export any conversation as a formatted PDF for official records |
| 🔗 **Source Citations** | Every answer shows which knowledge-base document was used |
| ⚡ **8 GB RAM Optimized** | Mistral 7B runs comfortably on machines with Intel UHD Graphics |
| 🔒 **Offline-first** | No internet connection required after initial setup |

---

## 🗂️ Project Structure

```
POLICE-BOT/
├── backend/
│   ├── main.py            # FastAPI application + API routes
│   ├── rag_pipeline.py    # RAG logic: Chroma DB + knowledge-graph retrieval
│   ├── llm_handler.py     # Ollama / Mistral 7B integration
│   ├── config.py          # All configuration (reads from .env)
│   └── utils.py           # PDF export, session helpers, logging
├── frontend/
│   ├── src/
│   │   ├── App.jsx                      # Root component
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx           # Main chat UI
│   │   │   ├── ChatHistory.jsx          # Session sidebar
│   │   │   ├── SourceCitations.jsx      # Source tags below bot answers
│   │   │   └── ExportPDF.jsx            # PDF export button
│   │   ├── services/
│   │   │   └── api.js                   # Axios wrapper for the backend API
│   │   ├── styles/
│   │   │   └── main.css                 # All CSS (variables, layout, dark themes)
│   │   └── index.js
│   ├── public/index.html
│   └── package.json
├── data/
│   ├── chroma_db/          # ← Copy your Chroma DB here
│   └── knowledge_graph.json # ← Copy your knowledge graph here
├── requirements.txt
├── .env.example
├── setup.bat               # One-click setup for Windows
├── setup.sh                # One-click setup for Linux/macOS
└── README.md               # This file
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.10 + | https://python.org |
| Node.js | 18 + | https://nodejs.org |
| Ollama | latest | https://ollama.ai/download |

---

### Step 1 — Copy your data files

```
# Windows
xcopy /E /I "D:\POLICE BOT\chroma_db" "data\chroma_db"
copy "D:\POLICE BOT\knowledge_graph.json" "data\knowledge_graph.json"

# Linux / macOS
cp -r "/path/to/chroma_db" data/
cp "/path/to/knowledge_graph.json" data/
```

> ⚠️ The application will still start without the data files (the RAG pipeline falls back gracefully), but answers will not be grounded in your NDPS knowledge base.

---

### Step 2 — Install Ollama & pull the model

```bash
# macOS / Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows: download installer from https://ollama.ai/download

# Pull the Mistral 7B model (≈4 GB, one-time download)
ollama pull mistral
```

---

### Step 3 — Run the setup script

**Windows:**
```bat
setup.bat
```

**Linux / macOS:**
```bash
chmod +x setup.sh && ./setup.sh
```

The script will:
- Check for Python & Node.js
- Create a `.env` file from `.env.example`
- Create a Python virtual environment
- Install all Python dependencies
- Install all npm dependencies

---

### Step 4 — Configure `.env`

Open the `.env` file and verify the paths:

```dotenv
CHROMA_DB_PATH=./data/chroma_db
KNOWLEDGE_GRAPH_PATH=./data/knowledge_graph.json
OLLAMA_MODEL=mistral
```

If your `chroma_db` is in a different location (e.g. `D:\POLICE BOT\chroma_db`), set the full absolute path:

```dotenv
CHROMA_DB_PATH=D:\POLICE BOT\chroma_db
KNOWLEDGE_GRAPH_PATH=D:\POLICE BOT\knowledge_graph.json
```

---

### Step 5 — Start the services

**Terminal 1 — Ollama:**
```bash
ollama serve
```

**Terminal 2 — FastAPI backend:**
```bash
# Windows
venv\Scripts\activate
cd backend
uvicorn main:app --reload --port 8000

# Linux / macOS
source venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 3 — React frontend:**
```bash
cd frontend
npm start
```

Open **http://localhost:3000** in your browser. 🎉

---

## 🔌 API Reference

The backend exposes the following REST endpoints:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Server + Ollama + RAG status |
| POST | `/api/chat` | Send a message, get an answer + sources |
| GET | `/api/sessions` | List all saved chat sessions |
| GET | `/api/sessions/{id}` | Retrieve full message history |
| DELETE | `/api/sessions/{id}` | Delete a session |
| GET | `/api/sessions/{id}/export/pdf` | Download session as PDF |

### Chat request body

```json
{
  "message": "What is the punishment for drug possession?",
  "session_id": null,
  "top_k": 5
}
```

### Chat response

```json
{
  "session_id": "uuid-...",
  "answer": "Under Section 20 of the NDPS Act...",
  "sources": ["ndps_act.pdf – Section 20 – Page 14"],
  "timestamp": "2024-01-15 10:30 UTC"
}
```

---

## ⚙️ Configuration Reference

All settings live in `.env` (copy from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `CHROMA_DB_PATH` | `./data/chroma_db` | Path to Chroma DB folder |
| `KNOWLEDGE_GRAPH_PATH` | `./data/knowledge_graph.json` | Path to knowledge graph JSON |
| `CASE_HISTORY_DIR` | `./data/case_history` | Where session JSON files are stored |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `mistral` | Model to use |
| `CHROMA_COLLECTION_NAME` | `ndps_documents` | Chroma collection name |
| `RAG_TOP_K` | `5` | Number of documents to retrieve per query |
| `RAG_SIMILARITY_THRESHOLD` | `0.3` | Minimum cosine similarity for retrieval |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## 🔧 Troubleshooting

### "Ollama server is not running"
Start it: `ollama serve`

### "Model 'mistral' is not available"
Pull it: `ollama pull mistral`

### Backend shows "0 documents in Chroma DB"
- Make sure you copied the `chroma_db` folder correctly.
- Check `CHROMA_DB_PATH` in `.env` — use the full absolute path if needed.
- Verify the collection name matches (`CHROMA_COLLECTION_NAME`).

### Frontend can't reach the backend
- Check the backend is running on port 8000.
- The `frontend/package.json` has `"proxy": "http://localhost:8000"` set.
- Check `CORS_ORIGINS` in `.env`.

### Slow responses on 8 GB RAM
- Mistral 7B uses ≈5–6 GB RAM; close other applications.
- Reduce `RAG_TOP_K` to `3` to shorten the context fed to the LLM.

---

## 📋 System Requirements

| Component | Minimum | Recommended |
|---|---|---|
| RAM | 8 GB | 16 GB |
| Storage | 10 GB free | 20 GB free |
| CPU | Any modern quad-core | Intel i5/i7 8th gen+ |
| GPU | CPU inference (Intel UHD OK) | NVIDIA GPU (faster) |
| OS | Windows 10/11, Ubuntu 20.04+, macOS 12+ | - |

---

## 🏗️ Architecture

```
  Browser (React)
       │  HTTP
       ▼
  FastAPI Backend (port 8000)
       │           │
       │           ▼
       │     RAG Pipeline
       │       ├── Chroma DB (vector search)
       │       └── Knowledge Graph JSON (keyword search)
       │
       ▼
  Ollama (port 11434)
       └── Mistral 7B (local, offline)
```

---

## 📜 License

This project is for official law enforcement use. All NDPS legal content is sourced from publicly available government publications.