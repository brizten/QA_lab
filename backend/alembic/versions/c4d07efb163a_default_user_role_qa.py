"""set QA as the default user role

Revision ID: c4d07efb163a
Revises: b437911c373c
Create Date: 2026-06-21 16:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c4d07efb163a"
down_revision: Union[str, Sequence[str], None] = "b437911c373c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'QA'::user_role")


def downgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'VIEWER'::user_role")
