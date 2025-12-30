"""Create initial poll tables

Revision ID: 0000_create_tables
Revises: None
Create Date: 2025-02-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = "0000_create_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "polls",
        sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True),
        sa.Column("title", sa.VARCHAR(length=200), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("is_active", mysql.SMALLINT(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            mysql.DATETIME(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            mysql.DATETIME(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("idx_polls_active", "polls", ["is_active"])

    op.create_table(
        "poll_options",
        sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True),
        sa.Column(
            "poll_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("polls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.VARCHAR(length=200), nullable=False),
        sa.Column("sort_order", mysql.INTEGER(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            mysql.DATETIME(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("idx_poll_options_poll", "poll_options", ["poll_id", "sort_order"])

    op.create_table(
        "votes",
        sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True),
        sa.Column(
            "poll_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("polls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "option_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("poll_options.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("voter_token", sa.VARCHAR(length=36), nullable=False),
        sa.Column(
            "created_at",
            mysql.DATETIME(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_unique_constraint("uniq_vote_per_poll", "votes", ["poll_id", "voter_token"])
    op.create_index("idx_votes_poll", "votes", ["poll_id"])
    op.create_index("idx_votes_option", "votes", ["option_id"])


def downgrade() -> None:
    op.drop_index("idx_votes_option", table_name="votes")
    op.drop_index("idx_votes_poll", table_name="votes")
    op.drop_constraint("uniq_vote_per_poll", "votes", type_="unique")
    op.drop_table("votes")

    op.drop_index("idx_poll_options_poll", table_name="poll_options")
    op.drop_table("poll_options")

    op.drop_index("idx_polls_active", table_name="polls")
    op.drop_table("polls")
