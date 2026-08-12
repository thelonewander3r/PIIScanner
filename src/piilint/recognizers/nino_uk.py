"""UK National Insurance Number (NINO) recognizer — format + required context."""

from __future__ import annotations

import re

from piilint.findings import EntityType
from piilint.recognizers import Match

# First letter not D/F/I/Q/U/V; second not D/F/I/O/Q/U/V; 6 digits; suffix A-D.
_NINO_RE = re.compile(
    r"(?<![A-Z0-9])"
    r"([A-CEGHJ-PR-TW-Z]{1}[A-CEGHJ-NPR-TW-Z]{1}"
    r"\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D])"
    r"(?![A-Z0-9])",
    re.IGNORECASE,
)

_DISALLOWED_PREFIXES = frozenset({"BG", "GB", "NK", "KN", "TN", "NT", "ZZ"})

_CONTEXT_KEYS = frozenset(
    {
        "nino",
        "nino_uk",
        "ni",
        "national_insurance",
        "nationalinsurance",
        "ni_number",
        "ninumber",
    }
)

_CONTEXT_WORDS = re.compile(
    r"\b(nino|national\s*insurance|NI)\b",
    re.IGNORECASE,
)


def _has_context(text: str, context_key: str | None) -> bool:
    if context_key:
        key = context_key.lower().replace(" ", "_")
        if key in _CONTEXT_KEYS:
            return True
    return _CONTEXT_WORDS.search(text) is not None


def _nino_format_ok(value: str) -> bool:
    compact = re.sub(r"\s+", "", value).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{6}[A-D]", compact):
        return False
    if compact[:2] in _DISALLOWED_PREFIXES:
        return False
    first, second = compact[0], compact[1]
    if first in "DFIQUV":
        return False
    return second not in "DFIOQUV"


class NinoUkRecognizer:
    entity = EntityType.NINO_UK
    enabled_by_default = False

    def scan(self, text: str, *, context_key: str | None = None) -> list[Match]:
        # Context is mandatory — do not emit without it.
        if not _has_context(text, context_key):
            return []
        matches: list[Match] = []
        for m in _NINO_RE.finditer(text):
            value = m.group(1)
            if not _nino_format_ok(value):
                continue
            matches.append(
                Match(
                    entity=EntityType.NINO_UK,
                    value=value,
                    start=m.start(1),
                    end=m.end(1),
                    confidence=0.9,
                )
            )
        return matches
