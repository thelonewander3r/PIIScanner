"""Metadata history MVP — trust boundary, local SQLite, dry-run (no network)."""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import threading
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
    HistoryError,
    default_history_path,
    new_findings_since,
    open_history,
    parse_since,
    record_metadata_run,
    summarize_payload,
)
from piilint.metadata import (
    FORBIDDEN_METADATA_KEYS,
    assert_no_forbidden_metadata,
    build_metadata_document,
    coerce_metadata_record,
    finding_to_metadata,
    iter_forbidden_keys,
    normalize_scanned_at,
    path_fingerprint,
    render_metadata_json,
    validate_metadata_record,
    workspace_repo_id,
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
    assert parse_since("30m", now=now) == now - timedelta(minutes=30)
    assert parse_since("0d", now=now) == now
    assert parse_since("7D", now=now) == now - timedelta(days=7)
    assert parse_since("2026-08-01T00:00:00Z") == datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
    assert parse_since("2026-08-01T00:00:00z") == datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)


def test_parse_since_rejects_oversized_relative() -> None:
    now = datetime(2026, 8, 12, 18, 0, tzinfo=timezone.utc)
    with pytest.raises(HistoryError, match="too large"):
        parse_since("9" * 400 + "d", now=now)
    with pytest.raises(HistoryError, match="too large"):
        parse_since("9" * 400 + "h", now=now)


def test_parse_since_rejects_empty_and_invalid() -> None:
    with pytest.raises(HistoryError, match="must not be empty"):
        parse_since("   ")
    with pytest.raises(HistoryError, match="Invalid --since"):
        parse_since("not-a-date")


def test_validate_metadata_record_rejects_unknown_and_missing_keys() -> None:
    cfg = default_config()
    good = finding_to_metadata(
        _finding(),
        config=cfg,
        scanned_at="2026-08-12T18:00:00Z",
    )
    validate_metadata_record(good)

    unknown = dict(good)
    unknown["path"] = "leak.py"
    with pytest.raises(ValueError, match="Forbidden"):
        validate_metadata_record(unknown)

    extra = dict(good)
    extra["masked_sample"] = "x@y.z"
    with pytest.raises(ValueError, match="Forbidden"):
        validate_metadata_record(extra)

    missing = {k: v for k, v in good.items() if k != "finding_fingerprint"}
    with pytest.raises(ValueError, match="Missing required metadata key"):
        validate_metadata_record(missing)

    surprise = dict(good)
    surprise["extra_field"] = "nope"
    with pytest.raises(ValueError, match="Unexpected metadata key"):
        validate_metadata_record(surprise)


def test_record_metadata_run_rejects_invalid_records(tmp_path: Path) -> None:
    db = tmp_path / "history.sqlite3"
    cfg = default_config()
    good = finding_to_metadata(
        _finding(),
        config=cfg,
        scanned_at="2026-08-12T18:00:00Z",
    )
    bad = dict(good)
    bad["path"] = "secret.py"

    with pytest.raises(HistoryError, match="Forbidden"):
        record_metadata_run([bad], db_path=db)

    assert not db.exists()


