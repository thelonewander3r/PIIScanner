"""Missing [office] must not crash the walk; xlsx/pdf/docx are skipped."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from piilint.adapters import default_adapters, select_adapter
from piilint.adapters.docx_ import DocxAdapter
from piilint.adapters.pdf import PdfAdapter
from piilint.adapters.xlsx import XlsxAdapter
from piilint.engine import scan_path


def test_xlsx_pdf_adapters_registered() -> None:
    names = {a.name for a in default_adapters()}
    assert "xlsx" in names
    assert "pdf" in names
    assert "docx" in names


def test_missing_office_skips_without_crash(tmp_path: Path) -> None:
    xlsx = tmp_path / "a.xlsx"
    pdf = tmp_path / "b.pdf"
    docx = tmp_path / "c.docx"
    xlsx.write_bytes(b"PK\x03\x04not-real")
    pdf.write_bytes(b"%PDF-1.4 not real")
    docx.write_bytes(b"PK\x03\x04not-real")
    with (
        mock.patch("piilint.adapters.xlsx.office_xlsx_available", return_value=False),
        mock.patch("piilint.adapters.pdf.office_pdf_available", return_value=False),
        mock.patch("piilint.adapters.docx_.office_docx_available", return_value=False),
    ):
        assert select_adapter(xlsx) is not None
        assert isinstance(select_adapter(xlsx), XlsxAdapter)
        assert list(XlsxAdapter().iter_units(xlsx, rel_path="a.xlsx")) == []
        assert list(PdfAdapter().iter_units(pdf, rel_path="b.pdf")) == []
        assert isinstance(select_adapter(docx), DocxAdapter)
        assert list(DocxAdapter().iter_units(docx, rel_path="c.docx")) == []
        # whole-tree scan of other formats still works
        txt = tmp_path / "ok.txt"
        txt.write_text("hello customer.alpha@retailmail.test\n", encoding="utf-8")
        result = scan_path(tmp_path)
        assert result.files_scanned >= 1
