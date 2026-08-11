import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import get_settings


def _db_path() -> Path:
    path = Path(get_settings().database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connect():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS keyword_chunks (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                document TEXT NOT NULL,
                page INTEGER,
                parent INTEGER,
                chunk INTEGER,
                text TEXT NOT NULL,
                parent_text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_keyword_chunks_scope
            ON keyword_chunks(session_id, source_type)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_keyword_chunks_document
            ON keyword_chunks(session_id, document)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS session_memories (
                session_id TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                memory_key TEXT NOT NULL,
                memory_value TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0.7,
                sensitivity TEXT NOT NULL DEFAULT 'normal',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_memories_user
            ON user_memories(user_id, memory_type, sensitivity)
            """
        )


def ensure_session(session_id: str, title: str | None = None) -> None:
    display_title = title or "New chat"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO sessions (session_id, title)
            VALUES (?, ?)
            ON CONFLICT(session_id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
            """,
            (session_id, display_title[:80]),
        )


def save_message(session_id: str, role: str, content: str) -> None:
    ensure_session(session_id, content if role == "user" else None)
    with connect() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        conn.execute(
            "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
            (session_id,),
        )


def list_sessions() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT session_id, title, updated_at FROM sessions ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_messages(session_id: str, limit: int = 20) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
        return [dict(row) for row in reversed(rows)]


def delete_session(session_id: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM session_memories WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM keyword_chunks WHERE session_id = ?", (session_id,))


def get_session_memory(session_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT session_id, summary, updated_at FROM session_memories WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return dict(row) if row else None


def upsert_session_memory(session_id: str, summary: str) -> None:
    cleaned = summary.strip()
    if not cleaned:
        return
    ensure_session(session_id)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO session_memories (session_id, summary)
            VALUES (?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                summary = excluded.summary,
                updated_at = CURRENT_TIMESTAMP
            """,
            (session_id, cleaned[:2000]),
        )


def list_user_memories(user_id: str = "local_user") -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, memory_type, memory_key, memory_value, confidence,
                   sensitivity, created_at, updated_at, expires_at
            FROM user_memories
            WHERE user_id = ?
              AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ORDER BY updated_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def upsert_user_memory(
    *,
    user_id: str,
    memory_type: str,
    memory_key: str,
    memory_value: str,
    confidence: float = 0.7,
    sensitivity: str = "normal",
    expires_at: str | None = None,
) -> None:
    key = memory_key.strip()[:120]
    value = memory_value.strip()[:600]
    if not key or not value:
        return
    with connect() as conn:
        existing = conn.execute(
            """
            SELECT id FROM user_memories
            WHERE user_id = ? AND memory_type = ? AND memory_key = ?
            """,
            (user_id, memory_type, key),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE user_memories
                SET memory_value = ?, confidence = ?, sensitivity = ?,
                    expires_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (value, confidence, sensitivity, expires_at, existing["id"]),
            )
            return
        conn.execute(
            """
            INSERT INTO user_memories (
                user_id, memory_type, memory_key, memory_value,
                confidence, sensitivity, expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, memory_type, key, value, confidence, sensitivity, expires_at),
        )


def delete_user_memory(memory_id: int, user_id: str = "local_user") -> bool:
    with connect() as conn:
        cursor = conn.execute("DELETE FROM user_memories WHERE id = ? AND user_id = ?", (memory_id, user_id))
        return cursor.rowcount > 0


def clear_user_memories(user_id: str = "local_user") -> int:
    with connect() as conn:
        cursor = conn.execute("DELETE FROM user_memories WHERE user_id = ?", (user_id,))
        return cursor.rowcount


def save_keyword_chunk(
    *,
    chunk_id: str,
    session_id: str,
    source_type: str,
    document: str,
    page: int,
    parent: int,
    chunk: int,
    text: str,
    parent_text: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO keyword_chunks (
                id, session_id, source_type, document, page, parent, chunk, text, parent_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (chunk_id, session_id, source_type, document, page, parent, chunk, text, parent_text),
        )


def list_keyword_chunks_for_scope(session_id: str, seed_session_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, session_id, source_type, document, page, parent, chunk, text, parent_text
            FROM keyword_chunks
            WHERE session_id IN (?, ?)
            """,
            (session_id, seed_session_id),
        ).fetchall()
        return [dict(row) for row in rows]


def delete_keyword_chunks(document_name: str, session_id: str | None = None) -> int:
    with connect() as conn:
        if session_id:
            cursor = conn.execute(
                "DELETE FROM keyword_chunks WHERE document = ? AND session_id = ?",
                (document_name, session_id),
            )
        else:
            cursor = conn.execute("DELETE FROM keyword_chunks WHERE document = ?", (document_name,))
        return cursor.rowcount


def clear_keyword_chunks(session_id: str | None = None) -> int:
    with connect() as conn:
        if session_id:
            cursor = conn.execute("DELETE FROM keyword_chunks WHERE session_id = ?", (session_id,))
        else:
            cursor = conn.execute("DELETE FROM keyword_chunks")
        return cursor.rowcount
