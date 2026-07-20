import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import Config


class SessionStore:
    """会话元数据 SQLite 存储（不含聊天记录）"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
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

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                self._migrate_schema(conn)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
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
                conn.commit()
            finally:
                conn.close()

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "session_id": row["session_id"],
            "subject": row["subject"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

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
                return self._row_to_dict(row) if row else None
            finally:
                conn.close()

    def list_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT session_id, subject, created_at, updated_at
                    FROM sessions
                    ORDER BY updated_at DESC
                    """
                ).fetchall()
                return [self._row_to_dict(row) for row in rows]
            finally:
                conn.close()

    def create(
        self,
        session_id: str,
        subject: str,
        now_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        now = now_ms or self._now_ms()
        safe_subject = (subject or "新对话").strip()[:30] or "新对话"
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO sessions (session_id, subject, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, safe_subject, now, now),
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

    def ensure_session(self, session_id: str, subject: str) -> Dict[str, Any]:
        """不存在则创建，存在则更新 updated_at"""
        session_id = (session_id or "").strip()
        if not session_id:
            raise ValueError("session_id 不能为空")

        existing = self.get(session_id)
        if existing:
            now = self._now_ms()
            self.touch(session_id, now)
            existing["updated_at"] = now
            return existing
        return self.create(session_id, subject)

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


_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore(Config.SESSION_DB_PATH)
    return _store
