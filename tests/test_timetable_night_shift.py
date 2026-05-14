from datetime import time

from app import db
from app.forms import NIGHT_SHIFT_ID, SHIFT_SLOT_VALUES, get_shift_bounds
from app.models import (
    Curso,
    Disciplina,
    GradeCurricular,
    GradeCurricularItem,
    Sala,
    Timetable,
    Turma,
)
from app.routes.admin import _build_night_shift_room_availability
from app.routes.helpers import find_timetable_conflict_with_turma


def _setup_catalog():
    sala_a = Sala(nome="Sala A", capacidade=30)
    sala_b = Sala(nome="Sala B", capacidade=30)
    curso = Curso(nome="Analise e Desenvolvimento de Sistemas", codigo="ADS", ativo=True, quantidade_periodos=8)
    disciplina_a = Disciplina(nome="Algoritmos", codigo="ALG001")
    disciplina_b = Disciplina(nome="Calculo", codigo="CAL001")
    db.session.add_all([sala_a, sala_b, curso, disciplina_a, disciplina_b])
    db.session.flush()

    grade = GradeCurricular(nome="Grade ADS 2026", curso_id=curso.id, ativa=True)
    db.session.add(grade)
    db.session.flush()

    db.session.add_all(
        [
            GradeCurricularItem(grade_id=grade.id, disciplina_id=disciplina_a.id, periodo=3),
            GradeCurricularItem(grade_id=grade.id, disciplina_id=disciplina_b.id, periodo=3),
        ]
    )

    turma = Turma(
        curso_id=curso.id,
        codigo="ADS-3N",
        semestre_letivo="2026.1",
        periodo=3,
        quantidade_alunos=25,
    )
    db.session.add(turma)
    db.session.commit()
    return sala_a, sala_b, disciplina_a, disciplina_b, turma


def test_new_timetable_applies_selected_shift(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    professor = user_factory("prof_turno", role="professor", password="123456", email="prof_turno@login.local")
    sala_a, _, disciplina_a, _, turma = _setup_catalog()
    professor.disciplinas_aptas = [disciplina_a]
    db.session.commit()

    login("admin", "Admin1234")
    selected_slot = SHIFT_SLOT_VALUES[0]
    start_time, end_time = get_shift_bounds(selected_slot)

    response = client.post(
        "/timetable/new",
        data={
            "dia": "Segunda",
            "horario_id": selected_slot,
            "turma_id": str(turma.id),
            "sala_id": str(sala_a.id),
            "professor_id": str(professor.id),
            "disciplina_id": str(disciplina_a.id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Alocacao criada com sucesso." in response.data

    created = Timetable.query.first()
    assert created is not None
    assert created.hora_inicio == start_time
    assert created.hora_fim == end_time
    assert created.turma_id == turma.id


def test_new_timetable_blocks_manual_post_with_busy_room(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    professor_a = user_factory("prof_a", role="professor", password="123456", email="prof_a@login.local")
    professor_b = user_factory("prof_b", role="professor", password="123456", email="prof_b@login.local")
    sala_a, _, disciplina_a, _, turma = _setup_catalog()
    slot_start, slot_end = get_shift_bounds(NIGHT_SHIFT_ID)
    professor_a.disciplinas_aptas = [disciplina_a]
    professor_b.disciplinas_aptas = [disciplina_a]
    db.session.commit()

    db.session.add(
        Timetable(
            dia="Segunda",
            hora_inicio=slot_start,
            hora_fim=slot_end,
            sala_id=sala_a.id,
            professor_id=professor_a.id,
            disciplina_id=disciplina_a.id,
            turma_id=turma.id,
        )
    )
    db.session.commit()

    login("admin", "Admin1234")

    response = client.post(
        "/timetable/new",
        data={
            "dia": "Segunda",
            "horario_id": NIGHT_SHIFT_ID,
            "turma_id": str(turma.id),
            "sala_id": str(sala_a.id),
            "professor_id": str(professor_b.id),
            "disciplina_id": str(disciplina_a.id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"sala selecionada nao esta disponivel" in response.data.lower()
    assert Timetable.query.count() == 1


def test_new_timetable_blocks_when_professor_has_no_aptitude(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    professor = user_factory("prof_apt", role="professor", password="123456", email="prof_apt@login.local")
    sala_a, _, disciplina_a, disciplina_b, turma = _setup_catalog()

    professor.disciplinas_aptas = [disciplina_a]
    db.session.commit()

    login("admin", "Admin1234")

    response = client.post(
        "/timetable/new",
        data={
            "dia": "Quarta",
            "horario_id": SHIFT_SLOT_VALUES[1],
            "turma_id": str(turma.id),
            "sala_id": str(sala_a.id),
            "professor_id": str(professor.id),
            "disciplina_id": str(disciplina_b.id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Professor sem aptidao para a disciplina selecionada." in response.data
    assert Timetable.query.count() == 0


def test_room_availability_ignores_legacy_accented_days(user_factory):
    professor = user_factory("prof_legacy", role="professor", password="123456", email="prof_legacy@login.local")
    sala_a, sala_b, disciplina_a, _, turma = _setup_catalog()
    professor.disciplinas_aptas = [disciplina_a]
    db.session.commit()

    db.session.add(
        Timetable(
            dia="Ter\u00e7a",
            hora_inicio=time(18, 30),
            hora_fim=time(20, 0),
            sala_id=sala_a.id,
            professor_id=professor.id,
            disciplina_id=disciplina_a.id,
            turma_id=turma.id,
        )
    )
    db.session.commit()

    availability = _build_night_shift_room_availability([sala_a, sala_b])
    available_ids_tuesday = {room["id"] for room in availability["Terca"]}

    assert sala_a.id not in available_ids_tuesday
    assert sala_b.id in available_ids_tuesday


def test_find_timetable_conflict_with_turma(user_factory):
    professor_a = user_factory("prof_conf_a", role="professor", password="123456", email="prof_conf_a@login.local")
    professor_b = user_factory("prof_conf_b", role="professor", password="123456", email="prof_conf_b@login.local")
    sala_a, sala_b, disciplina_a, _, turma = _setup_catalog()
    slot_start, slot_end = get_shift_bounds(NIGHT_SHIFT_ID)
    professor_a.disciplinas_aptas = [disciplina_a]
    professor_b.disciplinas_aptas = [disciplina_a]
    db.session.commit()

    db.session.add(
        Timetable(
            dia="Terca",
            hora_inicio=slot_start,
            hora_fim=slot_end,
            sala_id=sala_a.id,
            professor_id=professor_a.id,
            disciplina_id=disciplina_a.id,
            turma_id=turma.id,
        )
    )
    db.session.commit()

    conflict = find_timetable_conflict_with_turma(
        dia="Terca",
        hora_inicio=slot_start,
        hora_fim=slot_end,
        sala_id=sala_b.id,
        professor_id=professor_b.id,
        turma_id=turma.id,
    )

    assert conflict == "Conflito: a turma ja possui alocacao em horario sobreposto."
