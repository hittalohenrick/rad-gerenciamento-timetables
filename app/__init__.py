import sqlite3

from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, inspect
from sqlalchemy.engine import Engine

from config import Config


db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


REQUIRED_TABLES = {"user", "sala", "disciplina", "timetable", "aluno", "matricula", "presenca"}


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """Ensure SQLite foreign keys are enabled."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def ensure_minimum_schema(app):
    """Recover local SQLite database when tables are missing."""
    with app.app_context():
        existing_tables = set(inspect(db.engine).get_table_names())
        if not REQUIRED_TABLES.issubset(existing_tables):
            db.create_all()


def create_app(config_overrides=None):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Importa os modelos antes de create_all para registrar metadata das tabelas.
    from app import models  # noqa: F401

    if not app.config.get("TESTING", False):
        ensure_minimum_schema(app)

    login_manager.login_view = "main.login"
    login_manager.login_message = "Faca login para acessar esta pagina."

    from app.routes import bp

    app.register_blueprint(bp)

    return app
