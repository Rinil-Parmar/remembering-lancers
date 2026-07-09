"""Add scraper run history table

Revision ID: 0004_add_scrape_runs
Revises: 0003_default_obituary_tags
Create Date: 2026-07-01
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_add_scrape_runs"
down_revision = "0003_default_obituary_tags"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("city", sa.String(length=255), nullable=True),
        sa.Column("search_keyword", sa.String(length=255), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column(
            "saved_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "skipped_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "duplicate_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table("scrape_runs")
