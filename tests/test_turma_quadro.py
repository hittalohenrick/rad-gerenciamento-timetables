from datetime import time

from app import db
from app.forms import NIGHT_SHIFT_ID, allowed_slot_ids_for_turno, get_shift_bounds, resolve_shift_slot_id
from app.models import Curso, Disciplina, GradeCurricular, GradeCurricularItem, Sala, Timetable, Turma


def _setup_catalog(periodo=2, turno="matutino"):
    curso = Curso(nome="Sistemas de Informacao", codigo="SI", ativo=True, quantidade_periodos=8)
    disciplinas = [
        Disciplina(nome="Algoritmos", codigo="ALG100"),
        Disciplina(nome="Banco de Dados", codigo="BD100"),
        Disciplina(nome="Estruturas de Dados", codigo="ED100"),
        Disciplina(nome="Redes", codigo="RED100"),
    ]
    salas = [Sala(nome="Lab 01", capacidade=40), Sala(nome="Lab 02", capacidade=35)]
    db.session.add(curso)
    db.session.add_all(disciplinas + salas)
    db.session.flush()

    grade = GradeCurricular(nome="Grade SI 2026", curso_id=curso.id, ativa=True)
    db.session.add(grade)
    db.session.flush()

    for disciplina in disciplinas:
        db.session.add(GradeCurricularItem(grade_id=grade.id, disciplina_id=disciplina.id, periodo=periodo))

    turma = Turma(
        curso_id=curso.id,
        codigo="SI-2M",
        semestre_letivo="2026.1",
        periodo=periodo,
        turno=turno,
        quantidade_alunos=30,
    )
    db.session.add(turma)
    db.session.commit()
    return turma, disciplinas, salas


