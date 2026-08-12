"""JSON / JSONL adapter — keys act as column headers."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from piilint.adapters import Unit

JSON_SAMPLE_BYTES = 50 * 1024 * 1024
DEFAULT_SAMPLE_ROWS = 50_000


def _walk(
    value: Any,
    *,
    rel_path: str,
    key: str | None,
    line: int | None,
    sampled: bool,
) -> Iterator[Unit]:
    if isinstance(value, dict):
        for child_key, child in value.items():
            child_name = str(child_key)
            yield from _walk(
                child,
                rel_path=rel_path,
                key=child_name,
                line=line,
                sampled=sampled,
            )
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item, rel_path=rel_path, key=key, line=line, sampled=sampled)
    elif value is None:
        return
    else:
        text = str(value).strip()
        if not text:
            return
        yield Unit(
            text=text,
            path=rel_path,
            line=line,
            column=key,
            context_key=key,
            # Aggregate when we have a key (object fields); scalar JSONL rows stay per-line.
            aggregate=key is not None,
            sampled=sampled,
        )


class JsonAdapter:
    name = "json"
    extensions = frozenset({".json", ".jsonl"})

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions

    def iter_units(
        self,
        path: Path,
        *,
        rel_path: str,
        sample_rows: int | None = None,
    ) -> Iterator[Unit]:
        suffix = path.suffix.lower()
        try:
            size = path.stat().st_size
        except OSError:
            return

        if suffix == ".jsonl":
            yield from self._iter_jsonl(path, rel_path=rel_path, sample_rows=sample_rows, size=size)
            return

        sampled = size > JSON_SAMPLE_BYTES or sample_rows is not None
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return

        # Large JSON: if top-level list, sample first N elements.
        if isinstance(data, list) and (sampled or sample_rows is not None):
            limit = sample_rows or DEFAULT_SAMPLE_ROWS
            data = data[:limit]
            sampled = True

        yield from _walk(data, rel_path=rel_path, key=None, line=None, sampled=sampled)

    def _iter_jsonl(
        self,
        path: Path,
        *,
        rel_path: str,
        sample_rows: int | None,
        size: int,
    ) -> Iterator[Unit]:
        sampled = False
        row_limit = sample_rows
        if row_limit is None and size > JSON_SAMPLE_BYTES:
            row_limit = DEFAULT_SAMPLE_ROWS
            sampled = True
        elif sample_rows is not None:
            sampled = True

        try:
            with path.open(encoding="utf-8", errors="replace") as fh:
                for idx, line in enumerate(fh, start=1):
                    if row_limit is not None and idx > row_limit:
                        break
                    raw = line.strip()
                    if not raw:
                        continue
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        yield Unit(text=raw, path=rel_path, line=idx, sampled=sampled)
                        continue
                    yield from _walk(
                        data,
                        rel_path=rel_path,
                        key=None,
                        line=idx,
                        sampled=sampled,
                    )
        except OSError:
            return
