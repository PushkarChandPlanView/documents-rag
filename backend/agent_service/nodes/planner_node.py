"""Planner node — asks LLM to produce a list of search steps from the query."""
import json
import logging

from services import llm_client

logger = logging.getLogger(__name__)


async def planner_node(state: dict) -> dict:
    query         = state["query"]
    system_prompt = state["system_prompt"]
    tools         = state.get("enabled_tools", ["search_all"])

    tool_desc = "\n".join(
        f"- {t}" for t in tools
    )

    prompt = f"""{system_prompt}

You are a research agent. Given the user's query, produce a step-by-step plan (3-6 steps) that describes what to search for to answer it fully.
Available tools: {tool_desc}

Each step should be a short action sentence (e.g. "Search Jira for tickets about autoscaler latency").
Return ONLY a JSON array of step strings, nothing else.

User query: {query}"""

    try:
        text = await llm_client.generate(prompt, max_tokens=512)
        # Extract JSON array
        start = text.find("[")
        end   = text.rfind("]") + 1
        steps = json.loads(text[start:end]) if start >= 0 else [f"Search for: {query}"]
    except Exception as exc:
        logger.error("planner_node error: %s", exc)
        steps = [f"Search all documents for: {query}"]

    logger.info("Plan generated: %s steps", len(steps))
    return {"plan": steps, "current_step": 0}