def test_gerar_quadro_distribui_disciplinas_sem_professor(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    turma, disciplinas, _ = _setup_catalog(periodo=2, turno="matutino")

    login("admin", "Admin1234")
    response = client.post(
        f"/turma/{turma.id}/quadro/gerar",
        data={"submit": "1"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Quadro da turma gerado com sucesso." in response.data

    rows = Timetable.query.filter_by(turma_id=turma.id).all()
    assert len(rows) == len(disciplinas)
    assert all(row.professor_id is None for row in rows)
    assert all(row.dia in {"Segunda", "Terca", "Quarta", "Quinta", "Sexta"} for row in rows)

    slot_ids = {resolve_shift_slot_id(row.hora_inicio, row.hora_fim) for row in rows}
    assert slot_ids.issubset(set(allowed_slot_ids_for_turno("matutino")))


def test_new_timetable_bloqueia_horario_fora_do_turno_da_turma(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    professor = user_factory("prof_turno", role="professor", password="123456", email="prof_turno@login.local")
    turma, disciplinas, salas = _setup_catalog(periodo=2, turno="matutino")
    professor.disciplinas_aptas = [disciplinas[0]]
    db.session.commit()

    login("admin", "Admin1234")
    response = client.post(
        "/timetable/new",
        data={
            "dia": "Segunda",
            "horario_id": NIGHT_SHIFT_ID,
            "turma_id": str(turma.id),
            "sala_id": str(salas[0].id),
            "professor_id": str(professor.id),
            "disciplina_id": str(disciplinas[0].id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Horario invalido para o turno da turma" in response.data
    assert Timetable.query.filter_by(turma_id=turma.id).count() == 0


def test_alocar_professor_filtra_por_aptidao_e_disponibilidade(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    prof_livre = user_factory("prof_livre", role="professor", password="123456", email="prof_livre@login.local")
    prof_ocupado = user_factory("prof_ocup", role="professor", password="123456", email="prof_ocup@login.local")
    prof_inapto = user_factory("prof_inapto", role="professor", password="123456", email="prof_inapto@login.local")
    turma, disciplinas, salas = _setup_catalog(periodo=2, turno="matutino")

    prof_livre.disciplinas_aptas = [disciplinas[0]]
    prof_ocupado.disciplinas_aptas = [disciplinas[0]]
    prof_inapto.disciplinas_aptas = [disciplinas[1]]
    db.session.commit()

    login("admin", "Admin1234")
    client.post(
        f"/turma/{turma.id}/quadro/gerar",
        data={"submit": "1"},
        follow_redirects=True,
    )

    target = Timetable.query.filter_by(turma_id=turma.id, disciplina_id=disciplinas[0].id).first()
    assert target is not None

    turma2 = Turma(
        curso_id=turma.curso_id,
        codigo="SI-2M-B",
        semestre_letivo="2026.1",
        periodo=turma.periodo,
        turno=turma.turno,
        quantidade_alunos=25,
    )
    db.session.add(turma2)
    db.session.flush()
    db.session.add(
        Timetable(
            dia=target.dia,
            hora_inicio=target.hora_inicio,
            hora_fim=target.hora_fim,
            sala_id=salas[1].id if target.sala_id != salas[1].id else salas[0].id,
            professor_id=prof_ocupado.id,
            disciplina_id=disciplinas[1].id,
            turma_id=turma2.id,
        )
    )
    db.session.commit()

    page = client.get(f"/timetable/{target.id}/alocar-professor")
    assert page.status_code == 200
    assert b"prof_livre" in page.data
    assert b"prof_ocup" not in page.data
    assert b"prof_inapto" not in page.data

    submit = client.post(
        f"/timetable/{target.id}/alocar-professor",
        data={"professor_id": str(prof_livre.id), "submit": "1"},
        follow_redirects=True,
    )
    assert submit.status_code == 200
    assert b"Professor alocado com sucesso." in submit.data
    updated = db.session.get(Timetable, target.id)
    assert updated is not None
    assert updated.professor_id == prof_livre.id


def test_alocar_professor_exige_grade_completa(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    professor = user_factory("prof_req", role="professor", password="123456", email="prof_req@login.local")
    turma, disciplinas, salas = _setup_catalog(periodo=2, turno="matutino")
    professor.disciplinas_aptas = [disciplinas[0]]
    db.session.commit()

    start_time, end_time = get_shift_bounds(allowed_slot_ids_for_turno("matutino")[0])
    parcial = Timetable(
        dia="Segunda",
        hora_inicio=start_time or time(7, 0),
        hora_fim=end_time or time(8, 30),
        sala_id=salas[0].id,
        professor_id=None,
        disciplina_id=disciplinas[0].id,
        turma_id=turma.id,
    )
    db.session.add(parcial)
    db.session.commit()

    login("admin", "Admin1234")
    response = client.get(f"/timetable/{parcial.id}/alocar-professor", follow_redirects=True)

    assert response.status_code == 200
    assert b"Conclua primeiro a grade da turma" in response.data
    unchanged = db.session.get(Timetable, parcial.id)
    assert unchanged is not None
    assert unchanged.professor_id is None


def test_alocar_professores_em_lote_da_turma(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    professor = user_factory("prof_lote", role="professor", password="123456", email="prof_lote@login.local")
    turma, disciplinas, _ = _setup_catalog(periodo=2, turno="matutino")
    professor.disciplinas_aptas = disciplinas
    db.session.commit()

    login("admin", "Admin1234")
    client.post(
        f"/turma/{turma.id}/quadro/gerar",
        data={"submit": "1"},
        follow_redirects=True,
    )

    pending_rows = Timetable.query.filter_by(turma_id=turma.id, professor_id=None).all()
    assert pending_rows

    response_get = client.get(f"/turma/{turma.id}/alocar-professores-lote")
    assert response_get.status_code == 200
    assert b"Alocar Professores em Lote" in response_get.data

    payload = {"submit": "1"}
    for row in pending_rows:
        payload[f"professor_for_{row.id}"] = str(professor.id)

    response_post = client.post(
        f"/turma/{turma.id}/alocar-professores-lote",
        data=payload,
        follow_redirects=True,
    )

    assert response_post.status_code == 200
    assert b"Alocacao em lote concluida" in response_post.data
    updated_rows = Timetable.query.filter_by(turma_id=turma.id).all()
    assert all(row.professor_id == professor.id for row in updated_rows)


def test_alocar_professores_em_lote_exige_grade_completa(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    professor = user_factory("prof_lote_req", role="professor", password="123456", email="prof_lote_req@login.local")
    turma, disciplinas, salas = _setup_catalog(periodo=2, turno="matutino")
    professor.disciplinas_aptas = [disciplinas[0]]
    db.session.commit()

    start_time, end_time = get_shift_bounds(allowed_slot_ids_for_turno("matutino")[0])
    db.session.add(
        Timetable(
            dia="Segunda",
            hora_inicio=start_time or time(7, 0),
            hora_fim=end_time or time(8, 30),
            sala_id=salas[0].id,
            professor_id=None,
            disciplina_id=disciplinas[0].id,
            turma_id=turma.id,
        )
    )
    db.session.commit()

    login("admin", "Admin1234")
    response = client.get(f"/turma/{turma.id}/alocar-professores-lote", follow_redirects=True)

    assert response.status_code == 200
    assert b"Conclua primeiro a grade da turma" in response.data
    unchanged_rows = Timetable.query.filter_by(turma_id=turma.id).all()
    assert any(row.professor_id is None for row in unchanged_rows)
