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
    # The column 'year' likely doesn't exist at this point,
    # as it was probably handled by a migration in the other merged branch.
    # Skipping this operation.
    pass

def downgrade():
    # Correspondingly, skipping the downgrade operation.
    pass