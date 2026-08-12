"""JSON reporter — schema_version 1, masking, determinism, config_hash."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from piilint.cli import app
from piilint.config import default_config
from piilint.engine import ScanResult, scan_path
from piilint.findings import EntityType, Finding, Location, Severity
from piilint.reporters.json_ import config_hash, render_json

CORPUS_TEXT = Path(__file__).resolve().parent.parent / "corpus" / "text"

RAW_SECRETS = [
    "customer.alpha@retailmail.test",
    "ops.beta@corpmail.test",
    "+1 212-735-0182",
    "+14159032741",
    "234-56-7890",
    "512-48-3017",
    "4532015112830366",
    "4556737586899855",
    "GB82WEST12345698765432",
    "DE89370400440532013000",
]


def _sample_finding(
    *,
    path: str = "a.py",
    line: int = 1,
    entity: EntityType = EntityType.EMAIL,
    raw: str = "alpha@retailmail.test",
) -> Finding:
    return Finding.create(
        entity=entity,
        raw_value=raw,
        location=Location(path=path, line=line),
        confidence=0.9,
    )


def test_json_schema_version_and_required_keys() -> None:
    cfg = default_config()
    result = ScanResult(
        findings=[
            _sample_finding(),
            _sample_finding(path="b.py", line=3, raw="beta@retailmail.test"),
        ],
        files_scanned=2,
        elapsed_seconds=0.5,
    )
    doc = json.loads(render_json(result, cfg))
    assert doc["schema_version"] == 1
    assert doc["tool"]["name"] == "piilint"
    assert "version" in doc["tool"]
    assert isinstance(doc["config_hash"], str) and len(doc["config_hash"]) == 64
    assert set(doc["summary"]) >= {"files_scanned", "elapsed_seconds", "findings", "by_severity"}
    assert doc["summary"]["files_scanned"] == 2
    assert doc["summary"]["findings"] == 2
    assert set(doc["summary"]["by_severity"]) == {"high", "medium", "low"}
    for finding in doc["findings"]:
        assert set(finding) >= {
            "entity",
            "severity",
            "confidence",
            "path",
            "line",
            "column",
            "cell",
            "row",
            "masked_sample",
            "value_sha256",
            "fingerprint",
            "matched_count",
        }
        assert "normalized_value" not in finding
        assert "raw" not in finding
        assert "raw_value" not in finding


def test_json_no_raw_pii() -> None:
    result = scan_path(CORPUS_TEXT)
    text = render_json(result, default_config())
    for raw in RAW_SECRETS:
        assert raw not in text


def test_json_deterministic_double_render() -> None:
    cfg = default_config()
    result = ScanResult(
        findings=[
            _sample_finding(path="z.py", line=2, raw="z@retailmail.test"),
            _sample_finding(path="a.py", line=9, raw="a@retailmail.test"),
            Finding.create(
                entity=EntityType.CREDIT_CARD,
                raw_value="4532015112830366",
                location=Location(path="a.py", line=1),
                confidence=0.95,
                severity=Severity.HIGH,
            ),
        ],
        files_scanned=1,
        elapsed_seconds=1.25,
    )
    first = render_json(result, cfg)
    second = render_json(result, cfg)
    assert first == second
    paths = [f["path"] for f in json.loads(first)["findings"]]
    assert paths == sorted(paths)


def test_config_hash_stable_and_sensitive() -> None:
    a = default_config()
    b = default_config()
    assert config_hash(a) == config_hash(b)
    b.scan.fail_on = "medium"
    assert config_hash(a) != config_hash(b)


def test_cli_format_json() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app, ["scan", str(CORPUS_TEXT), "--format", "json", "--fail-on", "never"]
    )
    assert result.exit_code == 0, result.output
    doc = json.loads(result.output)
    assert doc["schema_version"] == 1
    assert doc["config_hash"]
    for raw in RAW_SECRETS:
        assert raw not in result.output
