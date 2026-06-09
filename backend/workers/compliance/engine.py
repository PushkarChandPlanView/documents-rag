"""
Compliance Engine — runs all active rules against a document and persists results.

Performance design:
- keyword_required / keyword_forbidden / age_limit_days: run in parallel (asyncio.gather)
- llm_check rules: single batch call using the governance framework prompt
- insights: one additional LLM call only when there are failures
- Each LLM call is wrapped in asyncio.wait_for (fail-closed on timeout)
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

from config import get_settings
from shared.providers import llm_factory

settings = get_settings()

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

_BLOCKING_SEVERITIES = {"critical", "high"}

# ── Governance framework prompt ───────────────────────────────────────────────

_GOVERNANCE_FRAMEWORK = """/no_think
You are a Document Compliance & Governance Engine.

Your task is to evaluate a document against a set of compliance rules and return violations, warnings, and informational findings.

## Severity Levels

* `info` → Informational recommendation. No action required.
* `warning` → Moderate issue that should be addressed.
* `high` → Significant compliance or governance concern requiring remediation.
* `critical` → Severe violation that may create legal, security, privacy, or regulatory risk.

## Enforcement Levels

* `advisory` → Does not block publication or sharing.
* `blocking` → Prevents publication, approval, or external sharing until resolved.

## Rule Evaluation Principles

1. Evaluate every rule independently.
2. Explain why a rule passed or failed.
3. Include evidence from the document when possible.
4. Do not generate findings when evidence is insufficient.
5. Return only findings that have reasonable confidence.
6. If a rule is not applicable, mark it as `not_applicable`.

## Output Format

Return JSON only.

{
  "overall_status": "pass | advisory_fail | blocking_fail",
  "summary": {
    "critical": 0,
    "high": 0,
    "warning": 0,
    "info": 0
  },
  "findings": [
    {
      "rule_name": "",
      "status": "pass | fail | not_applicable",
      "severity": "",
      "enforcement": "",
      "reason": "",
      "evidence": ""
    }
  ]
}

A document receives:
* `blocking_fail` if any failed rule has enforcement = blocking.
* `advisory_fail` if only advisory rules fail.
* `pass` if all applicable rules pass.
"""

INSIGHTS_PROMPT = """/no_think
You are a document compliance advisor. The document "{doc_name}" failed these compliance checks:

{failures}

Using the document summary below, provide:
1. A plain-English explanation of why each check failed.
2. Concrete, actionable steps the document owner can take to fix each issue.

Be concise (3-5 sentences total). Do not repeat rule names verbatim.

Document summary:
{summary}"""


def _build_chunk_text(chunks: list[ChunkMeta], max_chars: int = 6000) -> str:
    """Concatenate chunks into a single text block, truncated to max_chars."""
    parts = []
    total = 0
    for c in chunks:
        if total + len(c.text) > max_chars:
            remaining = max_chars - total
            if remaining > 100:
                parts.append(c.text[:remaining] + "…")
            break
        parts.append(c.text)
        total += len(c.text)
    return "\n\n".join(parts)


def _build_eval_prompt(rules: list[dict], document_text: str, content_label: str) -> str:
    rules_section = "\n".join(
        f"{i + 1}. {r['name']}: {r['params'].get('policy', r['name'])}"
        for i, r in enumerate(rules)
    )
    # Pre-seed the findings array with exact rule names so the LLM only fills
    # in verdict fields — this prevents it from inventing its own category names.
    seeded_findings = ",\n    ".join(
        json.dumps({
            "rule_name": r["name"],
            "status": "pass | fail | not_applicable",
            "severity": "info | warning | high | critical",
            "enforcement": "advisory | blocking",
            "reason": "",
            "evidence": "",
        })
        for r in rules
    )
    return (
        _GOVERNANCE_FRAMEWORK
        + "\n---\n\n"
        + f"Evaluate the {content_label} below against EXACTLY these {len(rules)} rules.\n"
        + "You MUST return one finding per rule. "
        + "Keep every `rule_name` value EXACTLY as written — do NOT rename or rephrase them.\n\n"
        + f"Rules:\n{rules_section}\n\n"
        + f"{content_label.title()}:\n{document_text}\n\n"
        + "Return ONLY this JSON with all fields filled in:\n"
        + '{\n  "overall_status": "pass | advisory_fail | blocking_fail",\n'
        + '  "summary": {"critical": 0, "high": 0, "warning": 0, "info": 0},\n'
        + f'  "findings": [\n    {seeded_findings}\n  ]\n}}'
    )


_SEVERITY_ORDER = ["info", "warning", "high", "critical"]


def _severity_to_enforcement(severity: str) -> str:
    return "blocking" if severity in _BLOCKING_SEVERITIES else "advisory"


def _cap_severity(llm_severity: str, rule_severity: str) -> str:
    """Prevent the LLM from escalating beyond the rule's configured severity."""
    llm_idx = _SEVERITY_ORDER.index(llm_severity) if llm_severity in _SEVERITY_ORDER else 3
    rule_idx = _SEVERITY_ORDER.index(rule_severity) if rule_severity in _SEVERITY_ORDER else 3
    return _SEVERITY_ORDER[min(llm_idx, rule_idx)]


