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

    def __init__(
        self,
        default_region: str = "US",
        extra_regions: list[str] | None = None,
    ) -> None:
        primary = (default_region or "US").strip().upper() or "US"
        extras = [
            r.strip().upper() for r in (extra_regions or []) if isinstance(r, str) and r.strip()
        ]
        # Primary first, then extras; dedupe while preserving order.
        regions: list[str] = []
        for region in [primary, *extras]:
            if region and region not in regions:
                regions.append(region)
        self.default_region = primary
        self.extra_regions = [r for r in regions if r != primary]
        self._regions = regions

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
            parsed = None
            for region in self._regions:
                try:
                    candidate_parsed = phonenumbers.parse(candidate, region)
                except phonenumbers.NumberParseException:
                    continue
                if phonenumbers.is_valid_number(candidate_parsed):
                    parsed = candidate_parsed
                    break
            if parsed is None:
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
