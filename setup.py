from __future__ import annotations

import argparse
from pathlib import Path

from app import create_app, db
from app.models import User

INSTANCE_DB = Path("instance/app.db")


def ensure_admin_user():
    admin = User.query.filter_by(role="admin").first()
    if admin:
        print(f"Admin ja existe: {admin.username}")
        return

    admin = User(username="admin", email="admin@example.com", role="admin")
    admin.set_password("Admin1234")
    db.session.add(admin)
    db.session.commit()
    print("Admin criado: admin / Admin1234")


def reset_database_file():
    if INSTANCE_DB.exists():
        INSTANCE_DB.unlink()
        print(f"Banco removido: {INSTANCE_DB}")
    else:
        print("Banco nao existia, seguindo com inicializacao limpa.")


def initialize(reset_db=False):
    if reset_db:
        reset_database_file()

    app = create_app()
    with app.app_context():
        db.create_all()
        print("Banco SQLite inicializado com sucesso.")
        ensure_admin_user()


def parse_args():
    parser = argparse.ArgumentParser(description="Inicializa ambiente local do sistema de timetables.")
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Remove instance/app.db antes de inicializar.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    initialize(reset_db=args.reset_db)
