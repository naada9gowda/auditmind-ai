"""
api/documents.py — Document upload, processing, and retrieval endpoints.

POST /api/documents                  — multipart upload (file + doc_type)
POST /api/documents/{id}/process     — trigger text extraction
POST /api/documents/{id}/analyze     — run compliance mapping + finding extraction
GET  /api/documents                  — list documents for the org
GET  /api/documents/{id}             — single document with pages + metadata
GET  /api/documents/{id}/pages/{n}   — single page text
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import _get_current_user, require_role
from app.config import ALLOWED_DOC_TYPES, ALLOWED_EXTENSIONS, MAX_UPLOAD_MB, PDF_MAGIC, UPLOAD_DIR
from app.database import get_db
from app.documents.processor import process_document
from app.models.activity_log import ActivityLog
from app.models.control import Control
from app.models.document import Document, DocumentPage
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.user import User
from app.schemas.document import DocumentDetailOut, DocumentOut, DocumentPageOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

_MAX_BYTES = MAX_UPLOAD_MB * 1024 * 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_doc_or_404(doc_id: str, org_id: str, db: Session) -> Document:
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.organisation_id == org_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


def _validate_upload(file: UploadFile, contents: bytes) -> None:
    """Validate extension, MIME magic bytes, and size. Raises HTTPException on failure."""
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"File extension '{ext}' is not allowed. Permitted: {sorted(ALLOWED_EXTENSIONS)}.",
        )

    if len(contents) > _MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the maximum allowed size of {MAX_UPLOAD_MB} MB.",
        )

    if len(contents) == 0:
        raise HTTPException(
            status_code=422,
            detail="Uploaded file is empty.",
        )

    # Check PDF magic bytes
    if ext == ".pdf" and not contents[:4].startswith(PDF_MAGIC):
        raise HTTPException(
            status_code=422,
            detail="File does not appear to be a valid PDF (magic bytes mismatch).",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document (PDF or TXT)",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF or plain-text file"),
    doc_type: str = Form(..., description="policy | audit_report | evidence"),
    version: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> Document:
    # Validate doc_type
    if doc_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"doc_type '{doc_type}' is not valid. Allowed: {sorted(ALLOWED_DOC_TYPES)}.",
        )

    # Read file contents (capped read to avoid OOM on huge files)
    try:
        contents = await file.read(_MAX_BYTES + 1)  # read one byte over limit to detect oversize
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not read uploaded file: {exc}")

    _validate_upload(file, contents)

    # Build safe storage path — never use the client-supplied filename as a path component
    original_filename = file.filename or "upload"
    ext = Path(original_filename).suffix.lower()
    safe_name = f"{uuid.uuid4()}{ext}"

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / safe_name

    try:
        dest.write_bytes(contents)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not save file: {exc}")

    doc = Document(
        organisation_id=user.organisation_id,
        filename=original_filename,       # display name only
        doc_type=doc_type,
        version=version,
        storage_ref=safe_name,            # safe path component only
        processing_status="Uploaded",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    logger.info("Uploaded document id=%s name=%r type=%s size=%d bytes", doc.id, original_filename, doc_type, len(contents))
    return doc


@router.post(
    "/{doc_id}/process",
    response_model=DocumentDetailOut,
    summary="Extract text and metadata from an uploaded document",
)
def trigger_processing(
    doc_id: str,
    db: Session = Depends(get_db),
    user: User = require_role("admin", "compliance_officer", "auditor"),
) -> Document:
    _get_doc_or_404(doc_id, user.organisation_id, db)  # 404 guard
    doc = process_document(doc_id=doc_id, db=db, upload_dir=UPLOAD_DIR)
    if doc is None:
        raise HTTPException(status_code=500, detail="Processing returned no result.")
    return doc


@router.get(
    "",
    response_model=List[DocumentOut],
    summary="List documents for the current organisation",
)
def list_documents(
    doc_type: Optional[str] = None,
    processing_status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> list:
    q = db.query(Document).filter(Document.organisation_id == user.organisation_id)
    if doc_type:
        q = q.filter(Document.doc_type == doc_type)
    if processing_status:
        q = q.filter(Document.processing_status == processing_status)
    return q.order_by(Document.uploaded_at.desc()).all()


@router.get(
    "/{doc_id}",
    response_model=DocumentDetailOut,
    summary="Get a single document with all pages and extracted metadata",
)
def get_document(
    doc_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> Document:
    return _get_doc_or_404(doc_id, user.organisation_id, db)


@router.get(
    "/{doc_id}/pages/{page_num}",
    response_model=DocumentPageOut,
    summary="Get a single page from a processed document",
)
def get_page(
    doc_id: str,
    page_num: int,
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> DocumentPage:
    # Verify document belongs to org
    _get_doc_or_404(doc_id, user.organisation_id, db)
    page = db.query(DocumentPage).filter(
        DocumentPage.document_id == doc_id,
        DocumentPage.page_number == page_num,
    ).first()
    if not page:
        raise HTTPException(status_code=404, detail=f"Page {page_num} not found in this document.")
    return page


# ---------------------------------------------------------------------------
# Analyze endpoint — compliance mapping + finding extraction
# ---------------------------------------------------------------------------

@router.post(
    "/{doc_id}/analyze",
    summary="Run compliance mapping and draft finding extraction on a processed document",
    status_code=status.HTTP_200_OK,
)
def analyze_document(
    doc_id: str,
    db: Session = Depends(get_db),
    user: User = require_role("admin", "compliance_officer", "auditor"),
) -> dict:
    """
    Runs the full compliance analysis pipeline on a processed document:
      1. Loads all pages from document_pages.
      2. Maps pages to controls (explicit code → keyword → optional LLM).
      3. For evidence/policy documents: runs deterministic evidence verification
         and upserts Evidence rows (all with review_status='Draft').
      4. For audit_report documents: extracts draft findings and upserts
         Finding rows (all with ai_generated=True, review_status='Draft').

    Nothing is auto-approved. All results require a human reviewer.

    Returns a summary: how many evidence items and findings were created.

    Security: uploaded document text is treated as untrusted DATA.
    Any text found in the document (including injected instructions like
    "ignore previous instructions") is passed to downstream services as
    opaque data only — it cannot change control status, approve findings,
    or override authentication.
    """
    from app.compliance.mapping import map_document_to_controls
    from app.compliance.verifier import verify_evidence
    from app.compliance.extract_findings import extract_findings, KNOWN_DEPARTMENTS
    from app.llm.service import get_llm_provider

    doc = _get_doc_or_404(doc_id, user.organisation_id, db)

    if doc.processing_status != "Processed":
        raise HTTPException(
            status_code=422,
            detail=f"Document must be in 'Processed' state before analysis. "
                   f"Current state: '{doc.processing_status}'. "
                   f"Call POST /api/documents/{doc_id}/process first.",
        )

    # Load pages from DB
    pages_rows = (
        db.query(DocumentPage)
        .filter(DocumentPage.document_id == doc_id)
        .order_by(DocumentPage.page_number)
        .all()
    )
    if not pages_rows:
        raise HTTPException(status_code=422, detail="Document has no extracted pages. Re-process first.")

    pages: list[tuple[int, str]] = [(p.page_number, p.text or "") for p in pages_rows]

    # Load all controls for this org
    controls = db.query(Control).filter(Control.organisation_id == user.organisation_id).all()
    if not controls:
        raise HTTPException(status_code=422, detail="No controls found for this organisation.")

    # Get LLM provider (NoneProvider if LLM_PROVIDER=none)
    llm_provider = get_llm_provider()

    # -----------------------------------------------------------------------
    # Step 1 — Map document to controls
    # -----------------------------------------------------------------------
    matches = map_document_to_controls(
        pages=pages,
        controls=controls,
        llm_provider=llm_provider if not isinstance(llm_provider, type(None)) else None,
    )

    now = datetime.now(timezone.utc)
    created_evidence: list[str] = []
    created_findings: list[str] = []

    # -----------------------------------------------------------------------
    # Step 2 — Evidence verification (for evidence and policy docs)
    # -----------------------------------------------------------------------
    if doc.doc_type in ("evidence", "policy"):
        # Build page_text lookup
        page_text_map: dict[int, str] = {p.page_number: (p.text or "") for p in pages_rows}

        for match in matches:
            ctrl = db.query(Control).filter(Control.id == match.control_id).first()
            if not ctrl:
                continue

            page_text = page_text_map.get(match.page_number or 1, "")

            result = verify_evidence(
                control=ctrl,
                document=doc,
                page_number=match.page_number,
                excerpt=match.excerpt,
                page_text=page_text,
                confidence=match.confidence,
            )

            # Upsert: replace any existing Draft for this (control, document) pair
            existing = db.query(Evidence).filter(
                Evidence.organisation_id == user.organisation_id,
                Evidence.control_id == ctrl.id,
                Evidence.document_id == doc.id,
                Evidence.review_status == "Draft",
            ).first()
            if existing:
                existing.assessment = result.assessment
                existing.page_number = result.page_number
                existing.excerpt = result.excerpt
                existing.evidence_date = result.evidence_date
                ev_id = existing.id
            else:
                ev = Evidence(
                    organisation_id=user.organisation_id,
                    document_id=doc.id,
                    control_id=ctrl.id,
                    evidence_date=result.evidence_date,
                    review_status="Draft",
                    assessment=result.assessment,
                    excerpt=result.excerpt,
                    page_number=result.page_number,
                )
                db.add(ev)
                db.flush()
                ev_id = ev.id

            created_evidence.append(ev_id)

            # Log
            db.add(ActivityLog(
                organisation_id=user.organisation_id,
                actor=user.id,
                action="evidence_analyzed",
                entity_type="evidence",
                entity_id=ev_id,
                detail=(
                    f"Auto-mapped document {doc.id} to control {ctrl.control_code}. "
                    f"Assessment: {result.assessment}. "
                    f"Reasons: {'; '.join(result.reasons)}"
                ),
                created_at=now,
            ))

    # -----------------------------------------------------------------------
    # Step 3 — Draft finding extraction (for audit_report docs)
    # -----------------------------------------------------------------------
    if doc.doc_type == "audit_report":
        ctrl_code_to_id: dict[str, str] = {c.control_code: c.id for c in controls}

        draft_findings = extract_findings(
            pages=pages,
            llm_provider=llm_provider,
            control_code_to_id=ctrl_code_to_id,
        )

        for df in draft_findings:
            ctrl_id: str | None = ctrl_code_to_id.get(df.control_code or "") or None

            # Avoid exact duplicates within same analysis run
            # (same control_id, source_page, first 80 chars of description)
            desc_key = (df.description or "")[:80]
            already = db.query(Finding).filter(
                Finding.organisation_id == user.organisation_id,
                Finding.source_document_id == doc.id,
                Finding.source_page == df.source_page,
                Finding.ai_generated == True,  # noqa: E712
                Finding.review_status == "Draft",
            ).all()
            if any((f.description or "")[:80] == desc_key for f in already):
                continue

            # Determine department — first from df, else try to match department
            dept = df.department
            if dept and dept not in KNOWN_DEPARTMENTS:
                dept = None  # discard unrecognised department

            finding = Finding(
                organisation_id=user.organisation_id,
                control_id=ctrl_id,
                department=dept,
                severity=df.severity,
                description=df.description,
                status="Open",
                source_document_id=doc.id,
                source_page=df.source_page,
                source_excerpt=df.source_excerpt,
                ai_generated=True,
                review_status="Draft",
            )
            db.add(finding)
            db.flush()
            created_findings.append(finding.id)

            db.add(ActivityLog(
                organisation_id=user.organisation_id,
                actor=user.id,
                action="finding_extracted",
                entity_type="finding",
                entity_id=finding.id,
                detail=(
                    f"Draft finding extracted from document {doc.id} page {df.source_page}. "
                    f"Control: {df.control_code or 'unknown'}. Severity: {df.severity}."
                ),
                created_at=now,
            ))

    db.commit()

    return {
        "document_id": doc_id,
        "doc_type": doc.doc_type,
        "control_matches": len(matches),
        "evidence_items_created": len(created_evidence),
        "evidence_ids": created_evidence,
        "findings_created": len(created_findings),
        "finding_ids": created_findings,
        "note": (
            "All results are DRAFT and require human review before becoming "
            "approved records. No control status has been changed."
        ),
    }
