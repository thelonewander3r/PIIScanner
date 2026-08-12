"""Date of birth recognizer — only with column/key-name context."""

from __future__ import annotations

import re

from piilint.findings import EntityType
from piilint.recognizers import Match

# Common date shapes; intentionally requires context_key — never bare dates in prose.
_DATE_RE = re.compile(
    r"(?<!\d)"
    r"("
    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"
    r"|"
    r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"
    r")"
    r"(?!\d)"
)

_CONTEXT_KEYS = frozenset(
    {
        "dob",
        "date_of_birth",
        "dateofbirth",
        "birth_date",
        "birthdate",
        "birthday",
        "born",
        "birth",
    }
)


class DobRecognizer:
    entity = EntityType.DOB
    enabled_by_default = True

    def scan(self, text: str, *, context_key: str | None = None) -> list[Match]:
        if not context_key:
            return []
        key = context_key.lower().replace(" ", "_")
        if key not in _CONTEXT_KEYS:
            return []
        matches: list[Match] = []
        for m in _DATE_RE.finditer(text):
            matches.append(
                Match(
                    entity=EntityType.DOB,
                    value=m.group(1),
                    start=m.start(1),
                    end=m.end(1),
                    confidence=0.85,
                )
            )
        return matches
