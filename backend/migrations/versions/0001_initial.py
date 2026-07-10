"""initial tenant-ready schema

Revision ID: 0001
Revises:
Create Date: 2026-07-11

Tenant-ready from the first migration (decision #8): ``tenant_id`` is present on
every top-level table. Mirrors redline_agent/repositories/orm.py.
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "negotiations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("represented_party", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "rounds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column(
            "negotiation_id",
            sa.Integer(),
            sa.ForeignKey("negotiations.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("submitted_by_party", sa.String(), nullable=False),
        sa.Column("blob_uri", sa.String(), nullable=True),
        sa.Column("canonical_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "clauses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column(
            "round_id",
            sa.Integer(),
            sa.ForeignKey("rounds.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("number_label", sa.String(), nullable=True),
        sa.Column("heading", sa.String(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=True),
    )
    op.create_table(
        "clause_lineage",
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
            "prev_clause_id",
            sa.Integer(),
            sa.ForeignKey("clauses.id"),
            nullable=True,
        ),
        sa.Column(
            "curr_clause_id",
            sa.Integer(),
            sa.ForeignKey("clauses.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("similarity", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "align_method", sa.String(), nullable=False, server_default="positional"
        ),
        sa.Column(
            "overridden", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.create_table(
        "changes",
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
            nullable=True,
        ),
        sa.Column(
            "to_round_id",
            sa.Integer(),
            sa.ForeignKey("rounds.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "curr_clause_id",
            sa.Integer(),
            sa.ForeignKey("clauses.id"),
            nullable=True,
        ),
        sa.Column(
            "prev_clause_id",
            sa.Integer(),
            sa.ForeignKey("clauses.id"),
            nullable=True,
        ),
        sa.Column("change_type", sa.String(), nullable=False),
        sa.Column("raw_before", sa.Text(), nullable=True),
        sa.Column("raw_after", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("materiality", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("favored_party", sa.String(), nullable=True),
        sa.Column("risk_flag", sa.Text(), nullable=True),
        sa.Column("interpretation_model", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("changes")
    op.drop_table("clause_lineage")
    op.drop_table("clauses")
    op.drop_table("rounds")
    op.drop_table("negotiations")
