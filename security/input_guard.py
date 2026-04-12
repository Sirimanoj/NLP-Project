from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field

from security.pii_masker import PIIMasker


@dataclass
class GuardDecision:
    allowed: bool
    reason: str
    matched_patterns: list[str] = field(default_factory=list)
    risk_score: float = 0.0


class InputGuard:
    DEFAULT_PATTERNS = [
        r"ignore\s+previous\s+instructions",
        r"ignore\s+all\s+rules",
        r"reveal\s+(all\s+)?(records|data|secrets)",
        r"developer\s+mode",
        r"bypass\s+(safety|guard|policy)",
        r"system\s+prompt",
        r"delete\s+all(\s+\w+){0,3}\s+records",
        r"override\s+(rules|instructions)",
        r"pretend\s+(you\s+are|to\s+be)",
        r"disregard\s+(all|your)\s+(rules|instructions|policies)",
    ]
    ZERO_WIDTH_CHARS = ["\u200b", "\u200c", "\u200d", "\u200e", "\u200f", "\ufeff"]
    ATTACK_KEYWORDS = ("ignore", "pretend", "jailbreak", "override", "bypass", "system prompt")
    EMOJI_RE = re.compile(
        "["  # Basic emoji ranges sufficient for a practical heuristic.
        "\U0001F300-\U0001F5FF"
        "\U0001F600-\U0001F64F"
        "\U0001F680-\U0001F6FF"
        "\U0001F700-\U0001F77F"
        "\U0001F900-\U0001F9FF"
        "\U0001FA70-\U0001FAFF"
        "\u2600-\u27BF"
        "]",
        flags=re.UNICODE,
    )

    def __init__(self, risk_threshold: float = 70.0, patterns: list[str] | None = None) -> None:
        self.risk_threshold = risk_threshold
        self.patterns = [re.compile(p, re.IGNORECASE) for p in (patterns or self.DEFAULT_PATTERNS)]

    def check_steganography(self, text: str) -> tuple[bool, str]:
        # 1) Zero-width hidden characters.
        if any(char in text for char in self.ZERO_WIDTH_CHARS):
            return True, "zero_width_unicode_payload"

        # 2) Suspicious base64 token with decoded attack intent.
        for token in text.split():
            if len(token) <= 20:
                continue
            if not re.fullmatch(r"[A-Za-z0-9+/=]+", token):
                continue
            padded = token + ("=" * ((4 - len(token) % 4) % 4))
            try:
                decoded = base64.b64decode(padded, validate=True).decode("utf-8", errors="ignore")
            except Exception:
                continue
            decoded_lower = decoded.lower()
            if any(keyword in decoded_lower for keyword in self.ATTACK_KEYWORDS):
                return True, "base64_obfuscated_instruction"

        # 3) Emoji-density heuristic for short, highly encoded payloads.
        emoji_count = len(self.EMOJI_RE.findall(text))
        word_count = len(text.split())
        if emoji_count > 5 and word_count < 50:
            return True, "emoji_dense_obfuscation"

        return False, ""

    def evaluate(self, text: str, risk_score: float | None = None) -> GuardDecision:
        # Steganography must be checked before prompt-injection regex.
        stego_hit, stego_reason = self.check_steganography(text)
        if stego_hit:
            return GuardDecision(
                allowed=False,
                reason=f"Blocked by steganography detector ({stego_reason}).",
                matched_patterns=[stego_reason],
                risk_score=risk_score or 0.0,
            )

        matches = [p.pattern for p in self.patterns if p.search(text)]
        if matches:
            return GuardDecision(
                allowed=False,
                reason="Blocked by prompt-injection signature rules.",
                matched_patterns=matches,
                risk_score=risk_score or 0.0,
            )
        if risk_score is not None and risk_score >= self.risk_threshold:
            return GuardDecision(
                allowed=False,
                reason=f"Blocked by risk threshold ({risk_score:.1f} >= {self.risk_threshold:.1f}).",
                matched_patterns=[],
                risk_score=risk_score,
            )
        return GuardDecision(
            allowed=True,
            reason="Input accepted.",
            matched_patterns=[],
            risk_score=risk_score or 0.0,
        )


_DEFAULT_GUARD = InputGuard()
_DEFAULT_MASKER = PIIMasker()


def guard_input(text: str) -> dict[str, str | bool]:
    """Convenience function for module-level guard checks in tests/scripts.

    Enforces: stego check -> regex check -> PII masking.
    """
    decision = _DEFAULT_GUARD.evaluate(text, risk_score=None)
    if not decision.allowed:
        return {"blocked": True, "reason": decision.reason, "clean": text}
    masked = _DEFAULT_MASKER.mask_text(text)
    return {"blocked": False, "reason": "", "clean": masked.masked_text}
