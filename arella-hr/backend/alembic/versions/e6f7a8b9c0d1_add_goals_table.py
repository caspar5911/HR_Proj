"""add goals table

Creates the ``goals`` table backing OKR-style objectives: one goal is one
objective owned by an employee for a labeled period (e.g. "H2 2026"), with a
0-100 progress value and an active/completed/archived lifecycle.

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-08-16 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'goals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('period', sa.String(20), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'active'")),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_goals_employee_id', 'goals', ['employee_id'], unique=False)
    op.create_index('ix_goals_period', 'goals', ['period'], unique=False)
    op.create_index('ix_goals_status', 'goals', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_goals_status', table_name='goals')
    op.drop_index('ix_goals_period', table_name='goals')
    op.drop_index('ix_goals_employee_id', table_name='goals')
    op.drop_table('goals')
