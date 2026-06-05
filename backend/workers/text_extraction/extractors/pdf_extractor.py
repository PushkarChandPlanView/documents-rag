"""
PDF text extraction using PyMuPDF with Tesseract OCR fallback for image-only pages.
"""
import logging
from dataclasses import dataclass

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

OCR_DPI = 200
OCR_MIN_CHARS = 10  # pages with fewer embedded chars trigger OCR


@dataclass
class ExtractionResult:
    text: str
    page_count: int


def _ocr_page(page: fitz.Page) -> str:
    """Render page to pixmap and run Tesseract via PyMuPDF's built-in OCR bridge."""
    try:
        mat = fitz.Matrix(OCR_DPI / 72, OCR_DPI / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
        # get_textpage_ocr requires Tesseract installed on PATH
        tp = page.get_textpage_ocr(flags=3, language="eng", dpi=OCR_DPI, full=False)
        return page.get_text(textpage=tp).strip()
    except Exception as exc:
        logger.warning("OCR failed for page %s: %s", page.number + 1, exc)
        return ""


def extract(file_bytes: bytes) -> ExtractionResult:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    parts = []
    ocr_pages = 0

    for page in doc:
        text = page.get_text("text").strip()
        if len(text) < OCR_MIN_CHARS:
            text = _ocr_page(page)
            if text:
                ocr_pages += 1

        if not text:
            continue

        page_num = page.number  # 0-based
        if page_num == 0:
            parts.append(text)
        else:
            parts.append(f"<<<PAGE_{page_num + 1}>>>\n{text}")

    page_count = len(doc)
    doc.close()

    if ocr_pages:
        logger.info("Used OCR on %d page(s)", ocr_pages)

    return ExtractionResult(text="\n\n".join(parts), page_count=page_count)
