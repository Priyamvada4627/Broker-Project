"""add_performance_indexes

Revision ID: d0281fd0b01c
Revises: 99bbd1de86fa
Create Date: 2026-11-09 23:49:01.578799

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0281fd0b01c'
down_revision: Union[str, Sequence[str], None] = '99bbd1de86fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Location city index for location searches and deduplication
    op.create_index('ix_locations_city', 'locations', ['city'], unique=False)

    # 2. Foreign keys and search indexes on properties
    op.create_index('ix_properties_seller_id', 'properties', ['seller_id'], unique=False)
    op.create_index('ix_properties_location_id', 'properties', ['location_id'], unique=False)
    op.create_index('ix_properties_agent_id', 'properties', ['agent_id'], unique=False)
    op.create_index('ix_properties_search', 'properties', ['is_available', 'purpose', 'price'], unique=False)

    # 3. Agent workload lookup on deals
    op.create_index('ix_deals_agent_status', 'deals', ['agent_id', 'status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_deals_agent_status', table_name='deals')
    op.drop_index('ix_properties_search', table_name='properties')
    op.drop_index('ix_properties_agent_id', table_name='properties')
    op.drop_index('ix_properties_location_id', table_name='properties')
    op.drop_index('ix_properties_seller_id', table_name='properties')
    op.drop_index('ix_locations_city', table_name='locations')
