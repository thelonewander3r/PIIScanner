"""Metadata-only findings payload (trust boundary).

Builds sync-shaped records from local findings: fingerprints and policy hashes
only — never raw paths, locations, masked samples, or match values.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from piilint import __version__
from piilint.config import Config
from piilint.findings import EntityType, Finding, Severity
from piilint.reporters.json_ import config_hash

# Local / sync metadata schema (TEAM_LAYER §3). Distinct from JSON reporter schema_version.
METADATA_SCHEMA_VERSION = 1

ALLOWED_FINDING_KEYS: frozenset[str] = frozenset(
    {
        "entity",
        "severity",
        "finding_fingerprint",
        "path_fingerprint",
        "value_fingerprint",
        "config_hash",
        "scanned_at",
        "repo_id",
        "tool_version",
        "schema_version",
    }
)

REQUIRED_FINDING_KEYS: frozenset[str] = frozenset(
    {
        "entity",
        "severity",
        "finding_fingerprint",
        "path_fingerprint",
        "value_fingerprint",
        "config_hash",
        "scanned_at",
        "tool_version",
        "schema_version",
    }
)

# Keys that must never appear in metadata JSON / DB-serialized rows.
_SHA256_HEX = re.compile(r"^[a-f0-9]{64}$")
_CANONICAL_SCANNED_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_ENTITY_VALUES = frozenset(e.value for e in EntityType)
_SEVERITY_VALUES = frozenset(s.value for s in Severity)

FORBIDDEN_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "path",
        "line",
        "row",
        "column",
        "cell",
        "cell_part",
        "masked_sample",
        "normalized_value",
        "raw",
        "raw_value",
        "value",
        "match",
        "matches",
        "show_matches",
        "offset",
        "confidence",
        "location",
        "extras",
        "file_bytes",
        "content",
        "text",
    }
)


def normalize_relative_path(path: str) -> str:
    """Normalize a relative path to forward slashes for hashing."""
    normalized = path.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def workspace_repo_id(scan_root: Path) -> str:
    """Deterministic opaque workspace id from scan/git root (never a raw path)."""
    resolved = scan_root.resolve()
    try:
        from piilint.gitutil import GitError, find_repo_root

        root = find_repo_root(resolved)
    except GitError:
        root = resolved.parent if resolved.is_file() else resolved
    material = normalize_relative_path(str(root))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def normalize_scanned_at(value: str) -> str:
    """Return canonical UTC ``YYYY-MM-DDTHH:MM:SSZ`` or raise ValueError."""
    raw = value.strip()
    if not raw:
        raise ValueError("scanned_at must be a non-empty UTC timestamp")
    if _CANONICAL_SCANNED_AT.fullmatch(raw):
        return raw
    if "." in raw:
        raise ValueError("scanned_at must not include fractional seconds")
    iso = raw
    if iso.endswith(("Z", "z")):
        iso = iso[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(iso)
    except ValueError as exc:
        raise ValueError(
            "scanned_at must be canonical UTC (YYYY-MM-DDTHH:MM:SSZ) or ISO with offset"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def path_fingerprint(path: str) -> str:
    """SHA-256 of the normalized relative path (never the raw path string in payloads)."""
    material = normalize_relative_path(path)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def finding_to_metadata(
    finding: Finding,
    *,
    config: Config,
    scanned_at: str,
    repo_id: str | None = None,
    tool_version: str | None = None,
    schema_version: int = METADATA_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Build one metadata record from a Finding + effective Config."""
    record: dict[str, Any] = {
        "config_hash": config_hash(config),
        "entity": finding.entity.value,
        "finding_fingerprint": finding.fingerprint,
        "path_fingerprint": path_fingerprint(finding.location.path),
        "scanned_at": scanned_at,
        "schema_version": schema_version,
        "severity": finding.severity.value,
        "tool_version": tool_version if tool_version is not None else __version__,
        "value_fingerprint": finding.value_sha256,
    }
    if repo_id is not None:
        record["repo_id"] = repo_id
    validate_metadata_record(record)
    return record


