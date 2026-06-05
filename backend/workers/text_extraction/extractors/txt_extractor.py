from dataclasses import dataclass


@dataclass
class ExtractionResult:
    text: str
    page_count: int


def extract(file_bytes: bytes) -> ExtractionResult:
    text = file_bytes.decode("utf-8", errors="replace").strip()
    word_count = len(text.split())
    estimated_pages = max(1, word_count // 250)
    return ExtractionResult(text=text, page_count=estimated_pages)
