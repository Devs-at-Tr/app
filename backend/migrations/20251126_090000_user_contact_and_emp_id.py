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


def _index_exists(conn, index: str) -> bool:
    dialect = conn.dialect.name.lower()
    if dialect == "sqlite":
        row = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='index' AND name = :name"
            ),
            {"name": index},
        ).fetchone()
        return row is not None
    if dialect in ("postgresql", "postgres"):
        result = conn.execute(
            text("SELECT to_regclass(:name)"),
            {"name": index},
        ).first()
        return bool(result and result[0])
    result = conn.execute(
        text(
            "SELECT 1 FROM information_schema.statistics WHERE index_name = :name LIMIT 1"
        ),
        {"name": index},
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


def _create_unique_index(conn, name: str, table: str, column: str) -> None:
    if _index_exists(conn, name):
        return
    dialect = conn.dialect.name.lower()
    if dialect == "sqlite":
        statement = f'CREATE UNIQUE INDEX IF NOT EXISTS "{name}" ON {table} ({column})'
    else:
        statement = f"CREATE UNIQUE INDEX {name} ON {table} ({column})"
    conn.execute(text(statement))


def run_migration(target_engine=None):
    engine = target_engine or _get_engine()
    if engine is None:
        raise RuntimeError("Database engine is not available for migration.")

    with engine.begin() as conn:
        if not _table_exists(conn, "users"):
            raise RuntimeError("users table must exist before running this migration.")

        dialect = conn.dialect.name.lower()
        if dialect in ("postgresql", "postgres"):
            contact_sql = "ALTER TABLE users ADD COLUMN contact_number VARCHAR(50) NULL"
            country_sql = "ALTER TABLE users ADD COLUMN country VARCHAR(100) NULL"
            emp_sql = "ALTER TABLE users ADD COLUMN emp_id VARCHAR(100) NULL"
        elif dialect == "sqlite":
            contact_sql = "ALTER TABLE users ADD COLUMN contact_number TEXT NULL"
            country_sql = "ALTER TABLE users ADD COLUMN country TEXT NULL"
            emp_sql = "ALTER TABLE users ADD COLUMN emp_id TEXT NULL"
        else:
            contact_sql = "ALTER TABLE users ADD COLUMN contact_number VARCHAR(50) NULL"
            country_sql = "ALTER TABLE users ADD COLUMN country VARCHAR(100) NULL"
            emp_sql = "ALTER TABLE users ADD COLUMN emp_id VARCHAR(100) NULL"

        _add_column(conn, "users", "contact_number", contact_sql, contact_sql)
        _add_column(conn, "users", "country", country_sql, country_sql)
        _add_column(conn, "users", "emp_id", emp_sql, emp_sql)

        _create_unique_index(conn, "uq_users_contact_number", "users", "contact_number")
        _create_unique_index(conn, "uq_users_emp_id", "users", "emp_id")


if __name__ == "__main__":
    run_migration()
