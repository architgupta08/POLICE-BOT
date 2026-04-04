import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data paths
DATA_DIR = os.getenv("DATA_DIR", str(BASE_DIR / "data"))
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "data" / "chroma_db"))
KNOWLEDGE_GRAPH_PATH = os.getenv(
    "KNOWLEDGE_GRAPH_PATH", str(BASE_DIR / "data" / "knowledge_graph.json")
)

# Case history
CASE_HISTORY_DIR = os.getenv("CASE_HISTORY_DIR", str(BASE_DIR / "data" / "case_history"))

# Ollama settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# Hugging Face settings
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")

# LLM backend: "ollama" (local) or "huggingface" (cloud)
LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama")

# Chroma settings
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "ndps_documents")

# RAG settings
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.3"))

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(BASE_DIR / "logs" / "police_bot.log"))

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "police_bot.db"))

# JWT authentication
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# Development mode: when True, authentication is optional (no token = dev user)
DEV_MODE = os.getenv("DEV_MODE", "true").lower() in ("1", "true", "yes")

# System prompt for LLM
SYSTEM_PROMPT = """You are an expert legal assistant specializing in the Narcotic Drugs and Psychotropic Substances (NDPS) Act of India. 
You provide accurate, precise, and actionable legal guidance to police officers.

Your responses should:
1. Be clear and concise
2. Reference specific sections of the NDPS Act when applicable
3. Provide step-by-step procedural guidance when needed
4. Highlight important legal requirements and deadlines
5. Flag any critical warnings or legal obligations

Always base your answers on the provided context. If the context does not contain enough information, say so clearly.
Do not make up information or guess at legal provisions."""
