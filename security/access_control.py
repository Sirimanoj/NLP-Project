from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AccessDecision:
    allowed: bool
    reason: str


class AccessController:
    DEFAULT_POLICY = {
        "user": {"rag_search", "check_balance", "update_email"},
        "admin": {"rag_search", "check_balance", "update_email", "delete_customer"},
    }

    def __init__(self, policy: dict[str, set[str]] | None = None) -> None:
        self.policy = policy or self.DEFAULT_POLICY

    def is_tool_allowed(self, role: str, tool_name: str) -> AccessDecision:
        allowed_tools = self.policy.get(role, set())
        if tool_name in allowed_tools:
            return AccessDecision(allowed=True, reason=f"Role '{role}' allowed to use '{tool_name}'.")
        return AccessDecision(allowed=False, reason=f"Role '{role}' cannot use tool '{tool_name}'.")

