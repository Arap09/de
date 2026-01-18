"""add tenant_invitations table

Revision ID: 965f6675f1c6
Revises: 3fb97b9b8776
Create Date: 2026-01-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "965f6675f1c6"
down_revision = "3fb97b9b8776"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_invitations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "inviter_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Indexes
    op.create_index(
        "ix_tenant_invitations_token",
        "tenant_invitations",
        ["token"],
        unique=True,
    )
    op.create_index(
        "ix_tenant_invitations_tenant_id",
        "tenant_invitations",
        ["tenant_id"],
    )
    op.create_index(
        "ix_tenant_invitations_tenant_email",
        "tenant_invitations",
        ["tenant_id", "email"],
    )
    # Useful for listing pending invites quickly (partial index)
    op.create_index(
        "ix_tenant_invitations_pending",
        "tenant_invitations",
        ["tenant_id"],
        postgresql_where=sa.text("accepted_at IS NULL AND revoked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_invitations_pending", table_name="tenant_invitations")
    op.drop_index("ix_tenant_invitations_tenant_email", table_name="tenant_invitations")
    op.drop_index("ix_tenant_invitations_tenant_id", table_name="tenant_invitations")
    op.drop_index("ix_tenant_invitations_token", table_name="tenant_invitations")
    op.drop_table("tenant_invitations")
