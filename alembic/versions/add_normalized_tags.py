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


def table_exists(table_name):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()

def index_exists_on_table(table_name, index_name):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for idx in inspector.get_indexes(table_name):
        if idx['name'] == index_name:
            return True
    return False

def fk_exists_on_table(table_name, fk_name):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for fk in inspector.get_foreign_keys(table_name):
        if fk['name'] == fk_name:
            return True
    return False

def column_exists_on_table(table_name, column_name):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for col in inspector.get_columns(table_name):
        if col['name'] == column_name:
            return True
    return False

def upgrade() -> None:
    # Create tag categories table
    if not table_exists('tag_categories'):
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
    # else:
    #     # Consider if you need to handle data insertion if table exists but data might be missing
    #     # For now, assuming if table exists, data is also as expected or managed separately
    #     pass


    # Use batch operations for SQLite compatibility
    with op.batch_alter_table('tags') as batch_op:
        if not column_exists_on_table('tags', 'normalized_name'):
            batch_op.add_column(sa.Column('normalized_name', sa.String(), nullable=True))
        if not column_exists_on_table('tags', 'category_id'):
            batch_op.add_column(sa.Column('category_id', sa.String(), nullable=True))
        if not column_exists_on_table('tags', 'is_canonical'):
            batch_op.add_column(sa.Column('is_canonical', sa.Integer(), nullable=False, server_default='1'))
        
        if not index_exists_on_table('tags', 'ix_tags_normalized_name'):
            batch_op.create_index('ix_tags_normalized_name', ['normalized_name'])
        
        # Checking foreign key existence is more complex and varies by backend.
        # For SQLite, Alembic's batch mode might handle re-adding if non-existent,
        # or it might error if it exists. Assuming for now it's safe to try.
        # If this causes issues, a more robust check or try-except block might be needed.
        if not fk_exists_on_table('tags', 'fk_tags_category'):
             batch_op.create_foreign_key('fk_tags_category', 'tag_categories', ['category_id'], ['id'])


    # Create tag variants table
    if not table_exists('tag_variants'):
        op.create_table('tag_variants',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('variant', sa.String(), nullable=False),
            sa.Column('canonical_tag_id', sa.String(), nullable=False),
            sa.ForeignKeyConstraint(['canonical_tag_id'], ['tags.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        if not index_exists_on_table('tag_variants', 'ix_tag_variants_variant'):
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