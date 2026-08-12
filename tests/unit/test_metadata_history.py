"""Metadata history MVP — trust boundary, local SQLite, dry-run (no network)."""

from __future__ import annotations

import json
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from piilint.cli import app
from piilint.config import default_config
from piilint.findings import EntityType, Finding, Location
from piilint.history import (
    default_history_path,
    new_findings_since,
    parse_since,
    record_metadata_run,
    summarize_payload,
)
from piilint.metadata import (
    FORBIDDEN_METADATA_KEYS,
    assert_no_forbidden_metadata,
    build_metadata_document,
    finding_to_metadata,
    iter_forbidden_keys,
    path_fingerprint,
    render_metadata_json,
)
from piilint.reporters.json_ import config_hash


def _finding(
    *,
    path: str = "src/a.py",
    entity: EntityType = EntityType.EMAIL,
    raw: str = "alpha@retailmail.test",
    line: int = 3,
) -> Finding:
    return Finding.create(
        entity=entity,
        raw_value=raw,
        location=Location(path=path, line=line, column="email", row=1, cell=2),
        confidence=0.95,
    )


def test_path_fingerprint_normalizes_slashes() -> None:
    a = path_fingerprint(r"src\pkg\file.py")
    b = path_fingerprint("src/pkg/file.py")
    assert a == b
    assert len(a) == 64
    # Must not equal a hash of an unnormalized Windows path with backslashes
    # when compared against itself after normalize — already equal above.


def test_metadata_payload_has_zero_forbidden_keys() -> None:
    cfg = default_config()
    findings = [
        _finding(),
        _finding(path="data/users.csv", entity=EntityType.SSN_US, raw="234-56-7890"),
    ]
    doc = build_metadata_document(findings, cfg)
    hits = iter_forbidden_keys(doc)
    assert hits == []
    assert_no_forbidden_metadata(doc)
    by_fp = {f.fingerprint: f for f in findings}
    for record in doc["findings"]:
        assert "path" not in record
        assert "masked_sample" not in record
        assert "line" not in record
        src = by_fp[record["finding_fingerprint"]]
        assert record["value_fingerprint"] == src.value_sha256
        assert record["finding_fingerprint"] == src.fingerprint
        assert record["config_hash"] == config_hash(cfg)


def test_forbidden_key_helper_detects_nested() -> None:
    bad: dict[str, Any] = {
        "findings": [{"entity": "EMAIL", "path": "secret.py", "nested": {"masked_sample": "x"}}]
    }
    hits = iter_forbidden_keys(bad)
    assert any(h.endswith(".path") for h in hits)
    assert any("masked_sample" in h for h in hits)
    with pytest.raises(ValueError, match="Forbidden"):
        assert_no_forbidden_metadata(bad)