def build_metadata_document(
    findings: Iterable[Finding],
    config: Config,
    *,
    scanned_at: datetime | None = None,
    repo_id: str | None = None,
) -> dict[str, Any]:
    """Build a metadata-only document suitable for local export / future sync."""
    when = scanned_at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    scanned_at_iso = when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cfg_hash = config_hash(config)
    records = [
        finding_to_metadata(
            f,
            config=config,
            scanned_at=scanned_at_iso,
            repo_id=repo_id,
        )
        for f in findings
    ]
    # Stable order for deterministic JSON
    records.sort(key=lambda r: (r["finding_fingerprint"], r["entity"], r["severity"]))
    for record in records:
        validate_metadata_record(record)
    return {
        "config_hash": cfg_hash,
        "findings": records,
        "schema_version": METADATA_SCHEMA_VERSION,
        "scanned_at": scanned_at_iso,
        "tool": {"name": "piilint", "version": __version__},
    }


def serialize_metadata_document(doc: Mapping[str, Any]) -> str:
    """Serialize an existing metadata document to deterministic JSON text."""
    return json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def render_metadata_json(
    findings: Iterable[Finding],
    config: Config,
    *,
    scanned_at: datetime | None = None,
    repo_id: str | None = None,
) -> str:
    """Return deterministic metadata-only JSON text."""
    doc = build_metadata_document(findings, config, scanned_at=scanned_at, repo_id=repo_id)
    return serialize_metadata_document(doc)


def iter_forbidden_keys(obj: Any, *, path: str = "$") -> list[str]:
    """Deep-scan a JSON-like structure for forbidden metadata keys."""
    hits: list[str] = []
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            key_s = str(key)
            here = f"{path}.{key_s}"
            if key_s in FORBIDDEN_METADATA_KEYS:
                hits.append(here)
            hits.extend(iter_forbidden_keys(value, path=here))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            hits.extend(iter_forbidden_keys(item, path=f"{path}[{idx}]"))
    return hits


def assert_no_forbidden_metadata(obj: Any) -> None:
    """Raise ValueError if any forbidden key is present (deep)."""
    hits = iter_forbidden_keys(obj)
    if hits:
        preview = ", ".join(hits[:12])
        more = f" (+{len(hits) - 12} more)" if len(hits) > 12 else ""
        raise ValueError(f"Forbidden metadata key(s) present: {preview}{more}")


def _non_empty_metadata_value(key: str, value: Any) -> bool:
    if value is None:
        return False
    if key == "schema_version":
        return isinstance(value, int) and value > 0
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _validate_sha256_field(key: str, value: Any) -> None:
    if not isinstance(value, str) or not _SHA256_HEX.fullmatch(value):
        raise ValueError(f"{key} must be a lowercase SHA-256 hex digest")


def _validate_opaque_string(key: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    if any(ch in value for ch in ("@", "/", "\\")):
        raise ValueError(f"{key} must not contain path-like or value-like data")


def validate_metadata_record(record: Mapping[str, Any]) -> None:
    """Raise ValueError if a finding record violates the metadata schema."""
    if not isinstance(record, Mapping):
        raise ValueError("metadata finding must be an object")
    assert_no_forbidden_metadata(record)
    keys = {str(key) for key in record}
    unknown = keys - ALLOWED_FINDING_KEYS
    if unknown:
        unknown_list = ", ".join(sorted(unknown))
        raise ValueError(f"Unexpected metadata key(s): {unknown_list}")
    missing = REQUIRED_FINDING_KEYS - keys
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"Missing required metadata key(s): {missing_list}")
    for key in REQUIRED_FINDING_KEYS:
        if not _non_empty_metadata_value(key, record[key]):
            raise ValueError(f"Required metadata field {key!r} must be non-empty")

    entity = record["entity"]
    if not isinstance(entity, str) or entity not in _ENTITY_VALUES:
        raise ValueError(f"entity must be one of: {', '.join(sorted(_ENTITY_VALUES))}")

    severity = record["severity"]
    if not isinstance(severity, str) or severity not in _SEVERITY_VALUES:
        raise ValueError(f"severity must be one of: {', '.join(sorted(_SEVERITY_VALUES))}")

    for hash_key in (
        "finding_fingerprint",
        "path_fingerprint",
        "value_fingerprint",
        "config_hash",
    ):
        _validate_sha256_field(hash_key, record[hash_key])

    schema_version = record["schema_version"]
    if not isinstance(schema_version, int) or schema_version != METADATA_SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {METADATA_SCHEMA_VERSION}")

    normalize_scanned_at(str(record["scanned_at"]))
    _validate_opaque_string("tool_version", record["tool_version"])

    if "repo_id" in keys:
        _validate_opaque_string("repo_id", record["repo_id"])


def coerce_metadata_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a copy with canonical ``scanned_at``."""
    validate_metadata_record(record)
    out = dict(record)
    out["scanned_at"] = normalize_scanned_at(str(record["scanned_at"]))
    return out
