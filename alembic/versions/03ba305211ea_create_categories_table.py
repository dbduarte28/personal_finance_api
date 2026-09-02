"""create categories table

Revision ID: 03ba305211ea
Revises: 81f74338ffac
Create Date: 2026-09-02 12:57:36.438246

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "03ba305211ea"
down_revision: str | None = "81f74338ffac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "type",
            sa.Enum("income", "expense", name="transaction_type"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "name",
            name="uq_categories_user_id_name",
        ),
    )


def downgrade() -> None:
    op.drop_table("categories")
    sa.Enum(name="transaction_type").drop(op.get_bind(), checkfirst=True)
