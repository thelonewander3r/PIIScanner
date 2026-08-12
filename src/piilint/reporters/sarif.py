"""SARIF 2.1.0 reporter — suitable for github/codeql-action/upload-sarif.

Deterministic rule/result order. Findings carry masked samples only (never raw PII).
Severity mapping: high→error, medium→warning, low→note.
"""

from __future__ import annotations

import json
from typing import Any

from piilint import __version__
from piilint.engine import ScanResult
from piilint.findings import DEFAULT_SEVERITY, EntityType, Finding, Severity
from piilint.reporters.json_ import sort_findings

_SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
_SEVERITY_TO_LEVEL = {
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
}

_ENTITY_HELP = {
    EntityType.CREDIT_CARD: "Possible payment card number (Luhn-validated).",
    EntityType.SSN_US: "Possible US Social Security Number.",
    EntityType.IBAN: "Possible International Bank Account Number.",
    EntityType.EMAIL: "Possible email address.",
    EntityType.PHONE: "Possible phone number.",
    EntityType.DOB: "Possible date of birth (context-key signal).",
    EntityType.IP_ADDRESS: "Possible IP address.",
    EntityType.PERSON: "Possible person name (NER).",
    EntityType.ADDRESS: "Possible physical address (NER).",
}


def _rule_id(entity: EntityType) -> str:
    return entity.value


def _rules_for(findings: list[Finding]) -> list[dict[str, Any]]:
    entities = sorted({f.entity for f in findings}, key=lambda e: e.value)
    rules: list[dict[str, Any]] = []
    for entity in entities:
        default_level = _SEVERITY_TO_LEVEL[DEFAULT_SEVERITY[entity]]
        rules.append(
            {
                "id": _rule_id(entity),
                "name": entity.value,
                "shortDescription": {"text": f"Detect {entity.value}"},
                "fullDescription": {"text": _ENTITY_HELP.get(entity, f"Detect {entity.value}")},
                "defaultConfiguration": {"level": default_level},
            }
        )
    return rules


def _region(finding: Finding) -> dict[str, Any] | None:
    line = finding.location.line
    if line is not None and line >= 1:
        region: dict[str, Any] = {"startLine": line}
        return region
    return None


def _result(finding: Finding) -> dict[str, Any]:
    message = f"{finding.entity.value}: {finding.masked_sample}"
    if finding.matched_count > 1:
        summary = finding.extras.get("column_summary")
        if summary:
            message = f"{message} ({summary})"
    physical: dict[str, Any] = {
        "artifactLocation": {"uri": finding.location.path.replace("\\", "/")},
    }
    region = _region(finding)
    if region is not None:
        physical["region"] = region
    # Column-only tabular findings: surface column name in logical locations message
    if finding.location.column is not None and region is None:
        message = f"{message} [column {finding.location.column!r}]"

    return {
        "ruleId": _rule_id(finding.entity),
        "level": _SEVERITY_TO_LEVEL[finding.severity],
        "message": {"text": message},
        "locations": [{"physicalLocation": physical}],
        "partialFingerprints": {"piilint/fingerprint": finding.fingerprint},
    }


def build_sarif_document(result: ScanResult) -> dict[str, Any]:
    findings = sort_findings(list(result.findings))
    return {
        "$schema": _SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "piilint",
                        "version": __version__,
                        "informationUri": "https://github.com/thelonewander3r/PIIScanner",
                        "rules": _rules_for(findings),
                    }
                },
                "results": [_result(f) for f in findings],
            }
        ],
    }


def render_sarif(result: ScanResult) -> str:
    """Return deterministic SARIF 2.1.0 JSON text."""
    doc = build_sarif_document(result)
    return json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
