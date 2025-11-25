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

def table_exists(conn, table: str) -> bool:
    dialect = conn.dialect.name.lower()
    if dialect == "sqlite":
        rows = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=:table"
        ), {"table": table}).fetchall()
        return bool(rows)
    if dialect in ("postgresql", "postgres"):
        rows = conn.execute(text("""
            SELECT 1 FROM information_schema.tables
            WHERE table_name = :table
            LIMIT 1
        """), {"table": table}).fetchall()
        return bool(rows)
    result = conn.execute(text("SHOW TABLES LIKE :table"), {"table": table}).first()
    return result is not None

def add_column(conn, table: str, column_sql: str) -> None:
    if not table_exists(conn, table):
        return
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
    if not table_exists(conn, "instagram_messages"):
        return
    message_id_column = 'message_id VARCHAR(255)'
    long_text_type = 'LONGTEXT' if dialect in ('mysql', 'mariadb') else 'TEXT'

    if not column_exists(conn, dialect, 'instagram_messages', 'message_id'):
        add_column(conn, 'instagram_messages', message_id_column)
    if not column_exists(conn, dialect, 'instagram_messages', 'raw_payload_json'):
        add_column(conn, 'instagram_messages', f'raw_payload_json {long_text_type}')
    if not column_exists(conn, dialect, 'instagram_messages', 'metadata_json'):
        add_column(conn, 'instagram_messages', f'metadata_json {long_text_type}')
    if not column_exists(conn, dialect, 'instagram_messages', 'is_gif'):
        if dialect in ('mysql', 'mariadb'):
            add_column(conn, 'instagram_messages', 'is_gif TINYINT(1) NOT NULL DEFAULT 0')
        elif dialect in ('postgresql', 'postgres'):
            add_column(conn, 'instagram_messages', 'is_gif BOOLEAN NOT NULL DEFAULT FALSE')
        else:
            add_column(conn, 'instagram_messages', 'is_gif BOOLEAN NOT NULL DEFAULT 0')
    if not column_exists(conn, dialect, 'instagram_messages', 'is_ticklegram'):
        if dialect in ('mysql', 'mariadb'):
            add_column(conn, 'instagram_messages', 'is_ticklegram TINYINT(1) NOT NULL DEFAULT 0')
        elif dialect in ('postgresql', 'postgres'):
            add_column(conn, 'instagram_messages', 'is_ticklegram BOOLEAN NOT NULL DEFAULT FALSE')
        else:
            add_column(conn, 'instagram_messages', 'is_ticklegram BOOLEAN NOT NULL DEFAULT 0')

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


def ensure_instagram_message_id_length(conn, dialect: str, target: int = 512) -> None:
    """Ensure instagram_messages.message_id has enough length to store Meta IDs."""
    if not table_exists(conn, "instagram_messages"):
        return
    if dialect in ('mysql', 'mariadb'):
        length = conn.execute(text("""
            SELECT CHARACTER_MAXIMUM_LENGTH
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'instagram_messages'
              AND column_name = 'message_id'
        """)).scalar()
        if length is not None and length < target:
            conn.execute(text(f"""
                ALTER TABLE instagram_messages
                MODIFY message_id VARCHAR({target})
            """))
    elif dialect in ('postgresql', 'postgres'):
        conn.execute(text(f"""
            ALTER TABLE instagram_messages
            ALTER COLUMN message_id TYPE VARCHAR({target})
        """))
    else:
        # SQLite and others do not enforce length strictly
        pass


def ensure_message_origin_column(conn, dialect: str) -> None:
    if not table_exists(conn, "messages"):
        return
    if column_exists(conn, dialect, 'messages', 'is_ticklegram'):
        return
    if dialect in ('mysql', 'mariadb'):
        add_column(conn, 'messages', 'is_ticklegram TINYINT(1) NOT NULL DEFAULT 0')
    elif dialect in ('postgresql', 'postgres'):
        add_column(conn, 'messages', 'is_ticklegram BOOLEAN NOT NULL DEFAULT FALSE')
    else:
        add_column(conn, 'messages', 'is_ticklegram BOOLEAN NOT NULL DEFAULT 0')


