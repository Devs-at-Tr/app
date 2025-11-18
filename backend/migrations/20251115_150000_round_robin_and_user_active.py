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


def _add_column(conn, table: str, column: str, ddl_sql: str, ddl_sqlite: str = None) -> None:
    if _column_exists(conn, table, column):
        return
    dialect = conn.dialect.name.lower()
    statement = ddl_sql
    if dialect == "sqlite" and ddl_sqlite:
        statement = ddl_sqlite
    conn.execute(text(statement))


def _create_assignment_cursor_table(conn) -> None:
    if _table_exists(conn, "assignment_cursors"):
        return
    dialect = conn.dialect.name.lower()
    if dialect == "sqlite":
        ddl = """
            CREATE TABLE assignment_cursors (
                name TEXT PRIMARY KEY,
                last_user_id TEXT NULL,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """
    elif dialect in ("postgresql", "postgres"):
        ddl = """
            CREATE TABLE assignment_cursors (
                name VARCHAR(64) PRIMARY KEY,
                last_user_id VARCHAR(36) NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """
    else:
        ddl = """
            CREATE TABLE assignment_cursors (
                name VARCHAR(64) PRIMARY KEY,
                last_user_id VARCHAR(36) NULL,
                updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
            )
        """
    conn.execute(text(ddl))


def _seed_cursor(conn) -> None:
    existing = conn.execute(
        text("SELECT name FROM assignment_cursors WHERE name = :name"),
        {"name": "default"},
    ).first()
    if existing:
        return
    conn.execute(
        text(
            """
            INSERT INTO assignment_cursors (name, last_user_id, updated_at)
            VALUES (:name, NULL, CURRENT_TIMESTAMP)
            """
        ),
        {"name": "default"},
    )


def run_migration(target_engine=None):
    engine = target_engine or _get_engine()
    if engine is None:
        raise RuntimeError("Database engine is not available for migration.")

    with engine.begin() as conn:
        dialect = conn.dialect.name.lower()
        if not _table_exists(conn, "users"):
            raise RuntimeError("users table must exist before running this migration.")
        if not _table_exists(conn, "chats"):
            raise RuntimeError("chats table must exist before running this migration.")

        # users.is_active
        user_column_sql = "ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
        user_column_sqlite = "ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
        if dialect in ("postgresql", "postgres"):
            user_column_sql = "ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"
        _add_column(conn, "users", "is_active", user_column_sql, user_column_sqlite)

        # chats.last_incoming_at
        if dialect in ("postgresql", "postgres"):
            incoming_sql = "ALTER TABLE chats ADD COLUMN last_incoming_at TIMESTAMPTZ NULL"
            outgoing_sql = "ALTER TABLE chats ADD COLUMN last_outgoing_at TIMESTAMPTZ NULL"
        elif dialect == "sqlite":
            incoming_sql = "ALTER TABLE chats ADD COLUMN last_incoming_at DATETIME NULL"
            outgoing_sql = "ALTER TABLE chats ADD COLUMN last_outgoing_at DATETIME NULL"
        else:
            incoming_sql = "ALTER TABLE chats ADD COLUMN last_incoming_at DATETIME(6) NULL"
            outgoing_sql = "ALTER TABLE chats ADD COLUMN last_outgoing_at DATETIME(6) NULL"

        _add_column(conn, "chats", "last_incoming_at", incoming_sql, incoming_sql)
        _add_column(conn, "chats", "last_outgoing_at", outgoing_sql, outgoing_sql)

        _create_assignment_cursor_table(conn)
        _seed_cursor(conn)


if __name__ == "__main__":
    run_migration()
