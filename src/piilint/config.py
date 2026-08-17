"""Typed configuration load + merge for piilint.

Precedence (highest wins):
1. CLI flags
2. piilint.toml at scan root (directory being scanned, or parent of a file)
3. [tool.piilint] in pyproject.toml (walks upward from scan root)
4. Built-in defaults
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from piilint.findings import DEFAULT_SEVERITY, EntityType, Severity

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised on 3.10 CI
    try:
        import tomli as tomllib
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ImportError(
            "TOML config requires tomllib (Python 3.11+) or the tomli package on 3.10"
        ) from exc


class ConfigError(Exception):
    """Invalid configuration — CLI must exit 2."""


_ENTITY_ALIASES: dict[str, EntityType] = {
    "credit_card": EntityType.CREDIT_CARD,
    "ssn_us": EntityType.SSN_US,
    "ssn": EntityType.SSN_US,
    "sin_ca": EntityType.SIN_CA,
    "sin": EntityType.SIN_CA,
    "nino_uk": EntityType.NINO_UK,
    "nino": EntityType.NINO_UK,
    "bsn_nl": EntityType.BSN_NL,
    "bsn": EntityType.BSN_NL,
    "iban": EntityType.IBAN,
    "email": EntityType.EMAIL,
    "phone": EntityType.PHONE,
    "dob": EntityType.DOB,
    "ip_address": EntityType.IP_ADDRESS,
    "ip": EntityType.IP_ADDRESS,
    "person": EntityType.PERSON,
    "address": EntityType.ADDRESS,
}

_FAIL_ON_VALUES = frozenset({"high", "medium", "low", "never"})
_SEVERITY_VALUES = {"high": Severity.HIGH, "medium": Severity.MEDIUM, "low": Severity.LOW}


def _default_entity_enabled() -> dict[EntityType, bool]:
    enabled = {e: True for e in EntityType}
    enabled[EntityType.IP_ADDRESS] = False
    enabled[EntityType.PERSON] = False
    enabled[EntityType.ADDRESS] = False
    enabled[EntityType.NINO_UK] = False
    enabled[EntityType.BSN_NL] = False
    return enabled


@dataclass(slots=True)
class ScanConfig:
    fail_on: str = "high"
    min_confidence: float = 0.6
    exclude: list[str] = field(default_factory=list)
    phone_region: str = "US"
    phone_regions: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AllowlistConfig:
    values: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Config:
    scan: ScanConfig = field(default_factory=ScanConfig)
    entity_enabled: dict[EntityType, bool] = field(default_factory=_default_entity_enabled)
    severity_overrides: dict[EntityType, Severity] = field(default_factory=dict)
    allowlist: AllowlistConfig = field(default_factory=AllowlistConfig)

    def is_entity_enabled(self, entity: EntityType) -> bool:
        return self.entity_enabled.get(entity, True)

    def severity_for(self, entity: EntityType) -> Severity:
        return self.severity_overrides.get(entity, DEFAULT_SEVERITY[entity])

    def copy(self) -> Config:
        """Deep-enough copy so callers can mutate without sharing state."""
        return Config(
            scan=ScanConfig(
                fail_on=self.scan.fail_on,
                min_confidence=self.scan.min_confidence,
                exclude=list(self.scan.exclude),
                phone_region=self.scan.phone_region,
                phone_regions=list(self.scan.phone_regions),
                columns=list(self.scan.columns),
            ),
            entity_enabled=dict(self.entity_enabled),
            severity_overrides=dict(self.severity_overrides),
            allowlist=AllowlistConfig(
                values=list(self.allowlist.values),
                domains=list(self.allowlist.domains),
            ),
        )


def default_config() -> Config:
    return Config()


def parse_entity_name(name: str) -> EntityType:
    key = name.strip().lower().replace("-", "_")
    upper = name.strip().upper()
    try:
        return EntityType(upper)
    except ValueError:
        pass
    if key in _ENTITY_ALIASES:
        return _ENTITY_ALIASES[key]
    raise ConfigError(
        f"Unknown entity name {name!r}. Expected one of: {', '.join(sorted(_ENTITY_ALIASES))}"
    )


def _as_bool(value: Any, *, path: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ConfigError(f"{path} must be a boolean, got {type(value).__name__}")


def _as_float(value: Any, *, path: str) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if not 0.0 <= number <= 1.0:
            raise ConfigError(f"{path} must be between 0.0 and 1.0, got {number}")
        return number
    raise ConfigError(f"{path} must be a number, got {type(value).__name__}")


def _as_str_list(value: Any, *, path: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ConfigError(f"{path} must be a list of strings")
    return list(value)


def _parse_fail_on(value: Any, *, path: str) -> str:
    if not isinstance(value, str) or value.lower() not in _FAIL_ON_VALUES:
        raise ConfigError(f"{path} must be one of: high, medium, low, never")
    return value.lower()


def _parse_severity(value: Any, *, path: str) -> Severity:
    if not isinstance(value, str) or value.lower() not in _SEVERITY_VALUES:
        raise ConfigError(f"{path} must be one of: high, medium, low")
    return _SEVERITY_VALUES[value.lower()]


def apply_mapping(cfg: Config, data: Mapping[str, Any], *, source: str) -> None:
    """Apply only keys present in ``data`` onto ``cfg`` (in-place overlay)."""
    if not isinstance(data, Mapping):
        raise ConfigError(f"{source}: root must be a table")

    scan_raw = data.get("scan")
    if scan_raw is not None:
        if not isinstance(scan_raw, Mapping):
            raise ConfigError(f"{source}: [scan] must be a table")
        if "fail_on" in scan_raw:
            cfg.scan.fail_on = _parse_fail_on(scan_raw["fail_on"], path=f"{source}: scan.fail_on")
        if "min_confidence" in scan_raw:
            cfg.scan.min_confidence = _as_float(
                scan_raw["min_confidence"], path=f"{source}: scan.min_confidence"
            )
        if "exclude" in scan_raw:
            cfg.scan.exclude = _as_str_list(scan_raw["exclude"], path=f"{source}: scan.exclude")
        if "phone_region" in scan_raw:
            region = scan_raw["phone_region"]
            if not isinstance(region, str) or not region.strip():
                raise ConfigError(f"{source}: scan.phone_region must be a non-empty string")
            cfg.scan.phone_region = region.strip().upper()
        if "phone_regions" in scan_raw:
            raw_regions = scan_raw["phone_regions"]
            if not isinstance(raw_regions, list) or not all(
                isinstance(x, str) for x in raw_regions
            ):
                raise ConfigError(f"{source}: scan.phone_regions must be a list of strings")
            cfg.scan.phone_regions = [
                r.strip().upper() for r in raw_regions if isinstance(r, str) and r.strip()
            ]

    entities_raw = data.get("entities")
    if entities_raw is not None:
        if not isinstance(entities_raw, Mapping):
            raise ConfigError(f"{source}: [entities] must be a table")
        for key, value in entities_raw.items():
            entity = parse_entity_name(str(key))
            if isinstance(value, bool):
                cfg.entity_enabled[entity] = value
            elif isinstance(value, Mapping):
                if "enabled" in value:
                    cfg.entity_enabled[entity] = _as_bool(
                        value["enabled"], path=f"{source}: entities.{key}.enabled"
                    )
                if "severity" in value:
                    cfg.severity_overrides[entity] = _parse_severity(
                        value["severity"], path=f"{source}: entities.{key}.severity"
                    )
            else:
                raise ConfigError(
                    f"{source}: entities.{key} must be a boolean or a table "
                    f"with enabled/severity, got {type(value).__name__}"
                )

    allow_raw = data.get("allowlist")
    if allow_raw is not None:
        if not isinstance(allow_raw, Mapping):
            raise ConfigError(f"{source}: [allowlist] must be a table")
        if "values" in allow_raw:
            cfg.allowlist.values = _as_str_list(
                allow_raw["values"], path=f"{source}: allowlist.values"
            )
        if "domains" in allow_raw:
            cfg.allowlist.domains = [
                d.strip().lower()
                for d in _as_str_list(allow_raw["domains"], path=f"{source}: allowlist.domains")
            ]


def config_from_mapping(data: Mapping[str, Any], *, source: str) -> Config:
    """Parse a TOML-like mapping into Config. Raises ConfigError on invalid input."""
    cfg = default_config()
    apply_mapping(cfg, data, source=source)
    return cfg


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ConfigError(f"Cannot read config file {path}: {exc}") from exc
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigError(f"Config file {path} is not valid UTF-8: {exc}") from exc
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Config file {path} root must be a table")
    return data


def find_pyproject(start: Path) -> Path | None:
    cur = start.resolve()
    if cur.is_file():
        cur = cur.parent
    for directory in [cur, *cur.parents]:
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


def load_file_config(path: Path) -> Config:
    data = _read_toml(path)
    if path.name == "pyproject.toml":
        tool = data.get("tool")
        if not isinstance(tool, Mapping):
            return default_config()
        section = tool.get("piilint")
        if section is None:
            return default_config()
        if not isinstance(section, Mapping):
            raise ConfigError(f"{path}: [tool.piilint] must be a table")
        return config_from_mapping(section, source=str(path))
    return config_from_mapping(data, source=str(path))


def merge_configs(*configs: Config) -> Config:
    """Merge full Config objects left-to-right; later entries win for scalars.

    Prefer ``load_config`` / ``apply_mapping`` for file overlays so unspecified
    keys do not reset earlier layers to defaults.
    """
    result = default_config()
    for cfg in configs:
        result.scan.fail_on = cfg.scan.fail_on
        result.scan.min_confidence = cfg.scan.min_confidence
        result.scan.phone_region = cfg.scan.phone_region
        result.scan.phone_regions = list(cfg.scan.phone_regions)
        if cfg.scan.exclude:
            result.scan.exclude = list(cfg.scan.exclude)
        result.entity_enabled.update(cfg.entity_enabled)
        result.severity_overrides.update(cfg.severity_overrides)
        if cfg.allowlist.values:
            result.allowlist.values = list(cfg.allowlist.values)
        if cfg.allowlist.domains:
            result.allowlist.domains = list(cfg.allowlist.domains)
    return result


def resolve_scan_root(target: Path) -> Path:
    """Directory used to locate piilint.toml / walk for pyproject.toml."""
    resolved = target.resolve()
    return resolved if resolved.is_dir() else resolved.parent


def load_config(
    target: Path,
    *,
    cli_fail_on: str | None = None,
    cli_min_confidence: float | None = None,
    cli_enable_ip: bool | None = None,
    cli_exclude: list[str] | None = None,
) -> Config:
    """Load config with documented precedence. Raises ConfigError."""
    scan_root = resolve_scan_root(target)
    cfg = default_config()

    pyproject = find_pyproject(scan_root)
    if pyproject is not None:
        data = _read_toml(pyproject)
        tool = data.get("tool")
        if isinstance(tool, Mapping):
            section = tool.get("piilint")
            if section is not None:
                if not isinstance(section, Mapping):
                    raise ConfigError(f"{pyproject}: [tool.piilint] must be a table")
                apply_mapping(cfg, section, source=str(pyproject))

    piilint_toml = scan_root / "piilint.toml"
    if piilint_toml.is_file():
        apply_mapping(cfg, _read_toml(piilint_toml), source=str(piilint_toml))

    if cli_fail_on is not None:
        cfg.scan.fail_on = _parse_fail_on(cli_fail_on, path="CLI --fail-on")
    if cli_min_confidence is not None:
        cfg.scan.min_confidence = _as_float(cli_min_confidence, path="CLI --min-confidence")
    if cli_enable_ip is not None:
        cfg.entity_enabled[EntityType.IP_ADDRESS] = cli_enable_ip
    if cli_exclude:
        cfg.scan.exclude = list(cli_exclude)

    return cfg
