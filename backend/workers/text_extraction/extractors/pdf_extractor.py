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

    full_text = "\n\n".join(p for p in pages if p)
    return ExtractionResult(text=full_text, page_count=len(pages))
