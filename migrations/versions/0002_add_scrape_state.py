"""Add scraper resume state table

Revision ID: 0002_add_scrape_state
Revises: 0001_initial_schema
Create Date: 2026-06-28
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_scrape_state"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scrape_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subdomain", sa.String(length=255), nullable=False),
        sa.Column("search_keyword", sa.String(length=255), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("last_processed_url", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "subdomain",
            "search_keyword",
            name="uq_scrape_state_subdomain_keyword",
        ),
    )


def downgrade():
    op.drop_table("scrape_state")
