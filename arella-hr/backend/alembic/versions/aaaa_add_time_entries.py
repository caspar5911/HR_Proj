"""add time entries table

Creates the ``time_entries`` table used by the attendance/time-tracking
feature: one row per employee per work day (clock in, clock out, breaks).

Revision ID: a7b8c9d0e1f2
Revises: d4e5f6a7b8c9
Create Date: 2026-08-16 01:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'time_entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('work_date', sa.Date(), nullable=False),
        sa.Column('clock_in', sa.Time(), nullable=False),
        sa.Column('clock_out', sa.Time(), nullable=True),
        sa.Column('breaks_minutes', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('employee_id', 'work_date', name='uq_time_entry_emp_date'),
    )
    op.create_index('ix_time_entries_employee_id', 'time_entries', ['employee_id'], unique=False)
    op.create_index('ix_time_entries_work_date', 'time_entries', ['work_date'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_time_entries_work_date', table_name='time_entries')
    op.drop_index('ix_time_entries_employee_id', table_name='time_entries')
    op.drop_table('time_entries')
