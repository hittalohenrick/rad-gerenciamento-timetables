import sqlite3

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Engine

from config import Config


db = SQLAlchemy()
login_manager = LoginManager()


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """Ensure SQLite foreign keys are enabled."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(config_overrides=None):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    login_manager.init_app(app)

    # Importa os modelos para registrar metadata das tabelas.
    from app import models  # noqa: F401

    login_manager.login_view = "main.login"
    login_manager.login_message = "Faca login para acessar esta pagina."

    from app.routes import bp

    app.register_blueprint(bp)

    with app.app_context():
        db.create_all()
        _ensure_runtime_schema()

    return app


def _ensure_runtime_schema():
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    if "timetable" in tables:
        timetable_columns = {column["name"] for column in inspector.get_columns("timetable")}
        if "turma_id" not in timetable_columns:
            db.session.execute(text("ALTER TABLE timetable ADD COLUMN turma_id INTEGER"))
            db.session.commit()

    if "matricula" in tables:
        matricula_columns = {column["name"] for column in inspector.get_columns("matricula")}
        if "turma_id" not in matricula_columns:
            db.session.execute(text("ALTER TABLE matricula ADD COLUMN turma_id INTEGER"))
            db.session.commit()

    if "curso" in tables:
        curso_columns = {column["name"] for column in inspector.get_columns("curso")}
        if "quantidade_periodos" not in curso_columns:
            db.session.execute(text("ALTER TABLE curso ADD COLUMN quantidade_periodos INTEGER DEFAULT 8"))
            db.session.execute(
                text("UPDATE curso SET quantidade_periodos = 8 WHERE quantidade_periodos IS NULL")
            )
            db.session.commit()

    if "turma" in tables:
        turma_columns = {column["name"] for column in inspector.get_columns("turma")}
        if "turno" not in turma_columns:
            db.session.execute(text("ALTER TABLE turma ADD COLUMN turno VARCHAR(20) DEFAULT 'noturno'"))
            db.session.execute(text("UPDATE turma SET turno = 'noturno' WHERE turno IS NULL"))
            db.session.commit()

    if "timetable" in tables:
        timetable_columns_info = {column["name"]: column for column in inspector.get_columns("timetable")}
        professor_column = timetable_columns_info.get("professor_id")
        if professor_column and professor_column.get("nullable") is False:
            db.session.execute(text("PRAGMA foreign_keys=OFF"))
            db.session.execute(
                text(
                    """
                    CREATE TABLE timetable_new (
                        id INTEGER NOT NULL PRIMARY KEY,
                        dia VARCHAR(20) NOT NULL,
                        hora_inicio TIME NOT NULL,
                        hora_fim TIME NOT NULL,
                        sala_id INTEGER NOT NULL,
                        professor_id INTEGER,
                        disciplina_id INTEGER NOT NULL,
                        turma_id INTEGER NOT NULL,
                        FOREIGN KEY(sala_id) REFERENCES sala (id),
                        FOREIGN KEY(professor_id) REFERENCES user (id),
                        FOREIGN KEY(disciplina_id) REFERENCES disciplina (id),
                        FOREIGN KEY(turma_id) REFERENCES turma (id),
                        CONSTRAINT unique_dia_horario_sala UNIQUE (dia, hora_inicio, hora_fim, sala_id),
                        CONSTRAINT unique_dia_horario_professor UNIQUE (dia, hora_inicio, hora_fim, professor_id),
                        CONSTRAINT unique_dia_horario_turma UNIQUE (dia, hora_inicio, hora_fim, turma_id)
                    )
                    """
                )
            )
            db.session.execute(
                text(
                    """
                    INSERT INTO timetable_new (
                        id, dia, hora_inicio, hora_fim, sala_id, professor_id, disciplina_id, turma_id
                    )
                    SELECT id, dia, hora_inicio, hora_fim, sala_id, professor_id, disciplina_id, turma_id
                    FROM timetable
                    """
                )
            )
            db.session.execute(text("DROP TABLE timetable"))
            db.session.execute(text("ALTER TABLE timetable_new RENAME TO timetable"))
            db.session.execute(text("PRAGMA foreign_keys=ON"))
            db.session.commit()
