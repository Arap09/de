"""add user_consents table

Revision ID: 3fb97b9b8776
Revises: 28851f93da54
Create Date: 2026-01-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "3fb97b9b8776"
down_revision = "28851f93da54"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_consents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("terms_version", sa.String(), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "user_id",
            "tenant_id",
            "role",
            "terms_version",
            name="uq_user_consent_role_terms",
        ),
    )


def downgrade():
    op.drop_table("user_consents")
    