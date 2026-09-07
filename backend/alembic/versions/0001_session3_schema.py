"""Session 3 schema: party, factions, world events, custom rulesets + additive columns.

This migration adds the Session 3 tables and additive columns. Because the
application also auto-creates tables via ``init_db()`` at startup (and the
lightweight migration helper backfills columns on SQLite), all operations here
are written defensively so re-applying against an already-current database is a
no-op.

Revision ID: 0001_session3_schema
Revises:
Create Date: Session 3
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_session3_schema"
down_revision = None
branch_labels = None
depends_on = None


def _inspector():
    bind = op.get_bind()
    return sa.inspect(bind)


def _has_table(name: str) -> bool:
    return name in _inspector().get_table_names()


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return column in {c["name"] for c in _inspector().get_columns(table)}


def upgrade() -> None:
    # --- Additive columns on existing tables --------------------------------
    if _has_table("campaigns"):
        if not _has_column("campaigns", "active_combat"):
            op.add_column("campaigns", sa.Column("active_combat", sa.JSON(), nullable=True))
        if not _has_column("campaigns", "current_session_id"):
            op.add_column(
                "campaigns", sa.Column("current_session_id", sa.String(length=36), nullable=True)
            )

    if _has_table("characters"):
        if not _has_column("characters", "player_name"):
            op.add_column(
                "characters", sa.Column("player_name", sa.String(length=200), nullable=True)
            )

    if _has_table("memories"):
        if not _has_column("memories", "tags"):
            op.add_column("memories", sa.Column("tags", sa.JSON(), nullable=True))
        if not _has_column("memories", "embedding"):
            op.add_column("memories", sa.Column("embedding", sa.JSON(), nullable=True))
        if not _has_column("memories", "source_action_id"):
            op.add_column(
                "memories", sa.Column("source_action_id", sa.String(length=36), nullable=True)
            )

    if _has_table("sessions"):
        if not _has_column("sessions", "key_events"):
            op.add_column("sessions", sa.Column("key_events", sa.JSON(), nullable=True))
        if not _has_column("sessions", "player_actions_count"):
            op.add_column(
                "sessions",
                sa.Column("player_actions_count", sa.Integer(), nullable=False, server_default="0"),
            )
        if not _has_column("sessions", "xp_awarded"):
            op.add_column("sessions", sa.Column("xp_awarded", sa.Integer(), nullable=True))

    # --- New tables ---------------------------------------------------------
    if not _has_table("party_members"):
        op.create_table(
            "party_members",
            sa.Column("campaign_id", sa.String(length=36), nullable=False),
            sa.Column("character_id", sa.String(length=36), nullable=False),
            sa.Column("joined_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("campaign_id", "character_id"),
        )

    if not _has_table("factions"):
        op.create_table(
            "factions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("campaign_id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("goals", sa.JSON(), nullable=True),
            sa.Column("resources", sa.Integer(), nullable=True),
            sa.Column("influence", sa.Integer(), nullable=True),
            sa.Column("disposition", sa.String(length=40), nullable=True),
            sa.Column("relationships", sa.JSON(), nullable=True),
            sa.Column("autonomy_level", sa.String(length=40), nullable=True),
            sa.Column("last_acted_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_factions_campaign_id", "factions", ["campaign_id"])

    if not _has_table("world_events"):
        op.create_table(
            "world_events",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("campaign_id", sa.String(length=36), nullable=False),
            sa.Column("faction_id", sa.String(length=36), nullable=True),
            sa.Column("event_type", sa.String(length=80), nullable=True),
            sa.Column("title", sa.String(length=300), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("impact", sa.JSON(), nullable=True),
            sa.Column("is_revealed", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["faction_id"], ["factions.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_world_events_campaign_id", "world_events", ["campaign_id"])

    if not _has_table("custom_rulesets"):
        op.create_table(
            "custom_rulesets",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("display_name", sa.String(length=200), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("dice_formula", sa.String(length=40), nullable=True),
            sa.Column("roll_mode", sa.String(length=40), nullable=True),
            sa.Column("success_threshold", sa.Integer(), nullable=True),
            sa.Column("attributes", sa.JSON(), nullable=True),
            sa.Column("resources", sa.JSON(), nullable=True),
            sa.Column("skills", sa.JSON(), nullable=True),
            sa.Column("prompt_instructions", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_custom_rulesets_name", "custom_rulesets", ["name"], unique=True)


def downgrade() -> None:
    for tbl, idx in [
        ("custom_rulesets", "ix_custom_rulesets_name"),
        ("world_events", "ix_world_events_campaign_id"),
        ("factions", "ix_factions_campaign_id"),
    ]:
        if _has_table(tbl):
            try:
                op.drop_index(idx, table_name=tbl)
            except Exception:  # noqa: BLE001
                pass
            op.drop_table(tbl)
    if _has_table("party_members"):
        op.drop_table("party_members")

    for col in ("xp_awarded", "player_actions_count", "key_events"):
        if _has_column("sessions", col):
            op.drop_column("sessions", col)
    for col in ("source_action_id", "embedding", "tags"):
        if _has_column("memories", col):
            op.drop_column("memories", col)
    if _has_column("characters", "player_name"):
        op.drop_column("characters", "player_name")
    for col in ("current_session_id", "active_combat"):
        if _has_column("campaigns", col):
            op.drop_column("campaigns", col)
