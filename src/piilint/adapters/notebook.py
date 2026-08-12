"""Jupyter notebook adapter — scans source cells and outputs."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import nbformat
from nbformat.reader import NotJSONError

from piilint.adapters import Unit


def _output_texts(output: object) -> list[str]:
    texts: list[str] = []
    output_type = getattr(output, "output_type", None) or (
        output.get("output_type") if isinstance(output, dict) else None
    )
    if output_type == "stream":
        text = getattr(output, "text", None)
        if text is None and isinstance(output, dict):
            text = output.get("text")
        if text:
            texts.append(text if isinstance(text, str) else "".join(text))
    elif output_type in {"execute_result", "display_data"}:
        data = getattr(output, "data", None)
        if data is None and isinstance(output, dict):
            data = output.get("data", {})
        if isinstance(data, dict) and "text/plain" in data:
            plain = data["text/plain"]
            texts.append(plain if isinstance(plain, str) else "".join(plain))
    return texts


class NotebookAdapter:
    name = "notebook"
    extensions = frozenset({".ipynb"})

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions

    def iter_units(self, path: Path, *, rel_path: str) -> Iterator[Unit]:
        try:
            nb = nbformat.read(path, as_version=4)  # type: ignore[no-untyped-call]
        except (OSError, NotJSONError, nbformat.ValidationError, ValueError):
            return

        for cell_idx, cell in enumerate(nb.cells):
            source = cell.get("source") or ""
            if isinstance(source, list):
                source = "".join(source)
            source = source.replace("\r\n", "\n").replace("\r", "\n")
            for line_idx, line in enumerate(source.split("\n"), start=1):
                yield Unit(
                    text=line,
                    path=rel_path,
                    cell=cell_idx,
                    cell_part="source",
                    line=line_idx,
                )

            if cell.get("cell_type") != "code":
                continue
            for output in cell.get("outputs") or []:
                for block in _output_texts(output):
                    block = block.replace("\r\n", "\n").replace("\r", "\n")
                    for line_idx, line in enumerate(block.split("\n"), start=1):
                        yield Unit(
                            text=line,
                            path=rel_path,
                            cell=cell_idx,
                            cell_part="output",
                            line=line_idx,
                        )
