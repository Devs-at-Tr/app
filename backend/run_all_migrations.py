"""
Run legacy migration scripts and then Alembic migrations in one go.

Legacy migrations expose a run_migration() helper and do not use Alembic's
`op` proxy; newer migrations should be executed through Alembic.
"""
from pathlib import Path
import sys

from alembic import command
from alembic.config import Config

# Ensure backend package is importable
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database import engine, get_database_url  # noqa: E402
from migrations import runner as legacy_runner  # noqa: E402


def run_legacy() -> None:
    """Execute legacy migration scripts that define run_migration."""
    legacy_runner.run_all_migrations(target_engine=engine)


def run_alembic() -> None:
    """Execute Alembic migrations (upgrade to head)."""
    alembic_cfg = Config(str(BASE_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BASE_DIR / "migrations"))
    db_url = get_database_url()
    if db_url:
        # ConfigParser treats % as interpolation; escape to preserve passwords with %.
        safe_url = db_url.replace("%", "%%")
        alembic_cfg.set_main_option("sqlalchemy.url", safe_url)
    command.upgrade(alembic_cfg, "head")


if __name__ == "__main__":
    run_legacy()
    run_alembic()
    print("[OK] Legacy and Alembic migrations completed")
