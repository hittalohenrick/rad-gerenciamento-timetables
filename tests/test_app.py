import os
import sys
from datetime import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.forms import TimetableForm
from app.models import Disciplina, Sala, Timetable, User
from app.routes import find_timetable_conflict, times_overlap


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def create_admin():
    admin = User(username="admin", email="admin@test.com", role="admin")
    admin.set_password("admin123")
    db.session.add(admin)
    db.session.commit()
    return admin


def login_as_admin(client):
    return client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )


def test_home_page_requires_login(client):
    response = client.get("/")
    assert response.status_code == 302


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.data


def test_non_admin_login_is_blocked(app, client):
    with app.app_context():
        create_admin()
        professor = User(username="professor-login", email="prof-login@test.com", role="professor")
        professor.set_password("prof12345")
        db.session.add(professor)
        db.session.commit()

    response = client.post(
        "/login",
        data={"username": "professor-login", "password": "prof12345"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Apenas o admin pode fazer login neste sistema." in response.data
    assert b"Login" in response.data

    admin_page = client.get("/admin")
    assert admin_page.status_code == 302


def test_professor_overlap_conflict_detection(app):
    with app.app_context():
        professor = User(username="professor1", email="prof1@test.com", role="professor")
        professor.set_password("prof12345")
        sala1 = Sala(nome="Sala 1", capacidade=30)
        sala2 = Sala(nome="Sala 2", capacidade=35)
        disciplina1 = Disciplina(nome="Matematica", codigo="MAT001")
        disciplina2 = Disciplina(nome="Fisica", codigo="FIS001")

        db.session.add_all([professor, sala1, sala2, disciplina1, disciplina2])
        db.session.commit()

        timetable1 = Timetable(
            dia="Segunda",
            hora_inicio=time(8, 0),
            hora_fim=time(10, 0),
            sala_id=sala1.id,
            professor_id=professor.id,
            disciplina_id=disciplina1.id,
        )
        db.session.add(timetable1)
        db.session.commit()

        assert times_overlap(timetable1.hora_inicio, timetable1.hora_fim, time(9, 0), time(11, 0))

        conflict = find_timetable_conflict(
            dia="Segunda",
            hora_inicio=time(9, 0),
            hora_fim=time(11, 0),
            sala_id=sala2.id,
            professor_id=professor.id,
        )
        assert conflict is not None
        assert "professor" in conflict.lower()


def test_room_overlap_conflict_detection(app):
    with app.app_context():
        professor1 = User(username="prof1", email="prof1@test.com", role="professor")
        professor2 = User(username="prof2", email="prof2@test.com", role="professor")
        professor1.set_password("prof12345")
        professor2.set_password("prof12345")
        sala = Sala(nome="Sala 1", capacidade=30)
        disciplina1 = Disciplina(nome="Matematica", codigo="MAT001")
        disciplina2 = Disciplina(nome="Fisica", codigo="FIS001")

        db.session.add_all([professor1, professor2, sala, disciplina1, disciplina2])
        db.session.commit()

        timetable1 = Timetable(
            dia="Segunda",
            hora_inicio=time(8, 0),
            hora_fim=time(10, 0),
            sala_id=sala.id,
            professor_id=professor1.id,
            disciplina_id=disciplina1.id,
        )
        db.session.add(timetable1)
        db.session.commit()

        conflict = find_timetable_conflict(
            dia="Segunda",
            hora_inicio=time(9, 0),
            hora_fim=time(11, 0),
            sala_id=sala.id,
            professor_id=professor2.id,
        )
        assert conflict is not None
        assert "sala" in conflict.lower()


def test_invalid_time_range_validation(app):
    with app.test_request_context():
        form = TimetableForm(meta={"csrf": False})
        form.dia.data = "Segunda"
        form.hora_inicio.data = time(10, 0)
        form.hora_fim.data = time(9, 0)

        form.sala_id.choices = [(1, "Sala 1")]
        form.professor_id.choices = [(1, "Professor")]
        form.disciplina_id.choices = [(1, "Disciplina")]
        form.sala_id.data = 1
        form.professor_id.data = 1
        form.disciplina_id.data = 1

        assert not form.validate()
        assert len(form.hora_fim.errors) > 0
        assert "inicio" in form.hora_fim.errors[0].lower()


def test_manual_time_input_accepts_non_fixed_intervals(app):
    with app.test_request_context():
        form = TimetableForm(meta={"csrf": False})
        form.dia.data = "Segunda"
        form.hora_inicio.data = time(20, 0)
        form.hora_fim.data = time(21, 30)

        form.sala_id.choices = [(1, "Sala 1")]
        form.professor_id.choices = [(1, "Professor")]
        form.disciplina_id.choices = [(1, "Disciplina")]
        form.sala_id.data = 1
        form.professor_id.data = 1
        form.disciplina_id.data = 1

        assert form.validate()


def test_prevent_delete_sala_with_timetable(app, client):
    with app.app_context():
        admin = create_admin()

        professor = User(username="professor", email="prof@test.com", role="professor")
        professor.set_password("prof12345")
        sala = Sala(nome="Sala A", capacidade=40)
        disciplina = Disciplina(nome="Quimica", codigo="QUI001")
        db.session.add_all([professor, sala, disciplina])
        db.session.commit()

        timetable = Timetable(
            dia="Segunda",
            hora_inicio=time(7, 0),
            hora_fim=time(8, 0),
            sala_id=sala.id,
            professor_id=professor.id,
            disciplina_id=disciplina.id,
        )
        db.session.add(timetable)
        db.session.commit()

        sala_id = sala.id

    login_as_admin(client)
    response = client.post(f"/sala/delete/{sala_id}", data={}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Nao e possivel deletar sala com alocacoes vinculadas." in response.data

    with app.app_context():
        assert db.session.get(Sala, sala_id) is not None


def test_delete_routes_disallow_get_method(app, client):
    with app.app_context():
        create_admin()
        sala = Sala(nome="Sala Teste", capacidade=20)
        db.session.add(sala)
        db.session.commit()
        sala_id = sala.id

    login_as_admin(client)
    response = client.get(f"/sala/delete/{sala_id}")
    assert response.status_code == 405


def test_prevent_duplicate_professor_email(app, client):
    with app.app_context():
        create_admin()
        professor = User(username="professor", email="prof@test.com", role="professor")
        professor.set_password("prof12345")
        db.session.add(professor)
        db.session.commit()

    login_as_admin(client)
    response = client.post(
        "/professor/new",
        data={"username": "outro-prof", "email": "prof@test.com"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Ja existe usuario com este email." in response.data
