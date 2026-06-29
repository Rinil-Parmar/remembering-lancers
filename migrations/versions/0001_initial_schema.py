"""Create initial obituary tables

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "obituary",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tags", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("birth_date", sa.String(length=50), nullable=True),
        sa.Column("death_date", sa.String(length=50), nullable=True),
        sa.Column("city", sa.String(length=255), nullable=True),
        sa.Column("province", sa.String(length=255), nullable=True),
        sa.Column("publication_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("obituary_url", sa.String(length=255), nullable=False),
        sa.Column("family_information", sa.Text(), nullable=True),
        sa.Column("donation_information", sa.Text(), nullable=True),
        sa.Column("is_alumni", sa.Boolean(), nullable=True),
        sa.Column("funeral_home", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.UniqueConstraint("obituary_url"),
    )

    op.create_table(
        "dist_obituary",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tags", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("birth_date", sa.String(length=50), nullable=True),
        sa.Column("death_date", sa.String(length=50), nullable=True),
        sa.Column("city", sa.String(length=255), nullable=True),
        sa.Column("province", sa.String(length=255), nullable=True),
        sa.Column("publication_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("obituary_url", sa.String(length=255), nullable=False),
        sa.Column("family_information", sa.Text(), nullable=True),
        sa.Column("donation_information", sa.Text(), nullable=True),
        sa.Column("is_alumni", sa.Boolean(), nullable=True),
        sa.Column("funeral_home", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.UniqueConstraint("obituary_url"),
    )


def downgrade():
    op.drop_table("dist_obituary")
    op.drop_table("obituary")
