"""
Migration to split the legacy `messages` table into platform specific tables and
introduce facebook_users plus instagram_message logs rename.
"""
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError
import os
from typing import Optional

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT_DIR / 'ticklegram.db'}")
engine = create_engine(DATABASE_URL)

from models import FacebookUser, FacebookMessage, InstagramMessage  # noqa: E402


def table_exists(conn: Connection, table_name: str) -> bool:
    dialect = conn.dialect.name.lower()
    if dialect == "sqlite":
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=:name"
        ), {"name": table_name}).first()
        return result is not None
    if dialect in ("postgresql", "postgres"):
        result = conn.execute(text("""
            SELECT 1 FROM information_schema.tables
            WHERE table_name = :name
            LIMIT 1
        """), {"name": table_name}).first()
        return result is not None
    result = conn.execute(text("SHOW TABLES LIKE :name"), {"name": table_name}).first()
    return result is not None


def column_exists(conn: Connection, table: str, column: str) -> bool:
    dialect = conn.dialect.name.lower()
    if dialect == "sqlite":
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return any(row[1] == column for row in rows)
    if dialect in ("postgresql", "postgres"):
        query = text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :table AND column_name = :column
            LIMIT 1
        """)
        return conn.execute(query, {"table": table, "column": column}).first() is not None
    query = text(f"SHOW COLUMNS FROM {table} LIKE :column")
    return conn.execute(query, {"column": column}).first() is not None


def add_column(conn: Connection, table: str, column_sql: str) -> None:
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_sql}"))


def rename_instagram_messages(conn: Connection, dialect: str) -> None:
    if table_exists(conn, "instagram_message_logs"):
        return
    if not table_exists(conn, "instagram_messages"):
        return
    if dialect in ("mysql", "mariadb"):
        conn.execute(text("RENAME TABLE instagram_messages TO instagram_message_logs"))
    else:
        conn.execute(text("ALTER TABLE instagram_messages RENAME TO instagram_message_logs"))


def ensure_new_tables(conn: Connection) -> None:
    FacebookUser.__table__.create(conn, checkfirst=True)
    InstagramMessage.__table__.create(conn, checkfirst=True)
    FacebookMessage.__table__.create(conn, checkfirst=True)


def ensure_chat_columns(conn: Connection, dialect: str) -> None:
    if not column_exists(conn, "chats", "facebook_user_id"):
        add_column(conn, "chats", "facebook_user_id VARCHAR(255)")
        if dialect != "sqlite":
            try:
                conn.execute(text("CREATE INDEX idx_chats_facebook_user_id ON chats (facebook_user_id)"))
            except Exception:
                pass
    if dialect in ("postgresql", "postgres"):
        conn.execute(text("ALTER TABLE chats ALTER COLUMN instagram_user_id DROP NOT NULL"))
    elif dialect in ("mysql", "mariadb"):
        conn.execute(text("ALTER TABLE chats MODIFY instagram_user_id VARCHAR(255) NULL"))
    # SQLite keeps legacy constraint; runtime layer keeps compatibility.


def upsert_facebook_user(conn: Connection, dialect: str, payload: dict) -> None:
    if dialect in ("postgresql", "postgres", "sqlite"):
        stmt = text("""
            INSERT INTO facebook_users (id, username, name, profile_pic_url, last_message, first_seen_at, last_seen_at)
            VALUES (:id, :username, :name, :profile_pic_url, :last_message, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                username=excluded.username,
                name=excluded.name,
                profile_pic_url=excluded.profile_pic_url,
                last_message=excluded.last_message,
                last_seen_at=CURRENT_TIMESTAMP
        """)
    else:
        stmt = text("""
            INSERT INTO facebook_users (id, username, name, profile_pic_url, last_message, first_seen_at, last_seen_at)
            VALUES (:id, :username, :name, :profile_pic_url, :last_message, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON DUPLICATE KEY UPDATE
                username=VALUES(username),
                name=VALUES(name),
                profile_pic_url=VALUES(profile_pic_url),
                last_message=VALUES(last_message),
                last_seen_at=CURRENT_TIMESTAMP
        """)
    conn.execute(stmt, payload)


def migrate_facebook_metadata(conn: Connection, dialect: str) -> None:
    if not column_exists(conn, "chats", "facebook_user_id"):
        return
    if not column_exists(conn, "chats", "profile_pic_url"):
        conn.execute(text("ALTER TABLE chats ADD COLUMN profile_pic_url TEXT NULL"))
    rows = conn.execute(text("""
        SELECT id, instagram_user_id, facebook_user_id, username, profile_pic_url, last_message
        FROM chats
        WHERE platform = 'FACEBOOK'
    """)).mappings().all()
    for row in rows:
        fb_id = row.get("facebook_user_id") or row.get("instagram_user_id")
        if not fb_id:
            continue
        upsert_facebook_user(conn, dialect, {
            "id": fb_id,
            "username": row["username"],
            "name": row["username"],
            "profile_pic_url": row["profile_pic_url"],
            "last_message": row["last_message"],
        })
        params = {"fb_id": fb_id, "chat_id": row["id"]}
        update_sql = "UPDATE chats SET facebook_user_id = :fb_id"
        if dialect in ("postgresql", "postgres", "mysql", "mariadb"):
            update_sql += ", instagram_user_id = NULL"
        update_sql += " WHERE id = :chat_id"
        conn.execute(text(update_sql), params)


def _safe_execute(conn: Connection, statement):
    try:
        return conn.execute(statement)
    except OperationalError:
        return None


def migrate_messages(conn: Connection) -> None:
    if not table_exists(conn, "messages"):
        return
    if not column_exists(conn, "messages", "chat_id"):
        return
    instagram_count = conn.execute(text("SELECT COUNT(1) FROM instagram_messages")).scalar() or 0
    facebook_count = conn.execute(text("SELECT COUNT(1) FROM facebook_messages")).scalar() or 0
    if instagram_count == 0:
        _safe_execute(conn, text("""
            INSERT INTO instagram_messages (
                id, chat_id, instagram_user_id, sender, content, message_type,
                platform, timestamp, attachments_json, metadata_json, is_gif, is_ticklegram
            )
            SELECT
                m.id, m.chat_id,
                COALESCE(c.instagram_user_id, c.facebook_user_id),
                m.sender, m.content, m.message_type,
                m.platform, m.timestamp, NULL, NULL, 0, m.is_ticklegram
            FROM messages m
            JOIN chats c ON c.id = m.chat_id
            WHERE m.platform = 'INSTAGRAM'
              AND COALESCE(c.instagram_user_id, c.facebook_user_id) IS NOT NULL
              AND EXISTS (
                  SELECT 1 FROM instagram_users iu
                  WHERE iu.igsid = COALESCE(c.instagram_user_id, c.facebook_user_id)
              )
        """))
    if facebook_count == 0:
        _safe_execute(conn, text("""
            INSERT INTO facebook_messages (
                id, chat_id, facebook_user_id, sender, content, message_type,
                platform, timestamp, attachments_json, metadata_json, is_gif, is_ticklegram
            )
            SELECT
                m.id, m.chat_id, c.facebook_user_id, m.sender, m.content, m.message_type,
                m.platform, m.timestamp, NULL, NULL, 0, m.is_ticklegram
            FROM messages m
            JOIN chats c ON c.id = m.chat_id
            WHERE m.platform = 'FACEBOOK'
              AND c.facebook_user_id IS NOT NULL
        """))
    _safe_execute(conn, text("DROP TABLE IF EXISTS messages"))


def run_migration(target_engine=None) -> None:
    engine_to_use = target_engine or engine
    with engine_to_use.begin() as conn:
        dialect = conn.dialect.name.lower()
        rename_instagram_messages(conn, dialect)
        ensure_new_tables(conn)
        ensure_chat_columns(conn, dialect)
        migrate_facebook_metadata(conn, dialect)
        migrate_messages(conn)
        print("[OK] Platform-specific message tables ready")


if __name__ == "__main__":
    run_migration()
