"""Allowlist, test-data downweight, entity disable, severity overrides."""

from __future__ import annotations

from piilint.config import AllowlistConfig, Config, ScanConfig, default_config
from piilint.findings import EntityType, Finding, Location, Severity
from piilint.policy import apply_policy, is_test_data


def _finding(
    entity: EntityType,
    value: str,
    *,
    confidence: float = 0.95,
    severity: Severity | None = None,
    line: int | None = 1,
    path: str = "a.py",
) -> Finding:
    return Finding.create(
        entity=entity,
        raw_value=value,
        location=Location(path=path, line=line),
        confidence=confidence,
        severity=severity,
    )


def test_allowlist_exact_value() -> None:
    cfg = default_config()
    cfg.allowlist = AllowlistConfig(values=["support@mycompany.com"])
    findings = [
        _finding(EntityType.EMAIL, "support@mycompany.com"),
        _finding(EntityType.EMAIL, "other@mycompany.com"),
    ]
    out = apply_policy(findings, cfg)
    assert len(out) == 1
    assert out[0].normalized_value == "other@mycompany.com"


def test_allowlist_domain_case_insensitive() -> None:
    cfg = default_config()
    cfg.allowlist = AllowlistConfig(domains=["MyCompany.DEV"])
    findings = [
        _finding(EntityType.EMAIL, "a@mycompany.dev"),
        _finding(EntityType.EMAIL, "b@other.com"),
    ]
    out = apply_policy(findings, cfg)
    assert len(out) == 1
    assert out[0].normalized_value.endswith("@other.com")


def test_entity_disable_drops() -> None:
    cfg = default_config()
    cfg.entity_enabled[EntityType.EMAIL] = False
    findings = [_finding(EntityType.EMAIL, "a@b.com"), _finding(EntityType.PHONE, "+12127350182")]
    # phone may or may not validate — use SSN instead for stability
    findings = [
        _finding(EntityType.EMAIL, "a@b.com"),
        _finding(EntityType.SSN_US, "234-56-7890"),
    ]
    out = apply_policy(findings, cfg)
    assert all(f.entity != EntityType.EMAIL for f in out)
    assert any(f.entity == EntityType.SSN_US for f in out)


def test_severity_override() -> None:
    cfg = default_config()
    cfg.severity_overrides[EntityType.EMAIL] = Severity.HIGH
    out = apply_policy([_finding(EntityType.EMAIL, "a@b.co")], cfg)
    assert len(out) == 1
    assert out[0].severity == Severity.HIGH


def test_test_data_email_example_com_downweight() -> None:
    cfg = default_config()
    cfg.scan.min_confidence = 0.6
    f = _finding(EntityType.EMAIL, "user@example.com", confidence=0.9, severity=Severity.MEDIUM)
    assert is_test_data(f)
    out = apply_policy([f], cfg)
    # 0.9 - 0.4 = 0.5 < 0.6 → dropped
    assert out == []


def test_test_data_downweight_keeps_above_floor() -> None:
    cfg = default_config()
    cfg.scan.min_confidence = 0.4
    f = _finding(EntityType.EMAIL, "user@example.org", confidence=0.9, severity=Severity.HIGH)
    out = apply_policy([f], cfg)
    assert len(out) == 1
    assert abs(out[0].confidence - 0.5) < 1e-9
    assert out[0].severity == Severity.LOW


def test_fake_card_downweight() -> None:
    cfg = default_config()
    cfg.scan.min_confidence = 0.5
    f = _finding(
        EntityType.CREDIT_CARD,
        "4111 1111 1111 1111",
        confidence=0.95,
        severity=Severity.HIGH,
    )
    assert is_test_data(f)
    out = apply_policy([f], cfg)
    assert len(out) == 1
    assert out[0].severity == Severity.LOW
    assert abs(out[0].confidence - 0.55) < 1e-9


def test_fake_phone_55501() -> None:
    f = _finding(EntityType.PHONE, "555-0123", confidence=0.9)
    # normalize strips punctuation → 5550123
    assert is_test_data(f)


def test_rfc5737_ip() -> None:
    f = _finding(EntityType.IP_ADDRESS, "192.0.2.44", confidence=0.8)
    assert is_test_data(f)


def test_min_confidence_drop() -> None:
    cfg = Config(scan=ScanConfig(min_confidence=0.8))
    f = _finding(EntityType.EMAIL, "a@b.co", confidence=0.7)
    assert apply_policy([f], cfg) == []
