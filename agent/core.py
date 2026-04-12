from __future__ import annotations

import os
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from agent.events import AgentEvent
from agent.tools import ToolRegistry
from audit.logger import HashChainedAuditLogger
from scorer.behavior_monitor import BehaviorMonitor
from scorer.threat_scorer import ThreatScorer
from security.access_control import AccessController
from security.input_guard import InputGuard
from security.output_filter import OutputFilter
from security.pii_masker import PIIMasker


@dataclass
class PendingAction:
    approval_id: str
    session_id: str
    user_id: str
    role: str
    tool_name: str
    tool_args: dict[str, Any]
    original_message: str


class AgentShieldService:
    RISKY_TOOLS = {"delete_customer"}

    def __init__(self) -> None:
        threshold = float(os.getenv("AGENTSHIELD_RISK_THRESHOLD", "70"))
        embeddings_enabled = os.getenv("AGENTSHIELD_ENABLE_EMBEDDINGS", "0").strip() in {"1", "true", "TRUE", "yes"}
        self.tool_registry = ToolRegistry(
            db_path=os.getenv("AGENTSHIELD_DB_PATH", "data/mock_db.sqlite"),
            kb_path=os.getenv("AGENTSHIELD_KB_PATH", "data/knowledge_base"),
        )
        self.threat_scorer = ThreatScorer(
            model_name=os.getenv("AGENTSHIELD_EMBED_MODEL", "all-MiniLM-L6-v2"),
            enable_embeddings=embeddings_enabled,
        )
        self.input_guard = InputGuard(risk_threshold=threshold)
        self.pii_masker = PIIMasker()
        self.access_control = AccessController()
        self.output_filter = OutputFilter()
        self.behavior_monitor = BehaviorMonitor()
        self.audit_logger = HashChainedAuditLogger(db_path=os.getenv("AGENTSHIELD_AUDIT_DB", "data/audit_log.sqlite"))
        self.session_history: dict[str, list[str]] = defaultdict(list)
        self.pending_actions: dict[str, PendingAction] = {}

    def process_message(self, session_id: str, user_id: str, role: str, message: str) -> dict[str, Any]:
        input_event = AgentEvent(
            event_type="user_input",
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=message,
        )
        self.audit_logger.append_event(input_event, payload={"stage": "received"})

        # L1 stage 1: detect hidden/encoded prompt injections on raw input.
        pre_guard = self.input_guard.evaluate(message, risk_score=None)
        if not pre_guard.allowed:
            response_text = "Request blocked by AgentShield. Please rephrase your request safely."
            response_event = AgentEvent(
                event_type="blocked_input",
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=response_text,
            )
            self.audit_logger.append_event(
                response_event,
                payload={
                    "reason": pre_guard.reason,
                    "patterns": pre_guard.matched_patterns,
                    "risk_score": 0.0,
                    "pii_entities": [],
                },
            )
            return {
                "ok": False,
                "blocked": True,
                "response": response_text,
                "reason": pre_guard.reason,
                "risk": None,
                "pii_entities": [],
            }

        # L1 stage 2: PII masking after payload validation.
        masking = self.pii_masker.mask_text(message)
        self.session_history[session_id].append(masking.masked_text)

        score = self.threat_scorer.score(masking.masked_text, history=self.session_history[session_id][:-1])
        guard = self.input_guard.evaluate(masking.masked_text, risk_score=score.total_score)

        if not guard.allowed:
            response_text = "Request blocked by AgentShield. Please rephrase your request safely."
            response_event = AgentEvent(
                event_type="blocked_input",
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=response_text,
            )
            self.audit_logger.append_event(
                response_event,
                payload={
                    "reason": guard.reason,
                    "patterns": guard.matched_patterns,
                    "risk_score": score.total_score,
                    "pii_entities": masking.entities,
                },
            )
            return {
                "ok": False,
                "blocked": True,
                "response": response_text,
                "reason": guard.reason,
                "risk": score.__dict__,
                "pii_entities": masking.entities,
            }

        tool_name, tool_args = self._plan(masking.masked_text)
        if tool_name in self.RISKY_TOOLS:
            approval_id = str(uuid.uuid4())
            pending = PendingAction(
                approval_id=approval_id,
                session_id=session_id,
                user_id=user_id,
                role=role,
                tool_name=tool_name,
                tool_args=tool_args,
                original_message=message,
            )
            self.pending_actions[approval_id] = pending
            self.audit_logger.append_event(
                AgentEvent(
                    event_type="hitl_required",
                    user_id=user_id,
                    session_id=session_id,
                    role=role,
                    content=f"Approval required for tool: {tool_name}",
                ),
                payload={"approval_id": approval_id, "tool_name": tool_name, "tool_args": tool_args},
            )
            return {
                "ok": True,
                "blocked": False,
                "response": f"High-risk action detected. Approval required with id: {approval_id}",
                "risk": score.__dict__,
                "pii_entities": masking.entities,
                "approval_required": True,
                "approval_id": approval_id,
            }

        execution = self._execute_tool(session_id, user_id, role, tool_name, tool_args)
        execution["risk"] = score.__dict__
        execution["pii_entities"] = masking.entities
        return execution

    def approve_action(self, approval_id: str, approved: bool) -> dict[str, Any]:
        pending = self.pending_actions.get(approval_id)
        if not pending:
            return {"ok": False, "error": "Invalid approval_id."}
        if not approved:
            self.audit_logger.append_event(
                AgentEvent(
                    event_type="hitl_rejected",
                    user_id=pending.user_id,
                    session_id=pending.session_id,
                    role=pending.role,
                    content=f"Approval rejected for {pending.tool_name}",
                ),
                payload={"approval_id": approval_id},
            )
            del self.pending_actions[approval_id]
            return {"ok": True, "response": "Action rejected by human reviewer."}

        result = self._execute_tool(
            session_id=pending.session_id,
            user_id=pending.user_id,
            role=pending.role,
            tool_name=pending.tool_name,
            tool_args=pending.tool_args,
        )
        del self.pending_actions[approval_id]
        return result

    def _plan(self, message: str) -> tuple[str, dict[str, Any]]:
        lower = message.lower()
        customer_id = self._extract_customer_id(message)
        if "balance" in lower:
            return "check_balance", {"customer_id": customer_id or "CUST1001"}
        if "update" in lower and "email" in lower:
            email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", message)
            new_email = email_match.group(0) if email_match else "updated@example.com"
            return "update_email", {"customer_id": customer_id or "CUST1001", "new_email": new_email}
        if "delete" in lower and "customer" in lower:
            return "delete_customer", {"customer_id": customer_id or "CUST1001"}
        return "rag_search", {"query": message}

    def _execute_tool(
        self,
        session_id: str,
        user_id: str,
        role: str,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> dict[str, Any]:
        access = self.access_control.is_tool_allowed(role, tool_name)
        if not access.allowed:
            response = f"Access denied. {access.reason}"
            self.audit_logger.append_event(
                AgentEvent(
                    event_type="access_denied",
                    user_id=user_id,
                    session_id=session_id,
                    role=role,
                    content=response,
                ),
                payload={"tool_name": tool_name, "tool_args": tool_args},
            )
            return {"ok": False, "blocked": True, "response": response}

        behavior = self.behavior_monitor.record_tool_call(session_id=session_id, role=role, tool_name=tool_name)
        tool_result = self.tool_registry.run(tool_name, **tool_args)
        safe_response = self.output_filter.sanitize(self._render_tool_result(tool_name, tool_result))

        self.audit_logger.append_event(
            AgentEvent(
                event_type="tool_execution",
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=safe_response,
            ),
            payload={
                "tool_name": tool_name,
                "tool_args": tool_args,
                "tool_result": tool_result,
                "behavior": behavior.__dict__,
            },
        )
        return {
            "ok": bool(tool_result.get("ok")),
            "blocked": False,
            "response": safe_response,
            "tool_name": tool_name,
            "tool_result": tool_result,
            "behavior": behavior.__dict__,
        }

    @staticmethod
    def _extract_customer_id(text: str) -> str | None:
        match = re.search(r"CUST\d{4}", text, re.IGNORECASE)
        return match.group(0).upper() if match else None

    @staticmethod
    def _render_tool_result(tool_name: str, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return result.get("error", "Tool failed.")
        if tool_name == "rag_search":
            source = result.get("source") or "unknown"
            return f"[{source}] {result.get('answer', '')}"
        if tool_name == "check_balance":
            return (
                f"Customer {result.get('customer_id')} ({result.get('full_name')}) has "
                f"balance {result.get('account_balance')}."
            )
        return result.get("message", "Action completed.")
