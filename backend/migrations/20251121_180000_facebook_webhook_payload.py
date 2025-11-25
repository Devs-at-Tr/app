"""
Create storage for full Facebook webhook payloads.
"""
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text

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


def _create_table(conn) -> None:
    if _table_exists(conn, "facebook_webhook_events"):
        return

    dialect = conn.dialect.name.lower()
    if dialect == "sqlite":
        ddl = """
            CREATE TABLE facebook_webhook_events (
                id TEXT PRIMARY KEY,
                object TEXT NULL,
                page_id TEXT NULL,
                payload TEXT NOT NULL,
                received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """
    elif dialect in ("postgresql", "postgres"):
        ddl = """
            CREATE TABLE facebook_webhook_events (
                id VARCHAR(36) PRIMARY KEY,
                object VARCHAR(64) NULL,
                page_id VARCHAR(255) NULL,
                payload JSONB NOT NULL,
                received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """
    else:
        ddl = """
            CREATE TABLE facebook_webhook_events (
                id VARCHAR(36) PRIMARY KEY,
                object VARCHAR(64) NULL,
                page_id VARCHAR(255) NULL,
                payload JSON NOT NULL,
                received_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
            )
        """

    conn.execute(text(ddl))

    try:
        conn.execute(
            text("CREATE INDEX ix_facebook_webhook_events_page_id ON facebook_webhook_events (page_id)")
        )
    except Exception:
        pass


def run_migration(target_engine=None):
    engine = target_engine or _get_engine()
    if engine is None:
        raise RuntimeError("Database engine is not available for migration.")

    with engine.begin() as conn:
        _create_table(conn)


def downgrade(target_engine=None):
    engine = target_engine or _get_engine()
    if engine is None:
        return
    with engine.begin() as conn:
        if _table_exists(conn, "facebook_webhook_events"):
            conn.execute(text("DROP TABLE facebook_webhook_events"))


if __name__ == "__main__":
    run_migration()
