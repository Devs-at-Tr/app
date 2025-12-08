"""
Bootstrap the schema for a fresh MySQL database by creating every table defined
on the SQLAlchemy metadata. For ongoing environments, prefer running Alembic
migrations to stay aligned with the documented schema.
"""
import sys

from database import Base, engine
import models  # noqa: F401  Ensure all models are imported so metadata is complete


def create_all_tables() -> bool:
    try:
        print("Creating all tables from SQLAlchemy metadata...")
        Base.metadata.create_all(bind=engine)
        print("All tables created.")
        return True
    except Exception as exc:  # pragma: no cover - setup utility
        print(f"Error creating tables: {exc}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("MySQL Schema Bootstrap")
    print("=" * 50)

    success = create_all_tables()
    if success:
        print("\nSchema creation completed successfully.")
        print("Next steps: run Alembic migrations going forward to stay aligned.")
        sys.exit(0)
    else:
        print("\nSchema creation failed.")
        sys.exit(1)
