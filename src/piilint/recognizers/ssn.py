"""US Social Security Number recognizer."""

from __future__ import annotations

import re

from piilint.findings import EntityType
from piilint.recognizers import Match

_SSN_RE = re.compile(
    r"(?<!\d)"
    r"(\d{3}[-\s]?\d{2}[-\s]?\d{4})"
    r"(?!\d)"
)

_CONTEXT_KEYS = frozenset(
    {
        "ssn",
        "social",
        "social_security",
        "socialsecurity",
        "social_security_number",
        "tin",
    }
)

_CONTEXT_WORDS = re.compile(
    r"\b(ssn|social\s*security|taxpayer\s*id)\b",
    re.IGNORECASE,
)


def _valid_ssn(digits: str) -> bool:
    if len(digits) != 9 or not digits.isdigit():
        return False
    area, group, serial = digits[:3], digits[3:5], digits[5:]
    if area == "000" or area == "666" or area.startswith("9"):
        return False
    return not (group == "00" or serial == "0000")


class SsnUsRecognizer:
    entity = EntityType.SSN_US
    enabled_by_default = True

    def scan(self, text: str, *, context_key: str | None = None) -> list[Match]:
        if not any(ch.isdigit() for ch in text):
            return []
        key_boost = (
            0.3 if context_key and context_key.lower().replace(" ", "_") in _CONTEXT_KEYS else 0.0
        )
        word_boost = 0.15 if _CONTEXT_WORDS.search(text) else 0.0
        matches: list[Match] = []
        for m in _SSN_RE.finditer(text):
            value = m.group(1)
            digits = re.sub(r"\D", "", value)
            if not _valid_ssn(digits):
                continue
            # Bare pattern is weak without context; still emit with lower confidence
            # so tabular column context / nearby words can clear the min_confidence gate.
            base = 0.55
            conf = min(0.95, base + key_boost + word_boost)
            matches.append(
                Match(
                    entity=EntityType.SSN_US,
                    value=value,
                    start=m.start(1),
                    end=m.end(1),
                    confidence=conf,
                )
            )
        return matches
