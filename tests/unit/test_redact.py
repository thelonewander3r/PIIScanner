"""Tests for piilint redact (span rewrite copies)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from piilint.cli import app
from piilint.config import default_config
from piilint.engine import scan_path
from piilint.findings import EntityType, mask_value
from piilint.recognizers import build_default_registry
from piilint.redact import apply_span_replacements, redact_plain_text, redact_tree

CORPUS_TEXT = Path(__file__).resolve().parent.parent / "corpus" / "text"
CORPUS_CSV = Path(__file__).resolve().parent.parent / "corpus" / "csv"
CORPUS_JSON = Path(__file__).resolve().parent.parent / "corpus" / "json"

RAW_SECRETS = [
    "customer.alpha@retailmail.test",
    "ops.beta@corpmail.test",
    "234-56-7890",
    "512-48-3017",
    "4532015112830366",
    "4556737586899855",
    "GB82WEST12345698765432",
    "DE89370400440532013000",
]


def test_apply_span_replacements_reverse_stable() -> None:
    text = "email customer.alpha@retailmail.test end"
    email = "customer.alpha@retailmail.test"
    start = text.index(email)
    from piilint.redact import _Span

    out = apply_span_replacements(
        text,
        [_Span(start=start, end=start + len(email), entity=EntityType.EMAIL, value=email)],
    )
    assert email not in out
    assert mask_value(email, EntityType.EMAIL) in out


def test_redact_plain_respects_inline_ignore() -> None:
    cfg = default_config()
    registry = build_default_registry()
    line = "secret customer.alpha@retailmail.test  # piilint: ignore[EMAIL]"
    out, n = redact_plain_text(line, registry=registry, config=cfg, rel_path="a.py")
    assert n == 0
    assert "customer.alpha@retailmail.test" in out


def test_redact_tree_text_corpus(tmp_path: Path) -> None:
    out = tmp_path / "clean"
    result = redact_tree(CORPUS_TEXT, out, config=default_config())
    assert result.files_written >= 1
    blob = "\n".join(p.read_text(encoding="utf-8") for p in out.rglob("*") if p.is_file())
    for raw in RAW_SECRETS:
        assert raw not in blob, f"raw leaked: {raw}"
    # sources untouched
    original = (CORPUS_TEXT / "emails.py").read_text(encoding="utf-8")
    assert "customer.alpha@retailmail.test" in original
    # rescan redacted tree → fewer email/ssn/card findings than original corpus scan
    before = scan_path(CORPUS_TEXT)
    after = scan_path(out)
    assert len(after.findings) < len(before.findings)


def test_redact_csv_and_json(tmp_path: Path) -> None:
    out = tmp_path / "clean"
    redact_tree(CORPUS_CSV, out / "csv", config=default_config())
    redact_tree(CORPUS_JSON, out / "json", config=default_config())
    csv_blob = (out / "csv" / "customers.csv").read_text(encoding="utf-8")
    json_blob = (out / "json" / "contacts.json").read_text(encoding="utf-8")
    for raw in ("234-56-7890", "512-48-3017"):
        assert raw not in csv_blob
    # contacts.json planted emails should be masked
    assert "retailmail.test" not in json_blob or "@" not in json_blob or "c***@" in json_blob
    # stronger: no full synthetic emails from RAW if present in contacts
    for raw in RAW_SECRETS:
        assert raw not in csv_blob
        assert raw not in json_blob


def test_cli_redact_requires_output(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["redact", str(tmp_path)])
    assert result.exit_code == 2


def test_cli_redact_writes_copies(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "note.txt").write_text(
        "contact customer.alpha@retailmail.test please\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(app, ["redact", str(src), "-o", str(out)])
    assert result.exit_code == 0, result.output
    cleaned = (out / "note.txt").read_text(encoding="utf-8")
    assert "customer.alpha@retailmail.test" not in cleaned
    assert "customer.alpha@retailmail.test" in (src / "note.txt").read_text(encoding="utf-8")
    for raw in RAW_SECRETS:
        assert raw not in result.output


def test_policy_packs_parse() -> None:
    from piilint.config import load_file_config

    root = Path(__file__).resolve().parents[2] / "examples" / "policies"
    for name in ("strict-ci.toml", "data-eng.toml", "open-source-lib.toml"):
        cfg = load_file_config(root / name)
        assert cfg.entity_enabled[EntityType.IP_ADDRESS] is False
        assert cfg.scan.min_confidence >= 0.65


CORPUS_NOTEBOOK = Path(__file__).resolve().parent.parent / "corpus" / "notebook"
CORPUS_PARQUET = Path(__file__).resolve().parent.parent / "corpus" / "parquet"


def test_redact_notebook_covers_outputs(tmp_path: Path) -> None:
    import nbformat

    out = tmp_path / "clean"
    result = redact_tree(CORPUS_NOTEBOOK, out, config=default_config())
    assert result.files_written >= 1
    assert result.spans_redacted >= 1
    dest = out / "leak_demo.ipynb"
    nb = nbformat.read(dest, as_version=4)
    blob = dest.read_text(encoding="utf-8")
    for raw in RAW_SECRETS:
        assert raw not in blob
    # Must still be a loadable notebook with outputs present
    assert nb.cells
    assert any(cell.get("outputs") for cell in nb.cells if cell.get("cell_type") == "code")
    # sources untouched
    original = (CORPUS_NOTEBOOK / "leak_demo.ipynb").read_text(encoding="utf-8")
    assert any(raw in original for raw in RAW_SECRETS) or "4111" in original or "4532" in original
    after = scan_path(out)
    before = scan_path(CORPUS_NOTEBOOK)
    assert len(after.findings) < len(before.findings)


def test_redact_parquet_string_columns(tmp_path: Path) -> None:
    import pyarrow.parquet as pq

    out = tmp_path / "clean"
    result = redact_tree(CORPUS_PARQUET, out, config=default_config())
    assert result.files_written >= 1
    dest = out / "users.parquet"
    table = pq.read_table(dest)
    assert table.num_rows >= 1
    blob = "\n".join(
        str(v) for col in table.column_names for v in table.column(col).to_pylist() if v is not None
    )
    for raw in RAW_SECRETS:
        assert raw not in blob
    after = scan_path(out)
    before = scan_path(CORPUS_PARQUET)
    assert len(after.findings) <= len(before.findings)


def test_filter_matches_drops_disabled_person() -> None:
    """Policy drops PERSON unless entity_enabled is on (the #49 redact --ner gap)."""
    from piilint.recognizers import Match
    from piilint.redact import _filter_matches

    text = "Agent Alice Exampleton"
    matches = [
        Match(
            entity=EntityType.PERSON,
            value="Alice Exampleton",
            start=6,
            end=22,
            confidence=0.85,
        )
    ]
    cfg = default_config()
    assert cfg.entity_enabled[EntityType.PERSON] is False
    assert _filter_matches(text, matches, config=cfg, rel_path="calls.xlsx") == []

    cfg.entity_enabled[EntityType.PERSON] = True
    kept = _filter_matches(text, matches, config=cfg, rel_path="calls.xlsx")
    assert len(kept) == 1
    assert kept[0].value == "Alice Exampleton"
    assert kept[0].entity == EntityType.PERSON
