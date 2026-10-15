"""initial schema: analysis_runs table

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-15 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.models.base import GUID

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'analysis_runs',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('ticker', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('result_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysis_runs_ticker'), 'analysis_runs', ['ticker'], unique=False)
    op.create_index(op.f('ix_analysis_runs_status'), 'analysis_runs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_analysis_runs_status'), table_name='analysis_runs')
    op.drop_index(op.f('ix_analysis_runs_ticker'), table_name='analysis_runs')
    op.drop_table('analysis_runs')
