"""
Add payout batches and link commissions

Revision ID: 9f625075dc88
Revises: 0f3a1d2c4b77
Create Date: 2026-01-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# --------------------------------------------------
# Revision identifiers, used by Alembic.
# --------------------------------------------------
revision = "9f625075dc88"
down_revision = "0f3a1d2c4b77"
branch_labels = None
depends_on = None


def upgrade():
    # --------------------------------------------------
    # Create payout_batches table
    # --------------------------------------------------
    op.create_table(
        "payout_batches",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "salesperson_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=8),
            nullable=False,
            server_default="KES",
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "total_amount_kes",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "paid_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_payout_batches_salesperson_user_id",
        "payout_batches",
        ["salesperson_user_id"],
    )

    # --------------------------------------------------
    # Link referral_commissions to payout_batches
    # --------------------------------------------------
    op.add_column(
        "referral_commissions",
        sa.Column(
            "payout_batch_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_referral_commissions_payout_batch_id",
        "referral_commissions",
        ["payout_batch_id"],
    )

    op.create_foreign_key(
        "fk_referral_commissions_payout_batch_id",
        "referral_commissions",
        "payout_batches",
        ["payout_batch_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    # --------------------------------------------------
    # Remove referral_commissions → payout_batches link
    # --------------------------------------------------
    op.drop_constraint(
        "fk_referral_commissions_payout_batch_id",
        "referral_commissions",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_referral_commissions_payout_batch_id",
        table_name="referral_commissions",
    )

    op.drop_column("referral_commissions", "payout_batch_id")

    # --------------------------------------------------
    # Drop payout_batches table
    # --------------------------------------------------
    op.drop_index(
        "ix_payout_batches_salesperson_user_id",
        table_name="payout_batches",
    )

    op.drop_table("payout_batches")
