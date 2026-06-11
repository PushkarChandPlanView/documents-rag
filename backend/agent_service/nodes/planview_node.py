"""
Planview node — converts synthesized agent answer into a Planview ProjectPlace
board with activities (planlets) and cards.

Flow:
  1. Ask LLM to convert the synthesized answer into structured JSON
  2. Create board
  3. For each activity: create planlet → link to board → create cards
  4. Return summary as planview_result
"""
import json
import logging
import re
from datetime import date

from services import llm_client, planview_client

logger = logging.getLogger(__name__)

_STRUCTURE_PROMPT = """\
You are a project planning assistant. Given the analysis below, produce a JSON \
project board structure with activities and task cards.

OUTPUT FORMAT — valid JSON only, no markdown fences:
{{
  "board_name": "<short name for the board>",
  "board_description": "<one sentence summary>",
  "activities": [
    {{
      "name": "<activity name>",
      "cards": [
        {{
          "title": "<card title>",
          "description": "<acceptance criteria or description>",
          "column_id": 0
        }}
      ]
    }}
  ]
}}

Rules:
- Create 5-12 activities covering the full project lifecycle.
- Each activity should have 3-8 cards.
- column_id is always 0 (Planned).
- Keep card titles concise (under 80 chars).
- Keep descriptions factual and tied to the analysis.
- Return ONLY the JSON object, nothing else.

ANALYSIS:
{answer}
"""


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response, stripping any markdown fences."""
    text = text.strip()
    # strip ```json ... ``` fences if present
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        text = match.group(1)
    return json.loads(text)


async def planview_node(state: dict) -> dict:
    answer = state.get("answer", "")
    query  = state.get("query", "project")

    if not answer:
        logger.warning("planview_node: no answer to convert")
        return {"planview_result": {"error": "No analysis to convert"}}

    today = date.today().isoformat()

    # ── Step 1: Ask LLM to structure the answer as board JSON ─────────────────
    logger.info("planview_node: asking LLM to generate board structure")
    try:
        structure_text = await llm_client.generate(
            _STRUCTURE_PROMPT.format(answer=answer),
            max_tokens=4096,
        )
        structure = _extract_json(structure_text)
    except Exception as exc:
        logger.error("planview_node: LLM structuring failed: %s", exc)
        return {"planview_result": {"error": f"Structuring failed: {exc}"}}

    board_name = structure.get("board_name", f"Project — {query[:50]}")
    board_desc = structure.get("board_description", "")
    activities = structure.get("activities", [])

    result = {
        "board_name": board_name,
        "board_id": None,
        "activities": [],
        "total_cards": 0,
        "errors": [],
    }

    # ── Step 2: Create board ──────────────────────────────────────────────────
    try:
        board = await planview_client.create_board(board_name, board_desc)
        board_id: int = board["id"]
        result["board_id"] = board_id
        logger.info("planview_node: board created id=%s", board_id)
    except Exception as exc:
        logger.error("planview_node: board creation failed: %s", exc)
        result["errors"].append(f"Board creation failed: {exc}")
        return {"planview_result": result}

    # ── Step 3: Create activities + link + create cards ───────────────────────
    for activity in activities:
        act_name  = activity.get("name", "Activity")
        cards_def = activity.get("cards", [])

        act_result = {
            "name": act_name,
            "planlet_id": None,
            "cards": [],
            "errors": [],
        }

        # Create planlet (activity)
        try:
            planlet = await planview_client.create_planlet(act_name, today)
            planlet_id: int = planlet["id"]
            act_result["planlet_id"] = planlet_id
        except Exception as exc:
            err = f"Planlet '{act_name}' creation failed: {exc}"
            logger.warning(err)
            act_result["errors"].append(err)
            result["activities"].append(act_result)
            continue

        # Link planlet → board
        try:
            await planview_client.link_planlet_to_board(planlet_id, board_id)
        except Exception as exc:
            logger.warning("planview_node: link failed for planlet %s: %s", planlet_id, exc)
            act_result["errors"].append(f"Link failed: {exc}")

        # Create cards
        for card_def in cards_def:
            try:
                card = await planview_client.create_card(
                    title=card_def.get("title", "Task"),
                    board_id=board_id,
                    planlet_id=planlet_id,
                    description=card_def.get("description", ""),
                    column_id=card_def.get("column_id", 0),
                )
                act_result["cards"].append({
                    "id": card.get("id"),
                    "title": card_def.get("title"),
                })
                result["total_cards"] += 1
            except Exception as exc:
                err = f"Card '{card_def.get('title')}' failed: {exc}"
                logger.warning(err)
                act_result["errors"].append(err)

        result["activities"].append(act_result)

    logger.info(
        "planview_node: done — board=%s activities=%d cards=%d errors=%d",
        board_id, len(result["activities"]), result["total_cards"], len(result["errors"]),
    )
    return {"planview_result": result}