def _parse_governance_response(
    raw: str, llm_rules: list[dict]
) -> tuple[str, list[tuple[dict, RuleResult]]]:
    """
    Parse the governance JSON response and map findings back to DB rules.
    Returns (overall_status, [(rule, RuleResult), ...]).
    Fail-closed: unmatched or unparseable rules → passed=False, enforcement=blocking.
    """
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        data: dict = json.loads(match.group() if match else raw.strip())
    except (json.JSONDecodeError, AttributeError):
        logger.warning("compliance: could not parse governance LLM response")
        return "blocking_fail", [
            (
                rule,
                RuleResult(
                    passed=False,
                    detail="LLM response could not be parsed — check not verified.",
                    severity=rule["severity"],
                    enforcement=_severity_to_enforcement(rule["severity"]),
                ),
            )
            for rule in llm_rules
        ]

    overall_status: str = data.get("overall_status", "blocking_fail")
    findings: list[dict] = data.get("findings", [])

    # Primary: match by normalised rule_name
    finding_map = {
        f.get("rule_name", "").lower().strip(): f for f in findings
    }
    # Fallback: positional match — if the LLM mangled names but returned
    # findings in the same order we sent the rules, use index alignment.
    findings_by_index: dict[int, dict] = {i: f for i, f in enumerate(findings)}

    results: list[tuple[dict, RuleResult]] = []
    for idx, rule in enumerate(llm_rules):
        finding = finding_map.get(rule["name"].lower().strip())
        if not finding:
            finding = findings_by_index.get(idx)
            if finding:
                logger.debug(
                    "compliance: rule '%s' matched by position %d (LLM returned rule_name='%s')",
                    rule["name"], idx, finding.get("rule_name", ""),
                )

        if not finding:
            results.append((
                rule,
                RuleResult(
                    passed=False,
                    detail="Rule was not evaluated by the LLM.",
                    severity=rule["severity"],
                    enforcement=_severity_to_enforcement(rule["severity"]),
                ),
            ))
            continue

        finding_status = finding.get("status", "fail")
        llm_severity = _cap_severity(finding.get("severity") or rule["severity"], rule["severity"])
        llm_enforcement = finding.get("enforcement") or _severity_to_enforcement(llm_severity)
        reason = (finding.get("reason") or "")[:500]
        evidence = (finding.get("evidence") or "")[:300]
        detail = " | ".join(p for p in [reason, f"Evidence: {evidence}" if evidence else ""] if p) or None

        if finding_status == "not_applicable":
            results.append((
                rule,
                RuleResult(
                    passed=True,
                    not_applicable=True,
                    detail=detail or "Not applicable to this document.",
                    severity=llm_severity,
                    enforcement="advisory",
                ),
            ))
        else:
            passed = finding_status == "pass"
            locations = (
                [Location(chunk_index=None, page_number=None, excerpt=evidence)]
                if evidence and not passed
                else None
            )
            results.append((
                rule,
                RuleResult(
                    passed=passed,
                    detail=detail,
                    severity=llm_severity,
                    enforcement=llm_enforcement,
                    locations=locations,
                ),
            ))

    return overall_status, results


