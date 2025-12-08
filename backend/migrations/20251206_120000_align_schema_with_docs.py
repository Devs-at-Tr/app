from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251206_120000_align_schema_with_docs"
down_revision = "20251201_193000_user_status_logs"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name.lower()
    inspector = sa.inspect(conn)
    now_sql = "CURRENT_TIMESTAMP" if dialect == "sqlite" else "NOW()"

    def _column_exists(table: str, column: str) -> bool:
        return column in {col["name"] for col in inspector.get_columns(table)}

    def _drop_column_if_exists(table: str, column: str) -> None:
        if _column_exists(table, column):
            op.drop_column(table, column)

    def _drop_index_if_exists(table: str, index_name: str) -> None:
        indexes = {ix["name"] for ix in inspector.get_indexes(table)}
        if index_name in indexes:
            op.drop_index(index_name, table_name=table)

    def _drop_unique_indexes_on_column(table: str, column: str) -> None:
        for ix in inspector.get_indexes(table):
            if ix.get("unique") and column in ix.get("column_names", []):
                op.drop_index(ix["name"], table_name=table)

    def _ensure_index(table: str, index_name: str, columns: list[str]) -> None:
        indexes = inspector.get_indexes(table)
        if any(set(ix.get("column_names") or []) == set(columns) for ix in indexes):
            return
        if index_name not in {ix["name"] for ix in indexes}:
            op.create_index(index_name, table, columns)

    def _now_default():
        # Keep CURRENT_TIMESTAMP for cross-dialect compatibility (MySQL/Postgres/SQLite).
        return sa.text("CURRENT_TIMESTAMP")

    # 1) Clean up instagram_messages extras
    _drop_index_if_exists("instagram_messages", "uq_instagram_messages_message_id")
    _drop_unique_indexes_on_column("instagram_messages", "message_id")
    _drop_column_if_exists("instagram_messages", "message_id")
    _drop_column_if_exists("instagram_messages", "raw_payload_json")

    # 2) Drop legacy tables if present
    for legacy_table in ("messages", "ig_messages"):
        conn.execute(sa.text(f"DROP TABLE IF EXISTS {legacy_table}"))

    # 3) Add missing index on instagram_accounts.user_id
    _ensure_index("instagram_accounts", "ix_instagram_accounts_user_id", ["user_id"])

    # 4) Backfill NULLs before enforcing NOT NULL + defaults
    conn.execute(sa.text(f"UPDATE positions SET is_system = 0 WHERE is_system IS NULL"))
    conn.execute(sa.text(f"UPDATE positions SET created_at = {now_sql} WHERE created_at IS NULL"))
    conn.execute(sa.text(f"UPDATE positions SET updated_at = {now_sql} WHERE updated_at IS NULL"))

    conn.execute(sa.text(f"UPDATE users SET created_at = {now_sql} WHERE created_at IS NULL"))
    conn.execute(sa.text(f"UPDATE users SET updated_at = {now_sql} WHERE updated_at IS NULL"))

    conn.execute(sa.text(f"UPDATE password_reset_tokens SET created_at = {now_sql} WHERE created_at IS NULL"))
    conn.execute(sa.text(f"UPDATE password_reset_tokens SET updated_at = {now_sql} WHERE updated_at IS NULL"))

    conn.execute(sa.text(f"UPDATE instagram_accounts SET connected_at = {now_sql} WHERE connected_at IS NULL"))

    conn.execute(sa.text(f"UPDATE chats SET created_at = {now_sql} WHERE created_at IS NULL"))
    conn.execute(sa.text(f"UPDATE chats SET updated_at = {now_sql} WHERE updated_at IS NULL"))

    conn.execute(sa.text(f"UPDATE facebook_users SET first_seen_at = {now_sql} WHERE first_seen_at IS NULL"))
    conn.execute(sa.text(f"UPDATE facebook_users SET last_seen_at = {now_sql} WHERE last_seen_at IS NULL"))

    conn.execute(sa.text(f"UPDATE facebook_pages SET is_active = 1 WHERE is_active IS NULL"))
    conn.execute(sa.text(f"UPDATE facebook_pages SET connected_at = {now_sql} WHERE connected_at IS NULL"))
    conn.execute(sa.text(f"UPDATE facebook_pages SET updated_at = {now_sql} WHERE updated_at IS NULL"))

    conn.execute(sa.text(f"UPDATE message_templates SET created_at = {now_sql} WHERE created_at IS NULL"))
    conn.execute(sa.text(f"UPDATE message_templates SET updated_at = {now_sql} WHERE updated_at IS NULL"))

    conn.execute(sa.text(f"UPDATE facebook_webhook_events SET received_at = {now_sql} WHERE received_at IS NULL"))

    conn.execute(sa.text(f"UPDATE instagram_users SET first_seen_at = {now_sql} WHERE first_seen_at IS NULL"))
    conn.execute(sa.text(f"UPDATE instagram_users SET last_seen_at = {now_sql} WHERE last_seen_at IS NULL"))

    conn.execute(sa.text(f"UPDATE instagram_message_logs SET created_at = {now_sql} WHERE created_at IS NULL"))

    conn.execute(sa.text(f"UPDATE instagram_comments SET created_at = {now_sql} WHERE created_at IS NULL"))
    conn.execute(sa.text(f"UPDATE instagram_comments SET updated_at = {now_sql} WHERE updated_at IS NULL"))

    conn.execute(sa.text(f"UPDATE facebook_page_status_logs SET changed_at = {now_sql} WHERE changed_at IS NULL"))
    conn.execute(sa.text(f"UPDATE user_status_logs SET changed_at = {now_sql} WHERE changed_at IS NULL"))

    conn.execute(sa.text(f"UPDATE instagram_marketing_events SET created_at = {now_sql} WHERE created_at IS NULL"))
    conn.execute(sa.text(f"UPDATE instagram_insights SET fetched_at = {now_sql} WHERE fetched_at IS NULL"))

    for table in ("facebook_messages", "instagram_messages", "instagram_message_logs"):
        if _column_exists(table, "timestamp"):
            conn.execute(sa.text(f"UPDATE {table} SET timestamp = {now_sql} WHERE timestamp IS NULL"))

    # 5) Alter columns to enforce NOT NULL + defaults (skip SQLite where ALTER is limited)
    if dialect != "sqlite":
        op.alter_column(
            "positions",
            "is_system",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default="0",
        )
        op.alter_column(
            "positions",
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )
        op.alter_column(
            "positions",
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )

        op.alter_column(
            "users",
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )
        op.alter_column(
            "users",
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )

        op.alter_column(
            "password_reset_tokens",
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )
        op.alter_column(
            "password_reset_tokens",
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )

        op.alter_column(
            "instagram_accounts",
            "connected_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )

        op.alter_column(
            "chats",
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )
        op.alter_column(
            "chats",
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )

        op.alter_column(
            "facebook_users",
            "first_seen_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )
        op.alter_column(
            "facebook_users",
            "last_seen_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )

        op.alter_column(
            "facebook_webhook_events",
            "received_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )

        op.alter_column(
            "facebook_pages",
            "is_active",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default="1",
        )
        op.alter_column(
            "facebook_pages",
            "connected_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )
        op.alter_column(
            "facebook_pages",
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )

        op.alter_column(
            "message_templates",
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )
        op.alter_column(
            "message_templates",
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )

        op.alter_column(
            "instagram_users",
            "first_seen_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )
        op.alter_column(
            "instagram_users",
            "last_seen_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )

        op.alter_column(
            "instagram_message_logs",
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )

        op.alter_column(
            "instagram_comments",
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )
        op.alter_column(
            "instagram_comments",
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )

        op.alter_column(
            "facebook_page_status_logs",
            "changed_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )
        op.alter_column(
            "user_status_logs",
            "changed_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )

        op.alter_column(
            "instagram_marketing_events",
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )

        op.alter_column(
            "instagram_insights",
            "fetched_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=_now_default(),
        )

        for table in ("facebook_messages", "instagram_messages", "instagram_message_logs"):
            if _column_exists(table, "timestamp"):
                op.alter_column(
                    table,
                    "timestamp",
                    existing_type=sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=_now_default(),
                )


def downgrade():
    raise NotImplementedError("Downgrade not supported for this schema alignment")
