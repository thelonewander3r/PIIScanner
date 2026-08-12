"""Config load, merge precedence, and invalid-config exit codes."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from piilint.cli import app
from piilint.config import (
    ConfigError,
    config_from_mapping,
    default_config,
    load_config,
    load_file_config,
    merge_configs,
)
from piilint.findings import EntityType, Severity


def test_defaults() -> None:
    cfg = default_config()
    assert cfg.scan.fail_on == "high"
    assert cfg.scan.min_confidence == 0.6
    assert cfg.entity_enabled[EntityType.IP_ADDRESS] is False
    assert cfg.entity_enabled[EntityType.EMAIL] is True


def test_piilint_toml_overrides_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.piilint.scan]
fail_on = "low"
min_confidence = 0.5
""",
        encoding="utf-8",
    )
    (tmp_path / "piilint.toml").write_text(
        """
[scan]
fail_on = "medium"
min_confidence = 0.7
""",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.scan.fail_on == "medium"
    assert cfg.scan.min_confidence == 0.7


def test_cli_overrides_piilint_toml(tmp_path: Path) -> None:
    (tmp_path / "piilint.toml").write_text(
        """
[scan]
fail_on = "low"
min_confidence = 0.5

[entities]
email = false
""",
        encoding="utf-8",
    )
    cfg = load_config(
        tmp_path,
        cli_fail_on="high",
        cli_min_confidence=0.9,
        cli_enable_ip=True,
    )
    assert cfg.scan.fail_on == "high"
    assert cfg.scan.min_confidence == 0.9
    assert cfg.entity_enabled[EntityType.IP_ADDRESS] is True
    assert cfg.entity_enabled[EntityType.EMAIL] is False


def test_pyproject_tool_piilint(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.piilint]
[tool.piilint.scan]
fail_on = "never"
exclude = ["vendor/**"]

[tool.piilint.entities.email]
severity = "high"

[tool.piilint.allowlist]
domains = ["Example.COM"]
""",
        encoding="utf-8",
    )
    cfg = load_file_config(tmp_path / "pyproject.toml")
    assert cfg.scan.fail_on == "never"
    assert cfg.scan.exclude == ["vendor/**"]
    assert cfg.severity_overrides[EntityType.EMAIL] == Severity.HIGH
    assert cfg.allowlist.domains == ["example.com"]


def test_entity_bool_and_severity_table() -> None:
    cfg = config_from_mapping(
        {
            "entities": {
                "ip_address": True,
                "email": {"severity": "low", "enabled": True},
                "phone": False,
            }
        },
        source="test",
    )
    assert cfg.entity_enabled[EntityType.IP_ADDRESS] is True
    assert cfg.entity_enabled[EntityType.PHONE] is False
    assert cfg.severity_overrides[EntityType.EMAIL] == Severity.LOW


def test_bad_toml_raises_config_error(tmp_path: Path) -> None:
    bad = tmp_path / "piilint.toml"
    bad.write_text("[scan\nfail_on = ", encoding="utf-8")
    try:
        load_file_config(bad)
        raise AssertionError("expected ConfigError")
    except ConfigError as exc:
        assert "Invalid TOML" in str(exc)


def test_bad_fail_on_raises() -> None:
    try:
        config_from_mapping({"scan": {"fail_on": "critical"}}, source="t")
        raise AssertionError("expected ConfigError")
    except ConfigError as exc:
        assert "fail_on" in str(exc)


def test_cli_bad_config_exits_2(tmp_path: Path) -> None:
    (tmp_path / "piilint.toml").write_text("[scan\n", encoding="utf-8")
    (tmp_path / "ok.txt").write_text("hello\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 2, result.output
    assert "Config error" in result.output or "Invalid TOML" in result.output


def test_cli_missing_path_exits_2() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["scan", "C:/nonexistent/piilint-path-xyz"])
    assert result.exit_code == 2


def test_partial_piilint_toml_preserves_pyproject_scalars(tmp_path: Path) -> None:
    """Unspecified keys in piilint.toml must not reset pyproject values to defaults."""
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.piilint.scan]
fail_on = "low"
min_confidence = 0.55
""",
        encoding="utf-8",
    )
    (tmp_path / "piilint.toml").write_text(
        """
[allowlist]
domains = ["mycompany.dev"]
""",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.scan.fail_on == "low"
    assert cfg.scan.min_confidence == 0.55
    assert cfg.allowlist.domains == ["mycompany.dev"]


def test_merge_later_wins() -> None:
    a = config_from_mapping({"scan": {"fail_on": "low"}}, source="a")
    b = config_from_mapping({"scan": {"fail_on": "high"}}, source="b")
    assert merge_configs(a, b).scan.fail_on == "high"