def test_finding_to_metadata_reuses_fingerprints() -> None:
    cfg = default_config()
    finding = _finding()
    scanned_at = "2026-08-12T18:00:00Z"
    record = finding_to_metadata(finding, config=cfg, scanned_at=scanned_at)
    assert record["finding_fingerprint"] == finding.fingerprint
    assert record["value_fingerprint"] == finding.value_sha256
    assert record["path_fingerprint"] == path_fingerprint(finding.location.path)
    assert record["config_hash"] == config_hash(cfg)
    assert set(record) <= {
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
    assert not (set(record) & FORBIDDEN_METADATA_KEYS)


def test_history_new_since(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "history.sqlite3"
    monkeypatch.setenv("PIILINT_HISTORY_PATH", str(db))
    assert default_history_path() == db

    cfg = default_config()
    older = build_metadata_document(
        [_finding(raw="old@retailmail.test")],
        cfg,
        scanned_at=datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
    )
    newer = build_metadata_document(
        [
            _finding(raw="old@retailmail.test"),
            _finding(raw="new@retailmail.test", path="src/b.py"),
        ],
        cfg,
        scanned_at=datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
    )
    record_metadata_run(
        older["findings"],
        scanned_at=str(older["scanned_at"]),
        config_hash=str(older["config_hash"]),
    )
    record_metadata_run(
        newer["findings"],
        scanned_at=str(newer["scanned_at"]),
        config_hash=str(newer["config_hash"]),
    )

    items = new_findings_since("2026-08-05T00:00:00Z")
    fps = {i.finding_fingerprint for i in items}
    old_fp = older["findings"][0]["finding_fingerprint"]
    new_fp = next(
        r["finding_fingerprint"] for r in newer["findings"] if r["finding_fingerprint"] != old_fp
    )
    assert old_fp not in fps
    assert new_fp in fps
    for item in items:
        assert_no_forbidden_metadata(item.as_dict())


def test_parse_since_relative_and_iso() -> None:
    now = datetime(2026, 8, 12, 18, 0, tzinfo=timezone.utc)
    assert parse_since("7d", now=now) == now - timedelta(days=7)
    assert parse_since("24h", now=now) == now - timedelta(hours=24)
    assert parse_since("2026-08-01T00:00:00Z") == datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)


def test_sync_dry_run_does_not_call_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "history.sqlite3"
    monkeypatch.setenv("PIILINT_HISTORY_PATH", str(db))
    cfg = default_config()
    doc = build_metadata_document([_finding()], cfg)
    record_metadata_run(
        doc["findings"],
        scanned_at=str(doc["scanned_at"]),
        config_hash=str(doc["config_hash"]),
    )

    # Guardrails: no socket / urllib / httpx usage on the dry-run path.
    with (
        patch("socket.socket") as mock_sock,
        patch("socket.create_connection", side_effect=AssertionError("network")),
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["sync", "--metadata", "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "<not configured>" in result.output
        assert "payload_bytes:" in result.output
        assert "EMAIL" in result.output
        mock_sock.assert_not_called()

    # Module imports for sync path must not pull network clients.
    import piilint.history as history_mod

    src = Path(history_mod.__file__).read_text(encoding="utf-8")
    assert "urllib" not in src
    assert "httpx" not in src
    assert "requests" not in src


def test_summarize_payload_byte_size() -> None:
    cfg = default_config()
    doc = build_metadata_document([_finding(), _finding(raw="beta@retailmail.test")], cfg)
    summary = summarize_payload(doc["findings"])
    assert summary["finding_count"] == 2
    assert summary["destination"] == "<not configured>"
    assert summary["payload_bytes"] > 0
    assert summary["by_entity"]["EMAIL"] == 2


def test_default_scan_does_not_create_history_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "history.sqlite3"
    monkeypatch.setenv("PIILINT_HISTORY_PATH", str(db))
    sample = tmp_path / "note.txt"
    sample.write_text("hello world\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(app, ["scan", str(sample), "--fail-on", "never"])
    assert result.exit_code == 0, result.output
    assert not db.exists()


def test_report_metadata_only_records_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "history.sqlite3"
    monkeypatch.setenv("PIILINT_HISTORY_PATH", str(db))
    sample = tmp_path / "leak.txt"
    sample.write_text("contact alpha@retailmail.test please\n", encoding="utf-8")
    out = tmp_path / "meta.json"

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["report", str(sample), "--metadata-only", "-o", str(out), "--fail-on", "never"],
    )
    assert result.exit_code == 0, result.output
    assert db.exists()
    assert out.exists()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert_no_forbidden_metadata(doc)
    assert "alpha@retailmail.test" not in out.read_text(encoding="utf-8")
    assert "retailmail" not in out.read_text(encoding="utf-8")

    hist = runner.invoke(app, ["history", "--since", "1d", "--json"])
    assert hist.exit_code == 0, hist.output
    payload = json.loads(hist.output)
    assert payload["count"] >= 1
    for finding in payload["findings"]:
        assert_no_forbidden_metadata(finding)


def test_pytest_socket_still_blocks_real_connect() -> None:
    from pytest_socket import SocketBlockedError

    with pytest.raises(SocketBlockedError):
        socket.create_connection(("example.com", 80), timeout=1)


def test_render_metadata_json_deterministic() -> None:
    cfg = default_config()
    findings = [
        _finding(path="z.py", raw="z@retailmail.test"),
        _finding(path="a.py", raw="a@retailmail.test"),
    ]
    scanned = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
    a = render_metadata_json(findings, cfg, scanned_at=scanned)
    b = render_metadata_json(list(reversed(findings)), cfg, scanned_at=scanned)
    assert a == b
