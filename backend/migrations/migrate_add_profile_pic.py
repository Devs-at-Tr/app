from sqlalchemy import create_engine, text
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# Get database URL from environment or use SQLite as fallback
database_url = os.getenv('DATABASE_URL', f"sqlite:///{ROOT_DIR / 'ticklegram.db'}")
engine = create_engine(database_url)


def run_migration():
    """Add profile_pic_url column to chats table in a dialect-safe, idempotent way.

    Supports sqlite, postgresql and mysql/mariadb. If the column already exists,
    the migration is a no-op.
    """
    try:
        with engine.connect() as conn:
            dialect = engine.dialect.name.lower()

            if dialect == 'sqlite':
                # Check pragma to avoid duplicate column error
                rows = conn.execute(text("PRAGMA table_info(chats)"))
                cols = [r[1] for r in rows.fetchall()]
                if 'profile_pic_url' not in cols:
                    conn.execute(text('ALTER TABLE chats ADD COLUMN profile_pic_url TEXT'))

            elif dialect in ('postgresql', 'postgres'):
                # Use a safe DO block to conditionally add the column
                conn.execute(text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name='chats' AND column_name='profile_pic_url'
                        ) THEN
                            ALTER TABLE chats ADD COLUMN profile_pic_url TEXT;
                        END IF;
                    END$$;
                """))

            elif dialect in ('mysql', 'mariadb'):
                # For MySQL/MariaDB check information_schema then alter
                dbname = conn.execute(text('SELECT DATABASE()')).scalar()
                exists = conn.execute(
                    text("""
                        SELECT COUNT(*) FROM information_schema.columns
                        WHERE table_schema = :db AND table_name = 'chats' AND column_name = 'profile_pic_url'
                    """),
                    {'db': dbname}
                ).scalar()
                if exists == 0:
                    # MySQL supports ADD COLUMN IF NOT EXISTS in newer versions, but using a guarded ALTER is safer
                    conn.execute(text('ALTER TABLE chats ADD COLUMN profile_pic_url TEXT'))

            else:
                # Fallback: try to add the column and ignore duplicate-column errors
                try:
                    conn.execute(text('ALTER TABLE chats ADD COLUMN profile_pic_url TEXT'))
                except Exception:
                    pass

            conn.commit()
            print("[OK] Successfully ensured profile_pic_url column exists on chats table")

    except Exception as e:
        print(f"⚠ Error during migration: {e}")
        raise


if __name__ == "__main__":
    run_migration()
