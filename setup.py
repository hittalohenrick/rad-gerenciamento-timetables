from app import create_app, db
from app.models import User


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


def initialize():
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Banco SQLite inicializado com sucesso.")
        ensure_admin_user()


if __name__ == "__main__":
    initialize()
