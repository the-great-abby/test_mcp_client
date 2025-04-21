"""add username column

Revision ID: add_username_column
Revises: 3fd9a38a10c3
Create Date: 2024-03-19 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_username_column'
down_revision: str = '3fd9a38a10c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add username column with unique constraint
    op.add_column('users',
        sa.Column('username', sa.String(), nullable=True)
    )
    # Make username unique after adding it
    op.create_unique_constraint('uq_users_username', 'users', ['username'])
    
    # Update existing users to have a username based on their email
    # This is needed since the model now expects username to be present
    op.execute("""
        UPDATE users 
        SET username = SPLIT_PART(email, '@', 1) 
        WHERE username IS NULL
    """)
    
    # Now make username required for future inserts
    op.alter_column('users', 'username',
        existing_type=sa.String(),
        nullable=False
    )

def downgrade() -> None:
    # Remove the unique constraint first
    op.drop_constraint('uq_users_username', 'users', type_='unique')
    # Then remove the column
    op.drop_column('users', 'username') 