"""
Safety migration to backfill missing columns for existing databases.
- Adds chats.profile_pic_url if absent.
- Adds users.position_id if absent (nullable) to match ORM.
"""
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
import os

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

try:
    from database import engine as default_engine
except Exception:
    default_engine = None


def _get_engine():
    return default_engine


def _table_exists(conn, table: str) -> bool:
    dialect = conn.dialect.name.lower()
    if dialect == "sqlite":
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name = :table"),
            {"table": table},
        ).fetchall()
        return bool(rows)
    if dialect in ("postgresql", "postgres"):
        result = conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_name = :table
                LIMIT 1
                """
            ),
            {"table": table},
        ).first()
        return result is not None
    result = conn.execute(text("SHOW TABLES LIKE :table"), {"table": table}).first()
    return result is not None


def _column_exists(conn, table: str, column: str) -> bool:
    dialect = conn.dialect.name.lower()
    if dialect == "sqlite":
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return column in {row[1] for row in rows}
    if dialect in ("postgresql", "postgres"):
        result = conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :table AND column_name = :column
                LIMIT 1
                """
            ),
            {"table": table, "column": column},
        ).first()
        return result is not None
    result = conn.execute(
        text(
            """
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_NAME = :table AND COLUMN_NAME = :column
            LIMIT 1
            """
        ),
        {"table": table, "column": column},
    ).first()
    return result is not None


def _add_column(conn, table: str, column: str, ddl_sql: str) -> None:
    if _column_exists(conn, table, column):
        return
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl_sql}"))


def _ensure_chats_profile_pic(conn) -> None:
    if not _table_exists(conn, "chats"):
        return
    dialect = conn.dialect.name.lower()
    if dialect in ("postgresql", "postgres"):
        ddl = "profile_pic_url TEXT NULL"
    elif dialect == "sqlite":
        ddl = "profile_pic_url TEXT NULL"
    else:
        ddl = "profile_pic_url TEXT NULL"
    _add_column(conn, "chats", "profile_pic_url", ddl)


def _ensure_users_position(conn) -> None:
    if not _table_exists(conn, "users"):
        return
    dialect = conn.dialect.name.lower()
    if dialect in ("postgresql", "postgres"):
        ddl = "position_id VARCHAR(36) NULL"
    else:
        ddl = "position_id VARCHAR(36) NULL"
    _add_column(conn, "users", "position_id", ddl)
    try:
        if dialect not in ("sqlite",):
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_position_id ON users (position_id)"))
    except Exception:
        pass


def run_migration(target_engine=None):
    engine = target_engine or _get_engine()
    if engine is None:
        raise RuntimeError("Database engine is not available for migration.")
    with engine.begin() as conn:
        _ensure_chats_profile_pic(conn)
        _ensure_users_position(conn)


if __name__ == "__main__":
    run_migration()
