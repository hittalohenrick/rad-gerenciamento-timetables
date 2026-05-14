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
