from __future__ import annotations

import re
from dataclasses import dataclass

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine

    PRESIDIO_AVAILABLE = True
except Exception:
    PRESIDIO_AVAILABLE = False
    AnalyzerEngine = None  # type: ignore[assignment]
    AnonymizerEngine = None  # type: ignore[assignment]


@dataclass
class MaskingResult:
    masked_text: str
    entities: list[str]
    used_presidio: bool


class PIIMasker:
    def __init__(self) -> None:
        self._analyzer = AnalyzerEngine() if PRESIDIO_AVAILABLE else None
        self._anonymizer = AnonymizerEngine() if PRESIDIO_AVAILABLE else None
        self._fallback_patterns = {
            "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
            "PHONE": re.compile(r"\b(?:\+?\d{1,3}[- ]?)?\d{10}\b"),
            "AADHAAR": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
        }

    def mask_text(self, text: str) -> MaskingResult:
        if self._analyzer and self._anonymizer:
            results = self._analyzer.analyze(text=text, language="en")
            if not results:
                return MaskingResult(masked_text=text, entities=[], used_presidio=True)
            entities = sorted({res.entity_type for res in results})
            anonymized = self._anonymizer.anonymize(text=text, analyzer_results=results)
            return MaskingResult(masked_text=anonymized.text, entities=entities, used_presidio=True)

        masked = text
        entities: list[str] = []
        for entity, pattern in self._fallback_patterns.items():
            if pattern.search(masked):
                entities.append(entity)
                masked = pattern.sub(f"<{entity}>", masked)
        return MaskingResult(masked_text=masked, entities=entities, used_presidio=False)