def ensure_message_sender_enum(conn, dialect: str) -> None:
    if not table_exists(conn, "messages"):
        return
    """Ensure messages.sender ENUM supports INSTAGRAM_PAGE and uses uppercase constants."""
    desired_values = ["AGENT", "INSTAGRAM_USER", "FACEBOOK_USER", "INSTAGRAM_PAGE"]
    lowercase_values = [value.lower() for value in desired_values]

    try:
        conn.execute(text(
            "UPDATE messages SET sender = 'INSTAGRAM_PAGE' WHERE sender = '' OR sender IS NULL"
        ))
    except Exception:
        pass

    if dialect in ('mysql', 'mariadb'):
        temp_enum = ",".join(f"'{val}'" for val in desired_values + lowercase_values)
        final_enum = ",".join(f"'{val}'" for val in desired_values)

        conn.execute(text(f"""
            ALTER TABLE messages
            MODIFY sender ENUM({temp_enum}) NOT NULL
        """))
        conn.execute(text("UPDATE messages SET sender = UPPER(sender) WHERE sender IS NOT NULL"))


def ensure_message_attachment_columns(conn, dialect: str) -> None:
    if not table_exists(conn, "messages"):
        return
    long_text = 'LONGTEXT' if dialect in ('mysql', 'mariadb') else 'TEXT'
    if not column_exists(conn, dialect, 'messages', 'attachments_json'):
        add_column(conn, 'messages', f'attachments_json {long_text}')
    if not column_exists(conn, dialect, 'messages', 'metadata_json'):
        add_column(conn, 'messages', f'metadata_json {long_text}')
    if not column_exists(conn, dialect, 'messages', 'is_gif'):
        if dialect in ('mysql', 'mariadb'):
            add_column(conn, 'messages', 'is_gif TINYINT(1) NOT NULL DEFAULT 0')
        elif dialect in ('postgresql', 'postgres'):
            add_column(conn, 'messages', 'is_gif BOOLEAN NOT NULL DEFAULT FALSE')
        else:
            add_column(conn, 'messages', 'is_gif BOOLEAN NOT NULL DEFAULT 0')


def ensure_message_attachment_columns(conn, dialect: str) -> None:
    if not table_exists(conn, "messages"):
        return
    long_text_type = 'LONGTEXT' if dialect in ('mysql', 'mariadb') else 'TEXT'
    if not column_exists(conn, dialect, 'messages', 'attachments_json'):
        add_column(conn, 'messages', f'attachments_json {long_text_type}')
    if not column_exists(conn, dialect, 'messages', 'metadata_json'):
        add_column(conn, 'messages', f'metadata_json {long_text_type}')
    if not column_exists(conn, dialect, 'messages', 'is_gif'):
        if dialect in ('mysql', 'mariadb'):
            add_column(conn, 'messages', 'is_gif TINYINT(1) NOT NULL DEFAULT 0')
        elif dialect in ('postgresql', 'postgres'):
            add_column(conn, 'messages', 'is_gif BOOLEAN NOT NULL DEFAULT FALSE')
        else:
            add_column(conn, 'messages', 'is_gif BOOLEAN NOT NULL DEFAULT 0')


def cleanup_legacy_tables(conn) -> None:
    drop_table_if_exists(conn, 'ig_messages')


def run_migration(target_engine=None) -> None:
    engine_to_use = target_engine or engine
    with engine_to_use.begin() as conn:
        dialect = engine_to_use.dialect.name.lower()
        ensure_instagram_user_columns(conn, dialect)
        ensure_instagram_message_columns(conn, dialect)
        ensure_instagram_message_id_length(conn, dialect)
        ensure_message_sender_enum(conn, dialect)
        ensure_message_origin_column(conn, dialect)
        ensure_message_attachment_columns(conn, dialect)
        cleanup_legacy_tables(conn)
        print("[OK] Ensured instagram profile/message schema and cleaned legacy tables")


if __name__ == '__main__':
    run_migration()
