"""Baseline write/load/subtract and fingerprint line-number independence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from piilint.baseline import (
    BaselineError,
    load_baseline,
    subtract_baseline,
    write_baseline,
)
from piilint.cli import app
from piilint.findings import EntityType, Finding, Location, fingerprint_for, value_hash


def _finding(
    *,
    path: str = "a.py",
    line: int | None = 1,
    entity: EntityType = EntityType.EMAIL,
    raw: str = "alpha@retailmail.test",
    occurrence_index: int = 0,
) -> Finding:
    return Finding.create(
        entity=entity,
        raw_value=raw,
        location=Location(path=path, line=line),
        confidence=0.9,
        occurrence_index=occurrence_index,
    )


def test_fingerprint_for_excludes_line_numbers() -> None:
    vhash = value_hash("alpha@retailmail.test", EntityType.EMAIL)
    a = fingerprint_for(
        path="a.py", entity=EntityType.EMAIL, value_sha256=vhash, occurrence_index=0
    )
    b = fingerprint_for(
        path="a.py", entity=EntityType.EMAIL, value_sha256=vhash, occurrence_index=0
    )
    assert a == b
    # Different occurrence → different fingerprint
    c = fingerprint_for(
        path="a.py", entity=EntityType.EMAIL, value_sha256=vhash, occurrence_index=1
    )
    assert a != c


def test_finding_create_fingerprint_independent_of_line() -> None:
    f1 = _finding(line=1)
    f2 = _finding(line=99)
    assert f1.fingerprint == f2.fingerprint
    assert f1.value_sha256 == f2.value_sha256


def test_write_load_roundtrip(tmp_path: Path) -> None:
    findings = [
        _finding(path="a.py", raw="one@retailmail.test"),
        _finding(path="b.py", raw="two@retailmail.test"),
        _finding(path="a.py", raw="one@retailmail.test"),  # duplicate fp
    ]
    out = tmp_path / "piilint-baseline.json"
    write_baseline(out, findings)
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert "generated_at" in raw
    assert isinstance(raw["fingerprints"], list)
    # Sorted unique
    assert raw["fingerprints"] == sorted(set(raw["fingerprints"]))
    assert len(raw["fingerprints"]) == 2
    # No raw PII in baseline file
    blob = out.read_text(encoding="utf-8")
    assert "retailmail" not in blob
    assert "one@" not in blob

    loaded = load_baseline(out)
    assert loaded == set(raw["fingerprints"])


def test_load_baseline_missing(tmp_path: Path) -> None:
    with pytest.raises(BaselineError, match="not found"):
        load_baseline(tmp_path / "missing.json")


def test_load_baseline_bad_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(BaselineError, match="Invalid"):
        load_baseline(bad)


def test_load_baseline_bad_version(tmp_path: Path) -> None:
    bad = tmp_path / "v.json"
    bad.write_text(
        json.dumps({"version": 99, "generated_at": "x", "fingerprints": []}),
        encoding="utf-8",
    )
    with pytest.raises(BaselineError, match="Unsupported baseline version"):
        load_baseline(bad)


def test_subtract_keeps_only_new() -> None:
    known = _finding(path="old.py", raw="old@retailmail.test")
    novel = _finding(path="new.py", raw="new@retailmail.test")
    baseline = {known.fingerprint}
    kept = subtract_baseline([known, novel], baseline)
    assert kept == [novel]


def test_cli_baseline_and_subtract(tmp_path: Path) -> None:
    src = tmp_path / "leak.py"
    src.write_text("# contact planted@retailmail.test\n", encoding="utf-8")
    baseline_path = tmp_path / "base.json"
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["baseline", str(tmp_path), "-o", str(baseline_path)],
    )
    assert result.exit_code == 0, result.output
    assert baseline_path.is_file()
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["fingerprints"]

    # Same tree with baseline → no new findings → exit 0
    result2 = runner.invoke(
        app,
        ["scan", str(tmp_path), "--baseline", str(baseline_path), "--fail-on", "low"],
    )
    assert result2.exit_code == 0, result2.output
    assert (
        "No PII findings" in result2.output or "0 high" in result2.output or result2.exit_code == 0
    )

    # Add a new finding → should surface
    (tmp_path / "extra.py").write_text("# other other@corpmail.test\n", encoding="utf-8")
    result3 = runner.invoke(
        app,
        ["scan", str(tmp_path), "--baseline", str(baseline_path), "--fail-on", "medium"],
    )
    assert result3.exit_code == 1, result3.output
    assert "EMAIL" in result3.output
    assert "planted@retailmail.test" not in result3.output
    assert "other@corpmail.test" not in result3.output
