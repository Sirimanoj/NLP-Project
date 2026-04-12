from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from agent.events import AgentEvent


class HashChainedAuditLogger:
    def __init__(self, db_path: str = "data/audit_log.sqlite") -> None:
        self.db_path = Path(db_path)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._using_memory_fallback = False
        self._conn = self._init_connection()
        self._init_db()

    def _init_connection(self) -> sqlite3.Connection:
        try:
            return sqlite3.connect(self.db_path, check_same_thread=False)
        except sqlite3.OperationalError:
            self._using_memory_fallback = True
            return sqlite3.connect("file:agentshield_audit?mode=memory&cache=shared", uri=True, check_same_thread=False)

    def _switch_to_memory_fallback(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
        self._using_memory_fallback = True
        self._conn = sqlite3.connect("file:agentshield_audit?mode=memory&cache=shared", uri=True, check_same_thread=False)

    def _connect(self) -> sqlite3.Connection:
        return self._conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    entry_hash TEXT NOT NULL
                )
                """
            )
            conn.commit()
        except sqlite3.OperationalError:
            if self._using_memory_fallback:
                raise
            self._switch_to_memory_fallback()
            self._init_db()

    def append_event(self, event: AgentEvent, payload: dict[str, Any]) -> str:
        with self._lock:
            return self._append_event_internal(event, payload, allow_fallback=True)

    def _append_event_internal(self, event: AgentEvent, payload: dict[str, Any], allow_fallback: bool) -> str:
        conn = self._connect()
        try:
            prev_hash = self._get_last_hash(conn)
            payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=True)
            hash_input = (
                f"{event.timestamp}|{event.event_type}|{event.user_id}|{event.session_id}|"
                f"{event.role}|{event.content}|{payload_json}|{prev_hash}"
            )
            entry_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
            conn.execute(
                """
                INSERT INTO audit_log
                (timestamp, event_type, user_id, session_id, role, content, payload_json, prev_hash, entry_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.timestamp,
                    event.event_type,
                    event.user_id,
                    event.session_id,
                    event.role,
                    event.content,
                    payload_json,
                    prev_hash,
                    entry_hash,
                ),
            )
            conn.commit()
            return entry_hash
        except sqlite3.OperationalError:
            if not allow_fallback or self._using_memory_fallback:
                raise
            self._switch_to_memory_fallback()
            self._init_db()
            return self._append_event_internal(event, payload, allow_fallback=False)

    def _get_last_hash(self, conn: sqlite3.Connection) -> str:
        row = conn.execute("SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        return row[0] if row else "GENESIS"

    def verify_chain(self) -> dict[str, Any]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT id, timestamp, event_type, user_id, session_id, role, content, payload_json, prev_hash, entry_hash
                FROM audit_log
                ORDER BY id ASC
                """
            ).fetchall()
        except sqlite3.OperationalError:
            if self._using_memory_fallback:
                raise
            self._switch_to_memory_fallback()
            self._init_db()
            rows = self._connect().execute(
                """
                SELECT id, timestamp, event_type, user_id, session_id, role, content, payload_json, prev_hash, entry_hash
                FROM audit_log
                ORDER BY id ASC
                """
            ).fetchall()
        expected_prev = "GENESIS"
        for row in rows:
            (
                row_id,
                timestamp,
                event_type,
                user_id,
                session_id,
                role,
                content,
                payload_json,
                prev_hash,
                entry_hash,
            ) = row
            if prev_hash != expected_prev:
                return {"ok": False, "error": f"Broken chain at row {row_id}: prev_hash mismatch."}
            hash_input = f"{timestamp}|{event_type}|{user_id}|{session_id}|{role}|{content}|{payload_json}|{prev_hash}"
            expected_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
            if expected_hash != entry_hash:
                return {"ok": False, "error": f"Broken chain at row {row_id}: entry_hash mismatch."}
            expected_prev = entry_hash
        return {"ok": True, "count": len(rows)}

    def recent_events(self, limit: int = 200) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT id, timestamp, event_type, user_id, session_id, role, content, payload_json, prev_hash, entry_hash
                FROM audit_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            if self._using_memory_fallback:
                raise
            self._switch_to_memory_fallback()
            self._init_db()
            rows = self._connect().execute(
                """
                SELECT id, timestamp, event_type, user_id, session_id, role, content, payload_json, prev_hash, entry_hash
                FROM audit_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "event_type": r[2],
                "user_id": r[3],
                "session_id": r[4],
                "role": r[5],
                "content": r[6],
                "payload_json": r[7],
                "prev_hash": r[8],
                "entry_hash": r[9],
            }
            for r in rows
        ]
