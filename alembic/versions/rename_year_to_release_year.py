"""rename year to release_year

Revision ID: rename_year_to_release_year
Revises: 07c2d02b6935
Create Date: 2025-03-09 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'rename_year_to_release_year'
down_revision = '07c2d02b6935'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('albums') as batch_op:
        batch_op.alter_column('year',
                            new_column_name='release_year',
                            existing_type=sa.Integer())

def downgrade():
    with op.batch_alter_table('albums') as batch_op:
        batch_op.alter_column('release_year',
                            new_column_name='year',
                            existing_type=sa.Integer())