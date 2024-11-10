"""Drop category column from transactions

Revision ID: 0f405298a599
Revises: 1f5a0326711c
Create Date: 2024-11-11 00:58:44.908593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f405298a599'
down_revision: Union[str, None] = '1f5a0326711c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Drop the "category" column from transactions
    op.drop_column('transactions', 'category')

def downgrade():
    # Re-add the "category" column if downgrading
    op.add_column('transactions', sa.Column('category', sa.String, nullable=True))
