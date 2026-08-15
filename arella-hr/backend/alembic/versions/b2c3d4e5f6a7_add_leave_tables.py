"""add leave tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-15 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Departments
    op.create_table('departments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('manager_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['manager_id'], ['employees.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_departments_name'), 'departments', ['name'], unique=True)

    # Leave types
    op.create_table('leave_types',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('days_per_year', sa.Numeric(precision=5, scale=1), nullable=False, server_default='25.0'),
        sa.Column('max_consecutive_days', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('is_paid', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('color', sa.String(length=7), nullable=False, server_default='#3b82f6'),
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Leave balances
    op.create_table('leave_balances',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('leave_type_id', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('allocated', sa.Numeric(precision=6, scale=1), nullable=False, server_default='0'),
        sa.Column('used', sa.Numeric(precision=6, scale=1), nullable=False, server_default='0'),
        sa.Column('carried_over', sa.Numeric(precision=6, scale=1), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['leave_type_id'], ['leave_types.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'leave_type_id', 'year', name='uq_employee_leave_year')
    )
    op.create_index('ix_leave_balance_employee_year', 'leave_balances', ['employee_id', 'year'], unique=False)

    # Leave requests
    op.create_table('leave_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('leave_type_id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('days_requested', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('manager_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['leave_type_id'], ['leave_types.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_leave_request_employee_status', 'leave_requests', ['employee_id', 'status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_leave_request_employee_status', table_name='leave_requests')
    op.drop_table('leave_requests')
    op.drop_index('ix_leave_balance_employee_year', table_name='leave_balances')
    op.drop_table('leave_balances')
    op.drop_table('leave_types')
    op.drop_index(op.f('ix_departments_name'), table_name='departments')
    op.drop_table('departments')