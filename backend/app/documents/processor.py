"""
documents/processor.py — DB-integrated document processing orchestrator.

Calls the pure extractor functions and writes results to the database.
Never crashes the app — all errors are caught, logged, and stored
in document.processing_error with status = Failed.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.documents.extractor import (
    extract_dates,
    extract_pages,
    extract_reference,
    extract_title,
)
from app.models.document import Document, DocumentPage

logger = logging.getLogger(__name__)


def process_document(
    *,
    doc_id: str,
    db: Session,
    upload_dir: Path,
) -> Document:
    """
    Extract text and metadata from a stored document file and persist to DB.

    Status transitions:
      Uploaded  → Processing  (at start)
      Processing → Processed  (on success)
      Processing → Failed     (on any error)

    Returns the refreshed Document ORM object.
    Raises ValueError if the document is not found or not in a processable state.
    """
    doc = db.get(Document, doc_id)
    if doc is None:
        raise ValueError(f"Document '{doc_id}' not found.")
    if doc.processing_status not in ("Uploaded", "Failed"):
        raise ValueError(
            f"Document is in state '{doc.processing_status}'; "
            "only Uploaded or Failed documents can be reprocessed."
        )

    # Mark as processing
    doc.processing_status = "Processing"
    doc.processing_error = None
    db.commit()

    try:
        file_path = upload_dir / doc.storage_ref
        if not file_path.exists():
            raise FileNotFoundError(f"Stored file not found: {file_path}")

        # ── Extract pages ──────────────────────────────────────────────────
        pages = extract_pages(file_path)

        # Remove any existing page records (allow reprocessing)
        db.query(DocumentPage).filter_by(document_id=doc_id).delete()

        for page_number, text in pages:
            db.add(DocumentPage(document_id=doc_id, page_number=page_number, text=text))

        # ── Extract metadata from full text ────────────────────────────────
        full_text = "\n".join(text for _, text in pages)
        dates = extract_dates(full_text)
        ref = extract_reference(full_text)
        title = extract_title(full_text)

        doc.extracted_date = dates[0] if dates else None
        doc.extracted_reference = ref
        doc.extracted_title = title
        doc.processing_status = "Processed"

        db.commit()
        db.refresh(doc)

        logger.info(
            "Processed document id=%s pages=%d ref=%s title=%r",
            doc_id, len(pages), ref, title,
        )
        return doc

    except Exception as exc:
        logger.exception("Processing failed for document %s: %s", doc_id, exc)
        try:
            db.rollback()
            # Reload doc since session may be stale after rollback
            doc = db.get(Document, doc_id)
            if doc:
                doc.processing_status = "Failed"
                doc.processing_error = str(exc)[:1000]
                db.commit()
                db.refresh(doc)
        except Exception as inner:
            logger.error("Could not persist failure status for %s: %s", doc_id, inner)
        return doc
