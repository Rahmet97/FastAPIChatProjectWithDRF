"""Create new room done

Revision ID: 94f25caf7780
Revises: 33a7f7c8b18a
Create Date: 2024-01-12 17:15:38.244415

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94f25caf7780'
down_revision: Union[str, None] = '33a7f7c8b18a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('room', sa.Column('sender_id', sa.Integer(), nullable=True))
    op.add_column('room', sa.Column('receiver_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'room', 'userdata', ['receiver_id'], ['id'])
    op.create_foreign_key(None, 'room', 'userdata', ['sender_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'room', type_='foreignkey')
    op.drop_constraint(None, 'room', type_='foreignkey')
    op.drop_column('room', 'receiver_id')
    op.drop_column('room', 'sender_id')
    # ### end Alembic commands ###
