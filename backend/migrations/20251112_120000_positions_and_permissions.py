from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from datetime import datetime, timezone
import os
import uuid
import json

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

DATABASE_URL = os.getenv('DATABASE_URL', f"sqlite:///{ROOT_DIR / 'ticklegram.db'}")
engine = create_engine(DATABASE_URL)


DEFAULT_POSITIONS = [
    {
        "name": "Super Admin",
        "slug": "super-admin",
        "description": "Unrestricted owner role.",
        "permissions": [
            "chat:view:assigned",
            "chat:view:team",
            "chat:view:all",
            "chat:message",
            "chat:assign",
            "template:use",
            "template:manage",
            "comment:moderate",
            "integration:manage",
            "position:manage",
            "position:assign",
            "user:invite",
            "stats:view",
        ],
        "is_system": True,
    },
    {
        "name": "Admin",
        "slug": "admin",
        "description": "Full control below Super Admins.",
        "permissions": [
            "chat:view:assigned",
            "chat:view:team",
            "chat:view:all",
            "chat:message",
            "chat:assign",
            "template:use",
            "template:manage",
            "comment:moderate",
            "integration:manage",
            "position:manage",
            "position:assign",
            "user:invite",
            "stats:view",
        ],
        "is_system": True,
    },
    {
        "name": "Supervisor",
        "slug": "supervisor",
        "description": "Manages teams and oversees conversations.",
        "permissions": [
            "chat:view:assigned",
            "chat:view:team",
            "chat:view:all",
            "chat:message",
            "chat:assign",
            "template:use",
            "comment:moderate",
            "stats:view",
        ],
        "is_system": True,
    },
    {
        "name": "Agent (Messaging)",
        "slug": "agent-messaging",
        "description": "Handles only their assigned DM conversations.",
        "permissions": [
            "chat:view:assigned",
            "chat:message",
            "template:use",
        ],
        "is_system": True,
    },
]


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
                SELECT 1 FROM information_schema.tables
                WHERE table_name = :table
                LIMIT 1
                """
            ),
            {"table": table},
        ).fetchall()
        return bool(rows)
    result = conn.execute(text("SHOW TABLES LIKE :table"), {"table": table}).first()
    return result is not None


def column_exists(conn, dialect: str, table: str, column: str) -> bool:
    if dialect == "sqlite":
        rows = conn.execute(text(f"PRAGMA table_info({table})"))
        return column in {row[1] for row in rows}
    if dialect in ("postgresql", "postgres"):
        query = text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = :table AND column_name = :column
            LIMIT 1
            """
        )
        return (
            conn.execute(query, {"table": table, "column": column}).scalar() is not None
        )
    if dialect in ("mysql", "mariadb"):
        dbname = conn.execute(text("SELECT DATABASE()")).scalar()
        query = text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = :db AND table_name = :table AND column_name = :column
            LIMIT 1
            """
        )
        return (
            conn.execute(
                query, {"db": dbname, "table": table, "column": column}
            ).scalar()
            is not None
        )
    try:
        conn.execute(text(f"SELECT {column} FROM {table} LIMIT 0"))
        return True
    except Exception:
        return False


def index_exists(conn, dialect: str, table: str, index_name: str) -> bool:
    if dialect == "sqlite":
        rows = conn.execute(text(f"PRAGMA index_list({table})"))
        return index_name in {row[1] for row in rows}
    if dialect in ("postgresql", "postgres"):
        query = text(
            """
            SELECT 1 FROM pg_indexes
            WHERE tablename = :table AND indexname = :index
            LIMIT 1
            """
        )
        return (
            conn.execute(query, {"table": table, "index": index_name}).scalar()
            is not None
        )
    if dialect in ("mysql", "mariadb"):
        query = text(f"SHOW INDEX FROM {table} WHERE Key_name = :index")
        return conn.execute(query, {"index": index_name}).first() is not None
    return False


def create_positions_table(conn, dialect: str) -> None:
    if table_exists(conn, "positions"):
        return
    ddl = """
        CREATE TABLE positions (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(255) NOT NULL UNIQUE,
            description TEXT NULL,
            permissions_json TEXT NOT NULL,
            is_system BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
    """
    conn.execute(text(ddl))
    if not index_exists(conn, dialect, "positions", "ix_positions_slug"):
        conn.execute(text("CREATE UNIQUE INDEX ix_positions_slug ON positions (slug)"))


def ensure_user_position_column(conn, dialect: str) -> None:
    if not table_exists(conn, "users"):
        return
    if not column_exists(conn, dialect, "users", "position_id"):
        conn.execute(text("ALTER TABLE users ADD COLUMN position_id VARCHAR(36)"))
    if not index_exists(conn, dialect, "users", "ix_users_position_id"):
        try:
            conn.execute(text("CREATE INDEX ix_users_position_id ON users (position_id)"))
        except Exception:
            pass


def upsert_position(conn, definition: dict) -> str:
    existing = conn.execute(
        text("SELECT id FROM positions WHERE slug = :slug"),
        {"slug": definition["slug"]},
    ).fetchone()
    if existing:
        return existing[0]
    position_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    conn.execute(
        text(
            """
            INSERT INTO positions (
                id, name, slug, description, permissions_json, is_system, created_at, updated_at
            ) VALUES (
                :id, :name, :slug, :description, :permissions_json, :is_system, :created_at, :updated_at
            )
            """
        ),
        {
            "id": position_id,
            "name": definition["name"],
            "slug": definition["slug"],
            "description": definition.get("description"),
            "permissions_json": json.dumps(definition.get("permissions") or []),
            "is_system": 1 if definition.get("is_system") else 0,
            "created_at": now,
            "updated_at": now,
        },
    )
    return position_id


def seed_positions(conn) -> dict:
    slug_to_id = {}
    for definition in DEFAULT_POSITIONS:
        slug_to_id[definition["slug"]] = upsert_position(conn, definition)
    return slug_to_id


def assign_existing_users(conn, slug_to_id: dict) -> None:
    admin_rows = conn.execute(
        text("SELECT id FROM users WHERE role = 'admin' ORDER BY created_at ASC")
    ).fetchall()
    if admin_rows:
        first_admin = admin_rows[0][0]
        conn.execute(
            text("UPDATE users SET position_id = :position WHERE id = :user_id"),
            {"position": slug_to_id.get("super-admin") or slug_to_id.get("admin"), "user_id": first_admin},
        )
        if len(admin_rows) > 1:
            remaining = [row[0] for row in admin_rows[1:]]
            for user_id in remaining:
                conn.execute(
                    text("UPDATE users SET position_id = :position WHERE id = :user_id"),
                    {"position": slug_to_id.get("admin"), "user_id": user_id},
                )
    agent_rows = conn.execute(
        text("SELECT id FROM users WHERE role = 'agent'")
    ).fetchall()
    for (user_id,) in agent_rows:
        conn.execute(
            text("UPDATE users SET position_id = :position WHERE id = :user_id"),
            {"position": slug_to_id.get("agent-messaging"), "user_id": user_id},
        )


def run_migration():
    with engine.begin() as conn:
        dialect = conn.dialect.name.lower()
        create_positions_table(conn, dialect)
        ensure_user_position_column(conn, dialect)
        slug_to_id = seed_positions(conn)
        assign_existing_users(conn, slug_to_id)


if __name__ == "__main__":
    run_migration()
