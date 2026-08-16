"""add user login lockout

Adds per-account brute-force defence on top of the existing per-IP rate
limit:

- ``users.login_failures`` — consecutive failed login attempts. Reset on a
  successful login; when it reaches the threshold the account is locked.
- ``users.locked_until`` — when set to a future timestamp, every login is
  refused (403) until that moment, even with the correct password.

The IP-based limiter stops mass sweeps across many accounts; the lockout
stops a sustained attack on a single account, which an attacker could
otherwise continue from rotating IPs.

Existing accounts start at 0 failures / no lockout, so the deploy changes
nothing for current users.

Revision ID: g7a8b9c0d1e2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-16 17:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g7a8b9c0d1e2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('login_failures', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'users',
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'login_failures')
