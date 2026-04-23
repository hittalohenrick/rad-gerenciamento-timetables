"""Remove legacy password policy fields from user

Revision ID: c2b0d9c4f7a1
Revises: 8f31c2ab09d4
Create Date: 2026-04-20 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c2b0d9c4f7a1"
down_revision = "8f31c2ab09d4"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("user")}

    if "password_changed_at" in existing_columns:
        op.drop_column("user", "password_changed_at")
    if "must_change_password" in existing_columns:
        op.drop_column("user", "must_change_password")


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("user")}

    if "must_change_password" not in existing_columns:
        op.add_column(
            "user",
            sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    if "password_changed_at" not in existing_columns:
        op.add_column(
            "user",
            sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        )
