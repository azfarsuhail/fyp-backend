"""add profile_log_table

Revision ID: add_profile_log
Revises: 0c1e48cb9649
Create Date: 2026-03-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_profile_log'
down_revision: Union[str, None] = '0c1e48cb9649'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('PROFILE_LOG',
    sa.Column('log_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('field_name', sa.String(), nullable=False),
    sa.Column('old_value', sa.Text(), nullable=True),
    sa.Column('new_value', sa.Text(), nullable=True),
    sa.Column('changed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['USER.user_id'], ),
    sa.PrimaryKeyConstraint('log_id')
    )
    op.create_index(op.f('ix_PROFILE_LOG_log_id'), 'PROFILE_LOG', ['log_id'], unique=False)
    op.create_index(op.f('ix_PROFILE_LOG_user_id'), 'PROFILE_LOG', ['user_id'], unique=False)
    op.create_index(op.f('ix_PROFILE_LOG_changed_at'), 'PROFILE_LOG', ['changed_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_PROFILE_LOG_changed_at'), table_name='PROFILE_LOG')
    op.drop_index(op.f('ix_PROFILE_LOG_user_id'), table_name='PROFILE_LOG')
    op.drop_index(op.f('ix_PROFILE_LOG_log_id'), table_name='PROFILE_LOG')
    op.drop_table('PROFILE_LOG')
