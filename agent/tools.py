from __future__ import annotations

import re
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from security.input_guard import InputGuard


@dataclass
class ToolSpec:
    name: str
    description: str
    risk_level: str
    handler: Callable[..., dict[str, Any]]


class ToolRegistry:
    def __init__(self, db_path: str = "data/mock_db.sqlite", kb_path: str = "data/knowledge_base") -> None:
        self.db_path = Path(db_path)
        self.kb_path = Path(kb_path)
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None
        self._using_memory_fallback = False
        self._ensure_dirs()
        self._init_connection()
        self._init_mock_db()
        self.retrieval_guard = InputGuard(risk_threshold=10_000.0)
        self.tools: dict[str, ToolSpec] = {
            "rag_search": ToolSpec(
                name="rag_search",
                description="Searches company knowledge base documents.",
                risk_level="low",
                handler=self.rag_search,
            ),
            "check_balance": ToolSpec(
                name="check_balance",
                description="Returns customer account balance.",
                risk_level="medium",
                handler=self.check_balance,
            ),
            "update_email": ToolSpec(
                name="update_email",
                description="Updates customer email address.",
                risk_level="high",
                handler=self.update_email,
            ),
            "delete_customer": ToolSpec(
                name="delete_customer",
                description="Deletes a customer record (admin-only).",
                risk_level="critical",
                handler=self.delete_customer,
            ),
        }

    def _ensure_dirs(self) -> None:
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.kb_path.mkdir(parents=True, exist_ok=True)

    def _init_connection(self) -> None:
        try:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        except sqlite3.OperationalError:
            self._switch_to_memory_fallback()

    def _switch_to_memory_fallback(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
        # Fallback keeps the project runnable on restricted/synced paths.
        self._conn = sqlite3.connect("file:agentshield_db?mode=memory&cache=shared", uri=True, check_same_thread=False)
        self._using_memory_fallback = True

    def _get_conn(self) -> sqlite3.Connection:
        if not self._conn:
            raise RuntimeError("Database connection not initialized.")
        return self._conn

    def _reset_to_memory_and_seed(self) -> None:
        if not self._using_memory_fallback:
            self._switch_to_memory_fallback()
        self._init_mock_db()

    def _init_mock_db(self) -> None:
        conn = self._get_conn()
        try:
            with self._lock:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS customers (
                        customer_id TEXT PRIMARY KEY,
                        full_name TEXT NOT NULL,
                        email TEXT NOT NULL,
                        account_balance REAL NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_id TEXT,
                        action TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                existing = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
                if existing == 0:
                    seed_rows = [
                        ("CUST1001", "Aarav Shah", "aarav@example.com", 15000.50),
                        ("CUST1002", "Diya Nair", "diya@example.com", 8320.00),
                        ("CUST1003", "Rohan Das", "rohan@example.com", 223.75),
                    ]
                    conn.executemany(
                        "INSERT INTO customers (customer_id, full_name, email, account_balance) VALUES (?, ?, ?, ?)",
                        seed_rows,
                    )
                conn.commit()
        except sqlite3.OperationalError:
            if self._using_memory_fallback:
                raise
            self._switch_to_memory_fallback()
            self._init_mock_db()

    def list_tools(self) -> dict[str, ToolSpec]:
        return self.tools

    def run(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        spec = self.tools.get(tool_name)
        if not spec:
            return {"ok": False, "error": f"Unknown tool: {tool_name}"}
        return spec.handler(**kwargs)

    def rag_search(self, query: str) -> dict[str, Any]:
        query_terms = {term.lower() for term in re.findall(r"\w+", query)}
        best_doc: Path | None = None
        best_score = -1
        blocked_docs: list[dict[str, str]] = []
        for doc in self.kb_path.glob("*.md"):
            content = doc.read_text(encoding="utf-8")
            guard = self.retrieval_guard.evaluate(content, risk_score=None)
            if not guard.allowed:
                blocked_docs.append({"doc": doc.name, "reason": guard.reason})
                continue
            tokens = {term.lower() for term in re.findall(r"\w+", content)}
            score = len(query_terms & tokens)
            if score > best_score:
                best_doc = doc
                best_score = score
        if not best_doc:
            answer = "No safe documents found." if blocked_docs else "No knowledge-base document found."
            return {"ok": True, "answer": answer, "source": None, "blocked_docs": blocked_docs}
        excerpt = best_doc.read_text(encoding="utf-8")[:700]
        return {
            "ok": True,
            "answer": excerpt,
            "source": best_doc.name,
            "score": best_score,
            "blocked_docs": blocked_docs,
        }

    def check_balance(self, customer_id: str) -> dict[str, Any]:
        for attempt in range(2):
            conn = self._get_conn()
            try:
                with self._lock:
                    row = conn.execute(
                        "SELECT customer_id, full_name, account_balance FROM customers WHERE customer_id = ?",
                        (customer_id,),
                    ).fetchone()
                    if not row:
                        return {"ok": False, "error": f"Customer '{customer_id}' not found."}
                    return {
                        "ok": True,
                        "customer_id": row[0],
                        "full_name": row[1],
                        "account_balance": row[2],
                    }
            except sqlite3.OperationalError:
                if attempt == 1:
                    raise
                self._reset_to_memory_and_seed()
        return {"ok": False, "error": "Balance lookup failed."}

    def update_email(self, customer_id: str, new_email: str) -> dict[str, Any]:
        for attempt in range(2):
            conn = self._get_conn()
            try:
                with self._lock:
                    cur = conn.execute(
                        "UPDATE customers SET email = ? WHERE customer_id = ?",
                        (new_email, customer_id),
                    )
                    if cur.rowcount == 0:
                        return {"ok": False, "error": f"Customer '{customer_id}' not found."}
                    conn.execute(
                        "INSERT INTO actions (customer_id, action) VALUES (?, ?)",
                        (customer_id, f"updated_email:{new_email}"),
                    )
                    conn.commit()
                    return {"ok": True, "message": f"Email updated for {customer_id}."}
            except sqlite3.OperationalError:
                if attempt == 1:
                    raise
                self._reset_to_memory_and_seed()
        return {"ok": False, "error": "Email update failed."}

    def delete_customer(self, customer_id: str) -> dict[str, Any]:
        for attempt in range(2):
            conn = self._get_conn()
            try:
                with self._lock:
                    cur = conn.execute("DELETE FROM customers WHERE customer_id = ?", (customer_id,))
                    if cur.rowcount == 0:
                        return {"ok": False, "error": f"Customer '{customer_id}' not found."}
                    conn.execute(
                        "INSERT INTO actions (customer_id, action) VALUES (?, ?)",
                        (customer_id, "deleted_customer"),
                    )
                    conn.commit()
                    return {"ok": True, "message": f"Customer {customer_id} deleted."}
            except sqlite3.OperationalError:
                if attempt == 1:
                    raise
                self._reset_to_memory_and_seed()
        return {"ok": False, "error": "Delete action failed."}
