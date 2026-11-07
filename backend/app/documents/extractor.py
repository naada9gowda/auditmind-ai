"""
documents/extractor.py — Pure, side-effect-free extraction functions.

These functions operate only on file paths and strings — no DB calls,
no network, no imports from app.* (except config). This keeps them
easily unit-testable.

Security note: uploaded document text is treated as untrusted DATA.
No extracted text is ever used as an instruction to a model or executed.
"""

from __future__ import annotations

import logging
import re
from calendar import month_abbr, month_name
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Month lookup (lowercase) used by date parsers
# ---------------------------------------------------------------------------
_MONTH_MAP: dict[str, int] = {}
for _i, (_full, _abbr) in enumerate(
    zip(list(month_name)[1:], list(month_abbr)[1:]), start=1
):
    _MONTH_MAP[_full.lower()] = _i
    _MONTH_MAP[_abbr.lower()] = _i

# ---------------------------------------------------------------------------
# Compiled date regexes
# ---------------------------------------------------------------------------
# ISO:  2026-01-15
_RE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

# Day-Month-Year:  15 January 2026  /  15 Jan 2026
_MONTHS_PATTERN = "|".join(
    sorted(_MONTH_MAP.keys(), key=len, reverse=True)  # longest first avoids partial matches
)
_RE_DMY = re.compile(
    rf"\b(\d{{1,2}})\s+({_MONTHS_PATTERN})\s+(\d{{4}})\b",
    re.IGNORECASE,
)

# Month-Day-Year:  January 15, 2026  /  Jan 15 2026
_RE_MDY = re.compile(
    rf"\b({_MONTHS_PATTERN})\s+(\d{{1,2}}),?\s+(\d{{4}})\b",
    re.IGNORECASE,
)

# Document reference pattern:  AUD-2026-001  /  POL-2024-012
_RE_REFERENCE = re.compile(r"\b([A-Z]{2,5}-\d{4}-\d{3,4})\b")


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def extract_pages(path: Path) -> list[tuple[int, str]]:
    """
    Extract (1-indexed page_number, text) pairs from a PDF or TXT file.

    - PDF: uses PyMuPDF; each PDF page → one tuple.
    - TXT: entire file → single tuple (page 1).
    - Scanned / image-only PDFs (all pages empty) raise RuntimeError.

    Raises:
        RuntimeError: if extraction fails or document appears to be image-only.
        ValueError:   if the file extension is unsupported.
    """
    suffix = path.suffix.lower()

    if suffix == ".txt":
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise RuntimeError(f"Cannot read text file: {exc}") from exc
        return [(1, text)]

    if suffix == ".pdf":
        try:
            import pymupdf  # noqa: PLC0415
        except ImportError:
            try:
                import fitz as pymupdf  # type: ignore[no-redef]
            except ImportError as exc:
                raise RuntimeError("PyMuPDF is not installed.") from exc

        try:
            doc = pymupdf.open(str(path))
        except Exception as exc:
            raise RuntimeError(f"Cannot open PDF: {exc}") from exc

        pages: list[tuple[int, str]] = []
        try:
            for i, page in enumerate(doc, start=1):
                try:
                    text = page.get_text()
                except Exception as exc:  # defensive — some pages may be corrupt
                    logger.warning("Page %d extraction failed: %s", i, exc)
                    text = ""
                pages.append((i, text or ""))
        finally:
            doc.close()

        if not pages:
            raise RuntimeError("PDF contains no pages.")

        all_empty = all(not t.strip() for _, t in pages)
        if all_empty:
            raise RuntimeError(
                "All pages appear empty — this may be a scanned / image-only PDF. "
                "Manual text entry or OCR is required."
            )

        return pages

    raise ValueError(f"Unsupported file extension: '{suffix}'. Only .pdf and .txt are supported.")


def extract_dates(text: str) -> list[date]:
    """
    Return all dates found in *text*, deduplicated and sorted ascending.
    Supports:
      - ISO:          2026-01-15
      - Day-Mon-Year: 15 January 2026 / 15 Jan 2026
      - Mon-Day-Year: January 15, 2026 / Jan 15 2026
    """
    found: set[date] = set()

    # ISO dates
    for m in _RE_ISO.finditer(text):
        try:
            found.add(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            pass  # e.g. month 13 — ignore

    # Day-Month-Year
    for m in _RE_DMY.finditer(text):
        month_num = _MONTH_MAP.get(m.group(2).lower())
        if month_num:
            try:
                found.add(date(int(m.group(3)), month_num, int(m.group(1))))
            except ValueError:
                pass

    # Month-Day-Year
    for m in _RE_MDY.finditer(text):
        month_num = _MONTH_MAP.get(m.group(1).lower())
        if month_num:
            try:
                found.add(date(int(m.group(3)), month_num, int(m.group(2))))
            except ValueError:
                pass

    return sorted(found)


def extract_reference(text: str) -> Optional[str]:
    """
    Return the first document reference matching the pattern
    LETTERS-YEAR-NUMBER (e.g. AUD-2026-001, POL-2024-012).
    Returns None if none found.
    """
    m = _RE_REFERENCE.search(text)
    return m.group(1) if m else None


def extract_title(text: str) -> Optional[str]:
    """
    Return the first meaningful non-empty line of text as the document title.
    Strips common header noise (page numbers, whitespace-only lines).
    """
    for line in text.splitlines():
        line = line.strip()
        # Skip blank lines, single characters, and lines that look like page numbers
        if len(line) < 4:
            continue
        if re.fullmatch(r"\d+", line):  # bare page number
            continue
        return line[:256]  # cap at 256 chars
    return None
