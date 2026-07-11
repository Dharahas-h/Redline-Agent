"""structural_alerts table + rounds.table_signatures

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-11

Adds the detect-and-flag structural alerts surfaced alongside the change feed
(defined-term definition changes and table changes; decision #6), plus the
per-round table signatures those table alerts are computed from (tables are
excluded from canonical_text). Structural alerts are not changes — the
deterministic differ still owns the change set (decision #1). Tenant-ready
(decision #8). Mirrors redline_agent/repositories/orm.py.
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rounds",
        sa.Column("table_signatures", sa.Text(), nullable=True),
    )
    op.create_table(
        "structural_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column(
            "negotiation_id",
            sa.Integer(),
            sa.ForeignKey("negotiations.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "from_round_id",
            sa.Integer(),
            sa.ForeignKey("rounds.id"),
            nullable=False,
        ),
        sa.Column(
            "to_round_id",
            sa.Integer(),
            sa.ForeignKey("rounds.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("alert_type", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("affected_clause_count", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("structural_alerts")
    op.drop_column("rounds", "table_signatures")
