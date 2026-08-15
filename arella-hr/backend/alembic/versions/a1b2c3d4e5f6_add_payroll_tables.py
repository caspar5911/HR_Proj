"""add payroll tables

Revision ID: a1b2c3d4e5f6
Revises: fcb3de592fd2
Create Date: 2026-08-15 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'fcb3de592fd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Deduction rules
    op.create_table('deduction_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('deduction_type', sa.String(length=20), nullable=False),
        sa.Column('value', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_deduction_rules_name'), 'deduction_rules', ['name'], unique=True)

    # Payroll runs
    op.create_table('payroll_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payroll_runs_status'), 'payroll_runs', ['status'], unique=False)

    # Payroll entries
    op.create_table('payroll_entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('payroll_run_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('gross_salary', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('bonuses', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('deductions', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('net_pay', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['payroll_run_id'], ['payroll_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_payroll_entries_payroll_run_employee', 'payroll_entries', ['payroll_run_id', 'employee_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_payroll_entries_payroll_run_employee', table_name='payroll_entries')
    op.drop_table('payroll_entries')
    op.drop_index(op.f('ix_payroll_runs_status'), table_name='payroll_runs')
    op.drop_table('payroll_runs')
    op.drop_index(op.f('ix_deduction_rules_name'), table_name='deduction_rules')
    op.drop_table('deduction_rules')