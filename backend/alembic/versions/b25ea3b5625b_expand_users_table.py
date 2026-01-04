"""expand users table

Revision ID: b25ea3b5625b
Revises: 5771b55a43ec
Create Date: 2026-01-03 11:23:06.119022
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b25ea3b5625b"
down_revision: Union[str, Sequence[str], None] = "5771b55a43ec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --------------------------------------------------
    # Ensure UUID generation support
    # --------------------------------------------------
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # --------------------------------------------------
    # Add new UUID column (temporary)
    # --------------------------------------------------
    op.add_column(
        "users",
        sa.Column(
            "id_uuid",
            postgresql.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )

    # --------------------------------------------------
    # Drop old PK constraint
    # --------------------------------------------------
    op.drop_constraint("users_pkey", "users", type_="primary")

    # --------------------------------------------------
    # Drop old integer id
    # --------------------------------------------------
    op.drop_column("users", "id")

    # --------------------------------------------------
    # Rename UUID column → id
    # --------------------------------------------------
    op.alter_column("users", "id_uuid", new_column_name="id")

    # --------------------------------------------------
    # Recreate primary key
    # --------------------------------------------------
    op.create_primary_key("users_pkey", "users", ["id"])

    # --------------------------------------------------
    # Add remaining columns (safe defaults)
    # --------------------------------------------------
    op.add_column("users", sa.Column("first_name", sa.String(50), nullable=False, server_default=""))
    op.add_column("users", sa.Column("last_name", sa.String(50), nullable=False, server_default=""))
    op.add_column("users", sa.Column("phone_number", sa.String(20), nullable=False, server_default=""))
    op.add_column("users", sa.Column("country_code", sa.String(5), nullable=False, server_default=""))
    op.add_column("users", sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("role", sa.String(50), nullable=False, server_default="client"))

    tier_enum = postgresql.ENUM(
        "sungura",
        "swara",
        "ndovu",
        name="tierenum",
        create_type=False,
    )

    op.add_column(
        "users",
        sa.Column("tier", tier_enum, nullable=False, server_default="sungura"),
    )

    op.add_column("users", sa.Column("trial_starts_at", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("trial_expires_at", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("referral_code", sa.String(12), nullable=False, server_default=""))
    op.add_column("users", sa.Column("referred_by_id", postgresql.UUID(), nullable=True))
    op.add_column("users", sa.Column("accepts_notifications", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("users", sa.Column("accepted_terms", sa.Boolean(), nullable=False, server_default=sa.false()))

    # --------------------------------------------------
    # Constraints / indexes
    # --------------------------------------------------
    op.create_unique_constraint(None, "users", ["email"])
    op.create_unique_constraint(None, "users", ["phone_number"])
    op.create_index("ix_users_referral_code", "users", ["referral_code"], unique=True)
    op.create_foreign_key(None, "users", "users", ["referred_by_id"], ["id"])

    # --------------------------------------------------
    # Cleanup defaults
    # --------------------------------------------------
    for col in (
        "first_name",
        "last_name",
        "phone_number",
        "country_code",
        "is_email_verified",
        "role",
        "tier",
        "referral_code",
        "accepts_notifications",
        "accepted_terms",
    ):
        op.alter_column("users", col, server_default=None)


def downgrade() -> None:
    raise RuntimeError("Downgrade not supported for UUID primary key migration")
