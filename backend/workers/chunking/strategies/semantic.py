"""
Semantic chunking: splits on sentence boundaries up to chunk_size chars.
Used for large documents > semantic_chunk_threshold_chars.
"""
import re
from dataclasses import dataclass

from config import get_settings

settings = get_settings()


@dataclass
class Chunk:
    text: str
    chunk_index: int
    char_count: int
    page_number: int | None = None


def _split_sentences(text: str) -> list[str]:
    # Simple sentence splitter — split on . ! ? followed by whitespace
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def chunk(text: str) -> list[Chunk]:
    sentences = _split_sentences(text)
    chunks: list[Chunk] = []
    current_parts: list[str] = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence)
        if current_len + sentence_len > settings.chunk_size and current_parts:
            chunk_text = " ".join(current_parts)
            chunks.append(Chunk(
                text=chunk_text,
                chunk_index=len(chunks),
                char_count=len(chunk_text),
            ))
            # Overlap: keep last sentence for context
            current_parts = current_parts[-1:] if settings.chunk_overlap > 0 else []
            current_len = len(current_parts[0]) if current_parts else 0

        current_parts.append(sentence)
        current_len += sentence_len + 1  # +1 for space

    # Flush remaining
    if current_parts:
        chunk_text = " ".join(current_parts)
        chunks.append(Chunk(
            text=chunk_text,
            chunk_index=len(chunks),
            char_count=len(chunk_text),
        ))

    return chunks
