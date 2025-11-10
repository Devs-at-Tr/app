from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import os

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

DATABASE_URL = os.getenv('DATABASE_URL', f"sqlite:///{ROOT_DIR / 'ticklegram.db'}")
engine = create_engine(DATABASE_URL)


def column_exists(conn, dialect: str, table: str, column: str) -> bool:
    if dialect == 'sqlite':
        rows = conn.execute(text(f"PRAGMA table_info({table})"))
        return column in {row[1] for row in rows}
    if dialect in ('postgresql', 'postgres'):
        query = text("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = :table AND column_name = :column
            LIMIT 1
        """)
        return conn.execute(query, {'table': table, 'column': column}).scalar() is not None
    if dialect in ('mysql', 'mariadb'):
        dbname = conn.execute(text('SELECT DATABASE()')).scalar()
        query = text("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = :db AND table_name = :table AND column_name = :column
            LIMIT 1
        """)
        return conn.execute(query, {'db': dbname, 'table': table, 'column': column}).scalar() is not None

    # Fallback: try DESCRIBE
    try:
        conn.execute(text(f"SELECT {column} FROM {table} LIMIT 0"))
        return True
    except Exception:
        return False


def add_column(conn, table: str, column_sql: str) -> None:
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_sql}"))


def drop_table_if_exists(conn, table: str) -> None:
    conn.execute(text(f"DROP TABLE IF EXISTS {table}"))


def index_exists(conn, dialect: str, table: str, index_name: str) -> bool:
    if dialect == 'sqlite':
        rows = conn.execute(text(f"PRAGMA index_list({table})"))
        return index_name in {row[1] for row in rows}
    if dialect in ('postgresql', 'postgres'):
        query = text("""
            SELECT 1 FROM pg_indexes
            WHERE tablename = :table AND indexname = :index
            LIMIT 1
        """)
        return conn.execute(query, {'table': table, 'index': index_name}).scalar() is not None
    if dialect in ('mysql', 'mariadb'):
        query = text(f"SHOW INDEX FROM {table} WHERE Key_name = :index")
        return conn.execute(query, {'index': index_name}).first() is not None
    return False


def ensure_instagram_user_columns(conn, dialect: str) -> None:
    if not column_exists(conn, dialect, 'instagram_users', 'username'):
        add_column(conn, 'instagram_users', 'username VARCHAR(255)')
    if not column_exists(conn, dialect, 'instagram_users', 'name'):
        add_column(conn, 'instagram_users', 'name VARCHAR(255)')


def ensure_instagram_message_columns(conn, dialect: str) -> None:
    message_id_column = 'message_id VARCHAR(255)'
    long_text_type = 'LONGTEXT' if dialect in ('mysql', 'mariadb') else 'TEXT'

    if not column_exists(conn, dialect, 'instagram_messages', 'message_id'):
        add_column(conn, 'instagram_messages', message_id_column)
    if not column_exists(conn, dialect, 'instagram_messages', 'raw_payload_json'):
        add_column(conn, 'instagram_messages', f'raw_payload_json {long_text_type}')

    index_name = 'uq_instagram_messages_message_id'
    if not index_exists(conn, dialect, 'instagram_messages', index_name):
        try:
            if dialect == 'sqlite':
                conn.execute(text(
                    f'CREATE UNIQUE INDEX {index_name} ON instagram_messages (message_id)'
                ))
            elif dialect in ('postgresql', 'postgres', 'mysql', 'mariadb'):
                conn.execute(text(
                    f'CREATE UNIQUE INDEX {index_name} ON instagram_messages (message_id)'
                ))
            else:
                conn.execute(text(
                    f'CREATE UNIQUE INDEX {index_name} ON instagram_messages (message_id)'
                ))
        except Exception:
            # Ignore if duplicates exist or database lacks unique support; user can clean up manually
            pass


def cleanup_legacy_tables(conn) -> None:
    drop_table_if_exists(conn, 'ig_messages')


def run_migration() -> None:
    with engine.begin() as conn:
        dialect = engine.dialect.name.lower()
        ensure_instagram_user_columns(conn, dialect)
        ensure_instagram_message_columns(conn, dialect)
        cleanup_legacy_tables(conn)
        print("✓ Ensured instagram user/message profile columns exist and cleaned legacy tables")


if __name__ == '__main__':
    run_migration()
