"""
tests/test_documents.py — Tests for document extraction, upload validation,
and processing.

Covers:
  - extract_dates: ISO, DMY, MDY formats; duplicates; invalid values
  - extract_reference: finds AUD-/POL- pattern; returns None if absent
  - extract_title: first meaningful line; skips blank/page-number lines
  - extract_pages: PDF via sample files; TXT; unsupported extension
  - Upload validation: bad extension, wrong MIME, oversize, empty
  - Processing: full flow against a synthesised PDF; Failed path for empty PDF
"""

from __future__ import annotations

import os
import tempfile
from datetime import date
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("LLM_PROVIDER", "none")

from app.documents.extractor import (  # noqa: E402
    extract_dates,
    extract_pages,
    extract_reference,
    extract_title,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf(path: Path, pages_text: list[str]) -> None:
    """Create a minimal multi-page PDF using PyMuPDF."""
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz  # type: ignore[no-redef]

    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page(width=595, height=842)
        rect = fitz.Rect(50, 50, 545, 790)
        page.insert_textbox(rect, text, fontsize=10, fontname="helv")
    doc.save(str(path))
    doc.close()


def _make_txt(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# extract_dates
# ---------------------------------------------------------------------------

class TestExtractDates:
    def test_iso_format(self):
        dates = extract_dates("Report date: 2026-01-15.")
        assert date(2026, 1, 15) in dates

    def test_dmy_long_month(self):
        dates = extract_dates("Issued 15 January 2026 for review.")
        assert date(2026, 1, 15) in dates

    def test_dmy_short_month(self):
        dates = extract_dates("Dated 10 Apr 2026.")
        assert date(2026, 4, 10) in dates

    def test_mdy_long_month(self):
        dates = extract_dates("Effective date: April 10, 2026.")
        assert date(2026, 4, 10) in dates

    def test_mdy_short_month(self):
        dates = extract_dates("Jan 15 2026 is the target date.")
        assert date(2026, 1, 15) in dates

    def test_multiple_dates_sorted(self):
        text = "Start: 2026-01-01. End: 2026-12-31. Mid: 15 July 2026."
        dates = extract_dates(text)
        assert dates == sorted(dates)
        assert len(dates) == 3

    def test_duplicates_deduplicated(self):
        text = "2026-01-15 and also 15 January 2026 — same day."
        dates = extract_dates(text)
        assert dates.count(date(2026, 1, 15)) == 1

    def test_invalid_date_ignored(self):
        # Month 13 — should be silently skipped
        dates = extract_dates("2026-13-01 is not valid.")
        assert not any(d.year == 2026 and d.month == 13 for d in dates)

    def test_no_dates_returns_empty(self):
        assert extract_dates("No dates here, just text.") == []

    def test_february_in_text(self):
        dates = extract_dates("Evidence submitted 14 February 2026.")
        assert date(2026, 2, 14) in dates


# ---------------------------------------------------------------------------
# extract_reference
# ---------------------------------------------------------------------------

class TestExtractReference:
    def test_aud_reference(self):
        ref = extract_reference("See audit report AUD-2026-001 for details.")
        assert ref == "AUD-2026-001"

    def test_pol_reference(self):
        ref = extract_reference("Policy reference: POL-2025-002.")
        assert ref == "POL-2025-002"

    def test_evd_reference(self):
        ref = extract_reference("Document Reference: EVD-2026-031 submitted.")
        assert ref == "EVD-2026-031"

    def test_first_reference_returned(self):
        ref = extract_reference("AUD-2026-001 and AUD-2026-002 both referenced.")
        assert ref == "AUD-2026-001"

    def test_no_reference_returns_none(self):
        assert extract_reference("No reference pattern here.") is None

    def test_lowercase_not_matched(self):
        # Pattern requires uppercase letters
        assert extract_reference("aud-2026-001 lowercase") is None

    def test_four_digit_number(self):
        ref = extract_reference("Reference AUD-2026-1234 is valid.")
        assert ref == "AUD-2026-1234"


# ---------------------------------------------------------------------------
# extract_title
# ---------------------------------------------------------------------------

class TestExtractTitle:
    def test_returns_first_meaningful_line(self):
        text = "\n\nABC TECHNOLOGIES AUDIT REPORT\nSome body text.\n"
        assert extract_title(text) == "ABC TECHNOLOGIES AUDIT REPORT"

    def test_skips_blank_lines(self):
        text = "\n\n\nActual Title Here\n"
        assert extract_title(text) == "Actual Title Here"

    def test_skips_page_numbers(self):
        text = "1\n\nReal Title\n"
        assert extract_title(text) == "Real Title"

    def test_skips_very_short_lines(self):
        text = "AB\n\nProper Title Line\n"
        assert extract_title(text) == "Proper Title Line"

    def test_caps_at_256_chars(self):
        long_line = "A" * 300
        result = extract_title(long_line)
        assert len(result) == 256

    def test_returns_none_for_empty_text(self):
        assert extract_title("") is None
        assert extract_title("\n\n\n") is None


# ---------------------------------------------------------------------------
# extract_pages — TXT files
# ---------------------------------------------------------------------------

class TestExtractPagesTxt:
    def test_txt_returns_single_page(self, tmp_path):
        f = tmp_path / "test.txt"
        _make_txt(f, "Hello world\nLine 2")
        pages = extract_pages(f)
        assert len(pages) == 1
        assert pages[0][0] == 1  # page number 1
        assert "Hello world" in pages[0][1]

    def test_txt_preserves_content(self, tmp_path):
        content = "Reference: AUD-2026-001\nDate: 15 January 2026"
        f = tmp_path / "test.txt"
        _make_txt(f, content)
        pages = extract_pages(f)
        assert content in pages[0][1]

    def test_unsupported_extension_raises(self, tmp_path):
        f = tmp_path / "file.exe"
        f.write_bytes(b"MZ\x00\x00")
        with pytest.raises(ValueError, match="Unsupported"):
            extract_pages(f)


# ---------------------------------------------------------------------------
# extract_pages — PDF files (synthesised)
# ---------------------------------------------------------------------------

class TestExtractPagesPdf:
    def test_single_page_pdf(self, tmp_path):
        f = tmp_path / "single.pdf"
        _make_pdf(f, ["Page one content. Reference AUD-2026-001."])
        pages = extract_pages(f)
        assert len(pages) == 1
        assert pages[0][0] == 1

    def test_multi_page_pdf_page_numbers(self, tmp_path):
        f = tmp_path / "multi.pdf"
        _make_pdf(f, ["Page 1 text", "Page 2 text", "Page 3 text"])
        pages = extract_pages(f)
        assert len(pages) == 3
        numbers = [p[0] for p in pages]
        assert numbers == [1, 2, 3]

    def test_specific_page_content(self, tmp_path):
        f = tmp_path / "audit.pdf"
        _make_pdf(f, [
            "Cover page. Reference AUD-2026-001. Date: 15 January 2026.",
            "Scope and methodology page.",
            "Executive summary page.",
            "Finding F1: SEC-014 Employee Access Reviews. Severity: High.",
        ])
        pages = extract_pages(f)
        assert len(pages) == 4
        # Page 4 must contain the access-review finding
        page4_text = pages[3][1]
        assert "SEC-014" in page4_text
        assert "High" in page4_text

    def test_pdf_reference_extractable(self, tmp_path):
        f = tmp_path / "ref.pdf"
        _make_pdf(f, ["Reference: AUD-2026-999 is on this page."])
        pages = extract_pages(f)
        full_text = "\n".join(t for _, t in pages)
        ref = extract_reference(full_text)
        assert ref == "AUD-2026-999"

    def test_pdf_date_extractable(self, tmp_path):
        f = tmp_path / "dated.pdf"
        _make_pdf(f, ["Report Date: 15 January 2026. Control SEC-014."])
        pages = extract_pages(f)
        full_text = "\n".join(t for _, t in pages)
        dates = extract_dates(full_text)
        assert date(2026, 1, 15) in dates


# ---------------------------------------------------------------------------
# Upload validation (via _validate_upload helper function)
# ---------------------------------------------------------------------------

class TestUploadValidation:
    """Test the validation logic directly (without spinning up the HTTP server)."""

    def _make_upload_mock(self, filename: str):
        """Return a minimal object that mimics UploadFile's .filename attribute."""
        class _Mock:
            pass
        m = _Mock()
        m.filename = filename
        return m

    def test_pdf_valid_accepted(self):
        from app.api.documents import _validate_upload
        mock = self._make_upload_mock("report.pdf")
        content = b"%PDF-1.4 valid content"
        # Should not raise
        _validate_upload(mock, content)

    def test_txt_valid_accepted(self):
        from app.api.documents import _validate_upload
        from fastapi import HTTPException
        mock = self._make_upload_mock("notes.txt")
        content = b"Plain text content"
        _validate_upload(mock, content)  # should not raise

    def test_exe_rejected(self):
        from app.api.documents import _validate_upload
        from fastapi import HTTPException
        mock = self._make_upload_mock("malware.exe")
        content = b"MZ\x00\x00"
        with pytest.raises(HTTPException) as exc_info:
            _validate_upload(mock, content)
        assert exc_info.value.status_code == 422

    def test_docx_rejected(self):
        from app.api.documents import _validate_upload
        from fastapi import HTTPException
        mock = self._make_upload_mock("report.docx")
        content = b"PK\x03\x04fake_docx_content"
        with pytest.raises(HTTPException) as exc_info:
            _validate_upload(mock, content)
        assert exc_info.value.status_code == 422

    def test_oversize_rejected(self):
        from app.api.documents import _validate_upload, _MAX_BYTES
        from fastapi import HTTPException
        mock = self._make_upload_mock("huge.pdf")
        # Content just over the limit
        content = b"%PDF" + b"x" * (_MAX_BYTES)
        with pytest.raises(HTTPException) as exc_info:
            _validate_upload(mock, content)
        assert exc_info.value.status_code == 413

    def test_empty_file_rejected(self):
        from app.api.documents import _validate_upload
        from fastapi import HTTPException
        mock = self._make_upload_mock("empty.pdf")
        with pytest.raises(HTTPException) as exc_info:
            _validate_upload(mock, b"")
        assert exc_info.value.status_code == 422

    def test_pdf_bad_magic_rejected(self):
        from app.api.documents import _validate_upload
        from fastapi import HTTPException
        mock = self._make_upload_mock("fake.pdf")
        content = b"not a pdf at all"
        with pytest.raises(HTTPException) as exc_info:
            _validate_upload(mock, content)
        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Full processing pipeline — synthesised PDF
# ---------------------------------------------------------------------------

class TestProcessDocument:
    def test_process_success(self, db, two_orgs, tmp_path):
        """Processing a valid PDF sets status=Processed and writes page rows."""
        from app.models.document import Document, DocumentPage
        from app.documents.processor import process_document

        org_a, user_a, _, _ = two_orgs

        # Create a 4-page PDF
        pdf_path = tmp_path / "aud.pdf"
        _make_pdf(pdf_path, [
            "Cover. Reference AUD-2026-001. Date: 15 January 2026.",
            "Scope page. Control SEC-014 is in scope.",
            "Summary page.",
            "Finding F1. Control SEC-014. Severity: High. IT Operations.",
        ])

        # Create a Document record pointing at our test PDF
        doc = Document(
            organisation_id=org_a.id,
            filename="aud.pdf",
            doc_type="audit_report",
            storage_ref=pdf_path.name,
            processing_status="Uploaded",
        )
        db.add(doc)
        db.commit()

        result = process_document(doc_id=doc.id, db=db, upload_dir=tmp_path)

        assert result.processing_status == "Processed"
        assert result.extracted_reference == "AUD-2026-001"
        assert result.extracted_date == date(2026, 1, 15)

        pages = db.query(DocumentPage).filter_by(document_id=doc.id).all()
        assert len(pages) == 4

        # Page 4 must contain SEC-014 finding text
        page4 = next(p for p in pages if p.page_number == 4)
        assert "SEC-014" in page4.text
        assert "High" in page4.text

    def test_process_txt_file(self, db, two_orgs, tmp_path):
        """Processing a TXT file creates a single page."""
        from app.models.document import Document, DocumentPage
        from app.documents.processor import process_document

        org_a, user_a, _, _ = two_orgs

        txt_path = tmp_path / "policy.txt"
        _make_txt(txt_path, "Reference POL-2025-002\nDate: 01 March 2025\nAccess Control Policy")

        doc = Document(
            organisation_id=org_a.id,
            filename="policy.txt",
            doc_type="policy",
            storage_ref=txt_path.name,
            processing_status="Uploaded",
        )
        db.add(doc)
        db.commit()

        result = process_document(doc_id=doc.id, db=db, upload_dir=tmp_path)

        assert result.processing_status == "Processed"
        assert result.extracted_reference == "POL-2025-002"
        pages = db.query(DocumentPage).filter_by(document_id=doc.id).all()
        assert len(pages) == 1

    def test_process_missing_file_sets_failed(self, db, two_orgs, tmp_path):
        """Processing a document whose file is missing sets status=Failed."""
        from app.models.document import Document
        from app.documents.processor import process_document

        org_a, user_a, _, _ = two_orgs

        doc = Document(
            organisation_id=org_a.id,
            filename="ghost.pdf",
            doc_type="audit_report",
            storage_ref="nonexistent_file.pdf",
            processing_status="Uploaded",
        )
        db.add(doc)
        db.commit()

        result = process_document(doc_id=doc.id, db=db, upload_dir=tmp_path)

        assert result.processing_status == "Failed"
        assert result.processing_error is not None

    def test_reprocess_clears_old_pages(self, db, two_orgs, tmp_path):
        """Re-processing a Failed document replaces old page records."""
        from app.models.document import Document, DocumentPage
        from app.documents.processor import process_document

        org_a, user_a, _, _ = two_orgs

        pdf_path = tmp_path / "reprocess.pdf"
        _make_pdf(pdf_path, ["First run. Reference AUD-2026-001. 15 January 2026."])

        doc = Document(
            organisation_id=org_a.id,
            filename="reprocess.pdf",
            doc_type="audit_report",
            storage_ref=pdf_path.name,
            processing_status="Uploaded",
        )
        db.add(doc)
        db.commit()

        process_document(doc_id=doc.id, db=db, upload_dir=tmp_path)
        # Force back to Failed so we can reprocess
        doc.processing_status = "Failed"
        db.commit()

        process_document(doc_id=doc.id, db=db, upload_dir=tmp_path)

        pages = db.query(DocumentPage).filter_by(document_id=doc.id).all()
        assert len(pages) == 1   # not doubled


# ---------------------------------------------------------------------------
# Sample PDFs integration test (runs only if make_sample_pdfs was executed)
# ---------------------------------------------------------------------------

class TestSamplePdfsIntegration:
    """
    Optional integration tests that run against the generated sample PDFs.
    Skipped automatically if the files don't exist.
    """

    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # auditmind-ai/
    _AUDITS = _REPO_ROOT / "data" / "sample_audits"

    @pytest.mark.skipif(
        not (_REPO_ROOT / "data" / "sample_audits" / "AUD-2026-001_January_Audit.pdf").exists(),
        reason="Sample PDFs not generated yet — run python backend/scripts/make_sample_pdfs.py first",
    )
    def test_aud_2026_001_has_five_pages(self):
        pdf = self._AUDITS / "AUD-2026-001_January_Audit.pdf"
        pages = extract_pages(pdf)
        assert len(pages) == 5

    @pytest.mark.skipif(
        not (_REPO_ROOT / "data" / "sample_audits" / "AUD-2026-001_January_Audit.pdf").exists(),
        reason="Sample PDFs not generated yet",
    )
    def test_aud_2026_001_page4_contains_sec014(self):
        pdf = self._AUDITS / "AUD-2026-001_January_Audit.pdf"
        pages = extract_pages(pdf)
        page4 = next(t for n, t in pages if n == 4)
        assert "SEC-014" in page4

    @pytest.mark.skipif(
        not (_REPO_ROOT / "data" / "sample_audits" / "AUD-2026-001_January_Audit.pdf").exists(),
        reason="Sample PDFs not generated yet",
    )
    def test_aud_2026_001_reference_extracted(self):
        pdf = self._AUDITS / "AUD-2026-001_January_Audit.pdf"
        pages = extract_pages(pdf)
        full_text = "\n".join(t for _, t in pages)
        assert extract_reference(full_text) == "AUD-2026-001"

    @pytest.mark.skipif(
        not (_REPO_ROOT / "data" / "sample_audits" / "AUD-2026-001_January_Audit.pdf").exists(),
        reason="Sample PDFs not generated yet",
    )
    def test_aud_2026_001_date_extracted(self):
        pdf = self._AUDITS / "AUD-2026-001_January_Audit.pdf"
        pages = extract_pages(pdf)
        full_text = "\n".join(t for _, t in pages)
        dates = extract_dates(full_text)
        assert date(2026, 1, 15) in dates
