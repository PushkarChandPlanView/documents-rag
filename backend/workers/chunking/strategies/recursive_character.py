import re
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import get_settings

settings = get_settings()

_PAGE_MARKER_RE = re.compile(r"<<<PAGE_(\d+)>>>")


@dataclass
class Chunk:
    text: str
    chunk_index: int
    char_count: int
    page_number: int | None = None


def _extract_page_number(text: str) -> tuple[str, int]:
    """Return (cleaned_text, page_number). Page number is the last marker found, defaulting to 1."""
    markers = _PAGE_MARKER_RE.findall(text)
    page = int(markers[-1]) if markers else 1
    clean = _PAGE_MARKER_RE.sub("", text).strip()
    return clean, page


def chunk(text: str) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    splits = splitter.split_text(text)
    chunks = []
    for i, split in enumerate(splits):
        clean_text, page_number = _extract_page_number(split)
        chunks.append(Chunk(
            text=clean_text,
            chunk_index=i,
            char_count=len(clean_text),
            page_number=page_number,
        ))
    return chunks
