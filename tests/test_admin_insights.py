from datetime import time

from app import db
from app.models import (
    Aluno,
    Curso,
    Disciplina,
    GradeCurricular,
    GradeCurricularItem,
    Matricula,
    Sala,
    Timetable,
    Turma,
)


def _setup_academic_catalog():
    curso = Curso(nome="Analise e Desenvolvimento de Sistemas", codigo="ADS", ativo=True, quantidade_periodos=8)
    disc_a = Disciplina(nome="Algoritmos", codigo="ALG001")
    disc_b = Disciplina(nome="Banco", codigo="BAN001")
    db.session.add_all([curso, disc_a, disc_b])
    db.session.flush()

    grade = GradeCurricular(nome="Grade ADS 2026", curso_id=curso.id, ativa=True)
    db.session.add(grade)
    db.session.flush()

    db.session.add_all(
        [
            GradeCurricularItem(grade_id=grade.id, disciplina_id=disc_a.id, periodo=1),
            GradeCurricularItem(grade_id=grade.id, disciplina_id=disc_b.id, periodo=1),
        ]
    )

    turma_a = Turma(
        curso_id=curso.id,
        codigo="ADS-1A",
        semestre_letivo="2026.1",
        periodo=1,
        quantidade_alunos=40,
    )
    turma_b = Turma(
        curso_id=curso.id,
        codigo="ADS-1B",
        semestre_letivo="2026.1",
        periodo=1,
        quantidade_alunos=40,
    )
    db.session.add_all([turma_a, turma_b])
    db.session.commit()
    return disc_a, disc_b, turma_a, turma_b


def test_admin_dashboard_hides_insights_panel(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    prof_1 = user_factory("prof_1", role="professor", password="123456", email="prof_1@login.local")
    user_factory("prof_2", role="professor", password="123456", email="prof_2@login.local")

    sala_critica = Sala(nome="Sala Critica", capacidade=2)
    sala_regular = Sala(nome="Sala Regular", capacidade=10)
    disc_a, disc_b, turma_a, turma_b = _setup_academic_catalog()
    db.session.add_all([sala_critica, sala_regular])
    db.session.commit()

    t1 = Timetable(
        dia="Segunda",
        hora_inicio=time(8, 0),
        hora_fim=time(9, 0),
        sala_id=sala_critica.id,
        professor_id=prof_1.id,
        disciplina_id=disc_a.id,
        turma_id=turma_a.id,
    )
    t2 = Timetable(
        dia="Terca",
        hora_inicio=time(8, 0),
        hora_fim=time(9, 0),
        sala_id=sala_regular.id,
        professor_id=prof_1.id,
        disciplina_id=disc_b.id,
        turma_id=turma_b.id,
    )
    t3 = Timetable(
        dia="Quarta",
        hora_inicio=time(8, 0),
        hora_fim=time(9, 0),
        sala_id=sala_regular.id,
        professor_id=prof_1.id,
        disciplina_id=disc_a.id,
        turma_id=turma_a.id,
    )
    t4 = Timetable(
        dia="Quinta",
        hora_inicio=time(8, 0),
        hora_fim=time(9, 0),
        sala_id=sala_regular.id,
        professor_id=prof_1.id,
        disciplina_id=disc_b.id,
        turma_id=turma_b.id,
    )
    db.session.add_all([t1, t2, t3, t4])
    db.session.commit()

    aluno_1 = Aluno(nome="Aluno 1", matricula="A001", curso_id=turma_a.curso_id)
    aluno_2 = Aluno(nome="Aluno 2", matricula="A002", curso_id=turma_a.curso_id)
    aluno_3 = Aluno(nome="Aluno 3", matricula="A003", curso_id=turma_b.curso_id)
    db.session.add_all([aluno_1, aluno_2, aluno_3])
    db.session.commit()

    db.session.add_all(
        [
            Matricula(aluno_id=aluno_1.id, turma_id=turma_a.id),
            Matricula(aluno_id=aluno_2.id, turma_id=turma_a.id),
            Matricula(aluno_id=aluno_3.id, turma_id=turma_b.id),
        ]
    )
    db.session.commit()

    login("admin", "Admin1234")

    response = client.get("/admin")

    assert response.status_code == 200
    assert b"Painel Administrativo" in response.data
    assert b"Insights para Decisao" not in response.data
    assert b"Capacidade de Novas Turmas" in response.data
    assert b"Capacidade Docente" in response.data
    assert b"Matutino" in response.data
    assert b"Vespertino" in response.data
    assert b"Noturno" in response.data


def test_admin_insights_page_is_available(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    login("admin", "Admin1234")

    response = client.get("/admin/insights")

    assert response.status_code == 200
    assert b"Insights Administrativos" in response.data
    assert b"Voltar ao Dashboard" in response.data
    assert b"Ocupacao por Sala" in response.data
    assert b"Carga de Turmas por Professor" in response.data
    assert b"Capacidade por Turno" in response.data
    assert b"Matutino" in response.data
    assert b"Vespertino" in response.data
    assert b"Noturno" in response.data
