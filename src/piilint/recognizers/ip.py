"""IPv4 / IPv6 syntactic recognizer (default off — noisy in code)."""

from __future__ import annotations

import ipaddress
import re

from piilint.findings import EntityType, Severity
from piilint.recognizers import Match

_IPV4_RE = re.compile(
    r"(?<!\d)"
    r"((?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3})"
    r"(?!\d)"
)

_IPV6_RE = re.compile(
    r"(?<![A-Za-z0-9:])"
    r"((?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}|::1|::)"
    r"(?![A-Za-z0-9:])"
)


class IpAddressRecognizer:
    entity = EntityType.IP_ADDRESS
    enabled_by_default = False

    def scan(self, text: str, *, context_key: str | None = None) -> list[Match]:
        del context_key
        matches: list[Match] = []
        for pattern in (_IPV4_RE, _IPV6_RE):
            for m in pattern.finditer(text):
                value = m.group(1)
                try:
                    ipaddress.ip_address(value)
                except ValueError:
                    continue
                matches.append(
                    Match(
                        entity=EntityType.IP_ADDRESS,
                        value=value,
                        start=m.start(1),
                        end=m.end(1),
                        confidence=0.7,
                        severity=Severity.LOW,
                    )
                )
        return matches
