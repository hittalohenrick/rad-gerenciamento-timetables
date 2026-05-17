from datetime import time

from app import db
from app.forms import NIGHT_SHIFT_ID, WEEKDAY_VALUES, allowed_slot_ids_for_turno, get_shift_bounds, resolve_shift_slot_id
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
    prof_livre.jornada_turnos = "matutino_vespertino"
    prof_ocupado.disciplinas_aptas = [disciplinas[0]]
    prof_ocupado.jornada_turnos = "matutino_vespertino"
    prof_inapto.disciplinas_aptas = [disciplinas[1]]
    prof_inapto.jornada_turnos = "matutino_vespertino"
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
    professor.jornada_turnos = "matutino_vespertino"
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


def test_new_timetable_bloqueia_professor_fora_da_jornada(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    professor = user_factory("prof_jornada", role="professor", password="123456", email="prof_jornada@login.local")
    professor.jornada_turnos = "vespertino_noturno"
    turma, disciplinas, salas = _setup_catalog(periodo=2, turno="matutino")
    professor.disciplinas_aptas = [disciplinas[0]]
    db.session.commit()

    login("admin", "Admin1234")
    response = client.post(
        "/timetable/new",
        data={
            "dia": "Segunda",
            "horario_id": allowed_slot_ids_for_turno("matutino")[0],
            "turma_id": str(turma.id),
            "sala_id": str(salas[0].id),
            "professor_id": str(professor.id),
            "disciplina_id": str(disciplinas[0].id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"nao possui jornada para o turno Matutino" in response.data
    assert Timetable.query.filter_by(turma_id=turma.id).count() == 0


def test_new_timetable_bloqueia_excesso_de_10_slots_no_turno(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    professor = user_factory("prof_turno_limite", role="professor", password="123456", email="prof_turno_limite@login.local")
    professor.jornada_turnos = "matutino_vespertino"
    turma, disciplinas, salas = _setup_catalog(periodo=2, turno="matutino")
    professor.disciplinas_aptas = [disciplinas[0]]
    db.session.flush()

    weekdays = WEEKDAY_VALUES[:5]
    matutino_slots = allowed_slot_ids_for_turno("matutino")
    for day_label in weekdays:
        for slot_id in matutino_slots:
            slot_start, slot_end = get_shift_bounds(slot_id)
            db.session.add(
                Timetable(
                    dia=day_label,
                    hora_inicio=slot_start or time(7, 0),
                    hora_fim=slot_end or time(8, 30),
                    sala_id=salas[0].id,
                    professor_id=professor.id,
                    disciplina_id=disciplinas[0].id,
                    turma_id=turma.id,
                )
            )

    turma_extra = Turma(
        curso_id=turma.curso_id,
        codigo="SI-2M-C",
        semestre_letivo=turma.semestre_letivo,
        periodo=turma.periodo,
        turno="matutino",
        quantidade_alunos=20,
    )
    db.session.add(turma_extra)
    db.session.commit()

    login("admin", "Admin1234")
    response = client.post(
        "/timetable/new",
        data={
            "dia": "Sabado",
            "horario_id": matutino_slots[0],
            "turma_id": str(turma_extra.id),
            "sala_id": str(salas[1].id),
            "professor_id": str(professor.id),
            "disciplina_id": str(disciplinas[0].id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"limite 10" in response.data


def test_bulk_alocacao_bloqueia_quando_estoura_limite_semanal(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    professor = user_factory("prof_bulk_limite", role="professor", password="123456", email="prof_bulk_limite@login.local")
    professor.jornada_turnos = "vespertino_noturno"
    turma, disciplinas, salas = _setup_catalog(periodo=2, turno="vespertino")
    professor.disciplinas_aptas = disciplinas
    db.session.flush()

    weekdays = WEEKDAY_VALUES[:5]
    vespertino_slots = allowed_slot_ids_for_turno("vespertino")
    noturno_slots = allowed_slot_ids_for_turno("noturno")
    for day_label in weekdays:
        for slot_id in vespertino_slots:
            slot_start, slot_end = get_shift_bounds(slot_id)
            db.session.add(
                Timetable(
                    dia=day_label,
                    hora_inicio=slot_start or time(13, 0),
                    hora_fim=slot_end or time(14, 30),
                    sala_id=salas[0].id,
                    professor_id=professor.id,
                    disciplina_id=disciplinas[0].id,
                    turma_id=turma.id,
                )
            )

    turma_noturno = Turma(
        curso_id=turma.curso_id,
        codigo="SI-2N-A",
        semestre_letivo=turma.semestre_letivo,
        periodo=turma.periodo,
        turno="noturno",
        quantidade_alunos=20,
    )
    db.session.add(turma_noturno)
    db.session.flush()
    noturno_count = 0
    for day_label in weekdays:
        for slot_id in noturno_slots:
            if noturno_count >= 9:
                break
            slot_start, slot_end = get_shift_bounds(slot_id)
            db.session.add(
                Timetable(
                    dia=day_label,
                    hora_inicio=slot_start or time(18, 0),
                    hora_fim=slot_end or time(19, 30),
                    sala_id=salas[1].id if len(salas) > 1 else salas[0].id,
                    professor_id=professor.id,
                    disciplina_id=disciplinas[1].id,
                    turma_id=turma_noturno.id,
                )
            )
            noturno_count += 1
        if noturno_count >= 9:
            break
    db.session.commit()

    turma_pendente = Turma(
        curso_id=turma.curso_id,
        codigo="SI-2N-B",
        semestre_letivo=turma.semestre_letivo,
        periodo=turma.periodo,
        turno="noturno",
        quantidade_alunos=20,
    )
    db.session.add(turma_pendente)
    db.session.flush()
    pending_rows = []
    pending_matrix = [
        ("Sabado", noturno_slots[0], disciplinas[0].id),
        ("Sabado", noturno_slots[1], disciplinas[1].id),
        ("Domingo", noturno_slots[0], disciplinas[2].id),
        ("Domingo", noturno_slots[1], disciplinas[3].id),
    ]
    for day_label, slot_id, disciplina_id in pending_matrix:
        slot_start, slot_end = get_shift_bounds(slot_id)
        row = Timetable(
            dia=day_label,
            hora_inicio=slot_start or time(18, 0),
            hora_fim=slot_end or time(19, 30),
            sala_id=salas[0].id,
            professor_id=None,
            disciplina_id=disciplina_id,
            turma_id=turma_pendente.id,
        )
        pending_rows.append(row)
    db.session.add_all(pending_rows)
    db.session.commit()
    pending = pending_rows[0]

    login("admin", "Admin1234")
    response = client.post(
        f"/turma/{turma_pendente.id}/alocar-professores-lote",
        data={
            "submit": "1",
            f"professor_for_{pending_rows[0].id}": str(professor.id),
            f"professor_for_{pending_rows[1].id}": str(professor.id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"limite 20" in response.data
    unchanged = db.session.get(Timetable, pending.id)
    assert unchanged is not None
    assert unchanged.professor_id is None
