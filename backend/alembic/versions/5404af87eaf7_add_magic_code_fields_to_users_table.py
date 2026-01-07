"""Add magic_code fields to users table

Revision ID: 5404af87eaf7
Revises: e15df335adb8
Create Date: 2026-01-07 08:42:43.736743

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5404af87eaf7'
down_revision: Union[str, Sequence[str], None] = 'e15df335adb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column('magic_code', sa.String(length=6), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('magic_code_expires_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'magic_code')
    op.drop_column('users', 'magic_code_expires_at')
