"""Remove poll date fields

Revision ID: 0001_remove_poll_dates
Revises: 0000_create_tables
Create Date: 2025-02-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_remove_poll_dates"
down_revision = "0000_create_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    table_exists = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = 'polls' LIMIT 1"
        )
    ).scalar()
    if not table_exists:
        return

    starts_at_exists = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = 'polls' "
            "AND column_name = 'starts_at' LIMIT 1"
        )
    ).scalar()
    ends_at_exists = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = 'polls' "
            "AND column_name = 'ends_at' LIMIT 1"
        )
    ).scalar()
    old_index_exists = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() AND table_name = 'polls' "
            "AND index_name = 'idx_polls_active_period' LIMIT 1"
        )
    ).scalar()
    new_index_exists = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() AND table_name = 'polls' "
            "AND index_name = 'idx_polls_active' LIMIT 1"
        )
    ).scalar()

    with op.batch_alter_table("polls") as batch:
        if starts_at_exists:
            batch.drop_column("starts_at")
        if ends_at_exists:
            batch.drop_column("ends_at")
        if old_index_exists:
            batch.drop_index("idx_polls_active_period")
        if not new_index_exists:
            batch.create_index("idx_polls_active", ["is_active"])


def downgrade() -> None:
    bind = op.get_bind()

    table_exists = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = 'polls' LIMIT 1"
        )
    ).scalar()
    if not table_exists:
        return

    starts_at_exists = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = 'polls' "
            "AND column_name = 'starts_at' LIMIT 1"
        )
    ).scalar()
    ends_at_exists = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = 'polls' "
            "AND column_name = 'ends_at' LIMIT 1"
        )
    ).scalar()
    old_index_exists = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() AND table_name = 'polls' "
            "AND index_name = 'idx_polls_active_period' LIMIT 1"
        )
    ).scalar()
    new_index_exists = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() AND table_name = 'polls' "
            "AND index_name = 'idx_polls_active' LIMIT 1"
        )
    ).scalar()

    with op.batch_alter_table("polls") as batch:
        if new_index_exists:
            batch.drop_index("idx_polls_active")
        if not starts_at_exists:
            batch.add_column(sa.Column("starts_at", sa.DATETIME(), nullable=False))
        if not ends_at_exists:
            batch.add_column(sa.Column("ends_at", sa.DATETIME(), nullable=False))
        if not old_index_exists:
            batch.create_index(
                "idx_polls_active_period", ["is_active", "starts_at", "ends_at"]
            )
