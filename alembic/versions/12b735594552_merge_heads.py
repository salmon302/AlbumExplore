"""merge heads

Revision ID: 12b735594552
Revises: 07c2d02b6935, add_normalized_tags
Create Date: 2025-03-08 00:45:55.902704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12b735594552'
down_revision: Union[str, None] = ('07c2d02b6935', 'add_normalized_tags')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
