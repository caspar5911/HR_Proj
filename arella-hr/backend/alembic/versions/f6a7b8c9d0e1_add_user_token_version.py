"""add user token version

Adds ``users.token_version``: a counter that is bumped every time a user's
password changes. All JWTs (access and refresh) issued to that user carry the
counter as a ``ver`` claim, and verification rejects any token whose version
lags the user's current one — so changing a password immediately invalidates
every session issued before it.

Existing users start at version 0, which matches the ``ver`` claim (default
0) of tokens already in circulation, so the deploy causes no forced logouts.

Revision ID: f6a7b8c9d0e1
Revises: e6f7a8b9c0d1
Create Date: 2026-08-16 16:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('users', 'token_version')
