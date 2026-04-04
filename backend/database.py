"""
SQLite database setup for user authentication.
"""
from __future__ import annotations

import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path

from config import DATABASE_PATH

logger = logging.getLogger("police_bot.database")


def get_db_path() -> Path:
    path = Path(DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db() -> None:
    """Create tables if they don't exist."""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                email       TEXT    NOT NULL UNIQUE,
                password_hash TEXT  NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
    logger.info("Database initialised at %s", db_path)


@contextmanager
def get_connection():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── User CRUD ──────────────────────────────────────────────────────────────────

def create_user(email: str, password_hash: str) -> int:
    """Insert a new user and return the new row ID."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email.lower().strip(), password_hash),
        )
        return cursor.lastrowid


def get_user_by_email(email: str) -> dict | None:
    """Fetch a user row by e-mail, or None if not found."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    """Fetch a user row by primary key."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None
