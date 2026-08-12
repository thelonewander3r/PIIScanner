"""Unit tests: masking, CLI exit codes, network block, no raw PII in output."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from piilint.cli import app
from piilint.engine import scan_path
from piilint.findings import EntityType, Finding, Location, mask_value

CORPUS_TEXT = Path(__file__).resolve().parent.parent / "corpus" / "text"

# Raw synthetic values planted in the corpus — must never appear in tool output.
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


def test_mask_email() -> None:
    masked = mask_value("customer.alpha@retailmail.test", EntityType.EMAIL)
    assert "@" in masked
    assert "customer.alpha" not in masked
    assert masked.startswith("c***@")


def test_mask_card_last4() -> None:
    masked = mask_value("4532015112830366", EntityType.CREDIT_CARD)
    assert masked.endswith("0366")
    assert "453201511283" not in masked.replace(" ", "")


def test_mask_ssn_full() -> None:
    assert mask_value("234-56-7890", EntityType.SSN_US) == "***-**-****"


def test_finding_never_stores_raw() -> None:
    f = Finding.create(
        entity=EntityType.EMAIL,
        raw_value="customer.alpha@retailmail.test",
        location=Location(path="x.py", line=1),
        confidence=0.9,
    )
    dumped = repr(f) + f.masked_sample + f.fingerprint + f.value_sha256
    assert "customer.alpha@retailmail.test" not in dumped


def test_scan_corpus_text_finds_planted() -> None:
    result = scan_path(CORPUS_TEXT)
    assert result.findings, "expected planted findings"
    entities = {f.entity for f in result.findings}
    assert EntityType.EMAIL in entities
    assert EntityType.CREDIT_CARD in entities
    assert EntityType.SSN_US in entities


def test_cli_scan_exits_1_on_findings() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["scan", str(CORPUS_TEXT), "--fail-on", "high"])
    assert result.exit_code == 1, result.output
    for raw in RAW_SECRETS:
        assert raw not in result.output, f"raw value leaked in output: {raw}"


def test_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert re.search(r"\d+\.\d+\.\d+", result.output)


def test_output_has_no_raw_corpus_values() -> None:
    result = scan_path(CORPUS_TEXT)
    blob = "\n".join(
        f"{f.entity.value}|{f.masked_sample}|{f.location.label()}|{f.fingerprint}"
        for f in result.findings
    )
    for raw in RAW_SECRETS:
        assert raw not in blob


def test_network_blocked_by_pytest_socket() -> None:
    import socket

    from pytest_socket import SocketBlockedError

    with pytest.raises(SocketBlockedError):
        socket.create_connection(("example.com", 80), timeout=1)
