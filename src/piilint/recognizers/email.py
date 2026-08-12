"""Email recognizer (RFC-lite with @ pre-filter)."""

from __future__ import annotations

import re

from piilint.findings import EntityType
from piilint.recognizers import Match

# Practical RFC-lite: local@domain.tld — avoids catastrophic backtracking.
_EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+\-])"
    r"([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})"
    r"(?![A-Za-z0-9._%+\-])"
)

_CONTEXT_KEYS = frozenset(
    {
        "email",
        "e-mail",
        "mail",
        "email_address",
        "emailaddress",
        "user_email",
    }
)


class EmailRecognizer:
    entity = EntityType.EMAIL
    enabled_by_default = True

    def scan(self, text: str, *, context_key: str | None = None) -> list[Match]:
        if "@" not in text:
            return []
        boost = (
            0.25 if context_key and context_key.lower().replace(" ", "_") in _CONTEXT_KEYS else 0.0
        )
        matches: list[Match] = []
        for m in _EMAIL_RE.finditer(text):
            value = m.group(1)
            conf = min(0.95, 0.75 + boost)
            matches.append(
                Match(
                    entity=EntityType.EMAIL,
                    value=value,
                    start=m.start(1),
                    end=m.end(1),
                    confidence=conf,
                )
            )
        return matches
