"""Unit tests for optional NER (PERSON/ADDRESS) — skip gracefully without extra/model."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from piilint.cli import app
from piilint.engine import scan_path
from piilint.findings import EntityType
from piilint.recognizers import build_default_registry
from piilint.recognizers.ner import (
    SPACY_MODEL,
    ner_deps_available,
    spacy_model_available,
)

CORPUS_NER = Path(__file__).resolve().parent.parent / "corpus" / "text" / "names_addresses.txt"

pytestmark = pytest.mark.ner


def test_ner_disabled_by_default() -> None:
    registry = build_default_registry()
    enabled = {r.entity for r in registry.enabled_recognizers()}
    assert EntityType.PERSON not in enabled
    assert EntityType.ADDRESS not in enabled

    result = scan_path(CORPUS_NER)
    entities = {f.entity for f in result.findings}
    assert EntityType.PERSON not in entities
    assert EntityType.ADDRESS not in entities


def test_cli_ner_missing_deps_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("piilint.recognizers.ner.ner_deps_available", lambda: False)
    runner = CliRunner()
    result = runner.invoke(app, ["scan", str(CORPUS_NER), "--ner", "--fail-on", "never"])
    assert result.exit_code == 2, result.output
    assert "piilint[ner]" in result.output
    assert "setup-ner" in result.output


def test_cli_ner_missing_model_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("piilint.recognizers.ner.ner_deps_available", lambda: True)
    monkeypatch.setattr(
        "piilint.recognizers.ner.spacy_model_available",
        lambda _m=SPACY_MODEL: False,
    )
    runner = CliRunner()
    result = runner.invoke(app, ["scan", str(CORPUS_NER), "--ner", "--fail-on", "never"])
    assert result.exit_code == 2, result.output
    assert "setup-ner" in result.output


def test_setup_ner_reports_missing_deps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("piilint.recognizers.ner.ner_deps_available", lambda: False)

    def _should_not_download(_model: str = SPACY_MODEL) -> None:
        raise AssertionError("download must not run when deps missing")

    monkeypatch.setattr("piilint.recognizers.ner.download_spacy_model", _should_not_download)
    runner = CliRunner()
    result = runner.invoke(app, ["setup-ner"])
    assert result.exit_code == 2, result.output
    assert "piilint[ner]" in result.output


@pytest.mark.skipif(not ner_deps_available(), reason="piilint[ner] not installed")
@pytest.mark.skipif(
    not spacy_model_available(),
    reason=f"{SPACY_MODEL} not installed; run piilint setup-ner",
)
def test_ner_finds_person_and_address() -> None:
    result = scan_path(CORPUS_NER, enable_ner=True)
    entities = {f.entity for f in result.findings}
    assert EntityType.PERSON in entities, result.findings
    assert EntityType.ADDRESS in entities, result.findings
    for finding in result.findings:
        if finding.entity in {EntityType.PERSON, EntityType.ADDRESS}:
            # Masked output only — full fake names must not appear in samples.
            assert "Alice Exampleton" not in finding.masked_sample
            assert "Fictitious Lane" not in finding.masked_sample
