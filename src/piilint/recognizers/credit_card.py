"""Credit card recognizer with Luhn + brand/length checks."""

from __future__ import annotations

import re

from piilint.findings import EntityType
from piilint.recognizers import Match

_CARD_RE = re.compile(
    r"(?<!\d)"
    r"((?:\d[ \-]?){13,19})"
    r"(?!\d)"
)

_CONTEXT_KEYS = frozenset(
    {
        "card",
        "credit_card",
        "creditcard",
        "card_number",
        "cardnumber",
        "pan",
        "cc",
        "ccnum",
    }
)


def luhn_valid(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if not digits:
        return False
    checksum = 0
    for idx, digit in enumerate(reversed(digits)):
        if idx % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def brand_and_length_ok(digits: str) -> bool:
    length = len(digits)
    if digits.startswith("4") and length in {13, 16, 19}:  # Visa
        return True
    # Mastercard 51-55 or 2221-2720
    if digits.startswith(("51", "52", "53", "54", "55")) and length == 16:
        return True
    if length == 16 and digits[:4].isdigit() and 2221 <= int(digits[:4]) <= 2720:
        return True
    if digits.startswith(("34", "37")) and length == 15:  # Amex
        return True
    if digits.startswith(("6011", "65")) and length == 16:  # Discover (simplified)
        return True
    return digits.startswith("35") and length == 16  # JCB simplified


class CreditCardRecognizer:
    entity = EntityType.CREDIT_CARD
    enabled_by_default = True

    def scan(self, text: str, *, context_key: str | None = None) -> list[Match]:
        if not any(ch.isdigit() for ch in text):
            return []
        boost = (
            0.2 if context_key and context_key.lower().replace(" ", "_") in _CONTEXT_KEYS else 0.0
        )
        matches: list[Match] = []
        for m in _CARD_RE.finditer(text):
            value = m.group(1).strip()
            digits = re.sub(r"\D", "", value)
            if len(digits) < 13 or len(digits) > 19:
                continue
            if not brand_and_length_ok(digits):
                continue
            if not luhn_valid(digits):
                continue
            conf = min(0.98, 0.95 + boost)
            matches.append(
                Match(
                    entity=EntityType.CREDIT_CARD,
                    value=value,
                    start=m.start(1),
                    end=m.end(1),
                    confidence=conf,
                )
            )
        return matches
