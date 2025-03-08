"""add normalized tags

Revision ID: add_normalized_tags
Revises: 07c2d02b6935
Create Date: 2025-03-06 15:44:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from alembic.context import get_context

# revision identifiers, used by Alembic.
revision: str = 'add_normalized_tags'
down_revision: Union[str, None] = '07c2d02b6935'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create tag categories table
    op.create_table('tag_categories',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Insert default categories
    op.execute("""
    INSERT INTO tag_categories (id, name, description) VALUES
    ('metal', 'Metal', 'Metal and related subgenres'),
    ('rock', 'Rock', 'Rock and related subgenres'), 
    ('fusion', 'Fusion', 'Fusion genres including jazz fusion'),
    ('experimental', 'Experimental', 'Experimental and avant-garde'),
    ('other', 'Other', 'Uncategorized tags')
    """)

    # Use batch operations for SQLite compatibility
    with op.batch_alter_table('tags') as batch_op:
        batch_op.add_column(sa.Column('normalized_name', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('category_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('is_canonical', sa.Integer(), nullable=False, server_default='1'))
        batch_op.create_index('ix_tags_normalized_name', ['normalized_name'])
        batch_op.create_foreign_key('fk_tags_category', 'tag_categories', ['category_id'], ['id'])

    # Create tag variants table
    op.create_table('tag_variants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('variant', sa.String(), nullable=False),
        sa.Column('canonical_tag_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['canonical_tag_id'], ['tags.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tag_variants_variant', 'tag_variants', ['variant'])

def downgrade() -> None:
    op.drop_index('ix_tag_variants_variant')
    op.drop_table('tag_variants')
    
    with op.batch_alter_table('tags') as batch_op:
        batch_op.drop_constraint('fk_tags_category', type_='foreignkey')
        batch_op.drop_index('ix_tags_normalized_name')
        batch_op.drop_column('is_canonical')
        batch_op.drop_column('category_id')
        batch_op.drop_column('normalized_name')
    
    op.drop_table('tag_categories')