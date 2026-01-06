"""Make identity and password fields nullable for magic-code auth

Revision ID: 88aa15a5ff2a
Revises: b25ea3b5625b
Create Date: 2026-01-06
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "88aa15a5ff2a"
down_revision = "b25ea3b5625b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Identity fields
    op.alter_column(
        "users",
        "first_name",
        existing_type=sa.String(length=50),
        nullable=True,
    )

    op.alter_column(
        "users",
        "last_name",
        existing_type=sa.String(length=50),
        nullable=True,
    )

    op.alter_column(
        "users",
        "phone_number",
        existing_type=sa.String(length=20),
        nullable=True,
    )

    op.alter_column(
        "users",
        "country_code",
        existing_type=sa.String(length=5),
        nullable=True,
    )

    # Authentication
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade() -> None:
    # Revert to previous strict requirements
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=False,
    )

    op.alter_column(
        "users",
        "country_code",
        existing_type=sa.String(length=5),
        nullable=False,
    )

    op.alter_column(
        "users",
        "phone_number",
        existing_type=sa.String(length=20),
        nullable=False,
    )

    op.alter_column(
        "users",
        "last_name",
        existing_type=sa.String(length=50),
        nullable=False,
    )

    op.alter_column(
        "users",
        "first_name",
        existing_type=sa.String(length=50),
        nullable=False,
    )
