from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '1f5a0326711c'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Get a database connection
    conn = op.get_bind()
    
    # Insert "Uncategorized" category if it doesn't exist
    conn.execute(text("INSERT INTO categories (name) VALUES ('uncategorized')"))
    
    # Retrieve the ID of the "Uncategorized" category
    uncategorized_id = conn.execute(text("SELECT id FROM categories WHERE name = 'uncategorized'")).scalar()
    
    # Add category_id column with a default value of "Uncategorized" ID
    op.add_column('transactions', sa.Column('category_id', sa.Integer(), nullable=False, server_default=str(uncategorized_id)))

    # Note: We skip dropping the default due to SQLite's limitations

def downgrade():
    # Reverse the changes made in the upgrade
    op.drop_column('transactions', 'category_id')
    conn = op.get_bind()
    conn.execute(text("DELETE FROM categories WHERE name = 'uncategorized'"))
