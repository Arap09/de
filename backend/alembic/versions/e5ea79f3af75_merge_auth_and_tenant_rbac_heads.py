"""Merge auth and tenant RBAC heads

Revision ID: e5ea79f3af75
Revises: 5404af87eaf7, 83c728a999e2
Create Date: 2026-01-11 14:44:32.607321
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5ea79f3af75'
down_revision: Union[str, Sequence[str], None] = ('5404af87eaf7', '83c728a999e2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge revision: no schema changes, ensure enum exists safely."""
    # Ensure tenant_role_enum exists but do not error if already present
    tenant_role_enum = postgresql.ENUM(
        "OWNER",
        "ADMIN",
        "MANAGER",
        "AGENT",
        name="tenant_role_enum",
    )
    tenant_role_enum.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    """Downgrade is a no-op for merge revision."""
    # No schema changes here; we do not drop enum in a merge revision
    pass
