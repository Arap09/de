from alembic import op
import sqlalchemy as sa

# --------------------------------------------------
# Alembic revision identifiers
# --------------------------------------------------
revision = "28851f93da54"
down_revision = "4c9ec3d09dda"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "tenants",
        sa.Column("referral_code_used", sa.String(length=12), nullable=True)
    )


def downgrade():
    op.drop_column("tenants", "referral_code_used")

