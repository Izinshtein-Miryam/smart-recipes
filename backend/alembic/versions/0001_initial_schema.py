"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-11-04 22:25:40.548853
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('ai_usage_log',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('feature', postgresql.ENUM('fridge_search', 'nutrition', 'adapt', 'chat', name='ai_feature'), nullable=False),
    sa.Column('model', sa.Text(), nullable=False),
    sa.Column('input_tokens', sa.Integer(), nullable=False),
    sa.Column('output_tokens', sa.Integer(), nullable=False),
    sa.Column('response_id', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('recipes',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('lang', postgresql.ENUM('he', 'en', name='lang'), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('servings', sa.Integer(), nullable=False),
    sa.Column('prep_minutes', sa.Integer(), nullable=False),
    sa.Column('difficulty', postgresql.ENUM('easy', 'medium', 'hard', name='difficulty'), nullable=False),
    sa.Column('equipment', postgresql.ARRAY(postgresql.ENUM('oven', 'stovetop', 'one_pot', 'no_cook', name='equipment')), server_default=sa.text("'{}'"), nullable=False),
    sa.Column('kashrut', postgresql.ENUM('meat', 'dairy', 'parve', name='kashrut'), nullable=False),
    sa.Column('ingredients', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('steps', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('nutrition', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('image_path', sa.Text(), nullable=True),
    sa.Column('status', postgresql.ENUM('pending', 'approved', 'rejected', name='recipe_status'), server_default='pending', nullable=False),
    sa.Column('source_recipe_id', sa.UUID(), nullable=True),
    sa.Column('submitter_ip_hash', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['source_recipe_id'], ['recipes.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_recipes_difficulty', 'recipes', ['difficulty'], unique=False)
    op.create_index('ix_recipes_equipment', 'recipes', ['equipment'], unique=False, postgresql_using='gin')
    op.create_index('ix_recipes_kashrut', 'recipes', ['kashrut'], unique=False)
    op.create_index('ix_recipes_prep_minutes', 'recipes', ['prep_minutes'], unique=False)
    op.create_index('ix_recipes_status', 'recipes', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_recipes_status', table_name='recipes')
    op.drop_index('ix_recipes_prep_minutes', table_name='recipes')
    op.drop_index('ix_recipes_kashrut', table_name='recipes')
    op.drop_index('ix_recipes_equipment', table_name='recipes', postgresql_using='gin')
    op.drop_index('ix_recipes_difficulty', table_name='recipes')
    op.drop_table('recipes')
    op.drop_table('ai_usage_log')
    for name in ('ai_feature', 'recipe_status', 'kashrut', 'equipment', 'difficulty', 'lang'):
        op.execute(f'DROP TYPE IF EXISTS {name}')
