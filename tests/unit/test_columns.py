"""Unit tests for --columns parsing (no office extra required)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from piilint.cli import app
from piilint.columns import ColumnError, ensure_sheet_files, parse_column_args, split_selector
from piilint.engine import scan_path


def test_parse_column_args_comma_and_repeatable() -> None:
    assert parse_column_args(None) == []
    assert parse_column_args([]) == []
    assert parse_column_args(["Agent,ANI/From"]) == ["Agent", "ANI/From"]
    assert parse_column_args(["Agent", "H"]) == ["Agent", "H"]
    assert parse_column_args([" Agent , ", "ANI/From", "Agent"]) == ["Agent", "ANI/From"]
    assert parse_column_args([",,,"]) == []


def test_split_selector_sheet_scope() -> None:
    assert split_selector("Agent") == (None, "Agent")
    assert split_selector("Sheet1!H") == ("Sheet1", "H")
    assert split_selector("Calls!ANI/From") == ("Calls", "ANI/From")


def test_ensure_sheet_files_rejects_empty() -> None:
    with pytest.raises(ColumnError, match="spreadsheet"):
        ensure_sheet_files([Path("notes.txt"), Path("data.csv")])


def test_scan_columns_on_text_exits_without_office(tmp_path: Path) -> None:
    src = tmp_path / "note.txt"
    src.write_text("phone 212-735-0182\n", encoding="utf-8")
    with pytest.raises(ColumnError, match="spreadsheet"):
        scan_path(src, columns=["Agent"])

    runner = CliRunner()
    result = runner.invoke(app, ["scan", str(src), "--columns", "Agent"])
    assert result.exit_code == 2
    assert "xlsx" in result.output.lower() or "spreadsheet" in result.output.lower()
