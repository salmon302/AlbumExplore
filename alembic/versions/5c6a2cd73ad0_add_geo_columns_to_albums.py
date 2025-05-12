"""add_geo_columns_to_albums

Revision ID: 5c6a2cd73ad0
Revises: ef823beee523
Create Date: 2025-05-11 18:15:21.611886

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c6a2cd73ad0'
down_revision: Union[str, None] = 'ef823beee523'  # This should be the merge_heads_manual revision
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists_on_table(table_name, column_name):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for col in inspector.get_columns(table_name):
        if col['name'] == column_name:
            return True
    return False

def upgrade() -> None:
    if not column_exists_on_table('albums', 'latitude'):
        op.add_column('albums', sa.Column('latitude', sa.Float(), nullable=True))
    if not column_exists_on_table('albums', 'longitude'):
        op.add_column('albums', sa.Column('longitude', sa.Float(), nullable=True))
    if not column_exists_on_table('albums', 'x'):
        op.add_column('albums', sa.Column('x', sa.Float(), nullable=True))
    if not column_exists_on_table('albums', 'y'):
        op.add_column('albums', sa.Column('y', sa.Float(), nullable=True))


def downgrade() -> None:
    # For downgrades, it's generally safer to assume the column might exist.
    # If it doesn't, op.drop_column might error or do nothing depending on backend/config.
    # For robustness, similar checks could be added, but often not as critical as for upgrades.
    if column_exists_on_table('albums', 'y'):
        op.drop_column('albums', 'y')
    if column_exists_on_table('albums', 'x'):
        op.drop_column('albums', 'x')
    if column_exists_on_table('albums', 'longitude'):
        op.drop_column('albums', 'longitude')
    if column_exists_on_table('albums', 'latitude'):
        op.drop_column('albums', 'latitude')
