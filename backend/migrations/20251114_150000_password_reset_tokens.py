from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import os

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

DEFAULT_SQLITE_URL = f"sqlite:///{ROOT_DIR / 'ticklegram.db'}"
DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("POSTGRES_URL")
    or os.getenv("MYSQL_URL")
    or DEFAULT_SQLITE_URL
)

engine = create_engine(DATABASE_URL)


def table_exists(conn, table: str) -> bool:
    dialect = conn.dialect.name.lower()
    if dialect == "sqlite":
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table"),
            {"table": table},
        ).fetchall()
        return bool(rows)
    if dialect in ("postgresql", "postgres"):
        rows = conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = :table
                LIMIT 1
                """
            ),
            {"table": table},
        ).fetchall()
        return bool(rows)
    result = conn.execute(text("SHOW TABLES LIKE :table"), {"table": table}).first()
    return result is not None


def index_exists(conn, table: str, index_name: str) -> bool:
    dialect = conn.dialect.name.lower()
    if dialect == "sqlite":
        rows = conn.execute(text(f"PRAGMA index_list('{table}')")).fetchall()
        return any(row[1] == index_name for row in rows)
    if dialect in ("postgresql", "postgres"):
        rows = conn.execute(
            text(
                """
                SELECT 1 FROM pg_indexes
                WHERE tablename = :table AND indexname = :index
                LIMIT 1
                """
            ),
            {"table": table, "index": index_name},
        ).fetchall()
        return bool(rows)
    if dialect in ("mysql", "mariadb"):
        rows = conn.execute(
            text(f"SHOW INDEX FROM {table} WHERE Key_name = :index"),
            {"index": index_name},
        ).fetchall()
        return bool(rows)
    return False


def create_reset_table(conn) -> None:
    if table_exists(conn, "password_reset_tokens"):
        return
    ddl = """
        CREATE TABLE password_reset_tokens (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            token_hash VARCHAR(128) NOT NULL,
            expires_at DATETIME NOT NULL,
            used_at DATETIME NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            CONSTRAINT fk_password_reset_user
                FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """
    conn.execute(text(ddl))


def create_indexes(conn) -> None:
    if not index_exists(conn, "password_reset_tokens", "ix_password_reset_tokens_user_id"):
        try:
            conn.execute(
                text(
                    "CREATE INDEX ix_password_reset_tokens_user_id ON password_reset_tokens (user_id)"
                )
            )
        except Exception:
            pass
    if not index_exists(conn, "password_reset_tokens", "ux_password_reset_tokens_hash"):
        try:
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX ux_password_reset_tokens_hash ON password_reset_tokens (token_hash)"
                )
            )
        except Exception:
            pass


def run_migration(target_engine=None):
    active_engine = target_engine or engine
    with active_engine.begin() as conn:
        create_reset_table(conn)
        create_indexes(conn)


if __name__ == "__main__":
    run_migration()
