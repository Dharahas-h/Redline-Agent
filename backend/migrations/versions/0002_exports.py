"""exports table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-11

Records each generated tracked-changes .docx (latest round vs prior). The bytes
live in the blob store; the row points at them by blob_uri. Tenant-ready
(decision #8). Mirrors redline_agent/repositories/orm.py.
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exports",
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
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("blob_uri", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("exports")
