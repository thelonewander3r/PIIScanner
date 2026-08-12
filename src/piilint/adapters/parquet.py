"""Parquet adapter — string columns via iter_batches (column batches)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from piilint.adapters import ColumnBatch, Unit
from piilint.adapters.csv_ import DEFAULT_SAMPLE_ROWS, SAMPLE_BYTE_THRESHOLD, _stringify

BATCH_SIZE = 65_536


class ParquetAdapter:
    name = "parquet"
    extensions = frozenset({".parquet"})

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions

    def iter_units(
        self,
        path: Path,
        *,
        rel_path: str,
        sample_rows: int | None = None,
    ) -> Iterator[Unit]:
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

        sampled = False
        row_limit = sample_rows
        if row_limit is None and size > SAMPLE_BYTE_THRESHOLD:
            row_limit = DEFAULT_SAMPLE_ROWS
            sampled = True
        elif sample_rows is not None:
            sampled = True

        try:
            pf = pq.ParquetFile(path)
        except (OSError, pa.ArrowInvalid, pa.ArrowTypeError):
            return

        schema = pf.schema_arrow
        string_cols = [
            field.name
            for field in schema
            if pa.types.is_string(field.type)
            or pa.types.is_large_string(field.type)
            or pa.types.is_dictionary(field.type)
        ]
        if not string_cols:
            string_cols = list(schema.names)

        rows_seen = 0
        try:
            for batch in pf.iter_batches(batch_size=BATCH_SIZE, columns=string_cols):
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
        except (OSError, pa.ArrowInvalid, pa.ArrowTypeError):
            return
