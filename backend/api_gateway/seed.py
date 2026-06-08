"""Seed script: creates the default admin user and baseline compliance rules."""
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from config import get_settings
from services.auth_service import create_user

settings = get_settings()

# Rules to seed — skip any whose name already exists in the DB.
# Existing: No Personal Identifiable Information, No Hardcoded Credentials,
#           Document Review Freshness, No Offensive Language,
#           Professional Tone and Completeness
COMPLIANCE_RULES = [
    # ── Document Expiration ───────────────────────────────────────────────────
    # Distinct from freshness (warning at 1 yr): hard critical expiry at 2 yrs.
    {
        "name": "Document Expiration",
        "description": "Documents older than 2 years must be reviewed, updated, or archived.",
        "rule_type": "age_limit_days",
        "params": {"days": 730},
        "severity": "critical",
    },
    # ── Owner Required ────────────────────────────────────────────────────────
    {
        "name": "Owner Required",
        "description": "Documents must identify an owner, author, or responsible party.",
        "rule_type": "keyword_required",
        "params": {
            "keywords": [
                "author", "owner", "prepared by", "written by",
                "contact", "responsible", "document owner",
            ]
        },
        "severity": "warning",
    },
    # ── Classification Required ───────────────────────────────────────────────
    {
        "name": "Classification Required",
        "description": "Documents must carry an information-classification label.",
        "rule_type": "keyword_required",
        "params": {
            "keywords": [
                "confidential", "internal", "public", "restricted",
                "classification", "sensitive", "proprietary",
            ]
        },
        "severity": "warning",
    },
    # ── Approval Required ─────────────────────────────────────────────────────
    {
        "name": "Approval Required",
        "description": "Documents must show evidence of review or approval by an authorised party.",
        "rule_type": "llm_check",
        "params": {
            "policy": (
                "The document must contain evidence of approval, sign-off, or authorisation — "
                "such as a reviewer name, approver, approval date, or signature block. "
                "Informal drafts with no approval markers are non-compliant."
            )
        },
        "severity": "warning",
    },
    # ── Placeholder Detection ─────────────────────────────────────────────────
    # Fast keyword check; complements the broader LLM-based quality rule.
    {
        "name": "Placeholder Detection",
        "description": "Documents must not contain template placeholders or draft markers.",
        "rule_type": "keyword_forbidden",
        "params": {
            "keywords": [
                "TODO", "TBD", "FIXME", "PLACEHOLDER",
                "[INSERT", "[TBD]", "lorem ipsum", "XXX",
                "coming soon", "to be determined", "fill in",
            ]
        },
        "severity": "warning",
    },
    # ── Duplicate Content Detection ───────────────────────────────────────────
    {
        "name": "Duplicate Content Detection",
        "description": "Documents must not contain excessive verbatim repetition or copy-paste blocks.",
        "rule_type": "llm_check",
        "params": {
            "policy": (
                "The document must not contain significant verbatim repeated sections or "
                "obvious copy-paste blocks. Each section should contribute unique information "
                "without excessive duplication of prior content within the same document."
            )
        },
        "severity": "warning",
    },
    # ── Required Section Validation ───────────────────────────────────────────
    {
        "name": "Required Section Validation",
        "description": "Documents must include core structural sections appropriate to their type.",
        "rule_type": "llm_check",
        "params": {
            "policy": (
                "The document must contain the core structural elements appropriate to its type: "
                "at minimum a clear introduction or purpose statement, a substantive main body, "
                "and a conclusion, summary, or next-steps section. "
                "Purely fragmentary documents with no discernible structure are non-compliant."
            )
        },
        "severity": "warning",
    },
]


async def run() -> None:
    engine = create_async_engine(settings.postgres_url)
    try:
        async with AsyncSession(engine) as db:
            # Admin user
            try:
                user = await create_user(db, "admin@example.com", "changeme", is_admin=True)
                print(f"Created admin user: {user.email}")
            except Exception as e:
                await db.rollback()
                print(f"Skipping user (may already exist): {e}")

            # Compliance rules — late import avoids circular deps at module level
            from models.compliance import ComplianceRule

            added = 0
            for rule_data in COMPLIANCE_RULES:
                existing = (await db.execute(
                    select(ComplianceRule).where(ComplianceRule.name == rule_data["name"])
                )).scalar_one_or_none()
                if existing:
                    print(f"  skip (exists): {rule_data['name']}")
                    continue
                db.add(ComplianceRule(**rule_data))
                print(f"  added: {rule_data['name']}")
                added += 1

            if added:
                await db.commit()
                print(f"Seeded {added} compliance rule(s).")
            else:
                print("All compliance rules already present.")
    finally:
        await engine.dispose()


asyncio.run(run())
