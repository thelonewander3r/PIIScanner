"""Local SQLite history for metadata-only finding fingerprints (no network)."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from piilint.metadata import METADATA_SCHEMA_VERSION, assert_no_forbidden_metadata

DB_SCHEMA_VERSION = 1

_ENV_HISTORY_PATH = "PIILINT_HISTORY_PATH"
_ENV_DATA_DIR = "PIILINT_DATA_DIR"


class HistoryError(Exception):
    """Raised for history DB / since-parse problems."""


@dataclass(frozen=True, slots=True)
class HistoryFinding:
    entity: str
    severity: str
    finding_fingerprint: str
    path_fingerprint: str
    value_fingerprint: str
    config_hash: str
    scanned_at: str
    repo_id: str | None = None
    tool_version: str | None = None
    schema_version: int = METADATA_SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "config_hash": self.config_hash,
            "entity": self.entity,
            "finding_fingerprint": self.finding_fingerprint,
            "path_fingerprint": self.path_fingerprint,
            "scanned_at": self.scanned_at,
            "schema_version": self.schema_version,
            "severity": self.severity,
            "value_fingerprint": self.value_fingerprint,
        }
        if self.repo_id is not None:
            data["repo_id"] = self.repo_id
        if self.tool_version is not None:
            data["tool_version"] = self.tool_version
        return data


def default_history_path() -> Path:
    """Resolve the local history DB path (Windows-first; stdlib only).

    Override with ``PIILINT_HISTORY_PATH`` (full file path) or ``PIILINT_DATA_DIR``
    (directory containing ``history.sqlite3``).

    Default locations:
    - Windows: ``%LOCALAPPDATA%\\piilint\\history.sqlite3``
      (fallback: ``~/AppData/Local/piilint/history.sqlite3``)
    - else: ``$XDG_DATA_HOME/piilint/history.sqlite3``
      (fallback: ``~/.local/share/piilint/history.sqlite3``)
    """
    override = os.environ.get(_ENV_HISTORY_PATH, "").strip()
    if override:
        return Path(override).expanduser()

    data_dir = os.environ.get(_ENV_DATA_DIR, "").strip()
    if data_dir:
        return Path(data_dir).expanduser() / "history.sqlite3"

    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "").strip()
        root = Path(local) if local else Path.home() / "AppData" / "Local"
        return root / "piilint" / "history.sqlite3"

    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    root = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return root / "piilint" / "history.sqlite3"


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY NOT NULL,
            value TEXT NOT NULL
        )
        """
    )
    row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    if row is None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scanned_at TEXT NOT NULL,
                config_hash TEXT NOT NULL,
                tool_version TEXT,
                schema_version INTEGER NOT NULL,
                repo_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS findings_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                entity TEXT NOT NULL,
                severity TEXT NOT NULL,
                finding_fingerprint TEXT NOT NULL,
                path_fingerprint TEXT NOT NULL,
                value_fingerprint TEXT NOT NULL,
                config_hash TEXT NOT NULL,
                scanned_at TEXT NOT NULL,
                repo_id TEXT,
                tool_version TEXT,
                schema_version INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_findings_meta_fp ON findings_meta(finding_fingerprint)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_findings_meta_scanned_at ON findings_meta(scanned_at)"
        )
        conn.execute(
            "INSERT INTO meta(key, value) VALUES ('schema_version', ?)",
            (str(DB_SCHEMA_VERSION),),
        )
        conn.commit()
        return

    version = int(row["value"])
    if version != DB_SCHEMA_VERSION:
        raise HistoryError(
            f"Unsupported history DB schema_version {version} (expected {DB_SCHEMA_VERSION})"
        )


def open_history(db_path: Path | None = None) -> sqlite3.Connection:
    """Open (and migrate) the history database."""
    path = db_path if db_path is not None else default_history_path()
    conn = _connect(path)
    try:
        _migrate(conn)
    except Exception:
        conn.close()
        raise
    return conn


