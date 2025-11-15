from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
import os

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

try:
    from database import engine as default_engine
except Exception:
    default_engine = None


def _get_engine():
    return default_engine


def _create_tables(conn, dialect: str) -> None:
    dialect = dialect.lower()
    if dialect == "sqlite":
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS db_schema_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    snapshot_json TEXT NOT NULL,
                    comment TEXT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS db_schema_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    change_type TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    column_name TEXT NULL,
                    details_json TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(snapshot_id) REFERENCES db_schema_snapshots(id) ON DELETE CASCADE
                )
                """
            )
        )
    else:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS db_schema_snapshots (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    snapshot_json LONGTEXT NOT NULL,
                    comment VARCHAR(255) NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS db_schema_changes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    snapshot_id INT NOT NULL,
                    change_type VARCHAR(50) NOT NULL,
                    table_name VARCHAR(255) NOT NULL,
                    column_name VARCHAR(255) NULL,
                    details_json LONGTEXT NULL,
                    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    CONSTRAINT fk_schema_change_snapshot
                        FOREIGN KEY (snapshot_id)
                        REFERENCES db_schema_snapshots(id)
                        ON DELETE CASCADE
                )
                """
            )
        )
        try:
            conn.execute(
                text(
                    """
                    CREATE INDEX ix_db_schema_changes_snapshot_id
                    ON db_schema_changes (snapshot_id)
                    """
                )
            )
        except Exception:
            pass


def run_migration(target_engine=None):
    engine = target_engine or _get_engine()
    if engine is None:
        raise RuntimeError("Database engine is not available for migration.")
    with engine.begin() as conn:
        _create_tables(conn, conn.dialect.name)


if __name__ == "__main__":
    run_migration()
