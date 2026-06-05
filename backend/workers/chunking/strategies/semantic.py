"""
Semantic chunking: splits on sentence boundaries up to chunk_size tokens.
Used for large documents > semantic_chunk_threshold_chars.
"""
import re
from dataclasses import dataclass

import tiktoken

from config import get_settings

settings = get_settings()

_PAGE_MARKER_RE = re.compile(r"<<<PAGE_(\d+)>>>")
_enc = tiktoken.get_encoding("cl100k_base")


@dataclass
class Chunk:
    text: str
    chunk_index: int
    char_count: int
    token_count: int
    page_number: int | None = None


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def _count_tokens(text: str) -> int:
    return len(_enc.encode(text))


def _extract_page_number(text: str) -> tuple[str, int]:
    """Return (cleaned_text, page_number). Page number is the last marker found, defaulting to 1."""
    markers = _PAGE_MARKER_RE.findall(text)
    page = int(markers[-1]) if markers else 1
    clean = _PAGE_MARKER_RE.sub("", text).strip()
    return clean, page


def chunk(text: str) -> list[Chunk]:
    sentences = _split_sentences(text)
    chunks: list[Chunk] = []
    current_parts: list[str] = []
    current_len = 0  # token count of current window

    for sentence in sentences:
        sentence_len = _count_tokens(sentence)
        if current_len + sentence_len > settings.chunk_size and current_parts:
            chunk_text = " ".join(current_parts)
            clean_text, page_number = _extract_page_number(chunk_text)
            chunks.append(Chunk(
                text=clean_text,
                chunk_index=len(chunks),
                char_count=len(clean_text),
                token_count=_count_tokens(clean_text),
                page_number=page_number,
            ))
            current_parts = current_parts[-1:] if settings.chunk_overlap > 0 else []
            current_len = _count_tokens(current_parts[0]) if current_parts else 0

        current_parts.append(sentence)
        current_len += sentence_len + 1  # +1 approximates the joining space

    if current_parts:
        chunk_text = " ".join(current_parts)
        clean_text, page_number = _extract_page_number(chunk_text)
        chunks.append(Chunk(
            text=clean_text,
            chunk_index=len(chunks),
            char_count=len(clean_text),
            token_count=_count_tokens(clean_text),
            page_number=page_number,
        ))

    return chunks
