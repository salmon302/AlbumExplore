"""merge_heads_manual

Revision ID: ef823beee523
Revises: 12b735594552, rename_year_to_release_year
Create Date: 2025-05-11 18:14:58.732760

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef823beee523'
down_revision: Union[str, None] = ('12b735594552', 'rename_year_to_release_year')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
