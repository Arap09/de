"""Add tenants and tenant memberships for RBAC

Revision ID: 83c728a999e2
Revises: e15df335adb8
Create Date: 2026-01-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "83c728a999e2"
down_revision = "e15df335adb8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --------------------------------------------------
    # Tenant role enum (safe creation)
    # --------------------------------------------------
    tenant_role_enum = postgresql.ENUM(
        "OWNER",
        "ADMIN",
        "MANAGER",
        "AGENT",
        name="tenant_role_enum",
    )
    tenant_role_enum.create(op.get_bind(), checkfirst=True)

    # --------------------------------------------------
    # Tenants table
    # --------------------------------------------------
    op.create_table(
        "tenants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # --------------------------------------------------
    # Tenant memberships table
    # --------------------------------------------------
    op.create_table(
        "tenant_memberships",
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
        sa.Column(
            "role",
            sa.Enum(
                "OWNER",
                "ADMIN",
                "MANAGER",
                "AGENT",
                name="tenant_role_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id",
            "tenant_id",
            name="uq_user_tenant_membership",
        ),
    )


def downgrade() -> None:
    op.drop_table("tenant_memberships")
    op.drop_table("tenants")

    tenant_role_enum = postgresql.ENUM(
        "OWNER",
        "ADMIN",
        "MANAGER",
        "AGENT",
        name="tenant_role_enum",
    )
    tenant_role_enum.drop(op.get_bind(), checkfirst=True)
