"""Netherlands Burgerservicenummer (BSN) recognizer with 11-proef."""

from __future__ import annotations

import re

from piilint.findings import EntityType
from piilint.recognizers import Match

# 9 digits, optional spaces (e.g. 1234 56 789 or 123456789).
_BSN_RE = re.compile(
    r"(?<!\d)"
    r"(\d{9}|\d{4}\s\d{2}\s\d{3}|\d{3}\s\d{3}\s\d{3})"
    r"(?!\d)"
)

_CONTEXT_KEYS = frozenset(
    {
        "bsn",
        "bsn_nl",
        "burgerservicenummer",
        "sofinummer",
        "sofi",
    }
)

_CONTEXT_WORDS = re.compile(
    r"\b(bsn|burgerservicenummer|sofinummer)\b",
    re.IGNORECASE,
)


def bsn_11_proef_valid(digits: str) -> bool:
    """NL BSN elfproef: (9*d1+...+2*d8-1*d9) % 11 == 0; reject all-zero."""
    if len(digits) != 9 or not digits.isdigit():
        return False
    if digits == "000000000":
        return False
    vals = [int(c) for c in digits]
    total = (
        9 * vals[0]
        + 8 * vals[1]
        + 7 * vals[2]
        + 6 * vals[3]
        + 5 * vals[4]
        + 4 * vals[5]
        + 3 * vals[6]
        + 2 * vals[7]
        - 1 * vals[8]
    )
    return total % 11 == 0


class BsnNlRecognizer:
    entity = EntityType.BSN_NL
    enabled_by_default = False

    def scan(self, text: str, *, context_key: str | None = None) -> list[Match]:
        if not any(ch.isdigit() for ch in text):
            return []
        boost = (
            0.1
            if (
                (context_key and context_key.lower().replace(" ", "_") in _CONTEXT_KEYS)
                or _CONTEXT_WORDS.search(text)
            )
            else 0.0
        )
        matches: list[Match] = []
        seen: set[tuple[int, int]] = set()
        for m in _BSN_RE.finditer(text):
            value = m.group(1)
            digits = re.sub(r"\D", "", value)
            if not bsn_11_proef_valid(digits):
                continue
            span = (m.start(1), m.end(1))
            if span in seen:
                continue
            seen.add(span)
            conf = min(0.95, 0.88 + boost)
            matches.append(
                Match(
                    entity=EntityType.BSN_NL,
                    value=value,
                    start=span[0],
                    end=span[1],
                    confidence=conf,
                )
            )
        return matches
