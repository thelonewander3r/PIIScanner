"""Text file adapter — line-by-line with binary sniff."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from piilint.adapters import Unit

TEXT_EXTENSIONS = frozenset(
    {
        ".py",
        ".md",
        ".txt",
        ".sql",
        ".yml",
        ".yaml",
        ".toml",
        ".env",
        ".cfg",
        ".ini",
        ".rst",
    }
)


def looks_binary(sample: bytes) -> bool:
    if b"\x00" in sample:
        return True
    if not sample:
        return False
    textish = sum(1 for b in sample if b in b"\t\n\r" or 32 <= b <= 126)
    return (textish / len(sample)) < 0.75


class TextAdapter:
    name = "text"
    extensions = TEXT_EXTENSIONS

    def supports(self, path: Path) -> bool:
        suffix = path.suffix.lower()
        if suffix in self.extensions:
            return True
        return suffix == ""

    def iter_units(self, path: Path, *, rel_path: str) -> Iterator[Unit]:
        try:
            data = path.read_bytes()
        except OSError:
            return
        if looks_binary(data[:8192]):
            return
        if data.startswith(b"\xef\xbb\xbf"):
            data = data[3:]
        text = data.decode("utf-8", errors="replace")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        for idx, line in enumerate(text.split("\n"), start=1):
            yield Unit(text=line, path=rel_path, line=idx)
