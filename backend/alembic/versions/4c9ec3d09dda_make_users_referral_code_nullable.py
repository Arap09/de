from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = "4c9ec3d09dda"
down_revision = "e5ea79f3af75"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "users",
        "referral_code",
        existing_type=sa.String(),
        nullable=True,
    )


def downgrade():
    op.alter_column(
        "users",
        "referral_code",
        existing_type=sa.String(),
        nullable=False,
    )
