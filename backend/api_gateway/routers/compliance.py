import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_current_user, get_db
from models.user import User
from schemas.compliance import (
    ComplianceIssuesResponse,
    ComplianceReportResponse,
    ComplianceRuleCreate,
    ComplianceRuleResponse,
    ComplianceRuleUpdate,
    ComplianceStatsResponse,
)
from schemas.kafka_events import SummaryGeneratedEvent, Topics
from services import compliance_service, kafka_producer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["compliance"])


async def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ── Rules ─────────────────────────────────────────────────────────────────────

@router.get("/rules", response_model=list[ComplianceRuleResponse])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await compliance_service.list_rules(db)


@router.post("/rules", response_model=ComplianceRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    body: ComplianceRuleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_admin),
):
    return await compliance_service.create_rule(
        db, name=body.name, description=body.description,
        rule_type=body.rule_type, params=body.params, severity=body.severity,
    )


@router.patch("/rules/{rule_id}", response_model=ComplianceRuleResponse)
async def update_rule(
    rule_id: UUID,
    body: ComplianceRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_admin),
):
    rule = await compliance_service.update_rule(
        db, rule_id=rule_id,
        name=body.name, description=body.description,
        params=body.params, severity=body.severity, is_active=body.is_active,
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_admin),
):
    deleted = await compliance_service.delete_rule(db, rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")


# ── Per-document ──────────────────────────────────────────────────────────────

@router.get("/documents/{document_id}", response_model=ComplianceReportResponse)
async def get_document_report(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await compliance_service.get_report(db, document_id)


@router.post("/documents/{document_id}/scan", status_code=status.HTTP_202_ACCEPTED)
async def trigger_rescan(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exists = await compliance_service.document_exists_and_completed(db, document_id)
    if not exists:
        raise HTTPException(
            status_code=404,
            detail="Document not found or not yet completed processing",
        )

    # Write SCANNING status to DB before queuing so the UI immediately reflects it
    await compliance_service.mark_scan_pending(db, document_id)

    # Publish a synthetic summary_generated event to re-trigger the compliance worker
    event = SummaryGeneratedEvent(
        document_id=document_id,
        user_id=current_user.id,
        summary_length=0,
        strategy="rescan",
    )
    await kafka_producer.publish(
        topic=Topics.SUMMARY_GENERATED,
        payload=event.to_json(),
        key=str(document_id),
    )
    logger.info("compliance: rescan queued for document_id=%s", document_id)
    return {"status": "scan_queued"}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=ComplianceStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await compliance_service.get_stats(db)


@router.get("/issues", response_model=ComplianceIssuesResponse)
async def get_issues(
    limit: int = 50,
    cursor: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if limit < 1 or limit > 200:
        limit = 50
    return await compliance_service.get_issues(db, limit=limit, cursor=cursor, status_filter=status_filter)
