"""IBAN recognizer with ISO 13616 mod-97 checksum."""

from __future__ import annotations

import re

from piilint.findings import EntityType
from piilint.recognizers import Match

_IBAN_RE = re.compile(
    r"(?<![A-Z0-9])"
    r"([A-Z]{2}\d{2}[A-Z0-9]{11,30})"
    r"(?![A-Z0-9])",
    re.IGNORECASE,
)

# Also allow spaced groups: GB82 WEST 1234 5698 7654 32
_IBAN_SPACED_RE = re.compile(
    r"(?<![A-Z0-9])"
    r"([A-Z]{2}\d{2}(?:\s[A-Z0-9]{4}){2,7}(?:\s[A-Z0-9]{1,4})?)"
    r"(?![A-Z0-9])",
    re.IGNORECASE,
)

_CONTEXT_KEYS = frozenset({"iban", "bank_account", "account_number", "accountnumber"})


def iban_mod97_valid(iban: str) -> bool:
    compact = re.sub(r"\s+", "", iban).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", compact):
        return False
    # Length sanity by country is complex; enforce overall bounds.
    if not (15 <= len(compact) <= 34):
        return False
    rearranged = compact[4:] + compact[:4]
    numeric = "".join(str(ord(ch) - 55) if ch.isalpha() else ch for ch in rearranged)
    return int(numeric) % 97 == 1


class IbanRecognizer:
    entity = EntityType.IBAN
    enabled_by_default = True

    def scan(self, text: str, *, context_key: str | None = None) -> list[Match]:
        boost = (
            0.2 if context_key and context_key.lower().replace(" ", "_") in _CONTEXT_KEYS else 0.0
        )
        matches: list[Match] = []
        seen: set[tuple[int, int]] = set()
        for pattern in (_IBAN_SPACED_RE, _IBAN_RE):
            for m in pattern.finditer(text):
                value = m.group(1)
                if not iban_mod97_valid(value):
                    continue
                span = (m.start(1), m.end(1))
                if span in seen:
                    continue
                # Prefer longer (spaced) match overlapping same region
                overlapping = any(not (span[1] <= s or span[0] >= e) for s, e in seen)
                if overlapping and " " not in value:
                    continue
                seen.add(span)
                conf = min(0.98, 0.95 + boost)
                matches.append(
                    Match(
                        entity=EntityType.IBAN,
                        value=value,
                        start=span[0],
                        end=span[1],
                        confidence=conf,
                    )
                )
        return matches
