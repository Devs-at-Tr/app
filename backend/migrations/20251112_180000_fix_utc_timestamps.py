from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import os

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

DATABASE_URL = os.getenv('DATABASE_URL', f"sqlite:///{ROOT_DIR / 'ticklegram.db'}")
engine = create_engine(DATABASE_URL)

SHIFT_MINUTES = 330  # 5 hours 30 minutes

TARGETS = {
    "positions": ["created_at", "updated_at"],
    "users": ["created_at", "updated_at"],
    "instagram_accounts": ["connected_at"],
    "chats": ["created_at", "updated_at"],
    "facebook_users": ["first_seen_at", "last_seen_at"],
    "facebook_pages": ["connected_at", "updated_at"],
    "message_templates": ["created_at", "updated_at"],
    "instagram_messages": ["timestamp"],
    "facebook_messages": ["timestamp"],
    "instagram_message_logs": ["created_at"],
}


def _shift_sql(table: str, column: str, dialect: str) -> str:
    if dialect in {"mysql", "mariadb"}:
        return f"""
            UPDATE {table}
            SET {column} = DATE_SUB({column}, INTERVAL {SHIFT_MINUTES} MINUTE)
            WHERE {column} IS NOT NULL
        """
    if dialect in {"postgresql", "postgres"}:
        return f"""
            UPDATE {table}
            SET {column} = {column} - INTERVAL '{SHIFT_MINUTES} minutes'
            WHERE {column} IS NOT NULL
        """
    if dialect == "sqlite":
        # SQLite stores datetimes as text; rely on julianday math
        return f"""
            UPDATE {table}
            SET {column} = DATETIME({column}, '-{SHIFT_MINUTES} minutes')
            WHERE {column} IS NOT NULL
        """
    raise RuntimeError(f"Unsupported dialect for timestamp migration: {dialect}")


def run_migration():
    with engine.begin() as conn:
        dialect = conn.dialect.name.lower()
        for table, columns in TARGETS.items():
            for column in columns:
                sql = _shift_sql(table, column, dialect)
                try:
                    conn.execute(text(sql))
                    print(f"Shifted {table}.{column} by -{SHIFT_MINUTES} minutes")
                except Exception as exc:
                    print(f"[WARN] Unable to shift {table}.{column}: {exc}")


if __name__ == "__main__":
    run_migration()
