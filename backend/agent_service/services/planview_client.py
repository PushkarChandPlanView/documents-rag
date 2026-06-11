"""
Planview ProjectPlace API client — OAuth1 auth.

Configure via env vars (or .env):
  PLANVIEW_BASE_URL             e.g. https://manohar.c.pp-dev.net
  PLANVIEW_CONSUMER_KEY         Client ID from developer settings
  PLANVIEW_CONSUMER_SECRET      Client secret from developer settings
  PLANVIEW_OAUTH_TOKEN          OAuth1 Token
  PLANVIEW_OAUTH_TOKEN_SECRET   OAuth1 Secret
  PLANVIEW_PROJECT_ID           numeric project id
  PLANVIEW_PLAN_ID              numeric plan id
"""
import asyncio
import logging
from functools import partial
from typing import Optional

from requests_oauthlib import OAuth1Session

from config import get_settings

logger = logging.getLogger(__name__)


def _session() -> OAuth1Session:
    """Build a signed OAuth1 session for every request."""
    s = get_settings()
    return OAuth1Session(
        client_key=s.planview_consumer_key,
        client_secret=s.planview_consumer_secret,
        resource_owner_key=s.planview_oauth_token,
        resource_owner_secret=s.planview_oauth_token_secret,
    )


def _url(path: str) -> str:
    return get_settings().planview_base_url.rstrip("/") + path


# ── Sync helpers (run in thread pool to keep async callers non-blocking) ───────

def _create_board_sync(name: str, description: str) -> dict:
    s = get_settings()
    url = _url(f"/api/v1/projects/{s.planview_project_id}/boards/create-new")
    res = _session().post(url, json={
        "name": name,
        "description": f"<p>{description}</p>" if description else "",
    })
    res.raise_for_status()
    board = res.json()
    logger.info("Created board id=%s name=%r", board.get("id"), name)
    return board


def _create_planlet_sync(name: str, start_date: str) -> dict:
    s = get_settings()
    url = _url(f"/api/v1/plan/{s.planview_project_id}/planlet/create")
    res = _session().post(url, json={
        "name": name,
        "kind": 0,
        "start_date": start_date,
    })
    res.raise_for_status()
    body = res.json()
    # Response: {"created": [{...planlet...}], "modified": [...]}
    planlet = body["created"][0] if body.get("created") else body
    logger.info("Created planlet id=%s name=%r", planlet.get("id"), name)
    return planlet


def _link_planlet_to_board_sync(planlet_id: int, board_id: int) -> bool:
    s = get_settings()
    url = _url(f"/api/v1/plan/{s.planview_project_id}/planlet/{planlet_id}/board_id")
    res = _session().put(url, json={"board_id": board_id})
    res.raise_for_status()
    logger.info("Linked planlet %s → board %s", planlet_id, board_id)
    return True


def _create_card_sync(
    title: str,
    board_id: int,
    planlet_id: Optional[int],
    description: str,
    column_id: int,
) -> dict:
    s = get_settings()
    url = _url(f"/api/v1/projects/{s.planview_project_id}/cards/create-new")
    body: dict = {
        "title": title,
        "board_id": board_id,
        "column_id": column_id,
    }
    if planlet_id is not None:
        body["planlet_id"] = planlet_id
    if description:
        body["description"] = description
    res = _session().post(url, json=body)
    res.raise_for_status()
    card = res.json()
    logger.info("Created card id=%s title=%r board=%s", card.get("id"), title, board_id)
    return card


# ── Async wrappers ─────────────────────────────────────────────────────────────

async def create_board(name: str, description: str = "") -> dict:
    return await asyncio.to_thread(_create_board_sync, name, description)


async def create_planlet(name: str, start_date: str) -> dict:
    return await asyncio.to_thread(_create_planlet_sync, name, start_date)


async def link_planlet_to_board(planlet_id: int, board_id: int) -> bool:
    return await asyncio.to_thread(_link_planlet_to_board_sync, planlet_id, board_id)


async def create_card(
    title: str,
    board_id: int,
    planlet_id: Optional[int] = None,
    description: str = "",
    column_id: int = 0,
) -> dict:
    fn = partial(_create_card_sync, title, board_id, planlet_id, description, column_id)
    return await asyncio.to_thread(fn)
