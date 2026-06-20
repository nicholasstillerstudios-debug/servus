"""Historico de conversas persistente em SQLite (%APPDATA%\\Servus\\history.db)."""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path


def _db_path() -> Path:
    base = Path(os.environ.get("APPDATA", str(Path.home()))) / "Servus"
    base.mkdir(parents=True, exist_ok=True)
    return base / "history.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_db_path()))
    c.execute("""CREATE TABLE IF NOT EXISTS conversations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at REAL NOT NULL,
        title TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conv_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        ts REAL NOT NULL,
        FOREIGN KEY(conv_id) REFERENCES conversations(id)
    )""")
    c.commit()
    return c


def new_conversation(title: str = "") -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO conversations(started_at, title) VALUES (?, ?)",
            (time.time(), title or "Conversa"),
        )
        return cur.lastrowid or 0


def add_message(conv_id: int, role: str, content: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO messages(conv_id, role, content, ts) VALUES (?, ?, ?, ?)",
            (conv_id, role, content, time.time()),
        )
        # se for o primeiro user msg, vira titulo da conversa
        if role == "user":
            row = c.execute(
                "SELECT COUNT(*) FROM messages WHERE conv_id=? AND role='user'", (conv_id,)
            ).fetchone()
            if row and row[0] == 1:
                title = content[:60].strip()
                c.execute("UPDATE conversations SET title=? WHERE id=?", (title, conv_id))


def list_conversations(limit: int = 50) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, started_at, title FROM conversations ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"id": r[0], "started_at": r[1], "title": r[2] or "Conversa"} for r in rows]


def get_messages(conv_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT role, content, ts FROM messages WHERE conv_id=? ORDER BY id", (conv_id,)
        ).fetchall()
        return [{"role": r[0], "content": r[1], "ts": r[2]} for r in rows]


def delete_conversation(conv_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM messages WHERE conv_id=?", (conv_id,))
        c.execute("DELETE FROM conversations WHERE id=?", (conv_id,))