def test_record_metadata_run_rolls_back_on_insert_failure(tmp_path: Path) -> None:
    db = tmp_path / "history.sqlite3"
    cfg = default_config()
    records = [
        finding_to_metadata(
            _finding(raw=f"user{i}@retailmail.test"),
            config=cfg,
            scanned_at="2026-08-12T18:00:00Z",
        )
        for i in range(2)
    ]

    open_history(db).close()
    conn = sqlite3.connect(str(db))
    try:
        conn.execute(
            """
            CREATE TRIGGER fail_second_finding_insert
            BEFORE INSERT ON findings_meta
            WHEN (SELECT COUNT(*) FROM findings_meta) >= 1
            BEGIN
                SELECT RAISE(ABORT, 'simulated insert failure');
            END
            """
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(HistoryError, match="unavailable or corrupt"):
        record_metadata_run(records, db_path=db)

    conn = open_history(db)
    try:
        run_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        finding_count = conn.execute("SELECT COUNT(*) FROM findings_meta").fetchone()[0]
    finally:
        conn.close()
    assert run_count == 0
    assert finding_count == 0


def test_default_history_path_env_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PIILINT_HISTORY_PATH", raising=False)
    monkeypatch.delenv("PIILINT_DATA_DIR", raising=False)
    monkeypatch.setenv("PIILINT_DATA_DIR", "/custom/piilint-data")
    assert default_history_path() == Path("/custom/piilint-data/history.sqlite3")

    monkeypatch.setenv("PIILINT_HISTORY_PATH", "/override/history.sqlite3")
    assert default_history_path() == Path("/override/history.sqlite3")


def test_default_history_path_windows_localappdata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PIILINT_HISTORY_PATH", raising=False)
    monkeypatch.delenv("PIILINT_DATA_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\test\AppData\Local")
    monkeypatch.setattr(os, "name", "nt", raising=False)
    assert default_history_path() == Path(r"C:\Users\test\AppData\Local\piilint\history.sqlite3")


def test_cli_report_requires_metadata_only(tmp_path: Path) -> None:
    sample = tmp_path / "note.txt"
    sample.write_text("hello\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["report", str(sample)])
    assert result.exit_code == 2
    assert "requires --metadata-only" in result.output


def test_cli_sync_and_history_error_exit_codes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PIILINT_HISTORY_PATH", str(tmp_path / "history.sqlite3"))
    runner = CliRunner()

    sync_missing = runner.invoke(app, ["sync"])
    assert sync_missing.exit_code == 2
    assert "requires --metadata" in sync_missing.output

    sync_no_dry = runner.invoke(app, ["sync", "--metadata"])
    assert sync_no_dry.exit_code == 2
    assert "dry-run" in sync_no_dry.output

    history_bad = runner.invoke(app, ["history", "--since", "bogus"])
    assert history_bad.exit_code == 2
    assert "History error" in history_bad.output


def test_cli_metadata_outputs_contain_no_filesystem_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "nested" / "history.sqlite3"
    monkeypatch.setenv("PIILINT_HISTORY_PATH", str(db))
    sample = tmp_path / "leak.txt"
    sample.write_text("contact alpha@retailmail.test please\n", encoding="utf-8")
    out = tmp_path / "meta.json"

    runner = CliRunner()
    report = runner.invoke(
        app,
        ["report", str(sample), "--metadata-only", "-o", str(out), "--fail-on", "never"],
    )
    assert report.exit_code == 0, report.output
    assert str(sample) not in report.output
    assert str(out) not in report.output
    assert str(db) not in report.output
    assert "alpha@retailmail.test" not in report.output

    sync = runner.invoke(app, ["sync", "--metadata", "--dry-run", str(tmp_path)])
    assert sync.exit_code == 0, sync.output
    assert str(db) not in sync.output
    assert "alpha@retailmail.test" not in sync.output

    hist = runner.invoke(app, ["history", "--since", "1d", str(tmp_path)])
    assert hist.exit_code == 0, hist.output
    assert str(db) not in hist.output
    assert "alpha@retailmail.test" not in hist.output
    assert "src/" not in hist.output
    assert "leak.txt" not in hist.output


def test_report_does_not_record_history_when_output_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "history.sqlite3"
    monkeypatch.setenv("PIILINT_HISTORY_PATH", str(db))
    sample = tmp_path / "leak.txt"
    sample.write_text("contact alpha@retailmail.test please\n", encoding="utf-8")
    blocked = tmp_path / "blocked" / "meta.json"

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["report", str(sample), "--metadata-only", "-o", str(blocked), "--fail-on", "never"],
    )
    assert result.exit_code == 2
    assert not db.exists()


def test_sync_dry_run_does_not_call_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "history.sqlite3"
    monkeypatch.setenv("PIILINT_HISTORY_PATH", str(db))
    cfg = default_config()
    repo_id = workspace_repo_id(tmp_path)
    doc = build_metadata_document([_finding()], cfg, repo_id=repo_id)
    record_metadata_run(
        doc["findings"],
        scanned_at=str(doc["scanned_at"]),
        config_hash=str(doc["config_hash"]),
        repo_id=repo_id,
    )

    # Guardrails: no socket / urllib / httpx usage on the dry-run path.
    with (
        patch("socket.socket") as mock_sock,
        patch("socket.create_connection", side_effect=AssertionError("network")),
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["sync", "--metadata", "--dry-run", str(tmp_path)])
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

    hist = runner.invoke(app, ["history", "--since", "1d", str(tmp_path), "--json"])
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


def test_cli_history_oversized_since_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PIILINT_HISTORY_PATH", str(tmp_path / "history.sqlite3"))
    runner = CliRunner()
    result = runner.invoke(app, ["history", "--since", "9" * 400 + "d", str(tmp_path)])
    assert result.exit_code == 2, result.output
    assert "History error" in result.output
    assert "too large" in result.output
    assert "Traceback" not in result.output


def test_concurrent_migration_initialization(tmp_path: Path) -> None:
    db = tmp_path / "history.sqlite3"
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            open_history(db).close()
        except BaseException as exc:  # noqa: BLE001 — collect thread failures
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    conn = open_history(db)
    try:
        version = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        run_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    finally:
        conn.close()
    assert version is not None
    assert int(version["value"]) == 1
    assert run_count == 0


def test_cli_integrity_error_during_report_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "history.sqlite3"
    monkeypatch.setenv("PIILINT_HISTORY_PATH", str(db))
    sample = tmp_path / "leak.txt"
    sample.write_text("contact alpha@retailmail.test please\n", encoding="utf-8")
    open_history(db).close()
    conn = sqlite3.connect(str(db))
    try:
        conn.execute(
            """
            CREATE TRIGGER fail_report_insert
            BEFORE INSERT ON runs
            BEGIN
                SELECT RAISE(ABORT, 'simulated constraint failure');
            END
            """
        )
        conn.commit()
    finally:
        conn.close()

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["report", str(sample), "--metadata-only", "--fail-on", "never"],
    )
    assert result.exit_code == 2, result.output
    assert "History error" in result.output
    assert "Traceback" not in result.output
    assert str(db) not in result.output


