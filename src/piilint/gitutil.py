"""Git helpers for ``--staged`` mode.

Uses stdlib ``subprocess`` only (no GitPython). No network — local git only.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class GitError(Exception):
    """Git unavailable, not a repository, or command failure."""


def _git_executable() -> str:
    exe = shutil.which("git")
    if not exe:
        raise GitError("git executable not found on PATH")
    return exe


def find_repo_root(start: Path | None = None) -> Path:
    """Return the git toplevel for ``start`` (file or directory). Raises GitError."""
    start_path = (start or Path.cwd()).resolve()
    cwd = start_path if start_path.is_dir() else start_path.parent
    git = _git_executable()
    try:
        proc = subprocess.run(
            [git, "-c", "safe.directory=*", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitError(f"Failed to run git: {exc}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "not a git repository").strip()
        raise GitError(f"Not a git repository ({cwd}): {detail}")
    return Path(proc.stdout.strip())


def staged_files(repo_root: Path | None = None) -> list[Path]:
    """Return absolute paths of staged files (Added/Copied/Modified/Renamed).

    Equivalent to ``git diff --cached --name-only --diff-filter=ACMR``.
    Returns an empty list when nothing is staged. Paths are absolute and
    resolved under the repo root for consistent intersection with the walker.
    """
    root = find_repo_root(repo_root) if repo_root is not None else find_repo_root()
    git = _git_executable()
    try:
        proc = subprocess.run(
            [
                git,
                "-c",
                "safe.directory=*",
                "diff",
                "--cached",
                "--name-only",
                "--diff-filter=ACMR",
                "-z",
            ],
            cwd=root,
            capture_output=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitError(f"Failed to run git: {exc}") from exc
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(f"git diff --cached failed: {err or 'unknown error'}")

    if not proc.stdout:
        return []

    text = proc.stdout.decode("utf-8", errors="surrogateescape")
    rels = [p for p in text.split("\0") if p]
    out: list[Path] = []
    for rel in rels:
        # Git reports paths relative to repo root (usually with / separators)
        out.append((root / rel).resolve())
    return sorted(out, key=lambda p: p.as_posix().casefold())
