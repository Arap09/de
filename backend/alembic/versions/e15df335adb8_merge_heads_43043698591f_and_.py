"""Merge heads 43043698591f and 88aa15a5ff2a

Revision ID: e15df335adb8
Revises: 43043698591f, 88aa15a5ff2a
Create Date: 2026-01-06 10:37:02.963830

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e15df335adb8'
down_revision: Union[str, Sequence[str], None] = ('43043698591f', '88aa15a5ff2a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
