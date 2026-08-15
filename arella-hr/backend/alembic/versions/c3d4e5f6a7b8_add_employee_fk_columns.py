"""add employee fk columns

Adds the auth link (employees.user_id) and the normalized department
reference (employees.department_id) that the ORM relationships and the
leave/payroll services depend on.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-15 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Link employee directory records to auth users.
    op.add_column('employees', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index('ix_employees_user_id', 'employees', ['user_id'], unique=False)
    op.create_foreign_key(
        'fk_employees_user_id', 'employees', 'users',
        ['user_id'], ['id'], ondelete='SET NULL',
    )

    # Normalize the department reference alongside the denormalized string.
    op.add_column('employees', sa.Column('department_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_employees_department_id', 'employees', 'departments',
        ['department_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_employees_department_id', 'employees', type_='foreignkey')
    op.drop_column('employees', 'department_id')

    op.drop_constraint('fk_employees_user_id', 'employees', type_='foreignkey')
    op.drop_index('ix_employees_user_id', table_name='employees')
    op.drop_column('employees', 'user_id')
