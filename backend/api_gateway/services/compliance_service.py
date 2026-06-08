"""
Compliance service — DB operations for compliance rules and reports.
The engine logic (run_compliance_check) lives in the workers package and is
replicated here for use by the API gateway re-scan background task.
"""
import base64
import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.compliance import (
    ComplianceIssueFailedRule,
    ComplianceIssueItem,
    ComplianceIssuesResponse,
    ComplianceReportResponse,
    ComplianceRuleResultResponse,
    ComplianceRuleResponse,
    ComplianceStatsResponse,
    LocationResponse,
)

logger = logging.getLogger(__name__)


# ── Rules hash helper ─────────────────────────────────────────────────────────

async def _compute_current_rules_hash(db: AsyncSession) -> str:
    rows = (await db.execute(
        sql_text("SELECT id, updated_at FROM compliance_rules WHERE is_active = true ORDER BY id")
    )).fetchall()
    parts = [f"{r.id}:{r.updated_at.isoformat()}" for r in rows]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


# ── Rules CRUD ────────────────────────────────────────────────────────────────

async def list_rules(db: AsyncSession) -> list[ComplianceRuleResponse]:
    rows = (await db.execute(
        sql_text("SELECT * FROM compliance_rules ORDER BY created_at")
    )).fetchall()
    return [
        ComplianceRuleResponse(
            id=r.id,
            name=r.name,
            description=r.description,
            rule_type=r.rule_type,
            params=r.params,
            severity=r.severity,
            is_active=r.is_active,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


async def create_rule(
    db: AsyncSession, name: str, description: Optional[str], rule_type: str,
    params: dict, severity: str
) -> ComplianceRuleResponse:
    row = (await db.execute(
        sql_text(
            "INSERT INTO compliance_rules (name, description, rule_type, params, severity) "
            "VALUES (:name, :description, :rule_type, CAST(:rule_params AS jsonb), :severity) "
            "RETURNING *"
        ).bindparams(
            name=name,
            description=description,
            rule_type=rule_type,
            rule_params=json.dumps(params),
            severity=severity,
        )
    )).fetchone()
    await db.commit()
    return ComplianceRuleResponse(
        id=row.id, name=row.name, description=row.description,
        rule_type=row.rule_type, params=row.params, severity=row.severity,
        is_active=row.is_active, created_at=row.created_at, updated_at=row.updated_at,
    )


async def update_rule(
    db: AsyncSession, rule_id: uuid.UUID,
    name: Optional[str], description: Optional[str],
    params: Optional[dict], severity: Optional[str], is_active: Optional[bool],
) -> Optional[ComplianceRuleResponse]:
    sets = []
    binds: dict[str, Any] = {"rule_id": rule_id}
    if name is not None:
        sets.append("name = :name"); binds["name"] = name
    if description is not None:
        sets.append("description = :description"); binds["description"] = description
    if params is not None:
        sets.append("params = CAST(:rule_params AS jsonb)"); binds["rule_params"] = json.dumps(params)
    if severity is not None:
        sets.append("severity = :severity"); binds["severity"] = severity
    if is_active is not None:
        sets.append("is_active = :is_active"); binds["is_active"] = is_active
    if not sets:
        return await _get_rule_by_id(db, rule_id)

    sets.append("updated_at = now()")
    row = (await db.execute(
        sql_text(
            f"UPDATE compliance_rules SET {', '.join(sets)} WHERE id = :rule_id RETURNING *"
        ).bindparams(**binds)
    )).fetchone()
    await db.commit()
    if not row:
        return None
    return ComplianceRuleResponse(
        id=row.id, name=row.name, description=row.description,
        rule_type=row.rule_type, params=row.params, severity=row.severity,
        is_active=row.is_active, created_at=row.created_at, updated_at=row.updated_at,
    )


async def _get_rule_by_id(db: AsyncSession, rule_id: uuid.UUID) -> Optional[ComplianceRuleResponse]:
    row = (await db.execute(
        sql_text("SELECT * FROM compliance_rules WHERE id = :id").bindparams(id=rule_id)
    )).fetchone()
    if not row:
        return None
    return ComplianceRuleResponse(
        id=row.id, name=row.name, description=row.description,
        rule_type=row.rule_type, params=row.params, severity=row.severity,
        is_active=row.is_active, created_at=row.created_at, updated_at=row.updated_at,
    )


async def delete_rule(db: AsyncSession, rule_id: uuid.UUID) -> bool:
    result = await db.execute(
        sql_text("DELETE FROM compliance_rules WHERE id = :id").bindparams(id=rule_id)
    )
    await db.commit()
    return result.rowcount > 0


# ── Per-document report ───────────────────────────────────────────────────────

async def get_report(db: AsyncSession, document_id: uuid.UUID) -> ComplianceReportResponse:
    report_row = (await db.execute(
        sql_text(
            "SELECT * FROM compliance_reports WHERE document_id = :doc_id AND is_current = true LIMIT 1"
        ).bindparams(doc_id=document_id)
    )).fetchone()

    if not report_row:
        # No scan has run yet — return a synthetic UNCHECKED response
        return ComplianceReportResponse(
            id=uuid.uuid4(),
            document_id=document_id,
            status="UNCHECKED",
            checked_at=datetime.utcnow(),
            is_stale=False,
            insights=None,
            results=[],
        )

    result_rows = (await db.execute(
        sql_text("SELECT * FROM compliance_rule_results WHERE report_id = :report_id ORDER BY created_at")
        .bindparams(report_id=report_row.id)
    )).fetchall()

    is_scanning = report_row.status == "SCANNING"
    current_hash = await _compute_current_rules_hash(db)
    is_stale = (not is_scanning) and (current_hash != report_row.rules_hash)

    results = []
    for r in result_rows:
        locs = None
        if r.locations is not None:
            raw = r.locations if isinstance(r.locations, list) else json.loads(r.locations)
            locs = [LocationResponse(**loc) for loc in raw]
        results.append(ComplianceRuleResultResponse(
            id=r.id,
            rule_id=r.rule_id,
            rule_name=r.rule_name,
            rule_type=r.rule_type,
            severity=r.severity,
            passed=r.passed,
            detail=r.detail,
            locations=locs,
        ))

    return ComplianceReportResponse(
        id=report_row.id,
        document_id=report_row.document_id,
        status=report_row.status,
        checked_at=report_row.checked_at,
        is_stale=is_stale,
        insights=report_row.insights,
        results=results,
    )


# ── Stats ─────────────────────────────────────────────────────────────────────

async def get_stats(db: AsyncSession) -> ComplianceStatsResponse:
    status_rows = (await db.execute(
        sql_text(
            "SELECT status, COUNT(*) as cnt FROM compliance_reports WHERE is_current = true GROUP BY status"
        )
    )).fetchall()
    counts = {r.status: int(r.cnt) for r in status_rows}

    total_docs = (await db.execute(
        sql_text("SELECT COUNT(*) FROM documents WHERE type = 'document' AND status = 'COMPLETED'")
    )).scalar() or 0
    checked = sum(counts.values())
    unchecked = max(0, int(total_docs) - checked)

    return ComplianceStatsResponse(
        compliant=counts.get("COMPLIANT", 0),
        warning=counts.get("WARNING", 0),
        non_compliant=counts.get("NON_COMPLIANT", 0),
        unchecked=unchecked,
        total_documents=int(total_docs),
    )


# ── Issues list ───────────────────────────────────────────────────────────────

def _encode_cursor(checked_at: datetime, report_id: uuid.UUID) -> str:
    payload = {"checked_at": checked_at.isoformat(), "id": str(report_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    return datetime.fromisoformat(payload["checked_at"]), uuid.UUID(payload["id"])


async def get_issues(
    db: AsyncSession,
    limit: int = 50,
    cursor: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> ComplianceIssuesResponse:
    where_clauses = ["cr.is_current = true", "cr.status != 'COMPLIANT'"]
    binds: dict[str, Any] = {}

    if status_filter:
        where_clauses.append("cr.status = :status_filter")
        binds["status_filter"] = status_filter

    if cursor:
        cursor_ts, cursor_id = _decode_cursor(cursor)
        where_clauses.append(
            "(cr.checked_at < :cursor_ts OR (cr.checked_at = :cursor_ts AND cr.id < :cursor_id))"
        )
        binds["cursor_ts"] = cursor_ts
        binds["cursor_id"] = cursor_id

    where_sql = " AND ".join(where_clauses)
    rows = (await db.execute(
        sql_text(
            f"SELECT cr.id, cr.document_id, cr.status, cr.checked_at, cr.rules_hash, "
            f"d.name as doc_name "
            f"FROM compliance_reports cr "
            f"JOIN documents d ON d.id = cr.document_id "
            f"WHERE {where_sql} "
            f"ORDER BY cr.checked_at DESC, cr.id DESC "
            f"LIMIT :limit"
        ).bindparams(limit=limit + 1, **binds)
    )).fetchall()

    current_hash = await _compute_current_rules_hash(db)
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = _encode_cursor(page[-1].checked_at, page[-1].id) if has_more and page else None

    items = []
    for row in page:
        fail_rows = (await db.execute(
            sql_text(
                "SELECT rule_name, severity, enforcement, detail FROM compliance_rule_results "
                "WHERE report_id = :report_id AND passed = false"
            ).bindparams(report_id=row.id)
        )).fetchall()
        items.append(ComplianceIssueItem(
            document_id=row.document_id,
            document_name=row.doc_name,
            report_id=row.id,
            status=row.status,
            checked_at=row.checked_at,
            is_stale=current_hash != row.rules_hash,
            failing_rules=[
                ComplianceIssueFailedRule(
                    rule_name=f.rule_name, severity=f.severity,
                    enforcement=f.enforcement, detail=f.detail,
                )
                for f in fail_rows
            ],
        ))

    return ComplianceIssuesResponse(items=items, next_cursor=next_cursor, has_more=has_more)


# ── Re-scan ───────────────────────────────────────────────────────────────────

async def document_exists_and_completed(db: AsyncSession, document_id: uuid.UUID) -> bool:
    row = (await db.execute(
        sql_text(
            "SELECT 1 FROM documents WHERE id = :doc_id AND type = 'document' AND status = 'COMPLETED'"
        ).bindparams(doc_id=document_id)
    )).fetchone()
    return row is not None


async def mark_scan_pending(db: AsyncSession, document_id: uuid.UUID) -> None:
    """Write a SCANNING row so the UI immediately reflects the in-progress state."""
    await db.execute(
        sql_text(
            "UPDATE compliance_reports SET is_current = false "
            "WHERE document_id = :doc_id AND is_current = true"
        ).bindparams(doc_id=document_id)
    )
    await db.execute(
        sql_text(
            "INSERT INTO compliance_reports "
            "(document_id, status, rules_hash, is_current, insights) "
            "VALUES (:doc_id, 'SCANNING', '', true, null)"
        ).bindparams(doc_id=document_id)
    )
    await db.commit()
