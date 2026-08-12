"""JSON reporter — schema_version 1, deterministic, masked-only findings.

``config_hash`` is SHA-256 of a canonical JSON object built from the effective
scan Config fields that affect detection/policy (fail_on, min_confidence,
exclude, entity_enabled, severity_overrides, allowlists, phone_region).
Volatile paths and timestamps are excluded so the hash is stable across runs
with the same policy.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

from piilint import __version__
from piilint.config import Config
from piilint.engine import ScanResult
from piilint.findings import EntityType, Finding, Severity


def config_hash(config: Config) -> str:
    """SHA-256 hex digest of the effective Config (canonical JSON, sorted keys)."""
    entity_enabled = {
        entity.value: bool(config.entity_enabled.get(entity, True))
        for entity in sorted(EntityType, key=lambda e: e.value)
    }
    severity_overrides = {
        entity.value: severity.value
        for entity, severity in sorted(
            config.severity_overrides.items(), key=lambda item: item[0].value
        )
    }
    payload: dict[str, Any] = {
        "allowlist_domains": sorted(config.allowlist.domains),
        "allowlist_values": sorted(config.allowlist.values),
        "entity_enabled": entity_enabled,
        "exclude": sorted(config.scan.exclude),
        "fail_on": config.scan.fail_on,
        "min_confidence": config.scan.min_confidence,
        "phone_region": config.scan.phone_region,
        "severity_overrides": severity_overrides,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _line_or_row(finding: Finding) -> int:
    loc = finding.location
    if loc.line is not None:
        return loc.line
    if loc.row is not None:
        return loc.row
    return -1


def sort_findings(findings: list[Finding]) -> list[Finding]:
    """Stable sort: path, line/row, entity, fingerprint."""
    return sorted(
        findings,
        key=lambda f: (f.location.path, _line_or_row(f), f.entity.value, f.fingerprint),
    )


def _finding_record(finding: Finding) -> dict[str, Any]:
    loc = finding.location
    return {
        "cell": loc.cell,
        "column": loc.column,
        "confidence": finding.confidence,
        "entity": finding.entity.value,
        "fingerprint": finding.fingerprint,
        "line": loc.line,
        "masked_sample": finding.masked_sample,
        "matched_count": finding.matched_count,
        "path": loc.path,
        "row": loc.row,
        "severity": finding.severity.value,
        "value_sha256": finding.value_sha256,
    }


def build_json_document(result: ScanResult, config: Config) -> dict[str, Any]:
    """Build the schema_version 1 document (no raw PII fields)."""
    findings = sort_findings(list(result.findings))
    counts = Counter(f.severity for f in findings)
    return {
        "config_hash": config_hash(config),
        "findings": [_finding_record(f) for f in findings],
        "schema_version": 1,
        "summary": {
            "by_severity": {
                "high": counts[Severity.HIGH],
                "low": counts[Severity.LOW],
                "medium": counts[Severity.MEDIUM],
            },
            "elapsed_seconds": result.elapsed_seconds,
            "files_scanned": result.files_scanned,
            "findings": len(findings),
        },
        "tool": {"name": "piilint", "version": __version__},
    }


def render_json(result: ScanResult, config: Config) -> str:
    """Return deterministic JSON text (sorted keys, indent=2, trailing newline)."""
    doc = build_json_document(result, config)
    return json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
