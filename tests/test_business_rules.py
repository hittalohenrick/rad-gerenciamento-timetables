from datetime import date, time, timedelta

from app import db
from app.models import (
    Aluno,
    Curso,
    Disciplina,
    GradeCurricular,
    GradeCurricularItem,
    Matricula,
    Presenca,
    Sala,
    Timetable,
    Turma,
)
from app.routes.helpers import find_timetable_conflict
from app.routes.professor import suggested_attendance_date


def _setup_academic_catalog(
    *,
    curso_nome="Analise e Desenvolvimento de Sistemas",
    curso_codigo="ADS",
    disciplina_nome="Matematica",
    disciplina_codigo="MAT001",
    turma_codigo="ADS-1A",
    semestre_letivo="2026.1",
    periodo=1,
    quantidade_alunos=40,
):
    curso = Curso(nome=curso_nome, codigo=curso_codigo, ativo=True, quantidade_periodos=8)
    disciplina = Disciplina(nome=disciplina_nome, codigo=disciplina_codigo)
    db.session.add_all([curso, disciplina])
    db.session.flush()

    grade = GradeCurricular(nome=f"Grade {curso_codigo} 2026", curso_id=curso.id, ativa=True)
    db.session.add(grade)
    db.session.flush()

    db.session.add(
        GradeCurricularItem(grade_id=grade.id, disciplina_id=disciplina.id, periodo=periodo)
    )

    turma = Turma(
        curso_id=curso.id,
        codigo=turma_codigo,
        semestre_letivo=semestre_letivo,
        periodo=periodo,
        quantidade_alunos=quantidade_alunos,
    )
    db.session.add(turma)
    db.session.commit()
    return disciplina, turma


def test_find_timetable_conflict_identifies_room_overlap(user_factory):
    prof_a = user_factory("prof_a", role="professor", password="123456", email="prof_a@login.local")
    prof_b = user_factory("prof_b", role="professor", password="123456", email="prof_b@login.local")

    sala_a = Sala(nome="Sala A", capacidade=20)
    sala_b = Sala(nome="Sala B", capacidade=20)
    disc, turma = _setup_academic_catalog()
    db.session.add_all([sala_a, sala_b])
    db.session.commit()

    existing = Timetable(
        dia="Segunda",
        hora_inicio=time(8, 0),
        hora_fim=time(10, 0),
        sala_id=sala_a.id,
        professor_id=prof_a.id,
        disciplina_id=disc.id,
        turma_id=turma.id,
    )
    db.session.add(existing)
    db.session.commit()

    conflict = find_timetable_conflict(
        dia="Segunda",
        hora_inicio=time(9, 0),
        hora_fim=time(11, 0),
        sala_id=sala_a.id,
        professor_id=prof_b.id,
    )

    assert conflict == "Conflito: a sala ja possui alocacao em horario sobreposto."


def test_matricula_blocks_when_capacity_is_reached(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    prof = user_factory("professor1", role="professor", password="123456", email="professor1@login.local")

    sala = Sala(nome="Sala Capacidade", capacidade=40)
    disc, turma = _setup_academic_catalog(
        curso_nome="Ciencia da Computacao",
        curso_codigo="CC",
        disciplina_nome="Fisica",
        disciplina_codigo="FIS001",
        turma_codigo="CC-1A",
        quantidade_alunos=1,
    )
    db.session.add(sala)
    db.session.commit()

    oferta = Timetable(
        dia="Segunda",
        hora_inicio=time(8, 0),
        hora_fim=time(9, 0),
        sala_id=sala.id,
        professor_id=prof.id,
        disciplina_id=disc.id,
        turma_id=turma.id,
    )
    aluno_1 = Aluno(nome="Aluno Um", matricula="A001")
    aluno_2 = Aluno(nome="Aluno Dois", matricula="A002")
    db.session.add_all([oferta, aluno_1, aluno_2])
    db.session.commit()

    login("admin", "Admin1234")

    first_enroll = client.post(
        "/matricula/new",
        data={"aluno_id": str(aluno_1.id), "turma_id": str(turma.id)},
        follow_redirects=True,
    )
    assert first_enroll.status_code == 200
    assert b"Aluno alocado com sucesso." in first_enroll.data

    second_enroll = client.post(
        "/matricula/new",
        data={"aluno_id": str(aluno_2.id), "turma_id": str(turma.id)},
        follow_redirects=True,
    )
    assert second_enroll.status_code == 200
    assert b"capacidade prevista da turma foi atingida" in second_enroll.data
    assert Matricula.query.filter_by(turma_id=turma.id).count() == 1


def test_professor_attendance_blocks_future_dates(client, login, user_factory):
    prof = user_factory("professor2", role="professor", password="123456", email="professor2@login.local")

    sala = Sala(nome="Sala Chamada", capacidade=30)
    disc, turma_ref = _setup_academic_catalog(
        curso_nome="Engenharia de Software",
        curso_codigo="ES",
        disciplina_nome="Historia",
        disciplina_codigo="HIS001",
        turma_codigo="ES-1A",
    )
    aluno = Aluno(nome="Aluno Presenca", matricula="A100")
    db.session.add_all([sala, aluno])
    db.session.commit()

    turma = Timetable(
        dia="Segunda",
        hora_inicio=time(10, 0),
        hora_fim=time(11, 0),
        sala_id=sala.id,
        professor_id=prof.id,
        disciplina_id=disc.id,
        turma_id=turma_ref.id,
    )
    db.session.add(turma)
    db.session.commit()

    db.session.add(Matricula(aluno_id=aluno.id, turma_id=turma_ref.id))
    db.session.commit()

    login("professor2", "123456")

    future_date = (date.today() + timedelta(days=1)).strftime("%d/%m/%Y")
    response = client.post(
        f"/professor/turma/{turma.id}/chamada",
        data={"chamada_data": future_date, "presentes": [str(aluno.id)]},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Nao e permitido registrar chamada em data futura." in response.data
    assert Presenca.query.count() == 0


def test_professor_attendance_saves_valid_date(client, login, user_factory):
    prof = user_factory("professor3", role="professor", password="123456", email="professor3@login.local")

    sala = Sala(nome="Sala Chamada 2", capacidade=30)
    disc, turma_ref = _setup_academic_catalog(
        curso_nome="Sistemas de Informacao",
        curso_codigo="SI",
        disciplina_nome="Geografia",
        disciplina_codigo="GEO001",
        turma_codigo="SI-1A",
    )
    aluno = Aluno(nome="Aluno Presente", matricula="A101")
    db.session.add_all([sala, aluno])
    db.session.commit()

    turma = Timetable(
        dia="Segunda",
        hora_inicio=time(13, 0),
        hora_fim=time(14, 0),
        sala_id=sala.id,
        professor_id=prof.id,
        disciplina_id=disc.id,
        turma_id=turma_ref.id,
    )
    db.session.add(turma)
    db.session.commit()

    db.session.add(Matricula(aluno_id=aluno.id, turma_id=turma_ref.id))
    db.session.commit()

    login("professor3", "123456")

    valid_date = suggested_attendance_date("Segunda").strftime("%d/%m/%Y")
    response = client.post(
        f"/professor/turma/{turma.id}/chamada",
        data={"chamada_data": valid_date, "presentes": [str(aluno.id)]},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Chamada salva com sucesso." in response.data
    presenca = Presenca.query.filter_by(aluno_id=aluno.id, timetable_id=turma.id).first()
    assert presenca is not None
    assert presenca.presente is True
