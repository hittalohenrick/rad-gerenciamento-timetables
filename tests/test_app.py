import os
import sys
from datetime import date, time, timedelta

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.forms import TimetableForm
from app.models import Aluno, Disciplina, Matricula, Presenca, Sala, Timetable, User
from app.routes import find_timetable_conflict, times_overlap


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

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


def create_professor(username="professor", email=None, password="prof12345"):
    if email is None:
        email = f"{username}@login.local"
    professor = User(
        username=username,
        email=email,
        role="professor",
    )
    professor.set_password(password)
    db.session.add(professor)
    db.session.commit()
    return professor


def login(client, username, password):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def login_as_admin(client):
    return login(client, "admin", "admin123")


def test_home_page_requires_login(client):
    response = client.get("/")
    assert response.status_code == 302


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.data


def test_professor_login_redirects_to_professor_dashboard(app, client):
    with app.app_context():
        create_admin()
        create_professor(username="professor-login", email="prof-login@test.com")

    response = login(client, "professor-login", "prof12345")

    assert response.status_code == 200
    assert b"Minhas Turmas" in response.data

    admin_page = client.get("/admin", follow_redirects=True)
    assert admin_page.status_code == 200
    assert b"Acesso restrito ao administrador." in admin_page.data
    assert b"Minhas Turmas" in admin_page.data


def test_professor_overlap_conflict_detection(app):
    with app.app_context():
        professor = create_professor(username="professor1", email="prof1@test.com")
        sala1 = Sala(nome="Sala 1", capacidade=30)
        sala2 = Sala(nome="Sala 2", capacidade=35)
        disciplina1 = Disciplina(nome="Matematica", codigo="MAT001")
        disciplina2 = Disciplina(nome="Fisica", codigo="FIS001")

        db.session.add_all([sala1, sala2, disciplina1, disciplina2])
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
        professor1 = create_professor(username="prof1", email="prof1@test.com")
        professor2 = create_professor(username="prof2", email="prof2@test.com")
        sala = Sala(nome="Sala 1", capacidade=30)
        disciplina1 = Disciplina(nome="Matematica", codigo="MAT001")
        disciplina2 = Disciplina(nome="Fisica", codigo="FIS001")

        db.session.add_all([sala, disciplina1, disciplina2])
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
        create_admin()
        professor = create_professor()
        sala = Sala(nome="Sala A", capacidade=40)
        disciplina = Disciplina(nome="Quimica", codigo="QUI001")
        db.session.add_all([sala, disciplina])
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


