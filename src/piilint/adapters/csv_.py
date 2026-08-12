"""CSV/TSV adapter via pyarrow streaming reader (column batches)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pacsv

from piilint.adapters import ColumnBatch, Unit

SAMPLE_BYTE_THRESHOLD = 250 * 1024 * 1024
DEFAULT_SAMPLE_ROWS = 50_000


def _stringify(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value != value:  # NaN
        return None
    text = str(value).strip()
    return text if text and text.lower() != "none" else None


class CsvAdapter:
    name = "csv"
    extensions = frozenset({".csv", ".tsv"})

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions

    def iter_units(
        self,
        path: Path,
        *,
        rel_path: str,
        sample_rows: int | None = None,
    ) -> Iterator[Unit]:
        # Compatibility shim — prefer iter_column_batches.
        for batch in self.iter_column_batches(path, rel_path=rel_path, sample_rows=sample_rows):
            for value in batch.values:
                yield Unit(
                    text=value,
                    path=batch.path,
                    column=batch.column,
                    context_key=batch.column,
                    aggregate=True,
                    sampled=batch.sampled,
                )

    def iter_column_batches(
        self,
        path: Path,
        *,
        rel_path: str,
        sample_rows: int | None = None,
    ) -> Iterator[ColumnBatch]:
        try:
            size = path.stat().st_size
        except OSError:
            return

        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        sampled = False
        row_limit: int | None = sample_rows
        if row_limit is None and size > SAMPLE_BYTE_THRESHOLD:
            row_limit = DEFAULT_SAMPLE_ROWS
            sampled = True
        elif sample_rows is not None:
            sampled = True

        try:
            reader = pacsv.open_csv(
                path,
                read_options=pacsv.ReadOptions(block_size=8 << 20),
                parse_options=pacsv.ParseOptions(delimiter=delimiter),
                convert_options=pacsv.ConvertOptions(strings_can_be_null=True),
            )
        except (OSError, pa.ArrowInvalid, pa.ArrowTypeError):
            return

        rows_seen = 0
        for batch in reader:
            n = batch.num_rows
            take = n
            if row_limit is not None:
                remaining = row_limit - rows_seen
                if remaining <= 0:
                    break
                take = min(n, remaining)

            for col_idx, col_name in enumerate(batch.schema.names):
                raw_values = batch.column(col_idx).slice(0, take).to_pylist()
                values = tuple(v for v in (_stringify(x) for x in raw_values) if v is not None)
                if not values:
                    continue
                yield ColumnBatch(
                    path=rel_path,
                    column=str(col_name),
                    values=values,
                    sampled=sampled,
                )
            rows_seen += take
            if row_limit is not None and rows_seen >= row_limit:
                break
