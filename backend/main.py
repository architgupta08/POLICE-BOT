"""
POLICE-BOT FastAPI Backend
Real-time NDPS legal guidance for police officers.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import CORS_ORIGINS
from llm_handler import OllamaHandler
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
llm: OllamaHandler = OllamaHandler()
logger = logging.getLogger("police_bot.api")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting POLICE-BOT backend …")
    try:
        rag.initialize()
        logger.info("RAG pipeline ready")
    except Exception as exc:  # noqa: BLE001
        logger.error("RAG pipeline initialization failed: %s", exc)

    if not llm.is_available():
        logger.warning("Ollama is not available — LLM responses will fail until it starts")
    elif not llm.is_model_available():
        logger.warning("Model '%s' is not pulled — run: ollama pull %s", llm.model, llm.model)
    else:
        logger.info("Ollama + model '%s' ready", llm.model)

    yield

    logger.info("Shutting down POLICE-BOT backend")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="POLICE-BOT API",
    description="NDPS Legal Guidance System for Police Officers",
    version="1.0.0",
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
    return {"status": "ok", "service": "POLICE-BOT API", "version": "1.0.0"}


@app.get("/api/health", tags=["Health"])
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "ollama_available": llm.is_available(),
        "model_available": llm.is_model_available(),
        "rag_status": rag.get_status(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/status", tags=["Health"])
async def status() -> dict[str, Any]:
    return rag.get_status()


# ---------------------------------------------------------------------------
# Routes — chat
# ---------------------------------------------------------------------------


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(req: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint.  Retrieves relevant NDPS context from the knowledge base
    and generates an answer using the local LLM.
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
        # Surface the error as a user-friendly message so the chat remains usable
        answer = (
            f"⚠️ I could not generate a response at this time.\n\n"
            f"**Reason:** {exc}\n\n"
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
# Routes — session management
# ---------------------------------------------------------------------------


@app.get("/api/sessions", response_model=list[SessionSummary], tags=["Sessions"])
async def get_sessions() -> list[SessionSummary]:
    """List all saved chat sessions."""
    return list_chat_sessions()  # type: ignore[return-value]


@app.get("/api/sessions/{session_id}", tags=["Sessions"])
async def get_session(session_id: str) -> dict[str, Any]:
    """Retrieve full message history for a session."""
    data = load_chat_session(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


@app.delete("/api/sessions/{session_id}", tags=["Sessions"])
async def delete_session(session_id: str) -> dict[str, str]:
    """Delete a saved chat session."""
    if not delete_chat_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}


# ---------------------------------------------------------------------------
# Routes — PDF export
# ---------------------------------------------------------------------------


@app.get("/api/sessions/{session_id}/export/pdf", tags=["Export"])
async def export_session_pdf(session_id: str) -> Response:
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
