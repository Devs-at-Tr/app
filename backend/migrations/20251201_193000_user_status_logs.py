from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, MetaData, Table
from sqlalchemy.sql import func
from database import engine


def run_migration(target_engine=None):
    eng = target_engine or engine
    metadata = MetaData()
    Table(
        "user_status_logs",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("user_id", String(36), ForeignKey("users.id"), nullable=False, index=True),
        Column("changed_by", String(255), nullable=False),
        Column("changed_to", Boolean, nullable=False),
        Column("changed_at", DateTime(timezone=True), server_default=func.now()),
        Column("note", Text, nullable=True),
    )
    metadata.create_all(eng, checkfirst=True)


def upgrade(engine=None):
    run_migration(engine)
