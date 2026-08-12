"""Adapter protocol and registry — scan chassis boundary (no recognizer imports)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Unit:
    """A scannable text unit (line, cell, column chunk, etc.)."""

    text: str
    path: str  # relative path using forward slashes
    line: int | None = None
    column: str | None = None
    cell: int | None = None
    cell_part: str | None = None
    row: int | None = None
    context_key: str | None = None
    # When set, engine aggregates matches for this column instead of emitting per-row.
    aggregate: bool = False
    sampled: bool = False


@dataclass(frozen=True, slots=True)
class ColumnBatch:
    """Non-null string values for one column in one read batch (tabular adapters)."""

    path: str
    column: str
    values: tuple[str, ...]
    sampled: bool = False


class Adapter(Protocol):
    name: str
    extensions: frozenset[str]

    def supports(self, path: Path) -> bool: ...

    def iter_units(self, path: Path, *, rel_path: str) -> Iterator[Unit]: ...


def default_adapters() -> Sequence[Adapter]:
    """Most-specific adapters first; TextAdapter is the fallback."""
    from piilint.adapters.csv_ import CsvAdapter
    from piilint.adapters.json_ import JsonAdapter
    from piilint.adapters.notebook import NotebookAdapter
    from piilint.adapters.parquet import ParquetAdapter
    from piilint.adapters.pdf import PdfAdapter
    from piilint.adapters.text import TextAdapter
    from piilint.adapters.xlsx import XlsxAdapter

    return (
        NotebookAdapter(),
        XlsxAdapter(),
        PdfAdapter(),
        CsvAdapter(),
        ParquetAdapter(),
        JsonAdapter(),
        TextAdapter(),
    )


def select_adapter(path: Path, adapters: Sequence[Adapter] | None = None) -> Adapter | None:
    for adapter in adapters or default_adapters():
        if adapter.supports(path):
            return adapter
    return None
