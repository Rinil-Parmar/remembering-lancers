"""Set default obituary tags to new

Revision ID: 0003_default_obituary_tags
Revises: 0002_add_scrape_state
Create Date: 2026-06-29
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_default_obituary_tags"
down_revision = "0002_add_scrape_state"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE obituary SET tags = 'new' WHERE tags IS NULL")
    op.execute("UPDATE dist_obituary SET tags = 'new' WHERE tags IS NULL")

    op.alter_column(
        "obituary",
        "tags",
        existing_type=sa.String(length=50),
        server_default="new",
        existing_nullable=True,
    )
    op.alter_column(
        "dist_obituary",
        "tags",
        existing_type=sa.String(length=50),
        server_default="new",
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "dist_obituary",
        "tags",
        existing_type=sa.String(length=50),
        server_default=None,
        existing_nullable=True,
    )
    op.alter_column(
        "obituary",
        "tags",
        existing_type=sa.String(length=50),
        server_default=None,
        existing_nullable=True,
    )
