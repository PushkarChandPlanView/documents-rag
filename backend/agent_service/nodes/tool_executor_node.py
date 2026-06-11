"""Tool executor node — runs one step's search and appends results."""
import logging
from typing import Optional

from services import es_client

logger = logging.getLogger(__name__)

# Keywords → source_types filter
_SOURCE_KEYWORDS = {
    "jira":       ["jira"],
    "confluence": ["confluence"],
    "slack":      ["slack"],
    "github":     ["github"],
    "hubspot":    ["hubspot"],
    "url":        ["url"],
    "upload":     ["upload"],
}


def _detect_sources(step_text: str) -> Optional[list[str]]:
    lower = step_text.lower()
    for keyword, types in _SOURCE_KEYWORDS.items():
        if keyword in lower:
            return types
    return None  # search all


async def tool_executor_node(state: dict) -> dict:
    plan         = state.get("plan", [])
    current_step = state.get("current_step", 0)
    user_id      = state.get("user_id", "")
    query        = state.get("query", "")

    if current_step >= len(plan):
        return {}

    step_text    = plan[current_step]
    source_types = _detect_sources(step_text)

    # Use step text as search query if it's specific enough, else fall back to original query
    search_query = step_text if len(step_text) > 20 else query

    logger.info("Step %d/%d: %r  sources=%s", current_step + 1, len(plan), step_text, source_types)

    results = await es_client.search(
        query=search_query,
        user_id=user_id,
        source_types=source_types,
        top_k=8,
    )

    step_result = {
        "step": current_step,
        "step_text": step_text,
        "source_types": source_types,
        "chunks": results,
    }

    return {
        "step_results": [step_result],
        "current_step": current_step + 1,
    }
