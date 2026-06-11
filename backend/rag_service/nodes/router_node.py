"""
Router node — decides which ES search mode to use based on query keywords.
On re-entry (after a failed reflection), bumps to hybrid and prepends reflection context.
"""
import logging
import uuid as _uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chains.agentic_chain import AgenticState

logger = logging.getLogger(__name__)

# Keywords that suggest a specific search mode
_MODE_KEYWORDS: dict[str, list[str]] = {
    "semantic": [
        "meaning", "concept", "about", "similar", "related", "topic",
        "explain", "describe", "summarize", "what is", "how does",
    ],
    "keyword": [
        "exact", "find", "show me", "list", "specific", "named",
        "called", "titled", "id", "key", "number",
    ],
}


def _pick_mode(query: str, current_mode: str, iteration: int) -> str:
    """Pick search mode from query keywords. On retry, always use hybrid."""
    if iteration > 0:
        return "hybrid"   # broaden on retry
    q = query.lower()
    for mode, keywords in _MODE_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return mode
    return "hybrid"       # default


def router_node(state: "AgenticState") -> dict:
    query      = state["query"]
    reflection = state.get("reflection")
    iteration  = state.get("iteration", 0)
    current_mode = state.get("mode", "hybrid")

    # On re-entry: prepend the reflection so the search is more targeted
    refined_query = query
    if reflection and iteration > 0:
        refined_query = f"{query} {reflection}"
        logger.info("Router re-entry: refined_query=%r", refined_query)

    mode = _pick_mode(refined_query, current_mode, iteration)
    logger.info("Router: mode=%s iteration=%d query=%r", mode, iteration, refined_query[:80])

    return {
        "mode":          mode,
        "refined_query": refined_query,
        "sufficient":    None,
        "reflection":    None,
    }
