import json
import logging
import re
from datetime import datetime
from typing import Optional

from shared.providers import llm_factory

from .base import ChunkMeta, Location, RuleChecker, RuleResult

logger = logging.getLogger(__name__)

LLM_CHECK_PROMPT = """/no_think
You are a document compliance checker. Evaluate whether the following document summary complies with the given policy.

Policy: {policy}

Document summary:
{summary}

Respond ONLY with valid JSON on a single line:
{{"compliant": true, "reason": "brief explanation (max 100 chars)", "relevant_excerpt": "quote from summary most relevant to this policy (max 120 chars, or empty string if compliant)"}}"""


def _parse_llm_response(raw: str) -> tuple[bool, str, str]:
    """Returns (compliant, reason, relevant_excerpt). Defaults to compliant=True on parse failure."""
    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError:
        match = re.search(r"\{.*?\}", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return True, "Could not parse LLM response — treated as compliant.", ""
        else:
            return True, "Could not parse LLM response — treated as compliant.", ""

    compliant = bool(data.get("compliant", True))
    reason = str(data.get("reason", ""))[:200]
    excerpt = str(data.get("relevant_excerpt", ""))[:200]
    return compliant, reason, excerpt


class LLMCheckChecker(RuleChecker):
    async def check(
        self,
        params: dict,
        chunks: list[ChunkMeta],
        summary: Optional[str],
        document_created_at: datetime,
    ) -> RuleResult:
        policy: str = params.get("policy", "")
        if not summary:
            return RuleResult(
                passed=True,
                detail="No document summary available — LLM check skipped.",
                locations=None,
            )

        prompt = LLM_CHECK_PROMPT.format(
            policy=policy,
            summary=summary[:4000],
        )

        try:
            raw = await llm_factory.generate(prompt)
        except Exception as exc:
            logger.warning("LLM check failed (provider error): %s — treating as compliant", exc)
            return RuleResult(
                passed=True,
                detail=f"LLM check unavailable ({type(exc).__name__}) — treated as compliant.",
                locations=None,
            )

        compliant, reason, excerpt = _parse_llm_response(raw)

        locations = None
        if excerpt:
            locations = [Location(chunk_index=None, page_number=None, excerpt=excerpt)]

        if compliant:
            return RuleResult(passed=True, detail=reason or "Policy check passed.", locations=locations)

        return RuleResult(
            passed=False,
            detail=reason or "Policy check failed.",
            locations=locations,
        )
