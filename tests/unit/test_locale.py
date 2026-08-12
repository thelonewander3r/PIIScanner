"""Locale coverage: phone regions + SIN_CA / NINO_UK / BSN_NL."""

from __future__ import annotations

from pathlib import Path

from piilint.config import config_from_mapping, default_config
from piilint.engine import scan_path
from piilint.findings import EntityType, mask_value
from piilint.recognizers.bsn_nl import BsnNlRecognizer, bsn_11_proef_valid
from piilint.recognizers.nino_uk import NinoUkRecognizer
from piilint.recognizers.phone import PhoneRecognizer
from piilint.recognizers.sin_ca import SinCaRecognizer, luhn_valid

CORPUS_TEXT = Path(__file__).resolve().parent.parent / "corpus" / "text"


def test_default_entity_toggles() -> None:
    cfg = default_config()
    assert cfg.entity_enabled[EntityType.SIN_CA] is True
    assert cfg.entity_enabled[EntityType.NINO_UK] is False
    assert cfg.entity_enabled[EntityType.BSN_NL] is False
    assert cfg.scan.phone_region == "US"
    assert cfg.scan.phone_regions == []


def test_phone_regions_config_parse() -> None:
    cfg = config_from_mapping(
        {"scan": {"phone_region": "us", "phone_regions": ["gb", "CA", ""]}},
        source="t",
    )
    assert cfg.scan.phone_region == "US"
    assert cfg.scan.phone_regions == ["GB", "CA"]


def test_mask_locale_ids() -> None:
    assert mask_value("046-454-286", EntityType.SIN_CA) == "***-***-***"
    assert mask_value("AB 12 34 56 C", EntityType.NINO_UK) == "** ****** *"
    assert mask_value("100000009", EntityType.BSN_NL) == "*********"


def test_sin_ca_valid_and_invalid() -> None:
    rec = SinCaRecognizer()
    hits = rec.scan("employee SIN 046-454-286 on file")
    assert len(hits) == 1
    assert hits[0].entity == EntityType.SIN_CA
    assert luhn_valid("046454286")
    assert not luhn_valid("123456789")
    assert rec.scan("fail 123-456-789") == []
    # Bare digits without context: no match (precision)
    assert rec.scan("id 046454286 stored") == []
    # Bare with context
    bare = rec.scan("SIN 046454286")
    assert len(bare) == 1


def test_nino_requires_context() -> None:
    rec = NinoUkRecognizer()
    assert rec.scan("AB 12 34 56 C") == []
    hits = rec.scan("NINO AB 12 34 56 C")
    assert len(hits) == 1
    assert hits[0].entity == EntityType.NINO_UK
    assert rec.scan("National Insurance JH178354A")
    # Disallowed prefix
    assert rec.scan("NI number BG123456A") == []
    # Bad suffix
    assert rec.scan("NI AB123456E") == []


def test_bsn_11_proef() -> None:
    rec = BsnNlRecognizer()
    assert bsn_11_proef_valid("100000009")
    assert not bsn_11_proef_valid("000000000")
    assert not bsn_11_proef_valid("123456789")
    hits = rec.scan("100000009")
    assert len(hits) == 1
    assert rec.scan("123456789") == []
    spaced = rec.scan("1000 00 010")
    assert len(spaced) == 1


def test_phone_extra_regions() -> None:
    us_only = PhoneRecognizer(default_region="US")
    assert us_only.scan("020 7946 0958") == []
    multi = PhoneRecognizer(default_region="US", extra_regions=["GB"])
    hits = multi.scan("020 7946 0958")
    assert len(hits) == 1
    # US numbers still work
    assert multi.scan("+1 212-735-0182")


def test_scan_nino_bsn_off_by_default() -> None:
    result = scan_path(CORPUS_TEXT / "locale_ids.txt")
    entities = {f.entity for f in result.findings}
    assert EntityType.SIN_CA in entities
    assert EntityType.NINO_UK not in entities
    assert EntityType.BSN_NL not in entities


def test_scan_enable_nino_bsn() -> None:
    cfg = default_config()
    cfg.entity_enabled[EntityType.NINO_UK] = True
    cfg.entity_enabled[EntityType.BSN_NL] = True
    result = scan_path(CORPUS_TEXT / "locale_ids.txt", config=cfg)
    entities = {f.entity for f in result.findings}
    assert EntityType.NINO_UK in entities
    assert EntityType.BSN_NL in entities


def test_scan_phone_regions_kwarg() -> None:
    target = CORPUS_TEXT / "phones_intl.txt"
    default = scan_path(target)
    phone_default = [f for f in default.findings if f.entity == EntityType.PHONE]
    assert len(phone_default) == 2
    with_gb = scan_path(target, phone_regions=["GB"])
    phone_gb = [f for f in with_gb.findings if f.entity == EntityType.PHONE]
    assert len(phone_gb) == 3


def test_hard_negatives_still_clean() -> None:
    result = scan_path(CORPUS_TEXT / "hard_negatives.txt")
    assert result.findings == []
