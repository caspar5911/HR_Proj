"""add review cycles and reviews tables

Creates the ``review_cycles`` and ``reviews`` tables backing performance
reviews: a cycle is one review period, and a review is one manager's
assessment of one employee within that cycle.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-08-16 06:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'review_cycles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'active'")),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_review_cycles_status', 'review_cycles', ['status'], unique=False)

    op.create_table(
        'reviews',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('cycle_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('reviewer_user_id', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('strengths', sa.Text(), nullable=True),
        sa.Column('improvements', sa.Text(), nullable=True),
        sa.Column('goals', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('shared_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['cycle_id'], ['review_cycles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('cycle_id', 'employee_id', name='uq_review_cycle_employee'),
    )
    op.create_index('ix_reviews_cycle_id', 'reviews', ['cycle_id'], unique=False)
    op.create_index('ix_reviews_employee_id', 'reviews', ['employee_id'], unique=False)
    op.create_index('ix_reviews_reviewer_user_id', 'reviews', ['reviewer_user_id'], unique=False)
    op.create_index('ix_reviews_status', 'reviews', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_reviews_status', table_name='reviews')
    op.drop_index('ix_reviews_reviewer_user_id', table_name='reviews')
    op.drop_index('ix_reviews_employee_id', table_name='reviews')
    op.drop_index('ix_reviews_cycle_id', table_name='reviews')
    op.drop_table('reviews')
    op.drop_index('ix_review_cycles_status', table_name='review_cycles')
    op.drop_table('review_cycles')
