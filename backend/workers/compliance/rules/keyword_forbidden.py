from datetime import datetime
from typing import Optional

from .base import ChunkMeta, Location, RuleChecker, RuleResult, make_excerpt


class KeywordForbiddenChecker(RuleChecker):
    async def check(
        self,
        params: dict,
        chunks: list[ChunkMeta],
        summary: Optional[str],
        document_created_at: datetime,
    ) -> RuleResult:
        keywords: list[str] = params.get("keywords", [])
        violations: list[Location] = []
        found_keywords: set[str] = set()

        for chunk in chunks:
            lower_text = chunk.text.lower()
            for keyword in keywords:
                if keyword.lower() in lower_text:
                    found_keywords.add(keyword)
                    violations.append(
                        Location(
                            chunk_index=chunk.chunk_index,
                            page_number=chunk.page_number,
                            excerpt=make_excerpt(chunk.text, keyword),
                        )
                    )

        if violations:
            kw_list = ", ".join(f"'{k}'" for k in sorted(found_keywords))
            return RuleResult(
                passed=False,
                detail=f"Forbidden keyword(s) {kw_list} found in {len(violations)} location(s).",
                locations=violations,
            )

        return RuleResult(passed=True, detail="No forbidden keywords found.", locations=[])
