"""Metadata-only findings payload (trust boundary).

Builds sync-shaped records from local findings: fingerprints and policy hashes
only — never raw paths, locations, masked samples, or match values.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from piilint import __version__
from piilint.config import Config
from piilint.findings import Finding
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

# Keys that must never appear in metadata JSON / DB-serialized rows.
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
    return {
        "config_hash": cfg_hash,
        "findings": records,
        "schema_version": METADATA_SCHEMA_VERSION,
        "scanned_at": scanned_at_iso,
        "tool": {"name": "piilint", "version": __version__},
    }


def render_metadata_json(
    findings: Iterable[Finding],
    config: Config,
    *,
    scanned_at: datetime | None = None,
    repo_id: str | None = None,
) -> str:
    """Return deterministic metadata-only JSON text."""
    doc = build_metadata_document(findings, config, scanned_at=scanned_at, repo_id=repo_id)
    return json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


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
