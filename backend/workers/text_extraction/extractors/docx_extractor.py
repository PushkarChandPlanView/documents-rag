import io
from dataclasses import dataclass

from docx import Document


@dataclass
class ExtractionResult:
    text: str
    page_count: int


def extract(file_bytes: bytes) -> ExtractionResult:
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
    full_text = "\n\n".join(paragraphs)
    # DOCX doesn't have explicit pages; estimate from word count
    word_count = len(full_text.split())
    estimated_pages = max(1, word_count // 250)
    return ExtractionResult(text=full_text, page_count=estimated_pages)
