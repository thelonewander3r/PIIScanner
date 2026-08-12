"""Phase 2 adapter behavior tests."""

from __future__ import annotations

from pathlib import Path

from piilint.engine import scan_path
from piilint.findings import EntityType

CORPUS = Path(__file__).resolve().parent.parent / "corpus"


def test_csv_column_aggregation() -> None:
    result = scan_path(CORPUS / "csv" / "customers.csv")
    emails = [f for f in result.findings if f.entity == EntityType.EMAIL]
    ssns = [f for f in result.findings if f.entity == EntityType.SSN_US]
    assert len(emails) == 1
    assert emails[0].matched_count == 2
    assert emails[0].location.column == "email"
    assert len(ssns) == 1
    assert ssns[0].matched_count == 2
    # Invalid SSN 000-12-3456 must not inflate count
    assert ssns[0].matched_count == 2


def test_json_phone_column() -> None:
    result = scan_path(CORPUS / "json" / "contacts.json")
    phones = [f for f in result.findings if f.entity == EntityType.PHONE]
    assert len(phones) == 1
    assert phones[0].matched_count == 2
    assert phones[0].location.column == "phone"


def test_jsonl_email() -> None:
    result = scan_path(CORPUS / "json" / "events.jsonl")
    emails = [f for f in result.findings if f.entity == EntityType.EMAIL]
    assert len(emails) == 1
    assert emails[0].matched_count == 2


def test_parquet_dob_requires_column_context() -> None:
    result = scan_path(CORPUS / "parquet" / "users.parquet")
    dobs = [f for f in result.findings if f.entity == EntityType.DOB]
    assert len(dobs) == 1
    assert dobs[0].location.column == "dob"
    assert dobs[0].matched_count == 3


def test_notebook_output_card_leak() -> None:
    result = scan_path(CORPUS / "notebook" / "leak_demo.ipynb")
    cards = [f for f in result.findings if f.entity == EntityType.CREDIT_CARD]
    assert len(cards) == 2
    assert all(f.location.cell_part == "output" for f in cards)


def test_no_raw_values_in_tabular_output() -> None:
    result = scan_path(CORPUS)
    blob = "\n".join(f.masked_sample + str(f.extras) for f in result.findings)
    for raw in (
        "customer.alpha@retailmail.test",
        "234-56-7890",
        "4532015112830366",
        "+1 212-735-0182",
    ):
        assert raw not in blob
