from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import get_settings

settings = get_settings()


@dataclass
class Chunk:
    text: str
    chunk_index: int
    char_count: int
    page_number: int | None = None


def chunk(text: str) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    splits = splitter.split_text(text)
    return [
        Chunk(
            text=split,
            chunk_index=i,
            char_count=len(split),
        )
        for i, split in enumerate(splits)
    ]
