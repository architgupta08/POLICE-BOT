"""
POLICE-BOT FastAPI Backend
Real-time NDPS legal guidance for police officers.
"""
from __future__ import annotations

import logging
import re
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from auth import create_access_token, get_current_user, hash_password, verify_password
from config import CORS_ORIGINS, DEV_MODE, LLM_BACKEND
from database import create_user, get_user_by_email, init_db
from rag_pipeline import RAGPipeline
from utils import (
    delete_chat_session,
    export_chat_to_pdf,
    format_sources,
    generate_session_id,
    list_chat_sessions,
    load_chat_session,
    save_chat_session,
)

# ---------------------------------------------------------------------------
# Globals (initialised on startup)
# ---------------------------------------------------------------------------

rag: RAGPipeline = RAGPipeline()
logger = logging.getLogger("police_bot.api")

# LLM handler — chosen based on LLM_BACKEND config
if LLM_BACKEND == "huggingface":
    from hf_handler import HuggingFaceHandler

    llm: Any = HuggingFaceHandler()
else:
    from llm_handler import OllamaHandler

    llm = OllamaHandler()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting POLICE-BOT backend …")

    # Initialise SQLite database
    try:
        init_db()
    except Exception as exc:  # noqa: BLE001
        logger.error("Database initialisation failed: %s", exc)

    try:
        rag.initialize()
        logger.info("RAG pipeline ready")
    except Exception as exc:  # noqa: BLE001
        logger.error("RAG pipeline initialization failed: %s", exc)

    if LLM_BACKEND == "huggingface":
        if llm.is_available():
            logger.info("Hugging Face LLM backend ready (model: %s)", llm.model)
        else:
            logger.warning("HF_API_TOKEN not set — LLM responses will fail")
    else:
        if not llm.is_available():
            logger.warning("Ollama is not available — LLM responses will fail until it starts")
        elif not llm.is_model_available():
            logger.info(
                "Model '%s' not found locally — pulling now (this may take several minutes)…",
                llm.model,
            )
            try:
                import httpx as _httpx

                with _httpx.Client(timeout=600.0) as _client:
                    _client.post(
                        f"{llm.base_url}/api/pull",
                        json={"name": llm.model},
                        timeout=600.0,
                    ).raise_for_status()
                logger.info("Model '%s' pulled successfully", llm.model)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Auto-pull of model '%s' failed: %s — run 'ollama pull %s' manually",
                    llm.model,
                    exc,
                    llm.model,
                )
        else:
            logger.info("Ollama + model '%s' ready", llm.model)

    if DEV_MODE:
        logger.warning(
            "DEV_MODE=true — authentication is optional "
            "(set DEV_MODE=false in production)"
        )

    yield

    logger.info("Shutting down POLICE-BOT backend")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="POLICE-BOT API",
    description="NDPS Legal Guidance System for Police Officers",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254, description="User e-mail")
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 chars)")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.strip().lower()


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User query")
    session_id: str | None = Field(None, description="Existing session ID (optional)")
    top_k: int = Field(5, ge=1, le=20, description="Number of KB documents to retrieve")


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[str]
    timestamp: str


class SessionSummary(BaseModel):
    session_id: str
    created_at: str
    updated_at: str
    message_count: int
    preview: str


# ---------------------------------------------------------------------------
# Routes — health / status
# ---------------------------------------------------------------------------


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    return {"status": "ok", "service": "POLICE-BOT API", "version": "2.0.0"}


@app.get("/api/health", tags=["Health"])
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "llm_backend": LLM_BACKEND,
        "llm_available": llm.is_available(),
        "model_available": llm.is_model_available(),
        "rag_status": rag.get_status(),
        "dev_mode": DEV_MODE,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/status", tags=["Health"])
async def status() -> dict[str, Any]:
    return rag.get_status()


# ---------------------------------------------------------------------------
# Routes — authentication
# ---------------------------------------------------------------------------


