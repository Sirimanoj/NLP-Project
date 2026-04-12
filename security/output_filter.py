from __future__ import annotations

import re


class OutputFilter:
    def __init__(self) -> None:
        self.sensitive_patterns = [
            re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}\b"),  # Aadhaar-like
            re.compile(r"\b(?:\+?\d{1,3}[- ]?)?\d{10}\b"),  # phone
            re.compile(r"system prompt", re.IGNORECASE),
        ]

    def sanitize(self, text: str) -> str:
        cleaned = text
        for pattern in self.sensitive_patterns:
            cleaned = pattern.sub("[REDACTED]", cleaned)
        return cleaned

