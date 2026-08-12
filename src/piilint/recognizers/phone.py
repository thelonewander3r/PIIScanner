"""US phone recognizer via phonenumbers."""

from __future__ import annotations

import re

import phonenumbers

from piilint.findings import EntityType
from piilint.recognizers import Match

# Candidate spans: +country or common NA formats.
_PHONE_CANDIDATE_RE = re.compile(
    r"(?<!\w)"
    r"("
    r"\+?\d[\d\s\-().]{7,20}\d"
    r")"
    r"(?!\w)"
)

_CONTEXT_KEYS = frozenset(
    {
        "phone",
        "mobile",
        "cell",
        "telephone",
        "tel",
        "phone_number",
        "phonenumber",
    }
)


class PhoneRecognizer:
    entity = EntityType.PHONE
    enabled_by_default = True

    def __init__(self, default_region: str = "US") -> None:
        self.default_region = default_region

    def scan(self, text: str, *, context_key: str | None = None) -> list[Match]:
        if not any(ch.isdigit() for ch in text):
            return []
        boost = (
            0.25 if context_key and context_key.lower().replace(" ", "_") in _CONTEXT_KEYS else 0.0
        )
        matches: list[Match] = []
        seen: set[tuple[int, int]] = set()
        for m in _PHONE_CANDIDATE_RE.finditer(text):
            candidate = m.group(1)
            digits = re.sub(r"\D", "", candidate)
            # Reject short / year-ish fragments (e.g. 2026-884421 order ids).
            if len(digits) < 10 or len(digits) > 15:
                continue
            if re.fullmatch(r"20\d{2}\d{6,}", digits):
                continue
            try:
                parsed = phonenumbers.parse(candidate, self.default_region)
            except phonenumbers.NumberParseException:
                continue
            if not phonenumbers.is_valid_number(parsed):
                continue
            start, end = m.start(1), m.end(1)
            if (start, end) in seen:
                continue
            seen.add((start, end))
            conf = min(0.95, 0.85 + boost)
            matches.append(
                Match(
                    entity=EntityType.PHONE,
                    value=candidate.strip(),
                    start=start,
                    end=end,
                    confidence=conf,
                )
            )
        return matches