@app.post("/auth/signup", response_model=AuthResponse, tags=["Auth"])
async def signup(req: SignupRequest) -> AuthResponse:
    """Register a new user and return a JWT access token."""
    if get_user_by_email(req.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    password_hash = hash_password(req.password)
    user_id = create_user(req.email, password_hash)

    token = create_access_token({"sub": str(user_id)})
    return AuthResponse(access_token=token, user_id=user_id, email=req.email)


@app.post("/auth/login", response_model=AuthResponse, tags=["Auth"])
async def login(req: LoginRequest) -> AuthResponse:
    """Authenticate a user and return a JWT access token."""
    user = get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": str(user["id"])})
    return AuthResponse(access_token=token, user_id=user["id"], email=user["email"])


@app.post("/auth/logout", tags=["Auth"])
async def logout() -> dict[str, str]:
    """
    Stateless logout — the client should discard the stored JWT token.
    """
    return {"message": "Logged out successfully"}


@app.get("/auth/me", tags=["Auth"])
async def me(current_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Return the currently authenticated user's profile."""
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"user_id": current_user["id"], "email": current_user["email"]}


# ---------------------------------------------------------------------------
# Routes — chat  (protected)
# ---------------------------------------------------------------------------


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(
    req: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    """
    Main chat endpoint.  Retrieves relevant NDPS context from the knowledge base
    and generates an answer using the configured LLM.

    Requires a valid JWT token (or DEV_MODE=true for local testing without auth).
    """
    # Resolve or create session
    session_id = req.session_id or generate_session_id()
    session_data = load_chat_session(session_id) or {"session_id": session_id, "messages": []}
    messages: list[dict[str, Any]] = session_data.get("messages", [])

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Store the user message immediately
    messages.append({"role": "user", "content": req.message, "timestamp": timestamp})

    # RAG retrieval
    context, retrieved_docs = rag.get_context_and_sources(req.message, top_k=req.top_k)
    sources = format_sources(retrieved_docs)

    # LLM generation
    history_for_llm = [
        {"role": m["role"], "content": m["content"]}
        for m in messages[:-1]  # exclude the just-added user turn
        if m["role"] in ("user", "assistant")
    ]

    try:
        answer = llm.generate(req.message, context=context, chat_history=history_for_llm)
    except RuntimeError as exc:
        answer = (
            f"⚠️ I could not generate a response at this time.\n\n"
            f"**Reason:** {exc}\n\n"
        )
        if LLM_BACKEND == "huggingface":
            answer += (
                "Please ensure `HF_API_TOKEN` is set in your environment variables "
                "and your Hugging Face account has access to the model."
            )
        else:
            answer += (
                "Please ensure Ollama is running (`ollama serve`) and the Mistral model "
                f"is pulled (`ollama pull {llm.model}`)."
            )
        sources = []

    # Store assistant response
    messages.append(
        {"role": "assistant", "content": answer, "timestamp": timestamp, "sources": sources}
    )
    save_chat_session(session_id, messages)

    return ChatResponse(
        session_id=session_id,
        answer=answer,
        sources=sources,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# Routes — session management  (protected)
# ---------------------------------------------------------------------------


@app.get("/api/sessions", response_model=list[SessionSummary], tags=["Sessions"])
async def get_sessions(
    current_user: dict = Depends(get_current_user),
) -> list[SessionSummary]:
    """List all saved chat sessions."""
    return list_chat_sessions()  # type: ignore[return-value]


@app.get("/api/sessions/{session_id}", tags=["Sessions"])
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve full message history for a session."""
    data = load_chat_session(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


@app.delete("/api/sessions/{session_id}", tags=["Sessions"])
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a saved chat session."""
    if not delete_chat_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}


# ---------------------------------------------------------------------------
# Routes — PDF export  (protected)
# ---------------------------------------------------------------------------


@app.get("/api/sessions/{session_id}/export/pdf", tags=["Export"])
async def export_session_pdf(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> Response:
    """Export a chat session as a formatted PDF."""
    data = load_chat_session(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        pdf_bytes = export_chat_to_pdf(session_id, data.get("messages", []))
    except Exception as exc:  # noqa: BLE001
        logger.error("PDF export failed for session %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}") from exc

    filename = f"police_bot_session_{session_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
