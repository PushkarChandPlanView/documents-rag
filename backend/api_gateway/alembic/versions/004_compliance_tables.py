"""Compliance tables + is_admin on users

Revision ID: 004
Revises: 003
Create Date: 2026-06-04
"""
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_admin to users
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false")

    # compliance_rules
    op.execute("""
        CREATE TABLE compliance_rules (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            name        VARCHAR(255) NOT NULL,
            description TEXT,
            rule_type   VARCHAR(50)  NOT NULL,
            params      JSONB        NOT NULL DEFAULT '{}',
            severity    VARCHAR(20)  NOT NULL,
            is_active   BOOLEAN      NOT NULL DEFAULT true,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
    """)
    op.execute("ALTER TABLE compliance_rules ADD CONSTRAINT uq_compliance_rules_name UNIQUE (name)")
    op.execute("CREATE INDEX ix_compliance_rules_is_active ON compliance_rules (is_active)")
    op.execute("CREATE INDEX ix_compliance_rules_rule_type ON compliance_rules (rule_type)")

    # compliance_reports
    op.execute("""
        CREATE TABLE compliance_reports (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID        NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            status      VARCHAR(20) NOT NULL,
            checked_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            rules_hash  VARCHAR(64) NOT NULL,
            is_current  BOOLEAN     NOT NULL DEFAULT true,
            insights    TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_compliance_reports_document_id ON compliance_reports (document_id)")
    op.execute("CREATE INDEX ix_compliance_reports_status ON compliance_reports (status)")
    op.execute("CREATE INDEX ix_compliance_reports_is_current ON compliance_reports (is_current)")

    # compliance_rule_results
    op.execute("""
        CREATE TABLE compliance_rule_results (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            report_id   UUID        NOT NULL REFERENCES compliance_reports(id) ON DELETE CASCADE,
            rule_id     UUID        REFERENCES compliance_rules(id) ON DELETE SET NULL,
            rule_name   VARCHAR(255) NOT NULL,
            rule_type   VARCHAR(50)  NOT NULL,
            severity    VARCHAR(20)  NOT NULL,
            passed      BOOLEAN      NOT NULL,
            detail      TEXT,
            locations   JSONB,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_compliance_rule_results_report_id ON compliance_rule_results (report_id)")
    op.execute("CREATE INDEX ix_compliance_rule_results_rule_id ON compliance_rule_results (rule_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS compliance_rule_results")
    op.execute("DROP TABLE IF EXISTS compliance_reports")
    op.execute("DROP TABLE IF EXISTS compliance_rules")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_admin")
