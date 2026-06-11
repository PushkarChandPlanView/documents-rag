"""
Quick smoke test for planview_client.
Run from agent_service container or locally with credentials in env:

  docker compose exec agent_service python test_planview.py

Or locally:
  cd backend/agent_service
  PLANVIEW_BASE_URL=https://manohar.c.pp-dev.net \
  PLANVIEW_CONSUMER_KEY=... \
  PLANVIEW_CONSUMER_SECRET=... \
  PLANVIEW_OAUTH_TOKEN=... \
  PLANVIEW_OAUTH_TOKEN_SECRET=... \
  PLANVIEW_PROJECT_ID=96 \
  PLANVIEW_PLAN_ID=96 \
  python test_planview.py
"""
import asyncio
import os
import sys

# Allow running from the agent_service directory without installing the package
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date
import services.planview_client as pv


async def main():
    today = date.today().isoformat()
    print(f"\n=== Planview smoke test ({today}) ===\n")

    # 1. Create board
    print("1. Creating board…")
    try:
        board = await pv.create_board("Test Board (smoke test)", "Created by smoke test — safe to delete")
        board_id = board["id"]
        print(f"   ✓ board id={board_id} name={board['name']!r}")
    except Exception as e:
        print(f"   ✗ board creation failed: {e}")
        return

    # 2. Create planlet (activity)
    print("2. Creating planlet (activity)…")
    try:
        planlet = await pv.create_planlet("Test Activity", today)
        planlet_id = planlet["id"]
        print(f"   ✓ planlet id={planlet_id} name={planlet['name']!r}")
    except Exception as e:
        print(f"   ✗ planlet creation failed: {e}")
        return

    # 3. Link planlet → board
    print("3. Linking planlet → board…")
    try:
        await pv.link_planlet_to_board(planlet_id, board_id)
        print(f"   ✓ planlet {planlet_id} linked to board {board_id}")
    except Exception as e:
        print(f"   ✗ link failed: {e}")

    # 4. Create a card
    print("4. Creating card…")
    try:
        card = await pv.create_card(
            title="Test card (smoke test)",
            board_id=board_id,
            planlet_id=planlet_id,
            description="This card was created by the smoke test.",
            column_id=0,
        )
        print(f"   ✓ card id={card.get('id')} title={card.get('title')!r}")
    except Exception as e:
        print(f"   ✗ card creation failed: {e}")

    print(f"\n✅ Done — check board {board_id} at {os.getenv('PLANVIEW_BASE_URL', '')}/workspaces\n")


if __name__ == "__main__":
    asyncio.run(main())
