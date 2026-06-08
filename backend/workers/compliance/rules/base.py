from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Location:
    chunk_index: Optional[int]
    page_number: Optional[int]
    excerpt: str

    def to_dict(self) -> dict:
        return {
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "excerpt": self.excerpt,
        }


@dataclass
class ChunkMeta:
    text: str
    chunk_index: int
    page_number: Optional[int]


@dataclass
class RuleResult:
    passed: bool
    detail: Optional[str] = None
    locations: Optional[list[Location]] = field(default=None)
    # LLM-assessed severity (info | warning | high | critical); falls back to rule config
    severity: Optional[str] = None
    # advisory → does not block; blocking → prevents publication until resolved
    enforcement: Optional[str] = None
    # True when the rule simply does not apply to this document (not a pass, not a fail)
    not_applicable: bool = False


class RuleChecker(ABC):
    @abstractmethod
    async def check(
        self,
        params: dict,
        chunks: list[ChunkMeta],
        summary: Optional[str],
        document_created_at: datetime,
    ) -> RuleResult: ...


def make_excerpt(text: str, keyword: str, context: int = 40) -> str:
    lower = text.lower()
    idx = lower.find(keyword.lower())
    if idx == -1:
        return text[:80].replace("\n", " ")
    start = max(0, idx - context)
    end = min(len(text), idx + len(keyword) + context)
    return text[start:end].replace("\n", " ")
