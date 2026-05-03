"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-01
"""
from typing import Sequence, Union

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables are managed via SQLAlchemy create_all on startup for Phase 2.
    # Future migrations will use op.create_table / op.add_column etc.
    pass


def downgrade() -> None:
    pass
