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


def run_migration(target_engine=None):
    engine = target_engine or _get_engine()
    if engine is None:
        raise RuntimeError("Database engine is not available for migration.")

    with engine.begin() as conn:
        if not _table_exists(conn, "users"):
            raise RuntimeError("users table must exist before running this migration.")

        dialect = conn.dialect.name.lower()
        # No-op if already nullable
        is_nullable = False
        if dialect in ("postgresql", "postgres", "mysql", "mariadb"):
            result = conn.execute(
                text(
                    """
                    SELECT IS_NULLABLE
                    FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name = 'email'
                    """
                )
            ).first()
            is_nullable = bool(result and str(result[0]).lower() == "yes")

        if is_nullable:
            return

        if dialect in ("postgresql", "postgres"):
            statement = "ALTER TABLE users ALTER COLUMN email DROP NOT NULL"
        elif dialect == "sqlite":
            # SQLite cannot drop NOT NULL easily without table rebuild; skip quietly.
            statement = None
        else:
            statement = "ALTER TABLE users MODIFY email VARCHAR(255) NULL"

        if statement:
            conn.execute(text(statement))


if __name__ == "__main__":
    run_migration()
