"""gitutil + --staged CLI tests (temp git repos)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from piilint.cli import app
from piilint.engine import scan_path
from piilint.findings import EntityType
from piilint.gitutil import GitError, find_repo_root, staged_files

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not available")


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "dev@example.com")
    _git(tmp_path, "config", "user.name", "Dev")
    # Avoid dependent on global defaults; keep content readable on Windows
    _git(tmp_path, "config", "core.autocrlf", "false")
    return tmp_path


def test_find_repo_root_and_staged(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    tracked = repo / "keep.py"
    tracked.write_text("# keep keep@retailmail.test\n", encoding="utf-8")
    _git(repo, "add", "keep.py")
    _git(repo, "commit", "-m", "init")

    dirty = repo / "staged.py"
    dirty.write_text("# staged staged@retailmail.test\n", encoding="utf-8")
    unstaged = repo / "unstaged.py"
    unstaged.write_text("# unstaged unstaged@retailmail.test\n", encoding="utf-8")
    _git(repo, "add", "staged.py")

    root = find_repo_root(repo / "keep.py")
    assert root.resolve() == repo.resolve()

    staged = staged_files(repo)
    staged_names = {p.name for p in staged}
    assert staged_names == {"staged.py"}

    # only_paths scan sees staged file only
    result = scan_path(repo, only_paths=staged)
    paths = {f.location.path for f in result.findings if f.entity == EntityType.EMAIL}
    assert "staged.py" in paths
    assert "unstaged.py" not in paths
    assert "keep.py" not in paths


def test_not_a_git_repo(tmp_path: Path) -> None:
    with pytest.raises(GitError, match="Not a git repository"):
        find_repo_root(tmp_path)


def test_cli_staged_nothing_staged_exits_0(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "a.py").write_text("# a a@retailmail.test\n", encoding="utf-8")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-m", "init")
    # working tree clean — nothing staged
    runner = CliRunner()
    result = runner.invoke(app, ["scan", str(repo), "--staged"])
    assert result.exit_code == 0, result.output
    assert "Nothing staged" in result.output


def test_cli_staged_not_git_exits_2(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("# a a@retailmail.test\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["scan", str(tmp_path), "--staged"])
    assert result.exit_code == 2, result.output
    assert "Git error" in result.output or "git" in result.output.lower()


def test_cli_staged_scans_only_staged(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "old.py").write_text("# old old@retailmail.test\n", encoding="utf-8")
    _git(repo, "add", "old.py")
    _git(repo, "commit", "-m", "init")
    (repo / "new.py").write_text("# new new@retailmail.test\n", encoding="utf-8")
    _git(repo, "add", "new.py")

    runner = CliRunner()
    result = runner.invoke(app, ["scan", str(repo), "--staged", "--fail-on", "medium"])
    assert result.exit_code == 1, result.output
    assert "new.py" in result.output
    assert "old.py" not in result.output
