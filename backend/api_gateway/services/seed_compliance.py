"""Seed 15 industry-standard compliance rules on first startup."""
import json
import logging

from dependencies import AsyncSessionLocal
from sqlalchemy import text as sql_text

logger = logging.getLogger(__name__)

DEFAULT_RULES = [
    # ── Sensitive Data ────────────────────────────────────────────────────────
    {
        "name": "No Personal Identifiable Information",
        "description": "Forbids SSN, credit card numbers, and passport details.",
        "rule_type": "keyword_forbidden",
        "params": {"keywords": ["social security number", "ssn", "credit card number", "passport number"]},
        "severity": "critical",
    },
    {
        "name": "No Hardcoded Credentials",
        "description": "Forbids documents containing passwords, API keys, or secret tokens.",
        "rule_type": "keyword_forbidden",
        "params": {"keywords": ["password:", "api_key", "secret_key", "private_key", "access_token"]},
        "severity": "critical",
    },
    # ── Document Hygiene ──────────────────────────────────────────────────────
    {
        "name": "Required Legal Disclaimer",
        "description": "Document must include a disclaimer or 'not legal advice' notice.",
        "rule_type": "keyword_required",
        "params": {"keywords": ["disclaimer", "not legal advice", "for informational purposes only"]},
        "severity": "warning",
    },
    {
        "name": "Document Review Freshness",
        "description": "Documents older than 365 days must be reviewed and updated.",
        "rule_type": "age_limit_days",
        "params": {"days": 365},
        "severity": "warning",
    },
    # ── Foul Language ─────────────────────────────────────────────────────────
    {
        "name": "No Foul Language",
        "description": "Forbids profanity and explicit language in documents.",
        "rule_type": "keyword_forbidden",
        "params": {
            "keywords": [
                "fuck", "fucking", "fucked", "fucker",
                "shit", "bullshit", "shitty",
                "asshole", "ass", "bastard",
                "bitch", "damn", "crap",
                "cunt", "dick", "cock", "prick",
                "motherfucker", "motherfucking",
                "hell", "piss", "pissed",
            ]
        },
        "severity": "critical",
    },
    # ── Content Quality (LLM) ─────────────────────────────────────────────────
    {
        "name": "No Offensive Language",
        "description": "LLM check — document must not contain offensive or discriminatory content.",
        "rule_type": "llm_check",
        "params": {
            "policy": (
                "The document must not contain offensive, discriminatory, or derogatory language "
                "based on race, gender, religion, nationality, age, or any protected characteristic."
            )
        },
        "severity": "critical",
    },
    {
        "name": "Professional Tone and Completeness",
        "description": "LLM check — document must be professional, coherent, and complete.",
        "rule_type": "llm_check",
        "params": {
            "policy": (
                "The document must maintain a professional and coherent tone. "
                "It must not contain placeholder text (Lorem ipsum, TBD, FIXME), "
                "be obviously incomplete, or consist of incoherent content."
            )
        },
        "severity": "warning",
    },
]


async def seed_compliance_rules() -> None:
    async with AsyncSessionLocal() as db:
        # Always ensure the default admin user is marked as admin
        await db.execute(
            sql_text("UPDATE users SET is_admin = true WHERE email = 'admin@example.com'")
        )
        await db.commit()

        existing = (await db.execute(
            sql_text("SELECT COUNT(*) FROM compliance_rules")
        )).scalar()
        if existing and existing > 0:
            return

        for rule in DEFAULT_RULES:
            await db.execute(
                sql_text(
                    "INSERT INTO compliance_rules (name, description, rule_type, params, severity) "
                    "VALUES (:name, :description, :rule_type, CAST(:rule_params AS jsonb), :severity) "
                    "ON CONFLICT (name) DO NOTHING"
                ).bindparams(
                    name=rule["name"],
                    description=rule["description"],
                    rule_type=rule["rule_type"],
                    rule_params=json.dumps(rule["params"]),
                    severity=rule["severity"],
                )
            )
        await db.commit()
        logger.info("Seeded %d default compliance rules", len(DEFAULT_RULES))
