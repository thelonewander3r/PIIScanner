"""Canada Social Insurance Number (SIN) recognizer with Luhn."""

from __future__ import annotations

import re

from piilint.findings import EntityType
from piilint.recognizers import Match

# Separated: XXX-XXX-XXX or XXX XXX XXX (preferred; high confidence when Luhn passes).
_SIN_SEP_RE = re.compile(
    r"(?<!\d)"
    r"(\d{3}[-\s]\d{3}[-\s]\d{3})"
    r"(?!\d)"
)

# Bare 9 digits — only emit with SIN context (precision over recall).
_SIN_BARE_RE = re.compile(
    r"(?<!\d)"
    r"(\d{9})"
    r"(?!\d)"
)

_CONTEXT_KEYS = frozenset(
    {
        "sin",
        "sin_ca",
        "social_insurance",
        "socialinsurance",
        "social_insurance_number",
        "nas",  # French: numero d'assurance sociale
    }
)

_CONTEXT_WORDS = re.compile(
    r"\b(sin|social\s*insurance|numero\s*d['']assurance\s*sociale|nas)\b",
    re.IGNORECASE,
)


def luhn_valid(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) != 9:
        return False
    checksum = 0
    for idx, digit in enumerate(reversed(digits)):
        if idx % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _has_context(text: str, context_key: str | None) -> bool:
    if context_key and context_key.lower().replace(" ", "_") in _CONTEXT_KEYS:
        return True
    return _CONTEXT_WORDS.search(text) is not None


class SinCaRecognizer:
    entity = EntityType.SIN_CA
    enabled_by_default = True

    def scan(self, text: str, *, context_key: str | None = None) -> list[Match]:
        if not any(ch.isdigit() for ch in text):
            return []
        ctx = _has_context(text, context_key)
        matches: list[Match] = []
        seen: set[tuple[int, int]] = set()

        for m in _SIN_SEP_RE.finditer(text):
            value = m.group(1)
            digits = re.sub(r"\D", "", value)
            if not luhn_valid(digits):
                continue
            span = (m.start(1), m.end(1))
            if span in seen:
                continue
            seen.add(span)
            conf = 0.92 if ctx else 0.85
            matches.append(
                Match(
                    entity=EntityType.SIN_CA,
                    value=value,
                    start=span[0],
                    end=span[1],
                    confidence=conf,
                )
            )

        if ctx:
            for m in _SIN_BARE_RE.finditer(text):
                value = m.group(1)
                if not luhn_valid(value):
                    continue
                span = (m.start(1), m.end(1))
                # Skip if already covered by a separated match overlapping this span.
                if any(not (span[1] <= s or span[0] >= e) for s, e in seen):
                    continue
                seen.add(span)
                matches.append(
                    Match(
                        entity=EntityType.SIN_CA,
                        value=value,
                        start=span[0],
                        end=span[1],
                        confidence=0.8,
                    )
                )
        return matches