def test_cli_corrupt_history_db_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    corrupt = tmp_path / "history.sqlite3"
    corrupt.write_bytes(b"not a sqlite database")
    monkeypatch.setenv("PIILINT_HISTORY_PATH", str(corrupt))
    sample = tmp_path / "leak.txt"
    sample.write_text("contact alpha@retailmail.test please\n", encoding="utf-8")
    runner = CliRunner()

    history = runner.invoke(app, ["history", "--since", "1d", str(tmp_path)])
    assert history.exit_code == 2, history.output
    assert "History error" in history.output
    assert "Traceback" not in history.output
    assert str(corrupt) not in history.output

    sync = runner.invoke(app, ["sync", "--metadata", "--dry-run", str(tmp_path)])
    assert sync.exit_code == 2, sync.output
    assert "History error" in sync.output or "History read failed" in sync.output
    assert "Traceback" not in sync.output

    report = runner.invoke(
        app,
        ["report", str(sample), "--metadata-only", "--fail-on", "never"],
    )
    assert report.exit_code == 2, report.output
    assert "History error" in report.output
    assert "Traceback" not in report.output


def test_cli_locked_history_db_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "history.sqlite3"
    monkeypatch.setenv("PIILINT_HISTORY_PATH", str(db))
    open_history(db).close()
    hold = sqlite3.connect(str(db))
    hold.execute("BEGIN EXCLUSIVE")
    try:
        env = os.environ.copy()
        env["PIILINT_HISTORY_PATH"] = str(db)
        proc = subprocess.run(
            [sys.executable, "-m", "piilint.cli", "history", "--since", "1d", str(tmp_path)],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        combined = proc.stdout + proc.stderr
        assert proc.returncode == 2, combined
        assert "History error" in combined or "History read failed" in combined
        assert "Traceback" not in combined
        assert str(db) not in combined
    finally:
        hold.close()


def test_report_fail_on_exit_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "history.sqlite3"
    monkeypatch.setenv("PIILINT_HISTORY_PATH", str(db))
    sample = tmp_path / "leak.txt"
    sample.write_text("contact alpha@retailmail.test please\n", encoding="utf-8")
    out = tmp_path / "meta.json"
    runner = CliRunner()

    high = runner.invoke(
        app,
        ["report", str(sample), "--metadata-only", "-o", str(out), "--fail-on", "high"],
    )
    assert high.exit_code == 0, high.output
    assert out.exists()

    medium = runner.invoke(
        app,
        ["report", str(sample), "--metadata-only", "-o", str(out), "--fail-on", "medium"],
    )
    assert medium.exit_code == 1, medium.output
    assert out.exists()

    never = runner.invoke(
        app,
        ["report", str(sample), "--metadata-only", "-o", str(out), "--fail-on", "never"],
    )
    assert never.exit_code == 0, never.output


def test_report_fail_on_config_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "history.sqlite3"
    monkeypatch.setenv("PIILINT_HISTORY_PATH", str(db))
    (tmp_path / "piilint.toml").write_text(
        '[scan]\nfail_on = "never"\n',
        encoding="utf-8",
    )
    sample = tmp_path / "leak.txt"
    sample.write_text("contact alpha@retailmail.test please\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["report", str(sample), "--metadata-only", "--fail-on", "medium"],
    )
    assert result.exit_code == 1, result.output


def test_report_output_timestamp_matches_sqlite_run(
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
    doc = json.loads(out.read_text(encoding="utf-8"))
    conn = open_history(db)
    try:
        row = conn.execute("SELECT scanned_at FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    finally:
        conn.close()
    assert row is not None
    assert doc["scanned_at"] == row["scanned_at"]
    for record in doc["findings"]:
        assert record["scanned_at"] == doc["scanned_at"]


def test_validate_metadata_record_rejects_pii_like_values(tmp_path: Path) -> None:
    cfg = default_config()
    good = finding_to_metadata(
        _finding(),
        config=cfg,
        scanned_at="2026-08-12T18:00:00Z",
    )
    validate_metadata_record(good)

    bad_entity = dict(good)
    bad_entity["entity"] = "alpha@retailmail.test"
    with pytest.raises(ValueError, match="entity must be one of"):
        validate_metadata_record(bad_entity)

    bad_severity = dict(good)
    bad_severity["severity"] = "critical"
    with pytest.raises(ValueError, match="severity must be one of"):
        validate_metadata_record(bad_severity)

    bad_path_fp = dict(good)
    bad_path_fp["path_fingerprint"] = "/etc/passwd"
    with pytest.raises(ValueError, match="path_fingerprint"):
        validate_metadata_record(bad_path_fp)

    bad_value_fp = dict(good)
    bad_value_fp["value_fingerprint"] = "not-a-sha256"
    with pytest.raises(ValueError, match="value_fingerprint"):
        validate_metadata_record(bad_value_fp)

    with pytest.raises(HistoryError, match="path_fingerprint"):
        record_metadata_run([bad_path_fp], db_path=tmp_path / "history.sqlite3")


def test_normalize_scanned_at_canonical_and_offset() -> None:
    assert normalize_scanned_at("2026-08-01T00:00:00Z") == "2026-08-01T00:00:00Z"
    assert normalize_scanned_at("2026-08-01T00:00:00+00:00") == "2026-08-01T00:00:00Z"
    assert normalize_scanned_at("2026-08-01T00:00:00") == "2026-08-01T00:00:00Z"
    with pytest.raises(ValueError, match="fractional"):
        normalize_scanned_at("2026-08-01T00:00:00.5Z")
    with pytest.raises(ValueError, match="fractional"):
        normalize_scanned_at("2026-08-01T00:00:00.123+00:00")


def test_coerce_metadata_record_normalizes_offset_timestamp() -> None:
    cfg = default_config()
    record = finding_to_metadata(
        _finding(),
        config=cfg,
        scanned_at="2026-08-12T18:00:00Z",
    )
    record["scanned_at"] = "2026-08-12T18:30:00+00:00"
    coerced = coerce_metadata_record(record)
    assert coerced["scanned_at"] == "2026-08-12T18:30:00Z"


def test_new_findings_since_deduplicates_same_second_runs(tmp_path: Path) -> None:
    db = tmp_path / "history.sqlite3"
    cfg = default_config()
    finding = _finding()
    ts = "2026-08-12T18:00:00Z"
    rec = finding_to_metadata(finding, config=cfg, scanned_at=ts)
    record_metadata_run(
        [rec],
        db_path=db,
        scanned_at=ts,
        config_hash=str(rec["config_hash"]),
    )
    record_metadata_run(
        [rec],
        db_path=db,
        scanned_at=ts,
        config_hash=str(rec["config_hash"]),
    )
    items = new_findings_since("1970-01-01T00:00:00Z", db_path=db)
    fps = [i.finding_fingerprint for i in items]
    assert fps.count(rec["finding_fingerprint"]) == 1


def test_history_scoped_by_workspace_repo_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "history.sqlite3"
    monkeypatch.setenv("PIILINT_HISTORY_PATH", str(db))
    ws_a = tmp_path / "workspace_a"
    ws_b = tmp_path / "workspace_b"
    ws_a.mkdir()
    ws_b.mkdir()
    sample = ws_a / "leak.txt"
    sample.write_text("contact alpha@retailmail.test please\n", encoding="utf-8")
    runner = CliRunner()
    report = runner.invoke(
        app,
        ["report", str(sample), "--metadata-only", "--fail-on", "never"],
    )
    assert report.exit_code == 0, report.output

    hist_a = runner.invoke(app, ["history", "--since", "1d", str(ws_a), "--json"])
    assert hist_a.exit_code == 0, hist_a.output
    assert json.loads(hist_a.output)["count"] >= 1

    hist_b = runner.invoke(app, ["history", "--since", "1d", str(ws_b), "--json"])
    assert hist_b.exit_code == 0, hist_b.output
    assert json.loads(hist_b.output)["count"] == 0

    assert workspace_repo_id(ws_a) != workspace_repo_id(ws_b)
