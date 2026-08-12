"""Inline # piilint: ignore suppressions (text/code lines)."""

from __future__ import annotations

from pathlib import Path

from piilint.config import default_config
from piilint.engine import scan_path
from piilint.findings import EntityType, Finding, Location
from piilint.policy import apply_policy, parse_inline_suppression


def test_parse_ignore_all() -> None:
    assert parse_inline_suppression("x = 1  # piilint: ignore") == frozenset()


def test_parse_ignore_entity_list() -> None:
    got = parse_inline_suppression("contact  # piilint: ignore[EMAIL, PHONE]")
    assert got == frozenset({EntityType.EMAIL, EntityType.PHONE})


def test_ignore_all_on_line() -> None:
    cfg = default_config()
    f = Finding.create(
        entity=EntityType.EMAIL,
        raw_value="a@b.com",
        location=Location(path="x.py", line=3),
        confidence=0.9,
    )
    line_texts = {("x.py", 3): "email = 'a@b.com'  # piilint: ignore"}
    assert apply_policy([f], cfg, line_texts=line_texts) == []


def test_ignore_email_only() -> None:
    cfg = default_config()
    email = Finding.create(
        entity=EntityType.EMAIL,
        raw_value="a@b.com",
        location=Location(path="x.py", line=1),
        confidence=0.9,
    )
    ssn = Finding.create(
        entity=EntityType.SSN_US,
        raw_value="234-56-7890",
        location=Location(path="x.py", line=1),
        confidence=0.95,
    )
    line_texts = {("x.py", 1): "a@b.com 234-56-7890  # piilint: ignore[EMAIL]"}
    out = apply_policy([email, ssn], cfg, line_texts=line_texts)
    assert len(out) == 1
    assert out[0].entity == EntityType.SSN_US


def test_engine_honors_inline_ignore(tmp_path: Path) -> None:
    src = tmp_path / "sample.py"
    src.write_text(
        "\n".join(
            [
                "# synthetic",
                "x = 'customer.alpha@retailmail.test'  # piilint: ignore",
                "y = 'ops.beta@corpmail.test'",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = scan_path(tmp_path)
    emails = [f for f in result.findings if f.entity == EntityType.EMAIL]
    assert len(emails) == 1
    # masked sample should correspond to ops.beta (o***@...)
    assert emails[0].masked_sample.startswith("o***@")


def test_column_aggregated_skips_inline_suppression() -> None:
    """Tabular findings have no line — inline ignore must not apply (v0)."""
    cfg = default_config()
    f = Finding.create(
        entity=EntityType.EMAIL,
        raw_value="a@b.com",
        location=Location(path="t.csv", column="email"),
        confidence=0.9,
        matched_count=5,
    )
    # Even if someone passed a bogus line map, no line on finding → not suppressed
    out = apply_policy([f], cfg, line_texts={("t.csv", 1): "# piilint: ignore"})
    assert len(out) == 1
