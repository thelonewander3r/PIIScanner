"""PDF adapter — embedded text only via optional ``piilint[office]`` (pypdf). No OCR."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path

from piilint.adapters import Unit

_INSTALL_HINT = 'pip install "piilint[office]"'
_warned = False


def office_pdf_available() -> bool:
    return importlib.util.find_spec("pypdf") is not None


def _warn_missing_once() -> None:
    global _warned
    if _warned:
        return
    _warned = True
    print(
        f"piilint: skipping .pdf (pypdf not installed). Install with: {_INSTALL_HINT}",
        file=sys.stderr,
    )


class PdfAdapter:
    name = "pdf"
    extensions = frozenset({".pdf"})

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions

    def iter_units(self, path: Path, *, rel_path: str) -> Iterator[Unit]:
        if not office_pdf_available():
            _warn_missing_once()
            return
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            reader = PdfReader(str(path))
        except (OSError, PdfReadError, ValueError):
            return

        for page_idx, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:  # noqa: BLE001 — malformed page content
                continue
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            if not text.strip():
                # Image-only / empty extract — nothing to scan (documented no-OCR limit).
                continue
            for line_idx, line in enumerate(text.split("\n"), start=1):
                if not line.strip():
                    continue
                yield Unit(
                    text=line,
                    path=rel_path,
                    line=line_idx,
                    row=page_idx,  # page number
                    cell_part="page",
                    aggregate=False,
                )
