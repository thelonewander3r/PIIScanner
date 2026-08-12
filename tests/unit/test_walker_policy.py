"""Walker .piiignore + config/CLI exclude integration."""

from __future__ import annotations

from pathlib import Path

from piilint.config import load_config
from piilint.engine import scan_path
from piilint.findings import EntityType
from piilint.walker import iter_files


def _write_email(path: Path, addr: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# contact {addr}\n", encoding="utf-8")


def test_piiignore_excludes_beyond_gitignore(tmp_path: Path) -> None:
    _write_email(tmp_path / "keep.py", "keep@retailmail.test")
    _write_email(tmp_path / "secret_fixtures" / "leak.py", "leak@retailmail.test")
    # .gitignore does NOT ignore secret_fixtures
    (tmp_path / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
    (tmp_path / ".piiignore").write_text("secret_fixtures/**\n", encoding="utf-8")

    found = {p.relative_to(tmp_path).as_posix() for p in iter_files(tmp_path)}
    assert "keep.py" in found
    assert "secret_fixtures/leak.py" not in found

    result = scan_path(tmp_path)
    emails = [f for f in result.findings if f.entity == EntityType.EMAIL]
    assert len(emails) == 1
    assert emails[0].location.path == "keep.py"


def test_config_scan_exclude(tmp_path: Path) -> None:
    _write_email(tmp_path / "ok.py", "ok@retailmail.test")
    _write_email(tmp_path / "fixtures" / "x.py", "x@retailmail.test")
    (tmp_path / "piilint.toml").write_text(
        """
[scan]
exclude = ["fixtures/**"]
""",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    result = scan_path(tmp_path, config=cfg)
    paths = {f.location.path for f in result.findings}
    assert "ok.py" in paths
    assert "fixtures/x.py" not in paths


def test_cli_exclude_kwarg(tmp_path: Path) -> None:
    _write_email(tmp_path / "a.py", "a@retailmail.test")
    _write_email(tmp_path / "skip" / "b.py", "b@retailmail.test")
    result = scan_path(tmp_path, exclude=["skip/**"])
    paths = {f.location.path for f in result.findings}
    assert "a.py" in paths
    assert "skip/b.py" not in paths
