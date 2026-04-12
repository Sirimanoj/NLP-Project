from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BehaviorDecision:
    anomaly_score: float
    alerts: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class BehaviorMonitor:
    def __init__(self, anomaly_threshold: float = 70.0) -> None:
        self.anomaly_threshold = anomaly_threshold
        self.role_tool_baseline: dict[str, Counter[str]] = defaultdict(Counter)
        self.session_tool_counts: dict[str, Counter[str]] = defaultdict(Counter)
        self.session_call_total: Counter[str] = Counter()

    def record_tool_call(self, session_id: str, role: str, tool_name: str) -> BehaviorDecision:
        self.session_tool_counts[session_id][tool_name] += 1
        self.session_call_total[session_id] += 1
        self.role_tool_baseline[role][tool_name] += 1

        alerts: list[str] = []
        score = 0.0

        # Burst detection for repeated tool call.
        repeat_count = self.session_tool_counts[session_id][tool_name]
        if repeat_count >= 5:
            alerts.append(f"Tool '{tool_name}' used {repeat_count} times in this session.")
            score += 35

        # Session saturation.
        total_calls = self.session_call_total[session_id]
        if total_calls >= 20:
            alerts.append(f"High tool-call volume in session ({total_calls}).")
            score += 20

        # Role novelty detection once baseline has enough samples.
        role_counts = self.role_tool_baseline[role]
        if sum(role_counts.values()) >= 15 and role_counts[tool_name] == 1:
            alerts.append(f"Role '{role}' invoked new tool '{tool_name}' outside baseline.")
            score += 45

        score = float(max(0.0, min(100.0, score)))
        details = {
            "session_tool_counts": dict(self.session_tool_counts[session_id]),
            "session_total_calls": total_calls,
            "role_baseline_size": sum(role_counts.values()),
            "threshold": self.anomaly_threshold,
            "is_anomalous": score >= self.anomaly_threshold,
        }
        return BehaviorDecision(anomaly_score=score, alerts=alerts, details=details)

