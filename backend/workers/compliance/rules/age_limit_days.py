from datetime import datetime, timezone
from typing import Optional

from .base import ChunkMeta, RuleChecker, RuleResult


class AgeLimitDaysChecker(RuleChecker):
    async def check(
        self,
        params: dict,
        chunks: list[ChunkMeta],
        summary: Optional[str],
        document_created_at: datetime,
    ) -> RuleResult:
        limit_days: int = params.get("days", 365)
        now = datetime.now(timezone.utc)

        if document_created_at.tzinfo is None:
            document_created_at = document_created_at.replace(tzinfo=timezone.utc)

        age_days = (now - document_created_at).days

        if age_days > limit_days:
            return RuleResult(
                passed=False,
                detail=(
                    f"Document is {age_days} days old, exceeding the {limit_days}-day limit. "
                    "Please review and update the document."
                ),
                locations=None,
            )

        return RuleResult(
            passed=True,
            detail=f"Document age ({age_days} days) is within the {limit_days}-day limit.",
            locations=None,
        )
