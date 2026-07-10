"""
PDF Utilities
=============
Helpers for rendering PDF pages to base64 PNGs and extracting text.
Uses PyMuPDF (fitz).
"""

from __future__ import annotations
import base64
import io
import logging
import fitz  # PyMuPDF
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_page_count(pdf_bytes: bytes) -> int:
    """Return the total number of pages in the PDF."""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        if doc.is_encrypted: raise ValueError("Encrypted PDFs are unsupported.")
        if not doc.page_count: raise ValueError("PDF has no pages.")
        if doc.page_count > settings.max_pdf_pages: return doc.page_count
        for page in doc:
            if page.rect.width * page.rect.height * (120 / 72)**2 > settings.max_render_pixels:
                raise ValueError("PDF page dimensions exceed rendering limits.")
        return doc.page_count


def render_pages_to_base64(pdf_bytes: bytes, dpi: int = 120) -> dict[int, str]:
    """
    Render every page of a PDF to a base64-encoded PNG string.

    Parameters
    ----------
    pdf_bytes : bytes  — raw PDF content
    dpi       : int    — rendering resolution (higher = better quality, larger size)

    Returns
    -------
    dict mapping 0-indexed page number → base64 PNG string
    """
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return render_selected_pages_to_base64(
            pdf_bytes=pdf_bytes,
            pages=range(doc.page_count),
            dpi=dpi,
        )


def render_selected_pages_to_base64(
    pdf_bytes: bytes,
    pages: list[int] | range | set[int],
    dpi: int = 120,
) -> dict[int, str]:
    """Render only selected PDF pages to base64 PNG strings."""
    result: dict[int, str] = {}
    zoom = dpi / 72.0  # fitz uses 72 dpi as baseline
    matrix = fitz.Matrix(zoom, zoom)

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page_num in sorted(set(pages)):
            if page_num < 0 or page_num >= doc.page_count:
                logger.warning("Skipping out-of-range page render request: %d", page_num)
                continue
            page = doc[page_num]
            if page.rect.width * page.rect.height * zoom**2 > settings.max_render_pixels:
                raise ValueError("PDF page exceeds rendering limits.")
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            png_bytes = pixmap.tobytes("png")
            result[page_num] = base64.b64encode(png_bytes).decode("utf-8")
            logger.debug("Rendered page %d (%d bytes PNG)", page_num, len(png_bytes))

    return result


def extract_page_texts(pdf_bytes: bytes) -> dict[int, str]:
    """
    Extract plain text from every page of a PDF.

    Parameters
    ----------
    pdf_bytes : bytes

    Returns
    -------
    dict mapping 0-indexed page number → extracted text string
    """
    result: dict[int, str] = {}

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text("text")
            if len(text) > settings.max_page_text_chars: raise ValueError("PDF page text exceeds the configured limit.")
            result[page_num] = text.strip()

    return result
