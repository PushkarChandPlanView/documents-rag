"""
Image text extraction using Tesseract OCR via pytesseract + Pillow.
Supports: JPEG, PNG, TIFF, BMP, WebP, GIF.
"""
import io
import logging

import pytesseract
from PIL import Image

from .pdf_extractor import ExtractionResult

logger = logging.getLogger(__name__)

# Modes that Tesseract handles natively (no conversion needed)
_SUPPORTED_MODES = {"RGB", "L"}


def extract(file_bytes: bytes) -> ExtractionResult:
    image = Image.open(io.BytesIO(file_bytes))

    # Normalize to RGB so Tesseract works with any input mode
    # (RGBA, P/palette, CMYK, etc.)
    if image.mode not in _SUPPORTED_MODES:
        image = image.convert("RGB")

    try:
        text = pytesseract.image_to_string(image, lang="eng").strip()
    except Exception as exc:
        logger.warning("Tesseract OCR failed: %s", exc)
        text = ""

    if text:
        logger.info("OCR extracted %d chars from image", len(text))
    else:
        logger.warning("OCR produced no text — image may have no readable content")

    # Wrap in a page marker so the chunking stage assigns page_number=1
    full_text = f"<<<PAGE_1>>>\n{text}" if text else ""
    return ExtractionResult(text=full_text, page_count=1)
