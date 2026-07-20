import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import Config


class SessionStore:
    """会话与聊天记录 SQLite 存储"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _migrate_schema(self, conn: sqlite3.Connection) -> None:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        ).fetchone()
        if not table:
            return

        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
        }
        if "id" in columns and "session_id" not in columns:
            conn.execute("ALTER TABLE sessions RENAME COLUMN id TO session_id")
        if "title" in columns and "subject" not in columns:
            conn.execute("ALTER TABLE sessions RENAME COLUMN title TO subject")
        if "fingerprint" not in columns:
            conn.execute(
                "ALTER TABLE sessions ADD COLUMN fingerprint TEXT NOT NULL DEFAULT ''"
            )

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                self._migrate_schema(conn)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        fingerprint TEXT NOT NULL DEFAULT '',
                        subject TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sessions_updated_at
                    ON sessions(updated_at DESC)
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        message_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL DEFAULT '',
                        reasoning TEXT,
                        citations_json TEXT,
                        created_at INTEGER NOT NULL,
                        FOREIGN KEY (session_id)
                            REFERENCES sessions(session_id)
                            ON DELETE CASCADE
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_chat_messages_session
                    ON chat_messages(session_id, created_at ASC)
                    """
                )
                conn.commit()
            finally:
                conn.close()

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _session_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "session_id": row["session_id"],
            "subject": row["subject"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _message_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        citations = None
        raw_citations = row["citations_json"]
        if raw_citations:
            try:
                citations = json.loads(raw_citations)
            except json.JSONDecodeError:
                citations = None
        return {
            "message_id": row["message_id"],
            "session_id": row["session_id"],
            "role": row["role"],
            "content": row["content"],
            "reasoning": row["reasoning"],
            "citations": citations,
            "created_at": row["created_at"],
        }

    @staticmethod
    def _encode_citations(citations: Optional[List[Dict[str, Any]]]) -> Optional[str]:
        if not citations:
            return None
        return json.dumps(citations, ensure_ascii=False)

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    """
                    SELECT session_id, subject, created_at, updated_at
                    FROM sessions WHERE session_id = ?
                    """,
                    (session_id,),
                ).fetchone()
                return self._session_row_to_dict(row) if row else None
            finally:
                conn.close()

    def list_all(self, fingerprint: str) -> List[Dict[str, Any]]:
        fingerprint = (fingerprint or "").strip()
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT session_id, subject, created_at, updated_at
                    FROM sessions
                    WHERE fingerprint = ?
                    ORDER BY updated_at DESC
                    """,
                    (fingerprint,),
                ).fetchall()
                return [self._session_row_to_dict(row) for row in rows]
            finally:
                conn.close()

    def _get_session_fingerprint(self, session_id: str) -> Optional[str]:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT fingerprint FROM sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                return row["fingerprint"] if row else None
            finally:
                conn.close()

    def create(
        self,
        session_id: str,
        subject: str,
        fingerprint: str,
        now_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        now = now_ms or self._now_ms()
        safe_subject = (subject or "新对话").strip()[:30] or "新对话"
        fp = (fingerprint or "").strip()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO sessions (
                        session_id, fingerprint, subject, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (session_id, fp, safe_subject, now, now),
                )
                conn.commit()
            finally:
                conn.close()
        return {
            "session_id": session_id,
            "subject": safe_subject,
            "created_at": now,
            "updated_at": now,
        }

    def touch(self, session_id: str, now_ms: Optional[int] = None) -> None:
        now = now_ms or self._now_ms()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                    (now, session_id),
                )
                conn.commit()
            finally:
                conn.close()

    def ensure_session(
        self,
        session_id: str,
        subject: str,
        fingerprint: str,
    ) -> Dict[str, Any]:
        """不存在则创建，存在则校验指纹并更新 updated_at"""
        session_id = (session_id or "").strip()
        fp = (fingerprint or "").strip()
        if not session_id:
            raise ValueError("session_id 不能为空")
        if not fp:
            raise ValueError("fingerprint 不能为空")

        existing = self.get(session_id)
        if existing:
            stored_fp = self._get_session_fingerprint(session_id)
            if stored_fp != fp:
                raise ValueError("会话不存在或无权访问")
            now = self._now_ms()
            self.touch(session_id, now)
            existing["updated_at"] = now
            return existing
        return self.create(session_id, subject, fp)

    def delete(self, session_id: str) -> bool:
        with self._lock:
            conn = self._connect()
            try:
                cursor = conn.execute(
                    "DELETE FROM sessions WHERE session_id = ?",
                    (session_id,),
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def add_message(
        self,
        session_id: str,
        message_id: str,
        role: str,
        content: str = "",
        reasoning: Optional[str] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        created_at: Optional[int] = None,
    ) -> Dict[str, Any]:
        message_id = (message_id or "").strip() or str(uuid.uuid4())
        role = (role or "").strip()
        if role not in {"user", "assistant"}:
            raise ValueError("role 必须为 user 或 assistant")

        now = created_at or self._now_ms()
        citations_json = self._encode_citations(citations)

        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO chat_messages (
                        message_id, session_id, role, content,
                        reasoning, citations_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message_id,
                        session_id,
                        role,
                        content,
                        reasoning,
                        citations_json,
                        now,
                    ),
                )
                conn.execute(
                    "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                    (now, session_id),
                )
                conn.commit()
            finally:
                conn.close()

        return {
            "message_id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "reasoning": reasoning,
            "citations": citations,
            "created_at": now,
        }

    def update_message(
        self,
        message_id: str,
        content: Optional[str] = None,
        reasoning: Optional[str] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        fields: List[str] = []
        values: List[Any] = []

        if content is not None:
            fields.append("content = ?")
            values.append(content)
        if reasoning is not None:
            fields.append("reasoning = ?")
            values.append(reasoning)
        if citations is not None:
            fields.append("citations_json = ?")
            values.append(self._encode_citations(citations))

        if not fields:
            return False

        values.append(message_id)
        with self._lock:
            conn = self._connect()
            try:
                cursor = conn.execute(
                    f"UPDATE chat_messages SET {', '.join(fields)} WHERE message_id = ?",
                    values,
                )
                if cursor.rowcount > 0:
                    row = conn.execute(
                        "SELECT session_id FROM chat_messages WHERE message_id = ?",
                        (message_id,),
                    ).fetchone()
                    if row:
                        conn.execute(
                            "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                            (self._now_ms(), row["session_id"]),
                        )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def list_messages(self, session_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT message_id, session_id, role, content,
                           reasoning, citations_json, created_at
                    FROM chat_messages
                    WHERE session_id = ?
                    ORDER BY created_at ASC, message_id ASC
                    """,
                    (session_id,),
                ).fetchall()
                return [self._message_row_to_dict(row) for row in rows]
            finally:
                conn.close()


_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore(Config.SESSION_DB_PATH)
    return _store
