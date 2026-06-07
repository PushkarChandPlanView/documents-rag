"""
Compliance Engine — runs all active rules against a document and persists results.

Performance design:
- keyword_required / keyword_forbidden / age_limit_days: run in parallel (asyncio.gather)
- llm_check rules: batched into a SINGLE LLM call instead of N separate calls
- insights: one additional LLM call only when there are failures
- Each LLM call is wrapped in asyncio.wait_for with a 90-second timeout (fail-open)
"""
import asyncio
import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.providers import llm_factory

from .rules.age_limit_days import AgeLimitDaysChecker
from .rules.base import ChunkMeta, Location, RuleChecker, RuleResult
from .rules.keyword_forbidden import KeywordForbiddenChecker
from .rules.keyword_required import KeywordRequiredChecker

logger = logging.getLogger(__name__)

LLM_TIMEOUT_SECONDS = 600  # 10 min — Ollama on CPU can take 90-120s per call

_FAST_CHECKERS: dict[str, RuleChecker] = {
    "keyword_required": KeywordRequiredChecker(),
    "keyword_forbidden": KeywordForbiddenChecker(),
    "age_limit_days": AgeLimitDaysChecker(),
}

# ── Batch LLM check ───────────────────────────────────────────────────────────

BATCH_LLM_PROMPT = """/no_think
You are a compliance checker. Evaluate the following document summary against each numbered policy below.

Document summary:
{summary}

Policies (evaluate each independently):
{policies}

Respond ONLY with a valid JSON array — one object per policy in the same order:
[
  {{"id": 1, "compliant": true, "reason": "brief explanation (max 80 chars)", "relevant_excerpt": "quote from summary (max 100 chars, or empty string)"}},
  ...
]"""

INSIGHTS_PROMPT = """/no_think
You are a document compliance advisor. The document "{doc_name}" failed these compliance checks:

{failures}

Using the document summary below, provide:
1. A plain-English explanation of why each check failed.
2. Concrete, actionable steps the document owner can take to fix each issue.

Be concise (3-5 sentences total). Do not repeat rule names verbatim.

Document summary:
{summary}"""


