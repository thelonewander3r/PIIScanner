"""Post-match / pre-report policy: allowlists, suppressions, downweight, entity gates.

Inline suppressions apply to text/code line findings only. Tabular / column-
aggregated findings skip inline suppressions in v0 (no stable per-row line text).

This module must not import adapters or recognizer implementations — only
Finding / EntityType / Severity (and Config).
"""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Mapping
from dataclasses import replace

from piilint.config import Config
from piilint.findings import EntityType, Finding, Severity, normalize_value

# Trailing / anywhere: # piilint: ignore  OR  # piilint: ignore[EMAIL,PHONE]
_INLINE_IGNORE_RE = re.compile(
    r"#\s*piilint:\s*ignore(?:\[(?P<entities>[^\]]*)\])?",
    re.IGNORECASE,
)

_TEST_EMAIL_DOMAINS = frozenset({"example.com", "example.org", "example.net", "localhost"})
_TEST_DOMAIN_PREFIX = "test."

# NANP fictional block 555-01xx (also with country code / punctuation stripped)
_FAKE_PHONE_55501 = re.compile(r"55501\d{2}$")

_FAKE_CARD_DIGITS = "4111111111111111"

# RFC 5737 documentation IPv4 ranges + RFC 3849 / RFC 4193-ish docs IPv6
_RFC5737_NETWORKS = (
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("2001:db8::/32"),  # documentation
)


def _email_domain(normalized_email: str) -> str | None:
    if "@" not in normalized_email:
        return None
    return normalized_email.rsplit("@", 1)[-1].lower()


def is_allowlisted(finding: Finding, config: Config) -> bool:
    """True if finding should be dropped by allowlist values or email domains."""
    norm = finding.normalized_value
    if not norm:
        return False

    for allowed in config.allowlist.values:
        if normalize_value(allowed, finding.entity) == norm:
            return True

    if finding.entity == EntityType.EMAIL and config.allowlist.domains:
        domain = _email_domain(norm)
        if domain is not None and domain in {d.lower() for d in config.allowlist.domains}:
            return True
    return False


def is_test_data(finding: Finding) -> bool:
    """Heuristic test-data detector used for confidence downweight."""
    norm = finding.normalized_value
    if not norm:
        return False

    if finding.entity == EntityType.EMAIL:
        domain = _email_domain(norm)
        if domain is None:
            return False
        if domain in _TEST_EMAIL_DOMAINS:
            return True
        if domain.startswith(_TEST_DOMAIN_PREFIX):
            return True
        # also treat host "localhost" with any TLD-less form already covered
        labels = domain.split(".")
        return bool(labels and labels[0] == "test")

    if finding.entity == EntityType.PHONE:
        digits = re.sub(r"\D", "", norm)
        # strip leading country code 1 for NANP check
        if digits.startswith("1") and len(digits) == 11:
            digits = digits[1:]
        return _FAKE_PHONE_55501.search(digits) is not None

    if finding.entity == EntityType.CREDIT_CARD:
        digits = re.sub(r"\D", "", norm)
        return digits == _FAKE_CARD_DIGITS

    if finding.entity == EntityType.IP_ADDRESS:
        try:
            addr = ipaddress.ip_address(norm)
        except ValueError:
            return False
        return any(addr in net for net in _RFC5737_NETWORKS)

    return False


def parse_inline_suppression(line: str) -> frozenset[EntityType] | None:
    """Return entities to suppress on this line, empty frozenset = all, or None."""
    match = _INLINE_IGNORE_RE.search(line)
    if match is None:
        return None
    entities_raw = match.group("entities")
    if entities_raw is None:
        return frozenset()  # suppress all
    names = [part.strip() for part in entities_raw.split(",") if part.strip()]
    if not names:
        return frozenset()
    out: set[EntityType] = set()
    for name in names:
        upper = name.upper()
        try:
            out.add(EntityType(upper))
        except ValueError:
            # Unknown entity token in ignore list — ignore that token only
            continue
    return frozenset(out)


def is_inline_suppressed(
    finding: Finding,
    line_texts: Mapping[tuple[str, int], str] | None,
) -> bool:
    """Inline suppressions for text/code line findings only (v0)."""
    if line_texts is None:
        return False
    # Column-aggregated / tabular findings have no line number — skip
    if finding.location.line is None:
        return False
    if finding.location.column is not None and finding.matched_count > 1:
        return False
    key = (finding.location.path, finding.location.line)
    line = line_texts.get(key)
    if line is None:
        return False
    suppressed = parse_inline_suppression(line)
    if suppressed is None:
        return False
    if len(suppressed) == 0:
        return True
    return finding.entity in suppressed


def apply_policy(
    findings: list[Finding],
    config: Config,
    *,
    line_texts: Mapping[tuple[str, int], str] | None = None,
) -> list[Finding]:
    """Filter and adjust findings. Runs after recognition, before reporters."""
    kept: list[Finding] = []
    min_conf = config.scan.min_confidence

    for finding in findings:
        if not config.is_entity_enabled(finding.entity):
            continue

        if is_inline_suppressed(finding, line_texts):
            continue

        if is_allowlisted(finding, config):
            continue

        severity = config.severity_for(finding.entity)
        confidence = finding.confidence

        if is_test_data(finding):
            confidence = max(0.0, confidence - 0.4)
            severity = Severity.LOW

        if confidence < min_conf:
            continue

        if severity != finding.severity or confidence != finding.confidence:
            finding = replace(finding, severity=severity, confidence=confidence)

        kept.append(finding)

    kept.sort(
        key=lambda f: (
            f.location.path,
            f.location.line if f.location.line is not None else -1,
            f.location.row if f.location.row is not None else -1,
            f.location.cell if f.location.cell is not None else -1,
            f.location.column or "",
            f.entity.value,
            f.fingerprint,
        )
    )
    return kept
