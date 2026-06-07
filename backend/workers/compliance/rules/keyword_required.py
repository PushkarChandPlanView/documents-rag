from datetime import datetime
from typing import Optional

from .base import ChunkMeta, Location, RuleChecker, RuleResult, make_excerpt


class KeywordRequiredChecker(RuleChecker):
    async def check(
        self,
        params: dict,
        chunks: list[ChunkMeta],
        summary: Optional[str],
        document_created_at: datetime,
    ) -> RuleResult:
        keywords: list[str] = params.get("keywords", [])

        for keyword in keywords:
            for chunk in chunks:
                if keyword.lower() in chunk.text.lower():
                    return RuleResult(
                        passed=True,
                        detail=f"Required keyword '{keyword}' found.",
                        locations=[
                            Location(
                                chunk_index=chunk.chunk_index,
                                page_number=chunk.page_number,
                                excerpt=make_excerpt(chunk.text, keyword),
                            )
                        ],
                    )

        missing = ", ".join(f"'{k}'" for k in keywords)
        return RuleResult(
            passed=False,
            detail=f"None of the required keywords ({missing}) were found in the document.",
            locations=[],
        )
