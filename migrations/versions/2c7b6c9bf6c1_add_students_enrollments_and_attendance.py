"""Add students, enrollments and attendance

Revision ID: 2c7b6c9bf6c1
Revises: a3fd5de956b3
Create Date: 2026-04-11 16:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2c7b6c9bf6c1"
down_revision = "a3fd5de956b3"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "aluno" not in existing_tables:
        op.create_table(
            "aluno",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=120), nullable=False),
            sa.Column("matricula", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("matricula"),
        )

    if "matricula" not in existing_tables:
        op.create_table(
            "matricula",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("aluno_id", sa.Integer(), nullable=False),
            sa.Column("timetable_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["aluno_id"], ["aluno.id"]),
            sa.ForeignKeyConstraint(["timetable_id"], ["timetable.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("aluno_id", "timetable_id", name="unique_aluno_turma"),
        )

    if "presenca" not in existing_tables:
        op.create_table(
            "presenca",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("data", sa.Date(), nullable=False),
            sa.Column("presente", sa.Boolean(), nullable=False),
            sa.Column("aluno_id", sa.Integer(), nullable=False),
            sa.Column("timetable_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["aluno_id"], ["aluno.id"]),
            sa.ForeignKeyConstraint(["timetable_id"], ["timetable.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("data", "aluno_id", "timetable_id", name="unique_presenca_data_aluno_turma"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "presenca" in existing_tables:
        op.drop_table("presenca")
    if "matricula" in existing_tables:
        op.drop_table("matricula")
    if "aluno" in existing_tables:
        op.drop_table("aluno")
