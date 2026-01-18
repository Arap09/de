"""add platform invitations + salesperson referral/commission

Revision ID: 0f3a1d2c4b77
Revises: 965f6675f1c6
Create Date: 2026-01-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0f3a1d2c4b77"
down_revision = "965f6675f1c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------
    # platform_memberships
    # ---------------------------
    op.create_table(
        "platform_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", name="uq_platform_memberships_user_id"),
    )
    op.create_index(
        "ix_platform_memberships_role_active",
        "platform_memberships",
        ["role", "is_active"],
        unique=False,
    )

    # ---------------------------
    # platform_invitations
    # ---------------------------
    op.create_table(
        "platform_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("inviter_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("invitee_type", sa.String(length=50), nullable=False),  # platform_admin | salesperson
        sa.Column("platform_role", sa.String(length=50), nullable=True),  # super_admin | platform_admin (only if invitee_type=platform_admin)
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["inviter_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("token", name="uq_platform_invitations_token"),
        sa.CheckConstraint(
            "invitee_type IN ('platform_admin','salesperson')",
            name="ck_platform_invitations_invitee_type",
        ),
        sa.CheckConstraint(
            "(invitee_type = 'platform_admin' AND platform_role IS NOT NULL) OR "
            "(invitee_type = 'salesperson' AND platform_role IS NULL)",
            name="ck_platform_invitations_role_required_by_type",
        ),
    )
    op.create_index("ix_platform_invitations_email", "platform_invitations", ["email"], unique=False)
    op.create_index("ix_platform_invitations_type_status", "platform_invitations", ["invitee_type", "accepted_at", "revoked_at", "expires_at"], unique=False)

    # ---------------------------
    # salesperson_profiles
    # ---------------------------
    op.create_table(
        "salesperson_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("referral_code", sa.String(length=32), nullable=False),
        sa.Column("commission_amount_kes", sa.Integer(), nullable=False, server_default=sa.text("500")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", name="uq_salesperson_profiles_user_id"),
        sa.UniqueConstraint("referral_code", name="uq_salesperson_profiles_referral_code"),
    )
    op.create_index("ix_salesperson_profiles_referral_code", "salesperson_profiles", ["referral_code"], unique=True)
    op.create_index("ix_salesperson_profiles_is_active", "salesperson_profiles", ["is_active"], unique=False)

    # ---------------------------
    # referral_commissions
    # ---------------------------
    op.create_table(
        "referral_commissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("salesperson_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=True),  # attach later when billing tables exist
        sa.Column("billing_event", sa.String(length=50), nullable=False),
        sa.Column("amount_kes", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default=sa.text("'KES'")),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("source_referral_code", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["salesperson_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_referral_commissions_salesperson", "referral_commissions", ["salesperson_user_id"], unique=False)
    op.create_index("ix_referral_commissions_tenant", "referral_commissions", ["tenant_id"], unique=False)
    op.create_index("ix_referral_commissions_status_created", "referral_commissions", ["status", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_referral_commissions_status_created", table_name="referral_commissions")
    op.drop_index("ix_referral_commissions_tenant", table_name="referral_commissions")
    op.drop_index("ix_referral_commissions_salesperson", table_name="referral_commissions")
    op.drop_table("referral_commissions")

    op.drop_index("ix_salesperson_profiles_is_active", table_name="salesperson_profiles")
    op.drop_index("ix_salesperson_profiles_referral_code", table_name="salesperson_profiles")
    op.drop_table("salesperson_profiles")

    op.drop_index("ix_platform_invitations_type_status", table_name="platform_invitations")
    op.drop_index("ix_platform_invitations_email", table_name="platform_invitations")
    op.drop_table("platform_invitations")

    op.drop_index("ix_platform_memberships_role_active", table_name="platform_memberships")
    op.drop_table("platform_memberships")