def test_prevent_duplicate_professor_login(app, client):
    with app.app_context():
        create_admin()
        create_professor(username="professor", email="prof@test.com")

    login_as_admin(client)
    response = client.post(
        "/professor/new",
        data={
            "username": "professor",
            "password": "Senha123",
            "password2": "Senha123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Ja existe usuario com este nome." in response.data


def test_professor_creation_accepts_simple_password(app, client):
    with app.app_context():
        create_admin()

    login_as_admin(client)
    response = client.post(
        "/professor/new",
        data={
            "username": "novo-prof",
            "password": "abc123",
            "password2": "abc123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Professor registrado com sucesso." in response.data


def test_professor_can_change_own_password(app, client):
    with app.app_context():
        create_admin()
        create_professor(
            username="prof-first-login",
            email="prof-first@test.com",
            password="Prof12345",
        )

    response = login(client, "prof-first-login", "Prof12345")
    assert response.status_code == 200
    assert b"Minhas Turmas" in response.data

    response = client.post(
        "/change-password",
        data={
            "current_password": "Prof12345",
            "new_password": "nova123",
            "new_password2": "nova123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Senha alterada com sucesso." in response.data

    with app.app_context():
        user = User.query.filter_by(username="prof-first-login").first()
        assert user is not None
        assert user.check_password("nova123")


def test_admin_can_create_student(app, client):
    with app.app_context():
        create_admin()

    login_as_admin(client)
    response = client.post(
        "/aluno/new",
        data={"nome": "Aluno Teste", "matricula": "MAT123"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Aluno cadastrado com sucesso." in response.data

    with app.app_context():
        aluno = Aluno.query.filter_by(matricula="MAT123").first()
        assert aluno is not None
        assert aluno.nome == "Aluno Teste"


def test_admin_can_allocate_student_to_timetable(app, client):
    with app.app_context():
        create_admin()
        professor = create_professor()
        sala = Sala(nome="Sala B", capacidade=35)
        disciplina = Disciplina(nome="Historia", codigo="HIS001")
        aluno = Aluno(nome="Aluno A", matricula="A001")
        db.session.add_all([sala, disciplina, aluno])
        db.session.commit()

        timetable = Timetable(
            dia="Terca",
            hora_inicio=time(10, 0),
            hora_fim=time(11, 0),
            sala_id=sala.id,
            professor_id=professor.id,
            disciplina_id=disciplina.id,
        )
        db.session.add(timetable)
        db.session.commit()

        aluno_id = aluno.id
        timetable_id = timetable.id

    login_as_admin(client)
    response = client.post(
        "/matricula/new",
        data={"aluno_id": aluno_id, "timetable_id": timetable_id},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Aluno alocado com sucesso." in response.data

    with app.app_context():
        matricula = Matricula.query.filter_by(aluno_id=aluno_id, timetable_id=timetable_id).first()
        assert matricula is not None


def test_prevent_allocation_when_room_capacity_is_full(app, client):
    with app.app_context():
        create_admin()
        professor = create_professor()
        sala = Sala(nome="Sala Lotada", capacidade=1)
        disciplina = Disciplina(nome="Artes", codigo="ART001")
        aluno1 = Aluno(nome="Aluno 1", matricula="AL001")
        aluno2 = Aluno(nome="Aluno 2", matricula="AL002")
        db.session.add_all([sala, disciplina, aluno1, aluno2])
        db.session.commit()

        timetable = Timetable(
            dia="Sexta",
            hora_inicio=time(10, 0),
            hora_fim=time(11, 0),
            sala_id=sala.id,
            professor_id=professor.id,
            disciplina_id=disciplina.id,
        )
        db.session.add(timetable)
        db.session.commit()

        db.session.add(Matricula(aluno_id=aluno1.id, timetable_id=timetable.id))
        db.session.commit()

        aluno2_id = aluno2.id
        timetable_id = timetable.id

    login_as_admin(client)
    response = client.post(
        "/matricula/new",
        data={"aluno_id": aluno2_id, "timetable_id": timetable_id},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"capacidade da sala ja foi atingida" in response.data


def test_prevent_student_schedule_conflict_in_allocation(app, client):
    with app.app_context():
        create_admin()
        professor1 = create_professor(username="prof-sched-1", email="prof-sched-1@test.com")
        professor2 = create_professor(username="prof-sched-2", email="prof-sched-2@test.com")
        sala1 = Sala(nome="Sala S1", capacidade=30)
        sala2 = Sala(nome="Sala S2", capacidade=30)
        disciplina1 = Disciplina(nome="Ingles", codigo="ING001")
        disciplina2 = Disciplina(nome="Espanhol", codigo="ESP001")
        aluno = Aluno(nome="Aluno Conflito", matricula="ALC001")
        db.session.add_all([sala1, sala2, disciplina1, disciplina2, aluno])
        db.session.commit()

        timetable1 = Timetable(
            dia="Quarta",
            hora_inicio=time(8, 0),
            hora_fim=time(10, 0),
            sala_id=sala1.id,
            professor_id=professor1.id,
            disciplina_id=disciplina1.id,
        )
        timetable2 = Timetable(
            dia="Quarta",
            hora_inicio=time(9, 0),
            hora_fim=time(11, 0),
            sala_id=sala2.id,
            professor_id=professor2.id,
            disciplina_id=disciplina2.id,
        )
        db.session.add_all([timetable1, timetable2])
        db.session.commit()

        db.session.add(Matricula(aluno_id=aluno.id, timetable_id=timetable1.id))
        db.session.commit()

        aluno_id = aluno.id
        timetable2_id = timetable2.id

    login_as_admin(client)
    response = client.post(
        "/matricula/new",
        data={"aluno_id": aluno_id, "timetable_id": timetable2_id},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"conflito de horario para este aluno" in response.data


def test_admin_can_reset_professor_password(app, client):
    with app.app_context():
        create_admin()
        professor = create_professor(username="prof-reset", email="prof-reset@test.com", password="ProfReset123")
        professor_id = professor.id

    login_as_admin(client)
    response = client.post(
        f"/professor/reset-password/{professor_id}",
        data={},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Senha redefinida de prof-reset: 123456." in response.data

    with app.app_context():
        professor = db.session.get(User, professor_id)
        assert professor is not None
        assert professor.check_password("123456")


def test_professor_can_submit_attendance(app, client):
    with app.app_context():
        create_admin()
        professor = create_professor(username="prof-call", email="prof-call@test.com")
        sala = Sala(nome="Sala C", capacidade=25)
        disciplina = Disciplina(nome="Geografia", codigo="GEO001")
        aluno = Aluno(nome="Aluno B", matricula="A002")
        db.session.add_all([sala, disciplina, aluno])
        db.session.commit()

        timetable = Timetable(
            dia="Quarta",
            hora_inicio=time(14, 0),
            hora_fim=time(15, 0),
            sala_id=sala.id,
            professor_id=professor.id,
            disciplina_id=disciplina.id,
        )
        db.session.add(timetable)
        db.session.commit()

        db.session.add(Matricula(aluno_id=aluno.id, timetable_id=timetable.id))
        db.session.commit()

        aluno_id = aluno.id
        timetable_id = timetable.id

    login(client, "prof-call", "prof12345")
    response = client.post(
        f"/professor/turma/{timetable_id}/chamada",
        data={"chamada_data": date(2026, 4, 8).strftime("%d/%m/%Y"), "presentes": [str(aluno_id)]},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Chamada salva com sucesso." in response.data

    with app.app_context():
        presenca = Presenca.query.filter_by(
            aluno_id=aluno_id,
            timetable_id=timetable_id,
            data=date(2026, 4, 8),
        ).first()
        assert presenca is not None
        assert presenca.presente is True


def test_professor_attendance_rejects_future_date(app, client):
    with app.app_context():
        create_admin()
        professor = create_professor(username="prof-future", email="prof-future@test.com")
        sala = Sala(nome="Sala F", capacidade=20)
        disciplina = Disciplina(nome="Banco de Dados", codigo="BD001")
        aluno = Aluno(nome="Aluno Futuro", matricula="AF001")
        db.session.add_all([sala, disciplina, aluno])
        db.session.commit()

        timetable = Timetable(
            dia="Quarta",
            hora_inicio=time(10, 0),
            hora_fim=time(11, 0),
            sala_id=sala.id,
            professor_id=professor.id,
            disciplina_id=disciplina.id,
        )
        db.session.add(timetable)
        db.session.commit()

        db.session.add(Matricula(aluno_id=aluno.id, timetable_id=timetable.id))
        db.session.commit()

        aluno_id = aluno.id
        timetable_id = timetable.id

    future_date = date.today() + timedelta(days=1)
    login(client, "prof-future", "prof12345")
    response = client.post(
        f"/professor/turma/{timetable_id}/chamada",
        data={"chamada_data": future_date.strftime("%d/%m/%Y"), "presentes": [str(aluno_id)]},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Nao e permitido registrar chamada em data futura." in response.data

    with app.app_context():
        presenca = Presenca.query.filter_by(
            aluno_id=aluno_id,
            timetable_id=timetable_id,
            data=future_date,
        ).first()
        assert presenca is None


def test_professor_attendance_rejects_wrong_weekday(app, client):
    with app.app_context():
        create_admin()
        professor = create_professor(username="prof-weekday", email="prof-weekday@test.com")
        sala = Sala(nome="Sala G", capacidade=25)
        disciplina = Disciplina(nome="Algoritmos", codigo="ALG001")
        aluno = Aluno(nome="Aluno Dia", matricula="AD001")
        db.session.add_all([sala, disciplina, aluno])
        db.session.commit()

        timetable = Timetable(
            dia="Quarta",
            hora_inicio=time(8, 0),
            hora_fim=time(10, 0),
            sala_id=sala.id,
            professor_id=professor.id,
            disciplina_id=disciplina.id,
        )
        db.session.add(timetable)
        db.session.commit()

        db.session.add(Matricula(aluno_id=aluno.id, timetable_id=timetable.id))
        db.session.commit()

        aluno_id = aluno.id
        timetable_id = timetable.id
        wrong_date = date(2026, 4, 10)  # Sexta-feira

    login(client, "prof-weekday", "prof12345")
    response = client.post(
        f"/professor/turma/{timetable_id}/chamada",
        data={"chamada_data": wrong_date.strftime("%d/%m/%Y"), "presentes": [str(aluno_id)]},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"deve corresponder ao dia da turma" in response.data

    with app.app_context():
        presenca = Presenca.query.filter_by(
            aluno_id=aluno_id,
            timetable_id=timetable_id,
            data=wrong_date,
        ).first()
        assert presenca is None


def test_professor_cannot_access_other_professor_attendance(app, client):
    with app.app_context():
        create_admin()
        professor_owner = create_professor(username="prof-owner", email="owner@test.com")
        create_professor(username="prof-other", email="other@test.com")
        sala = Sala(nome="Sala D", capacidade=40)
        disciplina = Disciplina(nome="Biologia", codigo="BIO001")
        aluno = Aluno(nome="Aluno C", matricula="A003")
        db.session.add_all([sala, disciplina, aluno])
        db.session.commit()

        timetable = Timetable(
            dia="Quinta",
            hora_inicio=time(9, 0),
            hora_fim=time(10, 0),
            sala_id=sala.id,
            professor_id=professor_owner.id,
            disciplina_id=disciplina.id,
        )
        db.session.add(timetable)
        db.session.commit()

        db.session.add(Matricula(aluno_id=aluno.id, timetable_id=timetable.id))
        db.session.commit()

        timetable_id = timetable.id

    login(client, "prof-other", "prof12345")
    response = client.get(f"/professor/turma/{timetable_id}/chamada", follow_redirects=True)

    assert response.status_code == 200
    assert b"Turma nao encontrada para este professor." in response.data
    assert b"Minhas Turmas" in response.data
