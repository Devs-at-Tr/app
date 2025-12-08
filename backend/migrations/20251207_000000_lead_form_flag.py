from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251207_000000_lead_form_flag"
down_revision = "20251206_120000_align_schema_with_docs"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name.lower()
    columns = []
    for table in ("instagram_messages", "facebook_messages"):
        inspector = sa.inspect(conn)
        existing_cols = {col["name"] for col in inspector.get_columns(table)}
        if "is_lead_form_message" not in existing_cols:
            op.add_column(
                table,
                sa.Column("is_lead_form_message", sa.Boolean(), nullable=False, server_default="0"),
            )
        columns.append(table)

    if dialect != "sqlite":
        # Clean server_default to match models
        for table in columns:
            op.alter_column(
                table,
                "is_lead_form_message",
                existing_type=sa.Boolean(),
                nullable=False,
                server_default="0",
            )


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for table in ("instagram_messages", "facebook_messages"):
        existing_cols = {col["name"] for col in inspector.get_columns(table)}
        if "is_lead_form_message" in existing_cols:
            op.drop_column(table, "is_lead_form_message")