def record_metadata_run(
    records: Sequence[dict[str, Any]],
    *,
    db_path: Path | None = None,
    scanned_at: str | None = None,
    config_hash: str | None = None,
    tool_version: str | None = None,
    repo_id: str | None = None,
    schema_version: int = METADATA_SCHEMA_VERSION,
) -> int:
    """Insert one run + its metadata findings. Returns run id.

    Each record must already be metadata-only (forbidden keys rejected).
    """
    for record in records:
        assert_no_forbidden_metadata(record)

    if not records and (scanned_at is None or config_hash is None):
        # Allow empty runs when caller supplies run-level fields.
        pass

    run_scanned_at = scanned_at
    run_config_hash = config_hash
    run_tool_version = tool_version
    run_repo_id = repo_id
    if records:
        first = records[0]
        run_scanned_at = run_scanned_at or str(first["scanned_at"])
        run_config_hash = run_config_hash or str(first["config_hash"])
        if run_tool_version is None:
            run_tool_version = first.get("tool_version")
        if run_repo_id is None:
            run_repo_id = first.get("repo_id")
        schema_version = int(first.get("schema_version", schema_version))

    if run_scanned_at is None or run_config_hash is None:
        raise HistoryError("scanned_at and config_hash are required to record a run")

    conn = open_history(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO runs(
                scanned_at, config_hash, tool_version, schema_version, repo_id
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                run_scanned_at,
                run_config_hash,
                run_tool_version,
                schema_version,
                run_repo_id,
            ),
        )
        if cur.lastrowid is None:
            raise HistoryError("failed to obtain run id after insert")
        run_id = int(cur.lastrowid)
        for record in records:
            conn.execute(
                """
                INSERT INTO findings_meta(
                    run_id, entity, severity, finding_fingerprint,
                    path_fingerprint, value_fingerprint, config_hash,
                    scanned_at, repo_id, tool_version, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    str(record["entity"]),
                    str(record["severity"]),
                    str(record["finding_fingerprint"]),
                    str(record["path_fingerprint"]),
                    str(record["value_fingerprint"]),
                    str(record["config_hash"]),
                    str(record["scanned_at"]),
                    record.get("repo_id"),
                    record.get("tool_version"),
                    int(record.get("schema_version", schema_version)),
                ),
            )
        conn.commit()
        return run_id
    finally:
        conn.close()


def parse_since(value: str, *, now: datetime | None = None) -> datetime:
    """Parse ``7d`` / ``24h`` / ``30m`` relative or ISO-8601 datetime to UTC."""
    raw = value.strip()
    if not raw:
        raise HistoryError("--since value must not be empty")

    now_utc = now or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    else:
        now_utc = now_utc.astimezone(timezone.utc)

    rel = re.fullmatch(r"(\d+)([dhms])", raw, flags=re.IGNORECASE)
    if rel:
        amount = int(rel.group(1))
        unit = rel.group(2).lower()
        delta = {
            "d": timedelta(days=amount),
            "h": timedelta(hours=amount),
            "m": timedelta(minutes=amount),
            "s": timedelta(seconds=amount),
        }[unit]
        return now_utc - delta

    iso = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso)
    except ValueError as exc:
        raise HistoryError(
            f"Invalid --since value {value!r}; use relative (7d, 24h) or ISO datetime"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_findings_since(
    since: datetime | str,
    *,
    db_path: Path | None = None,
    now: datetime | None = None,
) -> list[HistoryFinding]:
    """Return findings whose fingerprint was first seen at or after ``since``.

    Compared against prior stored runs: a fingerprint is "new" if its earliest
    ``scanned_at`` in the local DB is >= since.
    """
    since_dt = parse_since(since, now=now) if isinstance(since, str) else since
    if since_dt.tzinfo is None:
        since_dt = since_dt.replace(tzinfo=timezone.utc)
    since_iso = _iso(since_dt)

    conn = open_history(db_path)
    try:
        rows = conn.execute(
            """
            SELECT
                f.entity,
                f.severity,
                f.finding_fingerprint,
                f.path_fingerprint,
                f.value_fingerprint,
                f.config_hash,
                f.scanned_at,
                f.repo_id,
                f.tool_version,
                f.schema_version
            FROM findings_meta AS f
            INNER JOIN (
                SELECT finding_fingerprint, MIN(scanned_at) AS first_seen
                FROM findings_meta
                GROUP BY finding_fingerprint
            ) AS first
              ON f.finding_fingerprint = first.finding_fingerprint
             AND f.scanned_at = first.first_seen
            WHERE first.first_seen >= ?
            ORDER BY f.scanned_at ASC, f.finding_fingerprint ASC
            """,
            (since_iso,),
        ).fetchall()
        results: list[HistoryFinding] = []
        for row in rows:
            item = HistoryFinding(
                entity=row["entity"],
                severity=row["severity"],
                finding_fingerprint=row["finding_fingerprint"],
                path_fingerprint=row["path_fingerprint"],
                value_fingerprint=row["value_fingerprint"],
                config_hash=row["config_hash"],
                scanned_at=row["scanned_at"],
                repo_id=row["repo_id"],
                tool_version=row["tool_version"],
                schema_version=int(row["schema_version"]),
            )
            assert_no_forbidden_metadata(item.as_dict())
            results.append(item)
        return results
    finally:
        conn.close()


def latest_metadata_records(
    *,
    db_path: Path | None = None,
    limit_runs: int = 1,
) -> list[dict[str, Any]]:
    """Return metadata finding dicts from the most recent run(s)."""
    conn = open_history(db_path)
    try:
        run_rows = conn.execute(
            """
            SELECT id FROM runs
            ORDER BY scanned_at DESC, id DESC
            LIMIT ?
            """,
            (limit_runs,),
        ).fetchall()
        if not run_rows:
            return []
        run_ids = [int(r["id"]) for r in run_rows]
        placeholders = ",".join("?" for _ in run_ids)
        rows = conn.execute(
            f"""
            SELECT
                entity, severity, finding_fingerprint, path_fingerprint,
                value_fingerprint, config_hash, scanned_at, repo_id,
                tool_version, schema_version
            FROM findings_meta
            WHERE run_id IN ({placeholders})
            ORDER BY scanned_at ASC, finding_fingerprint ASC
            """,
            run_ids,
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            item = HistoryFinding(
                entity=row["entity"],
                severity=row["severity"],
                finding_fingerprint=row["finding_fingerprint"],
                path_fingerprint=row["path_fingerprint"],
                value_fingerprint=row["value_fingerprint"],
                config_hash=row["config_hash"],
                scanned_at=row["scanned_at"],
                repo_id=row["repo_id"],
                tool_version=row["tool_version"],
                schema_version=int(row["schema_version"]),
            )
            data = item.as_dict()
            assert_no_forbidden_metadata(data)
            out.append(data)
        return out
    finally:
        conn.close()


def records_from_document(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract finding metadata records from a metadata document."""
    findings = doc.get("findings", [])
    if not isinstance(findings, list):
        raise HistoryError("metadata document 'findings' must be a list")
    out: list[dict[str, Any]] = []
    for item in findings:
        if not isinstance(item, dict):
            raise HistoryError("each metadata finding must be an object")
        assert_no_forbidden_metadata(item)
        out.append(dict(item))
    return out


def summarize_payload(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Counts by entity/severity + UTF-8 payload byte size (for dry-run)."""
    by_entity: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    material: list[dict[str, Any]] = []
    for record in records:
        assert_no_forbidden_metadata(record)
        material.append(record)
        entity = str(record.get("entity", "?"))
        severity = str(record.get("severity", "?"))
        by_entity[entity] = by_entity.get(entity, 0) + 1
        by_severity[severity] = by_severity.get(severity, 0) + 1
    payload = json.dumps(
        {"findings": material, "schema_version": METADATA_SCHEMA_VERSION},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return {
        "by_entity": dict(sorted(by_entity.items())),
        "by_severity": dict(sorted(by_severity.items())),
        "destination": "<not configured>",
        "finding_count": len(material),
        "payload_bytes": len(payload.encode("utf-8")),
    }
