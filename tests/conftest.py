import sys
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app, db
from app.models import User


@pytest.fixture()
def app(tmp_path):
    db_path = tmp_path / "test.db"
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_ENGINE_OPTIONS": {"connect_args": {"check_same_thread": False}},
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(autouse=True)
def app_context(app):
    with app.app_context():
        yield


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user_factory():
    def _create_user(username, role="professor", password="123456", email=None):
        if email is None:
            domain = "admin.local" if role == "admin" else "login.local"
            email = f"{username}@{domain}"

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return _create_user


@pytest.fixture()
def login(client):
    def _login(username, password, follow_redirects=True):
        return client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=follow_redirects,
        )

    return _login
