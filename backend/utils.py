import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

from config import CASE_HISTORY_DIR, LOG_FILE, LOG_LEVEL

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    """Configure application-wide logging."""
    log_dir = Path(LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("police_bot")


logger = setup_logging()

# ---------------------------------------------------------------------------
# Case history helpers
# ---------------------------------------------------------------------------

def ensure_case_history_dir() -> Path:
    """Create the case history directory if it doesn't exist."""
    path = Path(CASE_HISTORY_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _validate_session_id(session_id: str) -> str:
    """
    Validate and sanitise a session ID to prevent path traversal attacks.

    Parses the value as a UUID (raises ValueError for anything invalid), then
    returns the canonical lower-case string form.  The round-trip through
    ``uuid.UUID`` guarantees the result contains only hex digits and hyphens
    in the standard 8-4-4-4-12 layout, so it is safe to use as a filename.
    """
    try:
        canonical = str(uuid.UUID(session_id))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid session ID format: {session_id!r}") from exc
    return canonical


def _safe_session_path(history_dir: Path, session_id: str) -> Path:
    """
    Build a session file path and verify it is confined to *history_dir*.

    Even after UUID validation, we resolve both paths and assert the session
    file is a direct child of the history directory.  This eliminates any
    residual path-traversal concern.
    """
    session_id = _validate_session_id(session_id)
    candidate = (history_dir / f"{session_id}.json").resolve()
    history_resolved = history_dir.resolve()
    if candidate.parent != history_resolved:
        raise ValueError(f"Session path escapes history directory: {candidate}")
    return candidate


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())


def save_chat_session(session_id: str, messages: list[dict[str, Any]]) -> str:
    """Persist a chat session to disk as JSON."""
    history_dir = ensure_case_history_dir()
    session_file = _safe_session_path(history_dir, session_id)
    # Use the canonical UUID string for the stored record
    canonical_id = _validate_session_id(session_id)

    session_data = {
        "session_id": canonical_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "messages": messages,
    }

    # Preserve created_at if file already exists
    if session_file.exists():
        try:
            existing = json.loads(session_file.read_text(encoding="utf-8"))
            session_data["created_at"] = existing.get("created_at", session_data["created_at"])
        except (json.JSONDecodeError, KeyError):
            pass

    session_file.write_text(json.dumps(session_data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Session %s saved (%d messages)", canonical_id, len(messages))
    return str(session_file)


def load_chat_session(session_id: str) -> dict[str, Any] | None:
    """Load a chat session from disk."""
    try:
        history_dir = ensure_case_history_dir()
        session_file = _safe_session_path(history_dir, session_id)
    except ValueError:
        return None

    if not session_file.exists():
        return None

    try:
        return json.loads(session_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse session file %s: %s", session_file, exc)
        return None


def list_chat_sessions() -> list[dict[str, Any]]:
    """Return metadata for all saved sessions, newest first."""
    history_dir = ensure_case_history_dir()
    sessions: list[dict[str, Any]] = []

    for session_file in history_dir.glob("*.json"):
        try:
            data = json.loads(session_file.read_text(encoding="utf-8"))
            sessions.append(
                {
                    "session_id": data.get("session_id", session_file.stem),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "message_count": len(data.get("messages", [])),
                    "preview": _get_session_preview(data.get("messages", [])),
                }
            )
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Skipping malformed session file %s: %s", session_file, exc)

    sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return sessions


def delete_chat_session(session_id: str) -> bool:
    """Delete a session file from disk."""
    try:
        history_dir = ensure_case_history_dir()
        session_file = _safe_session_path(history_dir, session_id)
    except ValueError:
        return False

    if session_file.exists():
        session_file.unlink()
        logger.info("Session %s deleted", session_id)
        return True
    return False


def _get_session_preview(messages: list[dict[str, Any]]) -> str:
    """Return the first user message as a short preview string."""
    for msg in messages:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            return content[:80] + "..." if len(content) > 80 else content
    return "Empty session"


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------

def export_chat_to_pdf(session_id: str, messages: list[dict[str, Any]]) -> bytes:
    """Generate a formatted PDF of the chat session and return the raw bytes."""
    from io import BytesIO

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=6,
        textColor=colors.HexColor("#1a237e"),
        alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=20,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )
    user_label_style = ParagraphStyle(
        "UserLabel",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#1565c0"),
        spaceAfter=2,
        fontName="Helvetica-Bold",
    )
    bot_label_style = ParagraphStyle(
        "BotLabel",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#2e7d32"),
        spaceAfter=2,
        fontName="Helvetica-Bold",
    )
    message_style = ParagraphStyle(
        "MessageText",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=12,
        leading=14,
        alignment=TA_LEFT,
    )
    source_style = ParagraphStyle(
        "SourceText",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
        spaceAfter=14,
        leftIndent=10,
    )

    story = []

    # Header
    story.append(Paragraph("🚔 POLICE-BOT - NDPS Legal Guidance", title_style))
    story.append(
        Paragraph(
            f"Case Session: {session_id} | Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            subtitle_style,
        )
    )

    # Divider line using a thin table
    divider_data = [[""] ]
    divider_table = Table(divider_data, colWidths=[6.5 * inch])
    divider_table.setStyle(
        TableStyle([("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor("#1a237e"))])
    )
    story.append(divider_table)
    story.append(Spacer(1, 0.2 * inch))

    # Messages
    for idx, msg in enumerate(messages):
        role = msg.get("role", "")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        sources = msg.get("sources", [])

        if role == "user":
            label = f"👮 Officer Query  [{timestamp}]" if timestamp else "👮 Officer Query"
            story.append(Paragraph(label, user_label_style))
            story.append(Paragraph(content, message_style))
        elif role == "assistant":
            label = f"🤖 Legal Guidance  [{timestamp}]" if timestamp else "🤖 Legal Guidance"
            story.append(Paragraph(label, bot_label_style))
            story.append(Paragraph(content, message_style))
            if sources:
                story.append(Paragraph("📚 Sources: " + " | ".join(sources), source_style))

        # Add spacing between messages, but not after the last one
        if idx < len(messages) - 1:
            story.append(Spacer(1, 0.05 * inch))

    # Footer
    story.append(Spacer(1, 0.2 * inch))
    footer_data = [["CONFIDENTIAL - FOR OFFICIAL USE ONLY"]]
    footer_table = Table(footer_data, colWidths=[6.5 * inch])
    footer_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1a237e")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(footer_table)

    doc.build(story)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_sources(source_docs: list[dict[str, Any]]) -> list[str]:
    """Extract readable source labels from retrieved documents."""
    sources: list[str] = []
    for doc in source_docs:
        meta = doc.get("metadata", {})
        source = meta.get("source", meta.get("file", meta.get("title", "")))
        page = meta.get("page", meta.get("page_number", ""))
        section = meta.get("section", "")

        parts = []
        if source:
            parts.append(os.path.basename(str(source)))
        if section:
            parts.append(f"Section {section}")
        if page:
            parts.append(f"Page {page}")

        label = " – ".join(parts) if parts else "NDPS Knowledge Base"
        if label not in sources:
            sources.append(label)

    return sources
