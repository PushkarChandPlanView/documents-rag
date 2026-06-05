"""
PDF text extraction using PyMuPDF (fitz) with pdfplumber as fallback for tables.
"""
from dataclasses import dataclass

import fitz  # PyMuPDF


@dataclass
class ExtractionResult:
    text: str
    page_count: int


def extract(file_bytes: bytes) -> ExtractionResult:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in doc:
        text = page.get_text("text")
        pages.append(text.strip())
    doc.close()

    parts = []
    for i, page_text in enumerate(pages):
        if not page_text:
            continue
        if i == 0:
            parts.append(page_text)
        else:
            parts.append(f"<<<PAGE_{i + 1}>>>\n{page_text}")
    full_text = "\n\n".join(parts)
    return ExtractionResult(text=full_text, page_count=len(pages))