# ── LLM call wrapper ──────────────────────────────────────────────────────────

async def _call_llm_with_timeout(prompt: str) -> Optional[str]:
    """Call the LLM with a timeout. Returns None on timeout or error (fail-closed)."""
    try:
        return await asyncio.wait_for(
            llm_factory.generate(prompt),
            timeout=LLM_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("compliance: LLM call timed out after %ds", LLM_TIMEOUT_SECONDS)
        return None
    except Exception as exc:
        logger.warning("compliance: LLM call failed: %s", exc)
        return None


def _unavailable_results(rules: list[dict]) -> list[tuple[dict, RuleResult]]:
    return [
        (
            rule,
            RuleResult(
                passed=False,
                detail="LLM check unavailable — could not verify compliance.",
                severity=rule["severity"],
                enforcement=_severity_to_enforcement(rule["severity"]),
            ),
        )
        for rule in rules
    ]


async def _run_batch_llm_check(
    llm_rules: list[dict],
    summary: str,
    chunks: list[ChunkMeta],
    doc_created_at: datetime,
) -> tuple[str, list[tuple[dict, RuleResult]]]:
    """
    Split llm_check rules by their 'content' param ('summary' vs 'chunks'),
    run each group in a separate parallel LLM call, merge results.
    Returns (overall_status, [(rule, RuleResult), ...]).
    """
    if not llm_rules:
        return "pass", []

    # Partition rules by content requirement
    summary_rules = [r for r in llm_rules if r["params"].get("content", "summary") == "summary"]
    chunk_rules   = [r for r in llm_rules if r["params"].get("content", "summary") == "chunks"]

    chunk_text = _build_chunk_text(chunks) if chunk_rules else ""

    async def call_group(rules: list[dict], text: str, label: str):
        if not rules:
            return "pass", []
        prompt = _build_eval_prompt(rules, text, label)
        raw = await _call_llm_with_timeout(prompt)
        if not raw:
            return "blocking_fail", _unavailable_results(rules)
        return _parse_governance_response(raw, rules)

    # Bedrock: parallel calls go to independent AWS infrastructure — no contention.
    # Ollama (local CPU): parallel calls compete for the same core and both time out
    # — run sequentially so each call gets full CPU attention.
    if settings.llm_provider == "bedrock":
        (sum_status, sum_results), (chk_status, chk_results) = await asyncio.gather(
            call_group(summary_rules, summary, "document summary"),
            call_group(chunk_rules, chunk_text, "document text"),
        )
    else:
        sum_status, sum_results = await call_group(summary_rules, summary, "document summary")
        chk_status, chk_results = await call_group(chunk_rules, chunk_text, "document text")

    # Merge: worst overall_status wins
    status_rank = {"pass": 0, "advisory_fail": 1, "blocking_fail": 2}
    overall = max(sum_status, chk_status, key=lambda s: status_rank.get(s, 0))
    return overall, sum_results + chk_results


# ── Rule hash ─────────────────────────────────────────────────────────────────

def _compute_rules_hash(rules: list[dict]) -> str:
    parts = [f"{r['id']}:{r['updated_at']}" for r in sorted(rules, key=lambda r: r["id"])]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


# ── Main engine ───────────────────────────────────────────────────────────────

async def run_compliance_check(document_id: uuid.UUID, session: AsyncSession) -> None:
    doc_id_str = str(document_id)

    doc_row = (await session.execute(
        sql_text("SELECT name, created_at FROM documents WHERE id = :doc_id").bindparams(doc_id=document_id)
    )).fetchone()
    if not doc_row:
        logger.warning("compliance: document %s not found — skipping", doc_id_str)
        return

    doc_name = doc_row.name
    doc_created_at: datetime = doc_row.created_at

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

    fast_rules = [r for r in rules if r["rule_type"] in _FAST_CHECKERS]
    llm_rules = [r for r in rules if r["rule_type"] == "llm_check"]

    async def run_fast_rule(rule: dict) -> tuple[dict, RuleResult]:
        checker = _FAST_CHECKERS[rule["rule_type"]]
        try:
            result = await checker.check(
                params=rule["params"],
                chunks=chunks,
                summary=summary,
                document_created_at=doc_created_at,
            )
            # Attach enforcement derived from the rule's configured severity
            result.enforcement = _severity_to_enforcement(rule["severity"])
        except Exception as exc:
            logger.error("compliance: rule '%s' raised: %s", rule["name"], exc)
            result = RuleResult(
                passed=False,
                detail=f"Check error: {exc}",
                severity=rule["severity"],
                enforcement=_severity_to_enforcement(rule["severity"]),
            )
        return rule, result

    fast_coros = [run_fast_rule(r) for r in fast_rules]
    llm_coro = _run_batch_llm_check(llm_rules, summary or "", chunks, doc_created_at)

    async def _empty_fast() -> list:
        return []

    fast_results_list, (llm_overall_status, llm_results) = await asyncio.gather(
        asyncio.gather(*fast_coros) if fast_coros else _empty_fast(),
        llm_coro,
    )

    # Combine — exclude not_applicable results from persistence
    all_results: list[tuple[dict, RuleResult]] = [
        (rule, res)
        for rule, res in list(fast_results_list) + llm_results
        if not res.not_applicable
    ]

    # Aggregate status: worst of fast-rule failures + LLM overall_status
    has_blocking_fail = (
        any(not res.passed and res.enforcement == "blocking" for _, res in all_results)
        or llm_overall_status == "blocking_fail"
    )
    has_advisory_fail = (
        any(not res.passed and res.enforcement == "advisory" for _, res in all_results)
        or llm_overall_status == "advisory_fail"
    )
    status = (
        "NON_COMPLIANT" if has_blocking_fail
        else "WARNING" if has_advisory_fail
        else "COMPLIANT"
    )

    # Insights — one extra LLM call only if there are failures
    insights: Optional[str] = None
    if status != "COMPLIANT" and summary:
        failures_text = "\n".join(
            f"- [{(res.severity or rule['severity']).upper()}] {rule['name']}: {res.detail or ''}"
            for rule, res in all_results if not res.passed
        )
        raw_insights = await _call_llm_with_timeout(
            INSIGHTS_PROMPT.format(doc_name=doc_name, failures=failures_text, summary=summary[:3000])
        )
        insights = raw_insights.strip() if raw_insights else None

    # Persist
    await session.execute(
        sql_text(
            "UPDATE compliance_reports SET is_current = false "
            "WHERE document_id = :doc_id AND is_current = true"
        ).bindparams(doc_id=document_id)
    )

    report_id = uuid.uuid4()
    await session.execute(
        sql_text(
            "INSERT INTO compliance_reports (id, document_id, status, rules_hash, is_current, insights) "
            "VALUES (:id, :doc_id, :status, :rules_hash, true, :insights)"
        ).bindparams(id=report_id, doc_id=document_id, status=status, rules_hash=rules_hash, insights=insights)
    )

    for rule, res in all_results:
        effective_severity = res.severity or rule["severity"]
        effective_enforcement = res.enforcement or _severity_to_enforcement(effective_severity)
        locations_json = (
            json.dumps([loc.to_dict() for loc in res.locations]) if res.locations else None
        )
        await session.execute(
            sql_text(
                "INSERT INTO compliance_rule_results "
                "(id, report_id, rule_id, rule_name, rule_type, severity, enforcement, passed, detail, locations) "
                "VALUES (:id, :report_id, :rule_id, :rule_name, :rule_type, :severity, :enforcement, "
                ":passed, :detail, CAST(:locations AS jsonb))"
            ).bindparams(
                id=uuid.uuid4(),
                report_id=report_id,
                rule_id=uuid.UUID(rule["id"]),
                rule_name=rule["name"],
                rule_type=rule["rule_type"],
                severity=effective_severity,
                enforcement=effective_enforcement,
                passed=res.passed,
                detail=res.detail,
                locations=locations_json,
            )
        )

    await session.commit()
    logger.info(
        "compliance: document %s → %s (%d rules, %d llm_check, llm_status=%s)",
        doc_id_str, status, len(all_results), len(llm_results), llm_overall_status,
    )
