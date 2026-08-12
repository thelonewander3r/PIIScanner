"""File walker: .gitignore + .piiignore + size/binary guards."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pathspec

# Skip obviously huge / binary-ish trees even without ignore files
DEFAULT_EXCLUDE_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "dist",
        "build",
        ".tox",
        ".eggs",
    }
)

DEFAULT_MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MiB hard cap for Phase 1 text path


def _load_ignore_spec(root: Path) -> Any:
    patterns: list[str] = []
    for name in (".gitignore", ".piiignore"):
        path = root / name
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            patterns.extend(
                line for line in text.splitlines() if line.strip() and not line.startswith("#")
            )
    if not patterns:
        return None
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def _rel_posix(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def iter_files(
    root: Path,
    *,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> Iterator[Path]:
    """Yield files under root respecting ignore rules. Deterministic sort order."""
    root = root.resolve()
    if root.is_file():
        yield root
        return

    ignore = _load_ignore_spec(root)
    include_spec = pathspec.PathSpec.from_lines("gitwildmatch", include) if include else None
    exclude_spec = pathspec.PathSpec.from_lines("gitwildmatch", exclude) if exclude else None

    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        # Directory component skip
        if any(part in DEFAULT_EXCLUDE_DIRS for part in path.parts):
            continue
        try:
            rel = _rel_posix(root, path)
        except ValueError:
            continue
        if ignore is not None and ignore.match_file(rel):
            continue
        if exclude_spec is not None and exclude_spec.match_file(rel):
            continue
        if include_spec is not None and not include_spec.match_file(rel):
            continue
        try:
            if path.stat().st_size > max_file_bytes:
                continue
        except OSError:
            continue
        found.append(path)

    yield from found