async def _call_llm_with_timeout(prompt: str) -> Optional[str]:
    """Call the LLM with a timeout. Returns None on timeout or error (fail-open)."""
    try:
        return await asyncio.wait_for(
            llm_factory.generate(prompt),
            timeout=LLM_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("compliance: LLM call timed out after %ds — treating as compliant", LLM_TIMEOUT_SECONDS)
        return None
    except Exception as exc:
        logger.warning("compliance: LLM call failed: %s — treating as compliant", exc)
        return None


async def _run_batch_llm_check(
    llm_rules: list[dict],
    summary: str,
    chunks: list[ChunkMeta],
    doc_created_at: datetime,
) -> list[tuple[dict, RuleResult]]:
    """Evaluate all llm_check rules in a single LLM call."""
    if not llm_rules:
        return []

    policy_lines = "\n".join(
        f"{i + 1}. {rule['params'].get('policy', '')}"
        for i, rule in enumerate(llm_rules)
    )
    prompt = BATCH_LLM_PROMPT.format(
        summary=summary[:4000],
        policies=policy_lines,
    )

    raw = await _call_llm_with_timeout(prompt)

    if not raw:
        # Fail-open: all llm_check rules pass
        return [
            (rule, RuleResult(passed=True, detail="LLM check unavailable — treated as compliant.", locations=None))
            for rule in llm_rules
        ]

    # Parse JSON array from response
    try:
        # Strip any surrounding text before/after the JSON array
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        items: list[dict] = json.loads(match.group()) if match else json.loads(raw.strip())
    except (json.JSONDecodeError, AttributeError):
        logger.warning("compliance: could not parse batch LLM response — treating all as compliant")
        return [
            (rule, RuleResult(passed=True, detail="LLM response parse error — treated as compliant.", locations=None))
            for rule in llm_rules
        ]

    results: list[tuple[dict, RuleResult]] = []
    for i, rule in enumerate(llm_rules):
        item = items[i] if i < len(items) else {}
        compliant = bool(item.get("compliant", True))
        reason = str(item.get("reason", ""))[:200]
        excerpt = str(item.get("relevant_excerpt", ""))[:200]

        locations = [Location(chunk_index=None, page_number=None, excerpt=excerpt)] if excerpt else None

        results.append((
            rule,
            RuleResult(passed=compliant, detail=reason or None, locations=locations),
        ))

    return results


# ── Rule hash ─────────────────────────────────────────────────────────────────

def _compute_rules_hash(rules: list[dict]) -> str:
    parts = [f"{r['id']}:{r['updated_at']}" for r in sorted(rules, key=lambda r: r["id"])]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


# ── Main engine ───────────────────────────────────────────────────────────────

async def run_compliance_check(document_id: uuid.UUID, session: AsyncSession) -> None:
    doc_id_str = str(document_id)

    # Load document metadata
    doc_row = (await session.execute(
        sql_text("SELECT name, created_at FROM documents WHERE id = :doc_id").bindparams(doc_id=document_id)
    )).fetchone()
    if not doc_row:
        logger.warning("compliance: document %s not found — skipping", doc_id_str)
        return

    doc_name = doc_row.name
    doc_created_at: datetime = doc_row.created_at

    # Load active rules
    rules_rows = (await session.execute(
        sql_text(
            "SELECT id, name, rule_type, params, severity, updated_at "
            "FROM compliance_rules WHERE is_active = true ORDER BY id"
        )
    )).fetchall()

    if not rules_rows:
        logger.info("compliance: no active rules for document %s", doc_id_str)
        return

    rules = [
        {
            "id": str(r.id), "name": r.name, "rule_type": r.rule_type,
            "params": r.params, "severity": r.severity, "updated_at": r.updated_at.isoformat(),
        }
        for r in rules_rows
    ]
    rules_hash = _compute_rules_hash(rules)

    # Load chunks and summary in parallel
    chunks_future = session.execute(
        sql_text(
            "SELECT text, chunk_index, page_number FROM document_chunks "
            "WHERE document_id = :doc_id ORDER BY chunk_index"
        ).bindparams(doc_id=document_id)
    )
    summary_future = session.execute(
        sql_text(
            "SELECT summary FROM document_summaries "
            "WHERE document_id = :doc_id AND is_active = true ORDER BY created_at DESC LIMIT 1"
        ).bindparams(doc_id=document_id)
    )
    chunks_result, summary_result = await asyncio.gather(chunks_future, summary_future)

    chunks = [
        ChunkMeta(text=r.text, chunk_index=r.chunk_index, page_number=r.page_number)
        for r in chunks_result.fetchall()
    ]
    summary_row = summary_result.fetchone()
    summary: Optional[str] = summary_row.summary if summary_row else None

    # Split rules by type
    fast_rules = [r for r in rules if r["rule_type"] in _FAST_CHECKERS]
    llm_rules = [r for r in rules if r["rule_type"] == "llm_check"]

    # Run fast rules in parallel, batch llm_check rules into one call — concurrently
    async def run_fast_rule(rule: dict) -> tuple[dict, RuleResult]:
        checker = _FAST_CHECKERS[rule["rule_type"]]
        try:
            result = await checker.check(
                params=rule["params"],
                chunks=chunks,
                summary=summary,
                document_created_at=doc_created_at,
            )
        except Exception as exc:
            logger.error("compliance: rule '%s' raised: %s", rule["name"], exc)
            result = RuleResult(passed=True, detail=f"Check error: {exc}", locations=None)
        return rule, result

    fast_coros = [run_fast_rule(r) for r in fast_rules]
    llm_coro = _run_batch_llm_check(llm_rules, summary or "", chunks, doc_created_at)

    async def _empty() -> list:
        return []

    fast_results_list, llm_results = await asyncio.gather(
        asyncio.gather(*fast_coros) if fast_coros else _empty(),
        llm_coro,
    )

    rule_results: list[tuple[dict, RuleResult]] = list(fast_results_list) + llm_results

    # Aggregate status
    has_critical_fail = any(not res.passed and rule["severity"] == "critical" for rule, res in rule_results)
    has_warning_fail = any(not res.passed and rule["severity"] == "warning" for rule, res in rule_results)
    status = "NON_COMPLIANT" if has_critical_fail else ("WARNING" if has_warning_fail else "COMPLIANT")

    # Generate insights (one more LLM call, only if there are failures)
    insights: Optional[str] = None
    if status != "COMPLIANT" and summary:
        failures_text = "\n".join(
            f"- [{rule['severity'].upper()}] {rule['name']}: {res.detail or ''}"
            for rule, res in rule_results if not res.passed
        )
        raw_insights = await _call_llm_with_timeout(
            INSIGHTS_PROMPT.format(doc_name=doc_name, failures=failures_text, summary=summary[:3000])
        )
        insights = raw_insights.strip() if raw_insights else None

    # Persist — mark old reports stale, insert new report + results
    await session.execute(
        sql_text(
            "UPDATE compliance_reports SET is_current = false WHERE document_id = :doc_id AND is_current = true"
        ).bindparams(doc_id=document_id)
    )

    report_id = uuid.uuid4()
    await session.execute(
        sql_text(
            "INSERT INTO compliance_reports (id, document_id, status, rules_hash, is_current, insights) "
            "VALUES (:id, :doc_id, :status, :rules_hash, true, :insights)"
        ).bindparams(id=report_id, doc_id=document_id, status=status, rules_hash=rules_hash, insights=insights)
    )

    for rule, res in rule_results:
        locations_json = (
            json.dumps([loc.to_dict() for loc in res.locations]) if res.locations is not None else None
        )
        await session.execute(
            sql_text(
                "INSERT INTO compliance_rule_results "
                "(id, report_id, rule_id, rule_name, rule_type, severity, passed, detail, locations) "
                "VALUES (:id, :report_id, :rule_id, :rule_name, :rule_type, :severity, :passed, :detail, CAST(:locations AS jsonb))"
            ).bindparams(
                id=uuid.uuid4(),
                report_id=report_id,
                rule_id=uuid.UUID(rule["id"]),
                rule_name=rule["name"],
                rule_type=rule["rule_type"],
                severity=rule["severity"],
                passed=res.passed,
                detail=res.detail,
                locations=locations_json,
            )
        )

    await session.commit()
    logger.info("compliance: document %s → %s (%d rules, %d llm_check batched)", doc_id_str, status, len(rule_results), len(llm_rules))
