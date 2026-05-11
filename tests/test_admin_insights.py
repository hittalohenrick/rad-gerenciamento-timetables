from datetime import time

from app import db
from app.models import Aluno, Disciplina, Matricula, Sala, Timetable


def test_admin_dashboard_hides_insights_panel(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    prof_1 = user_factory("prof_1", role="professor", password="123456", email="prof_1@login.local")
    user_factory("prof_2", role="professor", password="123456", email="prof_2@login.local")

    sala_critica = Sala(nome="Sala Critica", capacidade=2)
    sala_regular = Sala(nome="Sala Regular", capacidade=10)
    disc_a = Disciplina(nome="Algoritmos", codigo="ALG001")
    disc_b = Disciplina(nome="Banco", codigo="BAN001")
    db.session.add_all([sala_critica, sala_regular, disc_a, disc_b])
    db.session.commit()

    t1 = Timetable(
        dia="Segunda",
        hora_inicio=time(8, 0),
        hora_fim=time(9, 0),
        sala_id=sala_critica.id,
        professor_id=prof_1.id,
        disciplina_id=disc_a.id,
    )
    t2 = Timetable(
        dia="Terca",
        hora_inicio=time(8, 0),
        hora_fim=time(9, 0),
        sala_id=sala_regular.id,
        professor_id=prof_1.id,
        disciplina_id=disc_b.id,
    )
    t3 = Timetable(
        dia="Quarta",
        hora_inicio=time(8, 0),
        hora_fim=time(9, 0),
        sala_id=sala_regular.id,
        professor_id=prof_1.id,
        disciplina_id=disc_a.id,
    )
    t4 = Timetable(
        dia="Quinta",
        hora_inicio=time(8, 0),
        hora_fim=time(9, 0),
        sala_id=sala_regular.id,
        professor_id=prof_1.id,
        disciplina_id=disc_b.id,
    )
    db.session.add_all([t1, t2, t3, t4])
    db.session.commit()

    aluno_1 = Aluno(nome="Aluno 1", matricula="A001")
    aluno_2 = Aluno(nome="Aluno 2", matricula="A002")
    aluno_3 = Aluno(nome="Aluno 3", matricula="A003")
    db.session.add_all([aluno_1, aluno_2, aluno_3])
    db.session.commit()

    db.session.add_all(
        [
            Matricula(aluno_id=aluno_1.id, timetable_id=t1.id),
            Matricula(aluno_id=aluno_2.id, timetable_id=t1.id),
            Matricula(aluno_id=aluno_3.id, timetable_id=t2.id),
        ]
    )
    db.session.commit()

    login("admin", "Admin1234")

    response = client.get("/admin")

    assert response.status_code == 200
    assert b"Dashboard Administrativo" in response.data
    assert b"Insights para Decisao" not in response.data
    assert b"Turmas Sem Alunos" not in response.data


def test_admin_insights_page_is_available(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    login("admin", "Admin1234")

    response = client.get("/admin/insights")

    assert response.status_code == 200
    assert b"Insights Administrativos" in response.data
    assert b"Voltar ao Dashboard" in response.data
    assert b"Ocupacao por Sala" in response.data
    assert b"Carga de Turmas por Professor" in response.data
