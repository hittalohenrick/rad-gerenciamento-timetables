"""Initial migration

Revision ID: a3fd5de956b3
Revises: 
Create Date: 2026-03-23 21:50:39.773018

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3fd5de956b3'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "disciplina" not in existing_tables:
        op.create_table(
            "disciplina",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=100), nullable=False),
            sa.Column("codigo", sa.String(length=20), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("codigo"),
        )

    if "sala" not in existing_tables:
        op.create_table(
            "sala",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=100), nullable=False),
            sa.Column("capacidade", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if "user" not in existing_tables:
        op.create_table(
            "user",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=64), nullable=False),
            sa.Column("email", sa.String(length=120), nullable=False),
            sa.Column("password_hash", sa.String(length=128), nullable=True),
            sa.Column("role", sa.String(length=20), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
            sa.UniqueConstraint("username"),
        )

    if "timetable" not in existing_tables:
        op.create_table(
            "timetable",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("dia", sa.String(length=20), nullable=False),
            sa.Column("hora_inicio", sa.Time(), nullable=False),
            sa.Column("hora_fim", sa.Time(), nullable=False),
            sa.Column("sala_id", sa.Integer(), nullable=False),
            sa.Column("professor_id", sa.Integer(), nullable=False),
            sa.Column("disciplina_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["disciplina_id"], ["disciplina.id"]),
            sa.ForeignKeyConstraint(["professor_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["sala_id"], ["sala.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("dia", "hora_inicio", "hora_fim", "professor_id", name="unique_dia_horario_professor"),
            sa.UniqueConstraint("dia", "hora_inicio", "hora_fim", "sala_id", name="unique_dia_horario_sala"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "timetable" in existing_tables:
        op.drop_table("timetable")
    if "user" in existing_tables:
        op.drop_table("user")
    if "sala" in existing_tables:
        op.drop_table("sala")
    if "disciplina" in existing_tables:
        op.drop_table("disciplina")
