"""Add enforcement column to compliance_rule_results

Revision ID: 005
Revises: 004
Create Date: 2026-06-06
"""
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE compliance_rule_results "
        "ADD COLUMN IF NOT EXISTS enforcement VARCHAR(20) NOT NULL DEFAULT 'advisory'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_compliance_rule_results_enforcement "
        "ON compliance_rule_results (enforcement)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_compliance_rule_results_enforcement")
    op.execute("ALTER TABLE compliance_rule_results DROP COLUMN IF EXISTS enforcement")
