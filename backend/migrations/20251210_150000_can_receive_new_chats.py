from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251210_150000_can_receive_new_chats"
down_revision = "20251207_000000_lead_form_flag"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {col["name"] for col in inspector.get_columns("users")}
    if "can_receive_new_chats" not in existing_columns:
        op.add_column(
            "users",
            sa.Column(
                "can_receive_new_chats",
                sa.Boolean(),
                nullable=False,
                server_default="1",
            ),
        )

    dialect = conn.dialect.name.lower()
    if dialect != "sqlite":
        default_value = "TRUE" if dialect in ("postgresql", "postgres") else "1"
        op.alter_column(
            "users",
            "can_receive_new_chats",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=default_value,
        )


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {col["name"] for col in inspector.get_columns("users")}
    if "can_receive_new_chats" in existing_columns:
        op.drop_column("users", "can_receive_new_chats")
