"""SARIF 2.1.0 reporter — structure, severity mapping, no raw PII."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from piilint.cli import app
from piilint.config import default_config
from piilint.engine import ScanResult, scan_path
from piilint.findings import EntityType, Finding, Location, Severity
from piilint.reporters.json_ import render_json
from piilint.reporters.sarif import render_sarif

CORPUS_TEXT = Path(__file__).resolve().parent.parent / "corpus" / "text"

RAW_SECRETS = [
    "customer.alpha@retailmail.test",
    "ops.beta@corpmail.test",
    "4532015112830366",
    "4556737586899855",
    "234-56-7890",
    "GB82WEST12345698765432",
]


def test_sarif_version_and_structure() -> None:
    findings = [
        Finding.create(
            entity=EntityType.EMAIL,
            raw_value="alpha@retailmail.test",
            location=Location(path="a.py", line=2),
            confidence=0.9,
            severity=Severity.MEDIUM,
        ),
        Finding.create(
            entity=EntityType.CREDIT_CARD,
            raw_value="4532015112830366",
            location=Location(path="a.py", line=1),
            confidence=0.95,
            severity=Severity.HIGH,
        ),
        Finding.create(
            entity=EntityType.IP_ADDRESS,
            raw_value="203.0.113.10",
            location=Location(path="b.py", line=5),
            confidence=0.7,
            severity=Severity.LOW,
        ),
    ]
    text = render_sarif(ScanResult(findings=findings, files_scanned=2, elapsed_seconds=0.1))
    doc = json.loads(text)
    assert doc["version"] == "2.1.0"
    assert doc["$schema"] == "https://json.schemastore.org/sarif-2.1.0.json"
    assert len(doc["runs"]) == 1
    run = doc["runs"][0]
    assert run["tool"]["driver"]["name"] == "piilint"
    assert "version" in run["tool"]["driver"]
    rule_ids = [r["id"] for r in run["tool"]["driver"]["rules"]]
    assert rule_ids == sorted(rule_ids)
    assert set(rule_ids) >= {"EMAIL", "CREDIT_CARD", "IP_ADDRESS"}
    levels = {r["ruleId"]: r["level"] for r in run["results"]}
    assert levels["CREDIT_CARD"] == "error"
    assert levels["EMAIL"] == "warning"
    assert levels["IP_ADDRESS"] == "note"
    for result in run["results"]:
        assert "locations" in result
        phys = result["locations"][0]["physicalLocation"]
        assert "uri" in phys["artifactLocation"]
        if "region" in phys:
            assert phys["region"]["startLine"] >= 1
        assert "partialFingerprints" in result
        assert "piilint/fingerprint" in result["partialFingerprints"]
        msg = result["message"]["text"]
        assert result["ruleId"] in msg
        # Masked samples only — never full planted card/SSN/email strings
        assert "4532015112830366" not in msg


def test_sarif_no_raw_pii() -> None:
    result = scan_path(CORPUS_TEXT)
    text = render_sarif(result)
    for raw in RAW_SECRETS:
        assert raw not in text


def test_sarif_deterministic() -> None:
    findings = [
        Finding.create(
            entity=EntityType.EMAIL,
            raw_value="z@retailmail.test",
            location=Location(path="z.py", line=2),
            confidence=0.9,
        ),
        Finding.create(
            entity=EntityType.EMAIL,
            raw_value="a@retailmail.test",
            location=Location(path="a.py", line=1),
            confidence=0.9,
        ),
    ]
    result = ScanResult(findings=findings, files_scanned=1, elapsed_seconds=0.2)
    assert render_sarif(result) == render_sarif(result)


def test_cli_format_sarif() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app, ["scan", str(CORPUS_TEXT), "--format", "sarif", "--fail-on", "never"]
    )
    assert result.exit_code == 0, result.output
    doc = json.loads(result.output)
    assert doc["version"] == "2.1.0"
    for raw in RAW_SECRETS:
        assert raw not in result.output


def test_console_totals_line_shape() -> None:
    from io import StringIO

    from rich.console import Console

    from piilint.reporters import render_console

    findings = [
        Finding.create(
            entity=EntityType.CREDIT_CARD,
            raw_value="4532015112830366",
            location=Location(path="a.py", line=1),
            confidence=0.95,
            severity=Severity.HIGH,
        ),
        Finding.create(
            entity=EntityType.EMAIL,
            raw_value="a@retailmail.test",
            location=Location(path="a.py", line=2),
            confidence=0.9,
            severity=Severity.MEDIUM,
        ),
    ]
    buf = StringIO()
    render_console(
        ScanResult(findings=findings, files_scanned=3, elapsed_seconds=1.5),
        console=Console(file=buf, force_terminal=False, color_system=None),
    )
    text = buf.getvalue()
    assert "1 high · 1 medium · 0 low — 3 files scanned in 1.5s" in text
    assert "4532015112830366" not in text


def test_show_matches_refused_in_ci(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CI", "true")
    runner = CliRunner()
    result = runner.invoke(app, ["scan", str(CORPUS_TEXT), "--show-matches", "--fail-on", "never"])
    assert result.exit_code == 2
    assert "refused" in result.output.lower() or "CI" in result.output


def test_masking_across_formats() -> None:
    result = scan_path(CORPUS_TEXT)
    cfg = default_config()
    blobs = [render_json(result, cfg), render_sarif(result)]
    from io import StringIO

    from rich.console import Console

    from piilint.reporters import render_console

    buf = StringIO()
    render_console(result, console=Console(file=buf, force_terminal=False, color_system=None))
    blobs.append(buf.getvalue())
    for blob in blobs:
        for raw in RAW_SECRETS:
            assert raw not in blob
