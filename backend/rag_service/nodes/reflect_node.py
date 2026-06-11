"""
Reflect node — Claude Haiku judges whether retrieved chunks are sufficient to
answer the query. Returns sufficient=True/False and optional reflection text.
"""
import logging
from typing import TYPE_CHECKING

from services import llm_client

if TYPE_CHECKING:
    from chains.agentic_chain import AgenticState

logger = logging.getLogger(__name__)

# Use Haiku for fast, cheap judgment
_HAIKU_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
_FALLBACK_HAIKU = "us.anthropic.claude-3-5-haiku-20241022-v1:0"

_REFLECT_PROMPT = """\
You are evaluating whether retrieved document chunks are sufficient to answer a user query.

Query: {query}

Retrieved chunks ({n} total):
{chunks_preview}

Respond with EXACTLY one of:
  SUFFICIENT
  NEEDS_MORE: <one sentence describing what specific information is missing>

Do not add any other text."""


def _fmt_chunks(chunks: list[dict], max_chars: int = 3000) -> str:
    lines = []
    total = 0
    for i, c in enumerate(chunks):
        text = c.get("text", "")[:300]
        line = f"[{i+1}] ({c.get('document_name','?')}) {text}"
        total += len(line)
        if total > max_chars:
            break
        lines.append(line)
    return "\n".join(lines) or "(no chunks retrieved)"


async def reflect_node(state: "AgenticState") -> dict:
    query     = state.get("refined_query") or state["query"]
    chunks    = state.get("retrieved_chunks", [])
    iteration = state.get("iteration", 0)
    max_iter  = state.get("max_iter", 3)

    # Force sufficient if we've hit the ceiling
    if iteration >= max_iter:
        logger.info("Reflect: max_iter=%d reached — forcing sufficient", max_iter)
        return {"sufficient": True, "reflection": None, "iteration": iteration + 1}

    if not chunks:
        logger.info("Reflect: no chunks retrieved — needs_more")
        return {
            "sufficient":    False,
            "reflection":    "no documents were retrieved — try a different query",
            "refined_query": query,
            "iteration":     iteration + 1,
        }

    prompt = _REFLECT_PROMPT.format(
        query=query,
        n=len(chunks),
        chunks_preview=_fmt_chunks(chunks),
    )

    try:
        verdict = await llm_client.generate_with_model(
            prompt, model_id=_HAIKU_MODEL, max_tokens=128
        )
    except Exception:
        # Fallback to older Haiku model name
        try:
            verdict = await llm_client.generate_with_model(
                prompt, model_id=_FALLBACK_HAIKU, max_tokens=128
            )
        except Exception as exc:
            logger.warning("Reflect: Haiku call failed (%s) — assuming sufficient", exc)
            return {"sufficient": True, "reflection": None, "iteration": iteration + 1}

    logger.info("Reflect verdict: %r", verdict[:120])

    if verdict.strip().startswith("SUFFICIENT"):
        return {"sufficient": True, "reflection": None, "iteration": iteration + 1}

    # NEEDS_MORE: <reason>
    missing = verdict.split(":", 1)[-1].strip() if ":" in verdict else verdict
    return {
        "sufficient":    False,
        "reflection":    missing,
        "refined_query": f"{query} {missing}",
        "iteration":     iteration + 1,
    }
