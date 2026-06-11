"""CRUD routes + SSE /run endpoint for agents."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chains.agent_chain import run_agent
from db import get_db
from models.agent import Agent, AgentRun

router = APIRouter(prefix="/agents", tags=["agents"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class AgentCreate(BaseModel):
    user_id: str
    name: str
    description: Optional[str] = None
    system_prompt: str
    output_format: str = "markdown"
    tools: list[str] = ["search_all"]


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    output_format: Optional[str] = None
    tools: Optional[list[str]] = None


class RunRequest(BaseModel):
    query: str
    user_id: str


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("")
async def create_agent(body: AgentCreate, db: AsyncSession = Depends(get_db)):
    agent = Agent(
        user_id=body.user_id,
        name=body.name,
        description=body.description,
        system_prompt=body.system_prompt,
        output_format=body.output_format,
        tools=body.tools,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return _agent_dict(agent)


@router.get("")
async def list_agents(user_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = select(Agent).order_by(Agent.created_at.desc())
    if user_id:
        query = query.where(Agent.user_id == user_id)
    result = await db.execute(query)
    agents = result.scalars().all()
    return [_agent_dict(a) for a in agents]


@router.get("/{agent_id}")
async def get_agent(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _agent_dict(agent)


@router.patch("/{agent_id}")
async def update_agent(agent_id: uuid.UUID, body: AgentUpdate, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(agent, field, value)
    agent.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(agent)
    return _agent_dict(agent)


@router.delete("/{agent_id}")
async def delete_agent(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.delete(agent)
    await db.commit()
    return {"status": "deleted", "agent_id": str(agent_id)}


# ── Run ───────────────────────────────────────────────────────────────────────

@router.post("/{agent_id}/run")
async def run_agent_endpoint(
    agent_id: uuid.UUID,
    body: RunRequest,
    db: AsyncSession = Depends(get_db),
):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Create run record
    run = AgentRun(
        agent_id=agent_id,
        user_id=body.user_id,
        query=body.query,
        status="running",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    run_id = str(run.id)

    async def _stream():
        import json as _json
        from db import AsyncSessionLocal
        result_doc_id = None
        had_error     = False
        plan_steps    = None
        try:
            async for chunk in run_agent(
                run_id=run_id,
                agent_id=str(agent_id),
                agent_name=agent.name,
                user_id=body.user_id,
                query=body.query,
                system_prompt=agent.system_prompt,
                output_format=agent.output_format,
                enabled_tools=agent.tools,
            ):
                yield chunk
                try:
                    payload = _json.loads(chunk.removeprefix("data: ").strip())
                    if payload.get("type") == "uploaded":
                        result_doc_id = payload.get("document_id")
                    elif payload.get("type") == "plan":
                        plan_steps = payload.get("steps")
                    elif payload.get("type") == "error":
                        had_error = True
                except Exception:
                    pass
        except Exception:
            had_error = True

        # Update run status in a fresh session (generator owns this context)
        async with AsyncSessionLocal() as s:
            run_obj = await s.get(AgentRun, uuid.UUID(run_id))
            if run_obj:
                run_obj.status      = "failed" if had_error else "completed"
                run_obj.completed_at = datetime.now(timezone.utc)
                if result_doc_id:
                    run_obj.result_document_id = result_doc_id
                if plan_steps is not None:
                    run_obj.plan = plan_steps
                await s.commit()

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{agent_id}/runs")
async def list_runs(
    agent_id: uuid.UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.agent_id == agent_id)
        .order_by(AgentRun.created_at.desc())
        .limit(limit)
    )
    runs = result.scalars().all()
    return [_run_dict(r) for r in runs]


@router.get("/runs/{run_id}")
async def get_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    run = await db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_dict(run)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _run_dict(r: AgentRun) -> dict:
    return {
        "id":                 str(r.id),
        "agent_id":           str(r.agent_id),
        "user_id":            r.user_id,
        "query":              r.query,
        "status":             r.status,
        "plan":               r.plan,
        "result_document_id": r.result_document_id,
        "created_at":         r.created_at.isoformat() if r.created_at else None,
        "completed_at":       r.completed_at.isoformat() if r.completed_at else None,
    }


def _agent_dict(a: Agent) -> dict:
    return {
        "id": str(a.id),
        "user_id": a.user_id,
        "name": a.name,
        "description": a.description,
        "system_prompt": a.system_prompt,
        "output_format": a.output_format,
        "tools": a.tools,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }
