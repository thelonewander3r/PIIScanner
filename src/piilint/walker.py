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


def _passes_filters(
    path: Path,
    *,
    root: Path,
    ignore: Any,
    include_spec: Any,
    exclude_spec: Any,
    max_file_bytes: int,
) -> bool:
    if any(part in DEFAULT_EXCLUDE_DIRS for part in path.parts):
        return False
    try:
        rel = _rel_posix(root, path)
    except ValueError:
        return False
    if ignore is not None and ignore.match_file(rel):
        return False
    if exclude_spec is not None and exclude_spec.match_file(rel):
        return False
    if include_spec is not None and not include_spec.match_file(rel):
        return False
    try:
        if path.stat().st_size > max_file_bytes:
            return False
    except OSError:
        return False
    return True


def iter_files(
    root: Path,
    *,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    only_paths: list[Path] | None = None,
) -> Iterator[Path]:
    """Yield files under root respecting ignore rules. Deterministic sort order.

    If ``only_paths`` is provided, yield the intersection of those paths with
    ``root`` (still applying ignore/exclude/size filters). An empty list yields
    nothing — used for ``--staged`` with an empty index.
    """
    root = root.resolve()
    if root.is_file():
        if only_paths is not None:
            allowed = {p.resolve() for p in only_paths}
            if root in allowed:
                yield root
            return
        yield root
        return

    ignore = _load_ignore_spec(root)
    include_spec = pathspec.PathSpec.from_lines("gitwildmatch", include) if include else None
    exclude_spec = pathspec.PathSpec.from_lines("gitwildmatch", exclude) if exclude else None

    if only_paths is not None:
        found: list[Path] = []
        for raw in only_paths:
            path = raw.resolve()
            if not path.is_file():
                continue
            try:
                path.relative_to(root)
            except ValueError:
                continue
            if _passes_filters(
                path,
                root=root,
                ignore=ignore,
                include_spec=include_spec,
                exclude_spec=exclude_spec,
                max_file_bytes=max_file_bytes,
            ):
                found.append(path)
        yield from sorted(found)
        return

    found = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if _passes_filters(
            path,
            root=root,
            ignore=ignore,
            include_spec=include_spec,
            exclude_spec=exclude_spec,
            max_file_bytes=max_file_bytes,
        ):
            found.append(path)

    yield from found
