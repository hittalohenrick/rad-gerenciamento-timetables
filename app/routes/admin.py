import math

from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from app import db
from app.forms import (
    AlunoForm,
    BulkProfessorAssignmentForm,
    FIXED_SALA_CAPACITY,
    MAX_TURMA_CAPACITY,
    PROFESSOR_DEFAULT_WORKLOAD,
    PROFESSOR_WORKLOAD_TURNOS,
    TURNO_CHOICES,
    CursoForm,
    DeleteForm,
    DisciplinaForm,
    GradeCurricularForm,
    GradeCurricularItemForm,
    MatriculaForm,
    TurmaMatriculaForm,
    ProfessorAssignmentForm,
    ProfessorEditForm,
    ProfessorForm,
    ResetPasswordForm,
    SalaForm,
    SHIFT_SLOT_VALUES,
    TimetableForm,
    TurmaForm,
    NIGHT_SHIFT_ID,
    WEEKDAY_VALUES,
    allowed_slot_ids_for_turno,
    get_shift_bounds,
    get_shift_label,
    get_professor_workload_label,
    get_turno_label,
    resolve_shift_slot_id,
)
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
    User,
)
from app.services.professor_planner import rebuild_professores_automatico
from . import bp
from .helpers import (
    admin_required,
    aluno_has_schedule_conflict,
    aluno_matricula_exists,
    aluno_turma_same_semestre,
    aluno_turma_exists,
    active_grade_for_curso,
    canonical_day_label,
    curso_codigo_exists,
    curso_name_exists,
    disciplina_name_exists,
    find_timetable_conflict_with_turma,
    grade_item_exists,
    grade_nome_exists,
    generate_disciplina_code,
    normalize_text,
    allowed_disciplina_ids_for_turma,
    professor_can_teach_disciplina,
    sala_name_exists,
    synthetic_professor_email,
    turma_codigo_semestre_exists,
    turma_capacity_reached,
    username_exists,
)

def _day_sort_value(day_label):
    label = (day_label or "").lower()
    if label.startswith("seg"):
        return 1
    if label.startswith("ter"):
        return 2
    if label.startswith("qua"):
        return 3
    if label.startswith("qui"):
        return 4
    if label.startswith("sex"):
        return 5
    if label.startswith("sab") or "bado" in label:
        return 6
    if label.startswith("dom"):
        return 7
    return 99


PLANNING_WEEK_DAYS = WEEKDAY_VALUES[:5]
DISCIPLINAS_POR_TURMA_NOVA = 5
PROFESSOR_MAX_WEEKLY_SLOTS = 20
PROFESSOR_MAX_SLOTS_PER_TURNO = 10


def _slot_to_turno(slot_id):
    for turno, slot_ids in {
        turno_value: allowed_slot_ids_for_turno(turno_value) for turno_value, _ in TURNO_CHOICES
    }.items():
        if slot_id in slot_ids:
            return turno
    return None


def _infer_turno_from_interval(hora_inicio):
    if hora_inicio is None:
        return None
    hour_value = hora_inicio.hour
    if hour_value < 12:
        return "matutino"
    if hour_value < 18:
        return "vespertino"
    return "noturno"


def _resolve_timetable_turno(row):
    slot_id = resolve_shift_slot_id(row.hora_inicio, row.hora_fim)
    if slot_id:
        turno = _slot_to_turno(slot_id)
        if turno:
            return turno
    return _infer_turno_from_interval(row.hora_inicio)


def _professor_allowed_turnos(professor):
    profile_key = getattr(professor, "jornada_turnos", None) or PROFESSOR_DEFAULT_WORKLOAD
    allowed_turnos = PROFESSOR_WORKLOAD_TURNOS.get(profile_key)
    if not allowed_turnos:
        allowed_turnos = PROFESSOR_WORKLOAD_TURNOS[PROFESSOR_DEFAULT_WORKLOAD]
    return set(allowed_turnos)


def _build_professor_workload_index(exclude_timetable_id=None):
    turnos = [value for value, _ in TURNO_CHOICES]
    rows = Timetable.query.with_entities(
        Timetable.id,
        Timetable.professor_id,
        Timetable.hora_inicio,
        Timetable.hora_fim,
    ).all()
    workload = {}
    for row in rows:
        if row.professor_id is None:
            continue
        if exclude_timetable_id is not None and row.id == exclude_timetable_id:
            continue
        turno = _resolve_timetable_turno(row)
        if turno not in turnos:
            continue
        snapshot = workload.setdefault(
            row.professor_id,
            {
                "total": 0,
                "by_turno": {turno_value: 0 for turno_value in turnos},
            },
        )
        snapshot["total"] += 1
        snapshot["by_turno"][turno] += 1
    return workload


def _ensure_professor_workload_available(professor, timetable, workload_index, planned_increments=None):
    if professor is None or professor.role != "professor":
        return False, "Professor selecionado e invalido."

    turno = _resolve_timetable_turno(timetable)
    if turno is None:
        return False, "Nao foi possivel identificar o turno da alocacao."

    if turno not in _professor_allowed_turnos(professor):
        return (
            False,
            (
                f"Professor {professor.username} nao possui jornada para o turno "
                f"{get_turno_label(turno)}."
            ),
        )

    baseline = workload_index.get(professor.id, {"total": 0, "by_turno": {turno_value: 0 for turno_value, _ in TURNO_CHOICES}})
    extra_total = 0
    extra_turno = 0
    if planned_increments:
        professor_plan = planned_increments.get(professor.id, {})
        extra_total = professor_plan.get("total", 0)
        extra_turno = professor_plan.get("by_turno", {}).get(turno, 0)

    projected_total = baseline.get("total", 0) + extra_total + 1
    projected_turno = baseline.get("by_turno", {}).get(turno, 0) + extra_turno + 1

    if projected_total > PROFESSOR_MAX_WEEKLY_SLOTS:
        return (
            False,
            (
                f"Professor {professor.username} atingiria {projected_total} slots/semana "
                f"(limite {PROFESSOR_MAX_WEEKLY_SLOTS})."
            ),
        )
    if projected_turno > PROFESSOR_MAX_SLOTS_PER_TURNO:
        return (
            False,
            (
                f"Professor {professor.username} atingiria {projected_turno} slots no turno "
                f"{get_turno_label(turno)} (limite {PROFESSOR_MAX_SLOTS_PER_TURNO})."
            ),
        )
    return True, ""


def _build_turno_capacity_snapshot(salas, turmas, timetables, turmas_sem_quadro=None):
    if turmas_sem_quadro is None:
        turmas_com_quadro_ids = {row.turma_id for row in timetables if row.turma_id is not None}
        turmas_sem_quadro = [turma for turma in turmas if turma.id not in turmas_com_quadro_ids]
    total_salas = len(salas)
    turnos = [value for value, _ in TURNO_CHOICES]
    turno_label_map = dict(TURNO_CHOICES)

    slot_turno_map = {}
    for turno in turnos:
        for slot_id in allowed_slot_ids_for_turno(turno):
            slot_turno_map[slot_id] = turno

    occupied_slots_by_turno = {turno: set() for turno in turnos}
    for timetable in timetables:
        canonical_day = canonical_day_label(timetable.dia)
        if canonical_day not in PLANNING_WEEK_DAYS:
            continue
        slot_id = resolve_shift_slot_id(timetable.hora_inicio, timetable.hora_fim)
        turno = slot_turno_map.get(slot_id)
        if turno is None:
            continue
        occupied_slots_by_turno[turno].add((canonical_day, slot_id, timetable.sala_id))

    turmas_sem_quadro_por_turno = {turno: 0 for turno in turnos}
    for turma in turmas_sem_quadro:
        if turma.turno in turmas_sem_quadro_por_turno:
            turmas_sem_quadro_por_turno[turma.turno] += 1

    metrics = []
    total_teorico = 0
    total_disponivel = 0

    for turno in turnos:
        slot_ids_turno = allowed_slot_ids_for_turno(turno)
        capacidade_slots = total_salas * len(PLANNING_WEEK_DAYS) * len(slot_ids_turno)
        slots_ocupados = len(occupied_slots_by_turno[turno])
        slots_livres = max(0, capacidade_slots - slots_ocupados)
        turmas_possiveis_teorico = slots_livres // DISCIPLINAS_POR_TURMA_NOVA
        turmas_reservadas_sem_quadro = turmas_sem_quadro_por_turno[turno]
        turmas_possiveis_disponivel = max(0, turmas_possiveis_teorico - turmas_reservadas_sem_quadro)

        total_teorico += turmas_possiveis_teorico
        total_disponivel += turmas_possiveis_disponivel

        metrics.append(
            {
                "turno": turno,
                "turno_label": turno_label_map.get(turno, turno.title()),
                "capacidade_slots": capacidade_slots,
                "slots_ocupados": slots_ocupados,
                "slots_livres": slots_livres,
                "turmas_possiveis_teorico": turmas_possiveis_teorico,
                "turmas_reservadas_sem_quadro": turmas_reservadas_sem_quadro,
                "turmas_possiveis_disponivel": turmas_possiveis_disponivel,
            }
        )

    return {
        "disciplinas_por_turma": DISCIPLINAS_POR_TURMA_NOVA,
        "total_salas": total_salas,
        "dias_planejamento": len(PLANNING_WEEK_DAYS),
        "slots_por_turno_semana_por_sala": len(PLANNING_WEEK_DAYS) * len(allowed_slot_ids_for_turno("matutino")),
        "turno_metrics": metrics,
        "turmas_possiveis_teorico_total": total_teorico,
        "turmas_possiveis_disponivel_total": total_disponivel,
    }


def _disponibilidade_real_turno(turno_capacity, turno):
    for row in turno_capacity.get("turno_metrics", []):
        if row.get("turno") == turno:
            return row.get("turmas_possiveis_disponivel", 0)
    return 0


def _build_professor_capacity_snapshot(professores, timetables, turmas_sem_quadro):
    turnos = [value for value, _ in TURNO_CHOICES]
    turno_label_map = dict(TURNO_CHOICES)
    demanda_alocada_por_turno = {turno: 0 for turno in turnos}
    reserva_sem_quadro_por_turno = {turno: 0 for turno in turnos}
    capacidade_por_turno = {turno: 0 for turno in turnos}

    for timetable in timetables:
        turno = _resolve_timetable_turno(timetable)
        if turno in demanda_alocada_por_turno:
            demanda_alocada_por_turno[turno] += 1

    for turma in turmas_sem_quadro:
        if turma.turno in reserva_sem_quadro_por_turno:
            reserva_sem_quadro_por_turno[turma.turno] += DISCIPLINAS_POR_TURMA_NOVA

    profile_counts = {}
    for professor in professores:
        profile_key = professor.jornada_turnos or PROFESSOR_DEFAULT_WORKLOAD
        profile_counts[profile_key] = profile_counts.get(profile_key, 0) + 1
        for turno in _professor_allowed_turnos(professor):
            capacidade_por_turno[turno] += PROFESSOR_MAX_SLOTS_PER_TURNO

    metrics = []
    total_demanda_planejada = 0
    total_capacidade = len(professores) * PROFESSOR_MAX_WEEKLY_SLOTS
    total_deficit_slots = 0
    for turno in turnos:
        demanda_planejada = demanda_alocada_por_turno[turno] + reserva_sem_quadro_por_turno[turno]
        capacidade_turno = capacidade_por_turno[turno]
        deficit_slots = max(0, demanda_planejada - capacidade_turno)
        metrics.append(
            {
                "turno": turno,
                "turno_label": turno_label_map.get(turno, turno.title()),
                "demanda_alocada": demanda_alocada_por_turno[turno],
                "reserva_sem_quadro": reserva_sem_quadro_por_turno[turno],
                "demanda_planejada": demanda_planejada,
                "capacidade_docente": capacidade_turno,
                "saldo_slots": capacidade_turno - demanda_planejada,
                "deficit_slots": deficit_slots,
                "professores_adicionais_turno": math.ceil(deficit_slots / PROFESSOR_MAX_SLOTS_PER_TURNO),
            }
        )
        total_demanda_planejada += demanda_planejada
        total_deficit_slots += deficit_slots

    deficit_total_slots = max(0, total_demanda_planejada - total_capacidade)
    professores_adicionais_total = math.ceil(deficit_total_slots / PROFESSOR_MAX_WEEKLY_SLOTS)

    return {
        "metrics": metrics,
        "professores_total": len(professores),
        "demanda_total": total_demanda_planejada,
        "capacidade_total": total_capacidade,
        "saldo_total": total_capacidade - total_demanda_planejada,
        "deficit_total_slots": deficit_total_slots,
        "professores_adicionais_total": professores_adicionais_total,
        "deficit_turno_slots_soma": total_deficit_slots,
        "max_slots_semana": PROFESSOR_MAX_WEEKLY_SLOTS,
        "max_slots_turno": PROFESSOR_MAX_SLOTS_PER_TURNO,
        "profile_counts": profile_counts,
    }


def _build_slot_key(day_label, slot_id):
    return f"{day_label}|{slot_id}"


def _normalize_turma_selection(raw_turma_id):
    if raw_turma_id in (None, "", 0, "0"):
        return 0
    return int(raw_turma_id)


def _slot_allowed_for_turma(turma, slot_id):
    return slot_id in allowed_slot_ids_for_turno(getattr(turma, "turno", None))


def _build_timetable_availability(salas, professores, turmas, exclude_timetable_id=None):
    all_room_ids = {sala.id for sala in salas}
    all_professor_ids = {professor.id for professor in professores}

    occupied_rows_query = Timetable.query.with_entities(
        Timetable.dia,
        Timetable.hora_inicio,
        Timetable.hora_fim,
        Timetable.sala_id,
        Timetable.professor_id,
        Timetable.turma_id,
    )
    if exclude_timetable_id is not None:
        occupied_rows_query = occupied_rows_query.filter(Timetable.id != exclude_timetable_id)

    occupied_rows = occupied_rows_query.all()
    availability_by_key = {}

    for day_label in WEEKDAY_VALUES:
        for slot_id in SHIFT_SLOT_VALUES:
            slot_start, slot_end = get_shift_bounds(slot_id)
            busy_room_ids = set()
            busy_professor_ids = set()
            busy_turma_ids = set()

            for row in occupied_rows:
                if canonical_day_label(row.dia) != day_label:
                    continue
                if row.hora_inicio >= slot_end or row.hora_fim <= slot_start:
                    continue
                busy_room_ids.add(row.sala_id)
                if row.professor_id is not None:
                    busy_professor_ids.add(row.professor_id)
                if row.turma_id is not None:
                    busy_turma_ids.add(row.turma_id)

            turma_ids_for_slot = sorted(
                turma.id
                for turma in turmas
                if turma.id not in busy_turma_ids and _slot_allowed_for_turma(turma, slot_id)
            )

            key = _build_slot_key(day_label, slot_id)
            availability_by_key[key] = {
                "day": day_label,
                "slot_id": slot_id,
                "slot_label": get_shift_label(slot_id),
                "sala_ids": sorted(all_room_ids.difference(busy_room_ids)),
                "professor_ids": sorted(all_professor_ids.difference(busy_professor_ids)),
                "turma_ids": turma_ids_for_slot,
            }

    return availability_by_key


def _build_professor_aptitude_maps(professores, disciplinas):
    professor_to_disciplina = {}
    disciplina_to_professor = {disciplina.id: [] for disciplina in disciplinas}

    for professor in professores:
        aptas = sorted({disciplina.id for disciplina in professor.disciplinas_aptas})
        professor_to_disciplina[professor.id] = aptas
        for disciplina_id in aptas:
            if disciplina_id in disciplina_to_professor:
                disciplina_to_professor[disciplina_id].append(professor.id)

    for disciplina_id in disciplina_to_professor:
        disciplina_to_professor[disciplina_id] = sorted(set(disciplina_to_professor[disciplina_id]))

    return professor_to_disciplina, disciplina_to_professor


def _build_allocation_payload(salas, professores, disciplinas, turmas, exclude_timetable_id=None):
    availability_by_key = _build_timetable_availability(
        salas=salas,
        professores=professores,
        turmas=turmas,
        exclude_timetable_id=exclude_timetable_id,
    )
    professor_to_disciplina, disciplina_to_professor = _build_professor_aptitude_maps(professores, disciplinas)
    turma_to_disciplina = {
        str(turma.id): allowed_disciplina_ids_for_turma(turma)
        for turma in turmas
    }
    turma_to_turno = {
        str(turma.id): turma.turno
        for turma in turmas
    }
    turno_to_slots = {
        turno_value: allowed_slot_ids_for_turno(turno_value)
        for turno_value, _ in TURNO_CHOICES
    }
    slot_to_turno = {}
    for turno_value, slot_ids in turno_to_slots.items():
        for slot_id in slot_ids:
            slot_to_turno[slot_id] = turno_value
    professor_to_turnos = {
        str(professor.id): sorted(_professor_allowed_turnos(professor))
        for professor in professores
    }
    workload_index = _build_professor_workload_index(exclude_timetable_id=exclude_timetable_id)
    professor_workload = {}
    for professor in professores:
        snapshot = workload_index.get(
            professor.id,
            {
                "total": 0,
                "by_turno": {turno_value: 0 for turno_value, _ in TURNO_CHOICES},
            },
        )
        professor_workload[str(professor.id)] = snapshot

    return {
        "availability_by_key": availability_by_key,
        "professor_to_disciplina": {str(key): value for key, value in professor_to_disciplina.items()},
        "disciplina_to_professor": {str(key): value for key, value in disciplina_to_professor.items()},
        "turma_to_disciplina": turma_to_disciplina,
        "turma_to_turno": turma_to_turno,
        "professor_to_turnos": professor_to_turnos,
        "professor_workload": professor_workload,
        "slot_to_turno": slot_to_turno,
        "professor_limits": {
            "weekly": PROFESSOR_MAX_WEEKLY_SLOTS,
            "per_turno": PROFESSOR_MAX_SLOTS_PER_TURNO,
        },
        "turno_to_slots": turno_to_slots,
        "metadata": {
            "days": WEEKDAY_VALUES,
            "slots": [{"id": slot_id, "label": get_shift_label(slot_id)} for slot_id in SHIFT_SLOT_VALUES],
        },
    }


def _build_night_shift_room_availability(salas, exclude_timetable_id=None):
    """Compatibilidade com testes legados: disponibilidade de sala apenas para o turno noturno."""
    availability_by_key = _build_timetable_availability(
        salas=salas,
        professores=[],
        turmas=[],
        exclude_timetable_id=exclude_timetable_id,
    )
    room_by_day = {}
    for day_label in WEEKDAY_VALUES:
        key = _build_slot_key(day_label, NIGHT_SHIFT_ID)
        allowed_ids = set(availability_by_key.get(key, {}).get("sala_ids", []))
        room_by_day[day_label] = [
            {"id": sala.id, "nome": sala.nome}
            for sala in salas
            if sala.id in allowed_ids
        ]
    return room_by_day


def _load_turma_timetable_rows(turma_id):
    timetables = (
        Timetable.query.options(
            joinedload(Timetable.sala),
            joinedload(Timetable.professor),
            joinedload(Timetable.disciplina),
            joinedload(Timetable.turma).joinedload(Turma.curso),
        )
        .filter(Timetable.turma_id == turma_id)
        .all()
    )
    return sorted(
        timetables,
        key=lambda row: (
            _day_sort_value(canonical_day_label(row.dia)),
            row.hora_inicio,
            row.hora_fim,
        ),
    )


def _build_turma_schedule_grid(turma, timetables):
    weekdays = WEEKDAY_VALUES[:5]
    turno_slot_ids = allowed_slot_ids_for_turno(turma.turno)
    timetable_by_key = {}
    extra_rows = []

    for timetable in timetables:
        canonical_day = canonical_day_label(timetable.dia)
        slot_id = resolve_shift_slot_id(timetable.hora_inicio, timetable.hora_fim)
        if canonical_day in weekdays and slot_id in turno_slot_ids:
            timetable_by_key[_build_slot_key(canonical_day, slot_id)] = timetable
        else:
            extra_rows.append(timetable)

    grid_rows = []
    for slot_id in turno_slot_ids:
        row_cells = []
        for day_label in weekdays:
            row_cells.append(
                {
                    "day": day_label,
                    "timetable": timetable_by_key.get(_build_slot_key(day_label, slot_id)),
                }
            )
        grid_rows.append(
            {
                "slot_id": slot_id,
                "slot_label": get_shift_label(slot_id),
                "cells": row_cells,
            }
        )

    return {
        "days": weekdays,
        "rows": grid_rows,
        "extra_rows": extra_rows,
    }


def _build_turma_schedule_entries(turma, disciplinas, salas):
    weekdays = WEEKDAY_VALUES[:5]
    turno_slot_ids = allowed_slot_ids_for_turno(turma.turno)
    slot_sequence = [(day_label, slot_id) for day_label in weekdays for slot_id in turno_slot_ids]
    generated_entries = []
    generated_turma_slots = set()
    generated_room_slots = set()
    unallocated_names = []

    for disciplina in disciplinas:
        allocated = False
        for day_label, slot_id in slot_sequence:
            slot_start, slot_end = get_shift_bounds(slot_id)
            turma_slot_key = (day_label, slot_id)
            if turma_slot_key in generated_turma_slots:
                continue

            for sala in salas:
                room_slot_key = (day_label, slot_id, sala.id)
                if room_slot_key in generated_room_slots:
                    continue

                conflict_message = find_timetable_conflict_with_turma(
                    dia=day_label,
                    hora_inicio=slot_start,
                    hora_fim=slot_end,
                    sala_id=sala.id,
                    professor_id=None,
                    turma_id=turma.id,
                )
                if conflict_message:
                    continue

                generated_entries.append(
                    Timetable(
                        dia=day_label,
                        hora_inicio=slot_start,
                        hora_fim=slot_end,
                        sala_id=sala.id,
                        professor_id=None,
                        disciplina_id=disciplina.id,
                        turma_id=turma.id,
                    )
                )
                generated_turma_slots.add(turma_slot_key)
                generated_room_slots.add(room_slot_key)
                allocated = True
                break

            if allocated:
                break

        if not allocated:
            unallocated_names.append(disciplina.nome)

    return generated_entries, unallocated_names


def _turma_grade_completeness(turma, timetables):
    required_disciplina_ids = allowed_disciplina_ids_for_turma(turma)
    required_set = set(required_disciplina_ids)
    scheduled_ids = [row.disciplina_id for row in timetables if row.disciplina_id is not None]
    scheduled_set = set(scheduled_ids)

    missing_ids = sorted(required_set.difference(scheduled_set))
    extra_ids = sorted(scheduled_set.difference(required_set))
    duplicate_ids = sorted(
        disciplina_id
        for disciplina_id in scheduled_set
        if scheduled_ids.count(disciplina_id) > 1
    )

    return {
        "required_count": len(required_disciplina_ids),
        "scheduled_count": len(scheduled_ids),
        "missing_ids": missing_ids,
        "extra_ids": extra_ids,
        "duplicate_ids": duplicate_ids,
        "is_complete": not missing_ids and not extra_ids and not duplicate_ids and len(scheduled_ids) == len(required_disciplina_ids),
    }


def _professor_is_free_for_timetable(professor_id, timetable, exclude_timetable_id=None):
    if professor_id is None:
        return False

    overlapping_rows = (
        Timetable.query.with_entities(Timetable.id, Timetable.dia, Timetable.hora_inicio, Timetable.hora_fim)
        .filter(Timetable.professor_id == professor_id)
        .all()
    )
    for row in overlapping_rows:
        if exclude_timetable_id is not None and row.id == exclude_timetable_id:
            continue
        if canonical_day_label(row.dia) != canonical_day_label(timetable.dia):
            continue
        if row.hora_inicio < timetable.hora_fim and row.hora_fim > timetable.hora_inicio:
            return False
    return True


def _available_professores_for_timetable(timetable, workload_index=None):
    if workload_index is None:
        workload_index = _build_professor_workload_index(exclude_timetable_id=timetable.id)
    professores = User.query.filter_by(role="professor").order_by(User.username.asc()).all()
    available = []
    for professor in professores:
        if not professor_can_teach_disciplina(professor, timetable.disciplina_id):
            continue
        workload_ok, _ = _ensure_professor_workload_available(
            professor=professor,
            timetable=timetable,
            workload_index=workload_index,
        )
        if not workload_ok:
            continue
        if timetable.professor_id == professor.id:
            available.append(professor)
            continue
        if _professor_is_free_for_timetable(professor.id, timetable, exclude_timetable_id=timetable.id):
            available.append(professor)
    return available


def _bulk_assignment_field_name(timetable_id):
    return f"professor_for_{timetable_id}"


def _build_bulk_professor_options(timetables):
    workload_index = _build_professor_workload_index()
    options_by_timetable = {}
    for timetable in timetables:
        professores = _available_professores_for_timetable(timetable, workload_index=workload_index)
        options_by_timetable[timetable.id] = [(professor.id, professor.username) for professor in professores]
    return options_by_timetable


def _extract_bulk_assignment_payload(timetables):
    selected_by_timetable = {}
    for timetable in timetables:
        raw_value = normalize_text(request.form.get(_bulk_assignment_field_name(timetable.id)))
        if not raw_value:
            continue
        if not raw_value.isdigit():
            selected_by_timetable[timetable.id] = None
            continue
        selected_by_timetable[timetable.id] = int(raw_value)
    return selected_by_timetable


def _has_bulk_internal_professor_conflict(selected_by_timetable, timetable_by_id):
    timetable_ids_by_professor = {}
    for timetable_id, professor_id in selected_by_timetable.items():
        if professor_id is None:
            continue
        timetable_ids_by_professor.setdefault(professor_id, []).append(timetable_id)

    for professor_id, timetable_ids in timetable_ids_by_professor.items():
        rows = [timetable_by_id[row_id] for row_id in timetable_ids if row_id in timetable_by_id]
        for idx in range(len(rows)):
            current = rows[idx]
            for next_idx in range(idx + 1, len(rows)):
                candidate = rows[next_idx]
                if canonical_day_label(current.dia) != canonical_day_label(candidate.dia):
                    continue
                if current.hora_inicio < candidate.hora_fim and current.hora_fim > candidate.hora_inicio:
                    return {
                        "professor_id": professor_id,
                        "timetable_a": current,
                        "timetable_b": candidate,
                    }
    return None


def _build_admin_insights(salas, professores, timetables):
    total_salas = len(salas)
    matriculas_por_turma_oferta = dict(
        db.session.query(Matricula.turma_id, func.count(Matricula.id))
        .group_by(Matricula.turma_id)
        .all()
    )

    room_usage_map = {
        sala.id: {
            "nome": sala.nome,
            "turmas": 0,
            "capacidade_total": 0,
            "alunos": 0,
            "ocupacao": 0.0,
            "status": "Sem uso",
        }
        for sala in salas
    }
    professor_load_map = {
        professor.id: {
            "username": professor.username,
            "turmas": 0,
            "alunos": 0,
            "is_overloaded": False,
            "status": "Ok",
        }
        for professor in professores
    }
    disciplina_demand_map = {}
    slot_usage_map = {}

    total_capacity_slots = 0
    turmas_sem_alunos = 0
    turmas_criticas = 0

    for timetable in timetables:
        matriculados = int(matriculas_por_turma_oferta.get(timetable.turma_id, 0))
        capacidade = timetable.sala.capacidade if timetable.sala else 0
        ocupacao = round((matriculados / capacidade) * 100, 1) if capacidade else 0.0
        intervalo = f"{timetable.hora_inicio.strftime('%H:%M')} - {timetable.hora_fim.strftime('%H:%M')}"

        total_capacity_slots += capacidade
        if matriculados == 0:
            turmas_sem_alunos += 1
        if capacidade and ocupacao >= 90:
            turmas_criticas += 1

        if timetable.sala_id in room_usage_map:
            room_usage = room_usage_map[timetable.sala_id]
            room_usage["turmas"] += 1
            room_usage["capacidade_total"] += capacidade
            room_usage["alunos"] += matriculados

        if timetable.professor_id in professor_load_map:
            professor_load = professor_load_map[timetable.professor_id]
            professor_load["turmas"] += 1
            professor_load["alunos"] += matriculados

        disciplina_nome = timetable.disciplina.nome if timetable.disciplina else "Disciplina removida"
        disciplina_demand = disciplina_demand_map.setdefault(
            timetable.disciplina_id,
            {"nome": disciplina_nome, "turmas": 0, "alunos": 0},
        )
        disciplina_demand["turmas"] += 1
        disciplina_demand["alunos"] += matriculados

        slot_key = (timetable.dia, intervalo)
        slot_usage = slot_usage_map.setdefault(
            slot_key,
            {"dia": timetable.dia, "intervalo": intervalo, "turmas": 0, "salas_livres": 0},
        )
        slot_usage["turmas"] += 1

    total_matriculas = sum(matriculas_por_turma_oferta.values())
    ocupacao_geral = round((total_matriculas / total_capacity_slots) * 100, 1) if total_capacity_slots else 0.0

    media_turmas_por_professor = (len(timetables) / len(professores)) if professores else 0
    limite_sobrecarga = max(2, int(media_turmas_por_professor + 1))

    for professor_load in professor_load_map.values():
        if professor_load["turmas"] > limite_sobrecarga:
            professor_load["is_overloaded"] = True
            professor_load["status"] = "Sobrecarga"
        elif professor_load["turmas"] == 0:
            professor_load["status"] = "Sem turmas"

    for room_usage in room_usage_map.values():
        if room_usage["capacidade_total"] > 0:
            room_usage["ocupacao"] = round((room_usage["alunos"] / room_usage["capacidade_total"]) * 100, 1)
        if room_usage["turmas"] == 0:
            room_usage["status"] = "Sem uso"
        elif room_usage["ocupacao"] >= 90:
            room_usage["status"] = "Critica"
        elif room_usage["ocupacao"] < 40:
            room_usage["status"] = "Ociosa"
        else:
            room_usage["status"] = "Saudavel"

    slot_usage_list = []
    for slot_usage in slot_usage_map.values():
        slot_usage["salas_livres"] = max(0, total_salas - slot_usage["turmas"])
        slot_usage_list.append(slot_usage)

    professores_carga = sorted(
        professor_load_map.values(),
        key=lambda row: (-row["turmas"], -row["alunos"], row["username"].lower()),
    )
    salas_utilizacao = sorted(
        room_usage_map.values(),
        key=lambda row: (
            0 if row["status"] == "Critica" else 1 if row["status"] == "Ociosa" else 2,
            -row["ocupacao"],
            row["nome"].lower(),
        ),
    )
    disciplinas_demanda = sorted(
        disciplina_demand_map.values(),
        key=lambda row: (-row["alunos"], -row["turmas"], row["nome"].lower()),
    )[:5]
    slots_mais_concorridos = sorted(
        slot_usage_list,
        key=lambda row: (-row["turmas"], _day_sort_value(row["dia"]), row["intervalo"]),
    )[:5]
    slots_recomendados = sorted(
        slot_usage_list,
        key=lambda row: (-row["salas_livres"], row["turmas"], _day_sort_value(row["dia"]), row["intervalo"]),
    )[:3]

    professores_sobrecarregados = [row for row in professores_carga if row["is_overloaded"]]
    salas_ociosas = [row for row in salas_utilizacao if row["status"] == "Ociosa"]
    turmas_criticas_slots = [row for row in slot_usage_list if row["turmas"] >= max(2, total_salas)]

    alerts = []
    if not total_salas:
        alerts.append({"level": "danger", "message": "Nao ha salas cadastradas para planejamento."})
    if not professores:
        alerts.append({"level": "danger", "message": "Nao ha professores cadastrados para alocar turmas."})
    if turmas_sem_alunos > 0:
        alerts.append(
            {
                "level": "warning",
                "message": f"{turmas_sem_alunos} turma(s) estao sem alunos alocados.",
            }
        )
    if turmas_criticas > 0:
        alerts.append(
            {
                "level": "warning",
                "message": f"{turmas_criticas} turma(s) estao com ocupacao acima de 90%.",
            }
        )
    if professores_sobrecarregados:
        alerts.append(
            {
                "level": "warning",
                "message": f"{len(professores_sobrecarregados)} professor(es) estao acima do limite de carga ({limite_sobrecarga} turmas).",
            }
        )
    if ocupacao_geral < 40 and len(timetables) > 0:
        alerts.append({"level": "info", "message": "Capacidade geral baixa: ha margem para abrir novas turmas."})
    if not alerts:
        alerts.append({"level": "success", "message": "Operacao estavel: sem alertas criticos no momento."})

    recommendations = []
    if slots_recomendados and total_salas > 0:
        top_slot = slots_recomendados[0]
        recommendations.append(
            f"Priorizar novas turmas em {top_slot['dia']} ({top_slot['intervalo']}), com {top_slot['salas_livres']} sala(s) livre(s)."
        )
    if salas_ociosas:
        recommendations.append(
            f"Revisar uso de {len(salas_ociosas)} sala(s) ociosa(s) para redistribuir turmas."
        )
    if professores_sobrecarregados:
        recommendations.append(
            f"Redistribuir turmas de {len(professores_sobrecarregados)} professor(es) para reduzir sobrecarga."
        )
    if turmas_sem_alunos > 0:
        recommendations.append("Avaliar consolidacao ou campanha de matricula para turmas sem alunos.")
    if turmas_criticas_slots:
        recommendations.append("Analisar os horarios mais concorridos para evitar gargalos futuros.")
    if not recommendations:
        recommendations.append("Manter monitoramento semanal para antecipar desequilibrios.")

    summary = {
        "ocupacao_geral": ocupacao_geral,
        "turmas_sem_alunos": turmas_sem_alunos,
        "turmas_criticas": turmas_criticas,
        "professores_sobrecarregados": len(professores_sobrecarregados),
        "slots_monitorados": len(slot_usage_list),
        "salas_ociosas": len(salas_ociosas),
    }

    return {
        "summary": summary,
        "alerts": alerts,
        "recommendations": recommendations,
        "professores_carga": professores_carga,
        "salas_utilizacao": salas_utilizacao,
        "disciplinas_demanda": disciplinas_demanda,
        "slots_mais_concorridos": slots_mais_concorridos,
        "slots_recomendados": slots_recomendados,
        "limite_sobrecarga": limite_sobrecarga,
    }


def _load_admin_core_data():
    cursos = Curso.query.order_by(Curso.nome.asc()).all()
    grades = GradeCurricular.query.order_by(GradeCurricular.id.desc()).all()
    salas = Sala.query.order_by(Sala.nome.asc()).all()
    professores = User.query.filter_by(role="professor").order_by(User.username.asc()).all()
    disciplinas = Disciplina.query.order_by(Disciplina.nome.asc()).all()
    turmas = (
        Turma.query.options(joinedload(Turma.curso))
        .order_by(Turma.semestre_letivo.desc(), Turma.curso_id.asc(), Turma.codigo.asc())
        .all()
    )
    alunos = Aluno.query.filter(Aluno.ativo.is_(True)).order_by(Aluno.nome.asc()).all()
    timetables = (
        Timetable.query.options(
            joinedload(Timetable.sala),
            joinedload(Timetable.professor),
            joinedload(Timetable.disciplina),
            joinedload(Timetable.turma).joinedload(Turma.curso),
        )
        .order_by(Timetable.dia.asc(), Timetable.hora_inicio.asc())
        .all()
    )
    return {
        "cursos": cursos,
        "grades": grades,
        "salas": salas,
        "professores": professores,
        "disciplinas": disciplinas,
        "turmas": turmas,
        "alunos": alunos,
        "timetables": timetables,
    }


def _build_admin_operation_panel(context):
    cursos = context["cursos"]
    grades = context["grades"]
    turmas = context["turmas"]
    professores = context["professores"]
    timetables = context["timetables"]

    matriculas_por_turma = dict(
        db.session.query(Matricula.turma_id, func.count(Matricula.id))
        .group_by(Matricula.turma_id)
        .all()
    )
    alocacoes_por_turma = dict(
        db.session.query(Timetable.turma_id, func.count(Timetable.id))
        .group_by(Timetable.turma_id)
        .all()
    )
    cursos_com_grade_ativa = {grade.curso_id for grade in grades if grade.ativa}

    cursos_sem_grade = [curso for curso in cursos if curso.id not in cursos_com_grade_ativa]
    turmas_sem_quadro = [turma for turma in turmas if alocacoes_por_turma.get(turma.id, 0) == 0]
    turmas_sem_alunos = [turma for turma in turmas if matriculas_por_turma.get(turma.id, 0) == 0]
    horarios_sem_professor = [row for row in timetables if row.professor_id is None]
    professores_sem_aptidao = [professor for professor in professores if not professor.disciplinas_aptas]
    professores_aptidao_insuficiente = [
        professor for professor in professores if len(professor.disciplinas_aptas) < 6
    ]

    total_turmas = len(turmas)
    turmas_com_quadro = total_turmas - len(turmas_sem_quadro)
    maturidade_quadro = round((turmas_com_quadro / total_turmas) * 100, 1) if total_turmas else 0.0

    fluxo = [
        {
            "ordem": "01",
            "titulo": "Estrutura Fisica",
            "descricao": "Salas disponiveis para receber horarios.",
            "status": "ok" if len(context["salas"]) > 0 else "pendente",
            "meta": f"{len(context['salas'])} sala(s)",
            "cta_label": "Gerenciar Salas",
            "cta_url": url_for("main.salas"),
        },
        {
            "ordem": "02",
            "titulo": "Oferta Academica",
            "descricao": "Cursos, grades e disciplinas prontas.",
            "status": "ok" if len(cursos) > 0 and len(cursos_sem_grade) == 0 and len(context["disciplinas"]) > 0 else "alerta",
            "meta": f"{len(cursos)} curso(s) | {len(context['disciplinas'])} disciplina(s)",
            "cta_label": "Gerenciar Cursos/Grades",
            "cta_url": url_for("main.grades"),
        },
        {
            "ordem": "03",
            "titulo": "Turmas",
            "descricao": "Turmas abertas por semestre e periodo.",
            "status": "ok" if total_turmas > 0 else "pendente",
            "meta": f"{total_turmas} turma(s)",
            "cta_label": "Gerenciar Turmas",
            "cta_url": url_for("main.turmas"),
        },
        {
            "ordem": "04",
            "titulo": "Quadros de Horario",
            "descricao": "Disciplinas distribuidas por dia/tempo/sala.",
            "status": "ok" if total_turmas > 0 and len(turmas_sem_quadro) == 0 else "alerta",
            "meta": f"{turmas_com_quadro}/{total_turmas} turma(s) com quadro",
            "cta_label": "Ver Turmas Sem Quadro",
            "cta_url": url_for("main.turmas", f="sem_quadro"),
        },
        {
            "ordem": "05",
            "titulo": "Docentes",
            "descricao": "Professores aptos e alocados por disciplina.",
            "status": (
                "ok"
                if len(professores) > 0 and len(horarios_sem_professor) == 0 and len(professores_aptidao_insuficiente) == 0
                else "alerta"
            ),
            "meta": f"{len(professores)} professor(es)",
            "cta_label": "Gerenciar Professores",
            "cta_url": url_for("main.professores"),
        },
        {
            "ordem": "06",
            "titulo": "Alunos e Matriculas",
            "descricao": "Alunos cadastrados e vinculados a turmas.",
            "status": "ok" if len(context["alunos"]) > 0 and len(turmas_sem_alunos) == 0 else "alerta",
            "meta": f"{len(context['alunos'])} aluno(s)",
            "cta_label": "Gerenciar Turmas",
            "cta_url": url_for("main.turmas"),
        },
    ]

    return {
        "maturidade_quadro": maturidade_quadro,
        "cursos_sem_grade": cursos_sem_grade,
        "turmas_sem_quadro": turmas_sem_quadro,
        "turmas_sem_alunos": turmas_sem_alunos,
        "horarios_sem_professor": horarios_sem_professor,
        "professores_sem_aptidao": professores_sem_aptidao,
        "professores_aptidao_insuficiente": professores_aptidao_insuficiente,
        "fluxo": fluxo,
    }


def _build_admin_chart_data(insights, timetables):
    day_counts = {}
    for timetable in timetables:
        day_counts[timetable.dia] = day_counts.get(timetable.dia, 0) + 1

    sorted_days = sorted(day_counts.items(), key=lambda row: _day_sort_value(row[0]))
    day_labels = [row[0] for row in sorted_days]
    day_values = [row[1] for row in sorted_days]

    top_room_rows = insights["salas_utilizacao"][:8]
    room_labels = [row["nome"] for row in top_room_rows]
    room_occupancy = [row["ocupacao"] for row in top_room_rows]

    top_professor_rows = insights["professores_carga"][:8]
    professor_labels = [row["username"] for row in top_professor_rows]
    professor_load = [row["turmas"] for row in top_professor_rows]

    status_order = ["Critica", "Saudavel", "Ociosa", "Sem uso", "Outros"]
    room_status_counts = {key: 0 for key in status_order}
    for row in insights["salas_utilizacao"]:
        status = row["status"] if row["status"] in room_status_counts else "Outros"
        room_status_counts[status] += 1

    status_labels = status_order
    status_values = [room_status_counts[label] for label in status_labels]

    return {
        "room_occupancy": {"labels": room_labels, "values": room_occupancy},
        "professor_load": {"labels": professor_labels, "values": professor_load},
        "room_status": {"labels": status_labels, "values": status_values},
        "timetables_by_day": {"labels": day_labels, "values": day_values},
    }


def _load_admin_dashboard_data():
    context = _load_admin_core_data()
    context["matriculas_count"] = Matricula.query.count()
    context["operation_panel"] = _build_admin_operation_panel(context)
    context["turno_capacity"] = _build_turno_capacity_snapshot(
        salas=context["salas"],
        turmas=context["turmas"],
        timetables=context["timetables"],
        turmas_sem_quadro=context["operation_panel"]["turmas_sem_quadro"],
    )
    context["professor_capacity"] = _build_professor_capacity_snapshot(
        professores=context["professores"],
        timetables=context["timetables"],
        turmas_sem_quadro=context["operation_panel"]["turmas_sem_quadro"],
    )
    return context


def _load_admin_insights_data():
    context = _load_admin_core_data()
    insights = _build_admin_insights(
        salas=context["salas"],
        professores=context["professores"],
        timetables=context["timetables"],
    )
    context["insights"] = insights
    context["chart_data"] = _build_admin_chart_data(insights, context["timetables"])
    context["matriculas_count"] = Matricula.query.count()
    alocacoes_por_turma = dict(
        db.session.query(Timetable.turma_id, func.count(Timetable.id))
        .group_by(Timetable.turma_id)
        .all()
    )
    turmas_sem_quadro = [turma for turma in context["turmas"] if alocacoes_por_turma.get(turma.id, 0) == 0]
    context["turno_capacity"] = _build_turno_capacity_snapshot(
        salas=context["salas"],
        turmas=context["turmas"],
        timetables=context["timetables"],
        turmas_sem_quadro=turmas_sem_quadro,
    )
    context["professor_capacity"] = _build_professor_capacity_snapshot(
        professores=context["professores"],
        timetables=context["timetables"],
        turmas_sem_quadro=turmas_sem_quadro,
    )
    return context


@bp.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    context = _load_admin_dashboard_data()
    delete_form = DeleteForm()
    return render_template(
        "admin_dashboard.html",
        delete_form=delete_form,
        **context,
    )


@bp.route("/admin/insights")
@login_required
@admin_required
def admin_insights():
    context = _load_admin_insights_data()
    return render_template("admin_insights.html", **context)

@bp.route("/horarios")
@login_required
@admin_required
def horarios():
    timetables = (
        Timetable.query.options(
            joinedload(Timetable.sala),
            joinedload(Timetable.professor),
            joinedload(Timetable.disciplina),
            joinedload(Timetable.turma).joinedload(Turma.curso),
        )
        .order_by(Timetable.dia.asc(), Timetable.hora_inicio.asc())
        .all()
    )
    delete_form = DeleteForm()
    return render_template("horarios.html", timetables=timetables, delete_form=delete_form)

# CRUD Salas

@bp.route("/salas")
@login_required
@admin_required
def salas():
    salas = Sala.query.order_by(Sala.nome.asc()).all()
    delete_form = DeleteForm()
    return render_template("salas.html", salas=salas, delete_form=delete_form)

@bp.route("/sala/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_sala():
    form = SalaForm()
    if form.validate_on_submit():
        nome = normalize_text(form.nome.data)
        if sala_name_exists(nome):
            flash("Ja existe uma sala com este nome.", "warning")
            return render_template("sala_form.html", form=form, title="Nova Sala")
        sala = Sala(nome=nome, capacidade=FIXED_SALA_CAPACITY)
        db.session.add(sala)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel criar a sala.", "danger")
            return render_template("sala_form.html", form=form, title="Nova Sala")
        flash("Sala criada com sucesso.", "success")
        return redirect(url_for("main.salas"))
    return render_template("sala_form.html", form=form, title="Nova Sala")

@bp.route("/sala/edit/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_sala(id):
    sala = db.get_or_404(Sala, id)
    form = SalaForm()
    if form.validate_on_submit():
        nome = normalize_text(form.nome.data)
        if sala_name_exists(nome, exclude_sala_id=sala.id):
            flash("Ja existe uma sala com este nome.", "warning")
            return render_template("sala_form.html", form=form, title="Editar Sala")
        sala.nome = nome
        sala.capacidade = FIXED_SALA_CAPACITY
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel editar a sala.", "danger")
            return render_template("sala_form.html", form=form, title="Editar Sala")
        flash("Sala editada com sucesso.", "success")
        return redirect(url_for("main.salas"))
    if request.method == "GET":
        form.nome.data = sala.nome
    return render_template("sala_form.html", form=form, title="Editar Sala")

@bp.route("/sala/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_sala(id):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.salas"))
    sala = db.get_or_404(Sala, id)
    related_timetables = Timetable.query.filter_by(sala_id=sala.id).count()
    if related_timetables > 0:
        flash("Nao e possivel deletar sala com alocacoes vinculadas.", "warning")
        return redirect(url_for("main.salas"))
    db.session.delete(sala)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel deletar a sala.", "danger")
        return redirect(url_for("main.salas"))
    flash("Sala deletada com sucesso.", "success")
    return redirect(url_for("main.salas"))

# CRUD Cursos


@bp.route("/cursos")
@login_required
@admin_required
def cursos():
    cursos = Curso.query.order_by(Curso.nome.asc()).all()
    delete_form = DeleteForm()
    return render_template("cursos.html", cursos=cursos, delete_form=delete_form)


@bp.route("/curso/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_curso():
    form = CursoForm()
    if form.validate_on_submit():
        nome = normalize_text(form.nome.data)
        codigo = normalize_text(form.codigo.data)
        quantidade_periodos = form.quantidade_periodos.data
        if curso_name_exists(nome):
            flash("Ja existe curso com este nome.", "warning")
            return render_template("curso_form.html", form=form, title="Novo Curso")
        if curso_codigo_exists(codigo):
            flash("Ja existe curso com este codigo.", "warning")
            return render_template("curso_form.html", form=form, title="Novo Curso")

        curso = Curso(nome=nome, codigo=codigo, quantidade_periodos=quantidade_periodos)
        db.session.add(curso)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel criar o curso.", "danger")
            return render_template("curso_form.html", form=form, title="Novo Curso")
        flash("Curso criado com sucesso.", "success")
        return redirect(url_for("main.cursos"))
    return render_template("curso_form.html", form=form, title="Novo Curso")


@bp.route("/curso/edit/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_curso(id):
    curso = db.get_or_404(Curso, id)
    form = CursoForm()
    if form.validate_on_submit():
        nome = normalize_text(form.nome.data)
        codigo = normalize_text(form.codigo.data)
        quantidade_periodos = form.quantidade_periodos.data
        if curso_name_exists(nome, exclude_curso_id=curso.id):
            flash("Ja existe curso com este nome.", "warning")
            return render_template("curso_form.html", form=form, title="Editar Curso")
        if curso_codigo_exists(codigo, exclude_curso_id=curso.id):
            flash("Ja existe curso com este codigo.", "warning")
            return render_template("curso_form.html", form=form, title="Editar Curso")

        maior_periodo_turma = (
            db.session.query(func.max(Turma.periodo))
            .filter(Turma.curso_id == curso.id)
            .scalar()
            or 0
        )
        maior_periodo_grade = (
            db.session.query(func.max(GradeCurricularItem.periodo))
            .join(GradeCurricular, GradeCurricularItem.grade_id == GradeCurricular.id)
            .filter(GradeCurricular.curso_id == curso.id)
            .scalar()
            or 0
        )
        maior_periodo_em_uso = max(maior_periodo_turma, maior_periodo_grade)
        if quantidade_periodos < maior_periodo_em_uso:
            flash(
                f"Nao e possivel reduzir para {quantidade_periodos} periodos: existem registros ate o periodo {maior_periodo_em_uso}.",
                "warning",
            )
            return render_template("curso_form.html", form=form, title="Editar Curso")

        curso.nome = nome
        curso.codigo = codigo
        curso.quantidade_periodos = quantidade_periodos
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel editar o curso.", "danger")
            return render_template("curso_form.html", form=form, title="Editar Curso")
        flash("Curso editado com sucesso.", "success")
        return redirect(url_for("main.cursos"))

    if request.method == "GET":
        form.nome.data = curso.nome
        form.codigo.data = curso.codigo
        form.quantidade_periodos.data = curso.quantidade_periodos

    return render_template("curso_form.html", form=form, title="Editar Curso")


@bp.route("/curso/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_curso(id):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.cursos"))

    curso = db.get_or_404(Curso, id)
    has_turmas = Turma.query.filter_by(curso_id=curso.id).count()
    if has_turmas > 0:
        flash("Nao e possivel deletar curso com turmas vinculadas.", "warning")
        return redirect(url_for("main.cursos"))
    has_grades = GradeCurricular.query.filter_by(curso_id=curso.id).count()
    if has_grades > 0:
        flash("Nao e possivel deletar curso com grades vinculadas.", "warning")
        return redirect(url_for("main.cursos"))

    db.session.delete(curso)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel deletar o curso.", "danger")
        return redirect(url_for("main.cursos"))
    flash("Curso deletado com sucesso.", "success")
    return redirect(url_for("main.cursos"))


# CRUD Grades Curriculares


def _load_grade_choices(form):
    cursos = Curso.query.order_by(Curso.nome.asc()).all()
    form.curso_id.choices = [
        (curso.id, f"{curso.nome} ({curso.codigo}) - {curso.quantidade_periodos} periodos")
        for curso in cursos
    ]
    return cursos


@bp.route("/grades")
@login_required
@admin_required
def grades():
    grades = (
        GradeCurricular.query.options(joinedload(GradeCurricular.curso))
        .order_by(GradeCurricular.id.desc())
        .all()
    )
    delete_form = DeleteForm()
    return render_template("grades.html", grades=grades, delete_form=delete_form)


@bp.route("/grade/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_grade():
    form = GradeCurricularForm()
    cursos = _load_grade_choices(form)
    if form.validate_on_submit():
        if not cursos:
            flash("Cadastre ao menos um curso antes de criar uma grade.", "warning")
            return redirect(url_for("main.cursos"))

        nome = normalize_text(form.nome.data)
        curso_id = form.curso_id.data
        if grade_nome_exists(curso_id, nome):
            flash("Ja existe grade com este nome para o curso selecionado.", "warning")
            return render_template("grade_form.html", form=form, title="Nova Grade Curricular")

        GradeCurricular.query.filter_by(curso_id=curso_id).update({"ativa": False})
        grade = GradeCurricular(nome=nome, curso_id=curso_id, ativa=True)
        db.session.add(grade)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel criar a grade curricular.", "danger")
            return render_template("grade_form.html", form=form, title="Nova Grade Curricular")
        flash("Grade curricular criada com sucesso.", "success")
        return redirect(url_for("main.grade_items", grade_id=grade.id))

    return render_template("grade_form.html", form=form, title="Nova Grade Curricular")


@bp.route("/grade/edit/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_grade(id):
    grade = db.get_or_404(GradeCurricular, id)
    form = GradeCurricularForm()
    _load_grade_choices(form)
    if form.validate_on_submit():
        nome = normalize_text(form.nome.data)
        curso_id = form.curso_id.data
        if grade_nome_exists(curso_id, nome, exclude_grade_id=grade.id):
            flash("Ja existe grade com este nome para o curso selecionado.", "warning")
            return render_template("grade_form.html", form=form, title="Editar Grade Curricular")

        if grade.curso_id != curso_id:
            has_items = GradeCurricularItem.query.filter_by(grade_id=grade.id).count()
            if has_items > 0:
                flash("Nao e possivel trocar o curso de uma grade que ja possui itens.", "warning")
                return render_template("grade_form.html", form=form, title="Editar Grade Curricular")

        GradeCurricular.query.filter(
            GradeCurricular.curso_id == curso_id,
            GradeCurricular.id != grade.id,
        ).update({"ativa": False})
        grade.nome = nome
        grade.curso_id = curso_id
        grade.ativa = True
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel editar a grade curricular.", "danger")
            return render_template("grade_form.html", form=form, title="Editar Grade Curricular")
        flash("Grade curricular editada com sucesso.", "success")
        return redirect(url_for("main.grades"))

    if request.method == "GET":
        form.nome.data = grade.nome
        form.curso_id.data = grade.curso_id
    return render_template("grade_form.html", form=form, title="Editar Grade Curricular")


@bp.route("/grade/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_grade(id):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.grades"))

    grade = db.get_or_404(GradeCurricular, id)
    has_timetables = (
        Timetable.query.join(Turma, Timetable.turma_id == Turma.id)
        .filter(Turma.curso_id == grade.curso_id)
        .count()
    )
    if has_timetables > 0 and grade.ativa:
        flash("Nao e possivel deletar grade ativa com alocacoes de turma no curso.", "warning")
        return redirect(url_for("main.grades"))

    db.session.delete(grade)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel deletar a grade curricular.", "danger")
        return redirect(url_for("main.grades"))
    flash("Grade curricular deletada com sucesso.", "success")
    return redirect(url_for("main.grades"))


@bp.route("/grade/<int:grade_id>/itens")
@login_required
@admin_required
def grade_items(grade_id):
    grade = db.get_or_404(GradeCurricular, grade_id)
    items = (
        GradeCurricularItem.query.options(joinedload(GradeCurricularItem.disciplina))
        .filter_by(grade_id=grade.id)
        .order_by(GradeCurricularItem.periodo.asc(), GradeCurricularItem.id.asc())
        .all()
    )
    delete_form = DeleteForm()
    return render_template("grade_items.html", grade=grade, items=items, delete_form=delete_form)


def _load_grade_item_choices(form):
    disciplinas = Disciplina.query.order_by(Disciplina.nome.asc()).all()
    form.disciplina_id.choices = [(disciplina.id, disciplina.nome) for disciplina in disciplinas]
    return disciplinas


@bp.route("/grade/<int:grade_id>/item/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_grade_item(grade_id):
    grade = db.get_or_404(GradeCurricular, grade_id)
    form = GradeCurricularItemForm()
    disciplinas = _load_grade_item_choices(form)
    limite_periodos = grade.curso.quantidade_periodos if grade.curso else 16
    if form.validate_on_submit():
        if not disciplinas:
            flash("Cadastre disciplinas antes de montar a grade.", "warning")
            return redirect(url_for("main.disciplinas"))
        if form.periodo.data > limite_periodos:
            flash(
                f"O curso desta grade possui apenas {limite_periodos} periodo(s).",
                "warning",
            )
            return render_template("grade_item_form.html", form=form, grade=grade, title="Adicionar Item de Grade")
        if grade_item_exists(grade.id, form.disciplina_id.data):
            flash("Disciplina ja incluida nesta grade.", "warning")
            return render_template("grade_item_form.html", form=form, grade=grade, title="Adicionar Item de Grade")

        item = GradeCurricularItem(
            grade_id=grade.id,
            disciplina_id=form.disciplina_id.data,
            periodo=form.periodo.data,
        )
        db.session.add(item)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel adicionar item na grade.", "danger")
            return render_template("grade_item_form.html", form=form, grade=grade, title="Adicionar Item de Grade")
        flash("Item adicionado na grade com sucesso.", "success")
        return redirect(url_for("main.grade_items", grade_id=grade.id))

    return render_template("grade_item_form.html", form=form, grade=grade, title="Adicionar Item de Grade")


@bp.route("/grade/<int:grade_id>/item/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_grade_item(grade_id, item_id):
    grade = db.get_or_404(GradeCurricular, grade_id)
    item = db.get_or_404(GradeCurricularItem, item_id)
    if item.grade_id != grade.id:
        flash("Item de grade invalido.", "warning")
        return redirect(url_for("main.grade_items", grade_id=grade.id))

    form = GradeCurricularItemForm()
    _load_grade_item_choices(form)
    limite_periodos = grade.curso.quantidade_periodos if grade.curso else 16
    if form.validate_on_submit():
        if form.periodo.data > limite_periodos:
            flash(
                f"O curso desta grade possui apenas {limite_periodos} periodo(s).",
                "warning",
            )
            return render_template("grade_item_form.html", form=form, grade=grade, title="Editar Item de Grade")
        if grade_item_exists(grade.id, form.disciplina_id.data, exclude_item_id=item.id):
            flash("Disciplina ja incluida nesta grade.", "warning")
            return render_template("grade_item_form.html", form=form, grade=grade, title="Editar Item de Grade")

        item.disciplina_id = form.disciplina_id.data
        item.periodo = form.periodo.data
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel editar item da grade.", "danger")
            return render_template("grade_item_form.html", form=form, grade=grade, title="Editar Item de Grade")
        flash("Item da grade editado com sucesso.", "success")
        return redirect(url_for("main.grade_items", grade_id=grade.id))

    if request.method == "GET":
        form.disciplina_id.data = item.disciplina_id
        form.periodo.data = item.periodo

    return render_template("grade_item_form.html", form=form, grade=grade, title="Editar Item de Grade")


@bp.route("/grade/<int:grade_id>/item/delete/<int:item_id>", methods=["POST"])
@login_required
@admin_required
def delete_grade_item(grade_id, item_id):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.grade_items", grade_id=grade_id))

    item = db.get_or_404(GradeCurricularItem, item_id)
    if item.grade_id != grade_id:
        flash("Item de grade invalido.", "warning")
        return redirect(url_for("main.grade_items", grade_id=grade_id))

    db.session.delete(item)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel remover item da grade.", "danger")
        return redirect(url_for("main.grade_items", grade_id=grade_id))
    flash("Item removido da grade com sucesso.", "success")
    return redirect(url_for("main.grade_items", grade_id=grade_id))


# CRUD Disciplinas

@bp.route("/disciplinas")
@login_required
@admin_required
def disciplinas():
    disciplinas = Disciplina.query.order_by(Disciplina.nome.asc()).all()
    delete_form = DeleteForm()
    return render_template("disciplinas.html", disciplinas=disciplinas, delete_form=delete_form)

@bp.route("/disciplina/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_disciplina():
    form = DisciplinaForm()
    if form.validate_on_submit():
        nome = normalize_text(form.nome.data)
        if disciplina_name_exists(nome):
            flash("Ja existe uma disciplina com este nome.", "warning")
            return render_template("disciplina_form.html", form=form, title="Nova Disciplina")
        disciplina = Disciplina(nome=nome, codigo=generate_disciplina_code())
        db.session.add(disciplina)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel criar a disciplina.", "danger")
            return render_template("disciplina_form.html", form=form, title="Nova Disciplina")
        flash("Disciplina criada com sucesso.", "success")
        return redirect(url_for("main.disciplinas"))
    return render_template("disciplina_form.html", form=form, title="Nova Disciplina")

@bp.route("/disciplina/edit/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_disciplina(id):
    disciplina = db.get_or_404(Disciplina, id)
    form = DisciplinaForm()
    if form.validate_on_submit():
        nome = normalize_text(form.nome.data)
        if disciplina_name_exists(nome, exclude_disciplina_id=disciplina.id):
            flash("Ja existe uma disciplina com este nome.", "warning")
            return render_template("disciplina_form.html", form=form, title="Editar Disciplina")
        disciplina.nome = nome
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel editar a disciplina.", "danger")
            return render_template("disciplina_form.html", form=form, title="Editar Disciplina")
        flash("Disciplina editada com sucesso.", "success")
        return redirect(url_for("main.disciplinas"))
    if request.method == "GET":
        form.nome.data = disciplina.nome
    return render_template("disciplina_form.html", form=form, title="Editar Disciplina")

@bp.route("/disciplina/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_disciplina(id):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.disciplinas"))
    disciplina = db.get_or_404(Disciplina, id)
    related_timetables = Timetable.query.filter_by(disciplina_id=disciplina.id).count()
    if related_timetables > 0:
        flash("Nao e possivel deletar disciplina com alocacoes vinculadas.", "warning")
        return redirect(url_for("main.disciplinas"))
    related_grade_items = GradeCurricularItem.query.filter_by(disciplina_id=disciplina.id).count()
    if related_grade_items > 0:
        flash("Nao e possivel deletar disciplina vinculada a uma grade curricular.", "warning")
        return redirect(url_for("main.disciplinas"))
    for professor in disciplina.professores_aptos:
        professor.disciplinas_aptas = [d for d in professor.disciplinas_aptas if d.id != disciplina.id]
    db.session.delete(disciplina)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel deletar a disciplina.", "danger")
        return redirect(url_for("main.disciplinas"))
    flash("Disciplina deletada com sucesso.", "success")
    return redirect(url_for("main.disciplinas"))


# CRUD Turmas (oferta semestral)

@bp.route("/turmas")
@login_required
@admin_required
def turmas():
    active_filter = normalize_text(request.args.get("f")).lower()
    filter_sem_quadro = active_filter == "sem_quadro"
    turmas = (
        Turma.query.options(joinedload(Turma.curso))
        .order_by(Turma.semestre_letivo.desc(), Turma.curso_id.asc(), Turma.codigo.asc())
        .all()
    )
    alocacoes_por_turma = dict(
        db.session.query(Timetable.turma_id, func.count(Timetable.id))
        .group_by(Timetable.turma_id)
        .all()
    )
    if filter_sem_quadro:
        turmas = [turma for turma in turmas if alocacoes_por_turma.get(turma.id, 0) == 0]

    matriculas_por_turma = dict(
        db.session.query(Matricula.turma_id, func.count(Matricula.id))
        .group_by(Matricula.turma_id)
        .all()
    )
    delete_form = DeleteForm()
    return render_template(
        "turmas.html",
        turmas=turmas,
        alocacoes_por_turma=alocacoes_por_turma,
        delete_form=delete_form,
        turno_label_for=get_turno_label,
        matriculas_por_turma=matriculas_por_turma,
        active_filter=active_filter,
        filter_sem_quadro=filter_sem_quadro,
    )


def _load_turma_course_choices(form):
    cursos = Curso.query.order_by(Curso.nome.asc()).all()
    form.curso_id.choices = [
        (curso.id, f"{curso.nome} ({curso.codigo}) - {curso.quantidade_periodos} periodos")
        for curso in cursos
    ]
    return cursos


@bp.route("/turma/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_turma():
    form = TurmaForm()
    cursos = _load_turma_course_choices(form)
    curso_by_id = {curso.id: curso for curso in cursos}
    turno_capacity = _build_turno_capacity_snapshot(
        salas=Sala.query.order_by(Sala.nome.asc()).all(),
        turmas=Turma.query.all(),
        timetables=Timetable.query.all(),
    )
    if form.validate_on_submit():
        if not cursos:
            flash("Cadastre ao menos um curso antes de criar turmas.", "warning")
            return redirect(url_for("main.cursos"))

        curso_id = form.curso_id.data
        curso = curso_by_id.get(curso_id)
        if curso is None:
            flash("Curso invalido.", "warning")
            return render_template("turma_form.html", form=form, title="Nova Turma")
        codigo = normalize_text(form.codigo.data)
        semestre_letivo = normalize_text(form.semestre_letivo.data)
        if form.periodo.data > curso.quantidade_periodos:
            flash(
                f"O curso selecionado possui apenas {curso.quantidade_periodos} periodo(s).",
                "warning",
            )
            return render_template("turma_form.html", form=form, title="Nova Turma")
        if form.quantidade_alunos.data < 0 or form.quantidade_alunos.data > MAX_TURMA_CAPACITY:
            flash(
                f"A capacidade da turma deve estar entre 0 e {MAX_TURMA_CAPACITY} alunos.",
                "warning",
            )
            return render_template("turma_form.html", form=form, title="Nova Turma")
        if _disponibilidade_real_turno(turno_capacity, form.turno.data) <= 0:
            flash(
                f"Nao e possivel criar nova turma no turno {get_turno_label(form.turno.data)}: limite de capacidade atingido. Cadastre mais salas antes de abrir novas turmas.",
                "warning",
            )
            return render_template("turma_form.html", form=form, title="Nova Turma")
        if active_grade_for_curso(curso_id) is None:
            flash("Cadastre e ative uma grade curricular para o curso antes de abrir turmas.", "warning")
            return redirect(url_for("main.grades"))
        if turma_codigo_semestre_exists(curso_id=curso_id, codigo=codigo, semestre_letivo=semestre_letivo):
            flash("Ja existe turma com este codigo para o semestre informado.", "warning")
            return render_template("turma_form.html", form=form, title="Nova Turma")

        turma = Turma(
            curso_id=curso_id,
            codigo=codigo,
            semestre_letivo=semestre_letivo,
            periodo=form.periodo.data,
            turno=form.turno.data,
            quantidade_alunos=form.quantidade_alunos.data,
        )
        db.session.add(turma)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel criar a turma.", "danger")
            return render_template("turma_form.html", form=form, title="Nova Turma")

        flash("Turma criada com sucesso.", "success")
        return redirect(url_for("main.turmas"))

    return render_template("turma_form.html", form=form, title="Nova Turma")


@bp.route("/turma/edit/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_turma(id):
    turma = db.get_or_404(Turma, id)
    form = TurmaForm()
    cursos = _load_turma_course_choices(form)
    curso_by_id = {curso.id: curso for curso in cursos}
    if form.validate_on_submit():
        curso_id = form.curso_id.data
        curso = curso_by_id.get(curso_id)
        if curso is None:
            flash("Curso invalido.", "warning")
            return render_template("turma_form.html", form=form, title="Editar Turma")
        codigo = normalize_text(form.codigo.data)
        semestre_letivo = normalize_text(form.semestre_letivo.data)
        if form.periodo.data > curso.quantidade_periodos:
            flash(
                f"O curso selecionado possui apenas {curso.quantidade_periodos} periodo(s).",
                "warning",
            )
            return render_template("turma_form.html", form=form, title="Editar Turma")
        if form.quantidade_alunos.data < 0 or form.quantidade_alunos.data > MAX_TURMA_CAPACITY:
            flash(
                f"A capacidade da turma deve estar entre 0 e {MAX_TURMA_CAPACITY} alunos.",
                "warning",
            )
            return render_template("turma_form.html", form=form, title="Editar Turma")
        if active_grade_for_curso(curso_id) is None:
            flash("Cadastre e ative uma grade curricular para o curso antes de manter turmas.", "warning")
            return redirect(url_for("main.grades"))
        if turma_codigo_semestre_exists(
            curso_id=curso_id,
            codigo=codigo,
            semestre_letivo=semestre_letivo,
            exclude_turma_id=turma.id,
        ):
            flash("Ja existe turma com este codigo para o semestre informado.", "warning")
            return render_template("turma_form.html", form=form, title="Editar Turma")

        turma.curso_id = curso_id
        turma.codigo = codigo
        turma.semestre_letivo = semestre_letivo
        turma.periodo = form.periodo.data
        turma.turno = form.turno.data
        turma.quantidade_alunos = form.quantidade_alunos.data
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel editar a turma.", "danger")
            return render_template("turma_form.html", form=form, title="Editar Turma")

        flash("Turma editada com sucesso.", "success")
        return redirect(url_for("main.turmas"))

    if request.method == "GET":
        form.curso_id.data = turma.curso_id
        form.codigo.data = turma.codigo
        form.semestre_letivo.data = turma.semestre_letivo
        form.periodo.data = turma.periodo
        form.turno.data = turma.turno
        form.quantidade_alunos.data = turma.quantidade_alunos

    return render_template("turma_form.html", form=form, title="Editar Turma")


@bp.route("/turma/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_turma(id):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.turmas"))

    turma = db.get_or_404(Turma, id)
    related_timetables = Timetable.query.filter_by(turma_id=turma.id).count()
    if related_timetables > 0:
        flash("Nao e possivel deletar turma com alocacoes vinculadas.", "warning")
        return redirect(url_for("main.turmas"))
    related_matriculas = Matricula.query.filter_by(turma_id=turma.id).count()
    if related_matriculas > 0:
        flash("Nao e possivel deletar turma com alunos vinculados.", "warning")
        return redirect(url_for("main.turmas"))

    db.session.delete(turma)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel deletar a turma.", "danger")
        return redirect(url_for("main.turmas"))

    flash("Turma deletada com sucesso.", "success")
    return redirect(url_for("main.turmas"))


@bp.route("/turma/<int:id>/quadro")
@login_required
@admin_required
def turma_quadro(id):
    turma = db.get_or_404(Turma, id)
    timetables = _load_turma_timetable_rows(turma.id)
    disciplinas_ids = allowed_disciplina_ids_for_turma(turma)
    disciplinas = []
    if disciplinas_ids:
        disciplinas = (
            Disciplina.query.filter(Disciplina.id.in_(disciplinas_ids))
            .order_by(Disciplina.nome.asc())
            .all()
        )

    schedule_grid = _build_turma_schedule_grid(turma, timetables)
    completeness = _turma_grade_completeness(turma, timetables)
    all_disciplina_ids = sorted(set(completeness["missing_ids"] + completeness["extra_ids"] + completeness["duplicate_ids"]))
    disciplina_name_by_id = {}
    if all_disciplina_ids:
        disciplina_name_by_id = {
            row.id: row.nome
            for row in Disciplina.query.with_entities(Disciplina.id, Disciplina.nome)
            .filter(Disciplina.id.in_(all_disciplina_ids))
            .all()
        }

    pending_teacher_count = sum(1 for timetable in timetables if timetable.professor_id is None)
    form = DeleteForm()
    return render_template(
        "turma_quadro.html",
        turma=turma,
        disciplinas=disciplinas,
        timetables=timetables,
        schedule_grid=schedule_grid,
        pending_teacher_count=pending_teacher_count,
        generate_form=form,
        turno_label=get_turno_label(turma.turno),
        completeness=completeness,
        missing_disciplinas=[disciplina_name_by_id.get(row_id, f"ID {row_id}") for row_id in completeness["missing_ids"]],
        extra_disciplinas=[disciplina_name_by_id.get(row_id, f"ID {row_id}") for row_id in completeness["extra_ids"]],
        duplicate_disciplinas=[disciplina_name_by_id.get(row_id, f"ID {row_id}") for row_id in completeness["duplicate_ids"]],
    )


@bp.route("/turma/<int:id>/quadro/gerar", methods=["POST"])
@login_required
@admin_required
def gerar_turma_quadro(id):
    turma = db.get_or_404(Turma, id)
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.turma_quadro", id=turma.id))

    replace_existing = request.form.get("replace") == "1"
    existing_rows = Timetable.query.filter_by(turma_id=turma.id).all()
    if existing_rows and not replace_existing:
        flash("Esta turma ja possui quadro cadastrado. Use a opcao de regenerar para substituir.", "warning")
        return redirect(url_for("main.turma_quadro", id=turma.id))

    if existing_rows:
        existing_ids = [row.id for row in existing_rows]
        has_presencas = Presenca.query.filter(Presenca.timetable_id.in_(existing_ids)).count()
        if has_presencas > 0:
            flash("Nao e possivel regenerar quadro com chamadas ja registradas.", "warning")
            return redirect(url_for("main.turma_quadro", id=turma.id))
        for row in existing_rows:
            db.session.delete(row)
        db.session.flush()

    disciplinas_ids = allowed_disciplina_ids_for_turma(turma)
    if not disciplinas_ids:
        db.session.rollback()
        flash("A turma nao possui disciplinas configuradas para o periodo na grade ativa.", "warning")
        return redirect(url_for("main.turma_quadro", id=turma.id))

    disciplinas = (
        Disciplina.query.filter(Disciplina.id.in_(disciplinas_ids))
        .order_by(Disciplina.nome.asc())
        .all()
    )
    if not disciplinas:
        db.session.rollback()
        flash("Nao ha disciplinas disponiveis para montar o quadro da turma.", "warning")
        return redirect(url_for("main.turma_quadro", id=turma.id))

    salas = Sala.query.order_by(Sala.nome.asc()).all()
    if not salas:
        db.session.rollback()
        flash("Cadastre salas antes de gerar o quadro de horarios.", "warning")
        return redirect(url_for("main.salas"))

    slot_capacity = len(WEEKDAY_VALUES[:5]) * len(allowed_slot_ids_for_turno(turma.turno))
    if len(disciplinas) > slot_capacity:
        db.session.rollback()
        flash(
            f"Ha {len(disciplinas)} disciplinas para apenas {slot_capacity} slots no turno {get_turno_label(turma.turno).lower()}.",
            "warning",
        )
        return redirect(url_for("main.turma_quadro", id=turma.id))

    generated_entries, unallocated_names = _build_turma_schedule_entries(
        turma=turma,
        disciplinas=disciplinas,
        salas=salas,
    )
    if unallocated_names:
        db.session.rollback()
        flash(
            "Nao foi possivel distribuir todas as disciplinas por falta de sala disponivel: "
            + ", ".join(unallocated_names),
            "warning",
        )
        return redirect(url_for("main.turma_quadro", id=turma.id))

    db.session.add_all(generated_entries)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel gerar o quadro da turma.", "danger")
        return redirect(url_for("main.turma_quadro", id=turma.id))

    flash(
        "Quadro da turma gerado com sucesso. Agora aloque os professores em cada horario.",
        "success",
    )
    return redirect(url_for("main.turma_quadro", id=turma.id))


@bp.route("/timetable/<int:id>/alocar-professor", methods=["GET", "POST"])
@login_required
@admin_required
def alocar_professor_timetable(id):
    timetable = (
        Timetable.query.options(
            joinedload(Timetable.sala),
            joinedload(Timetable.professor),
            joinedload(Timetable.disciplina),
            joinedload(Timetable.turma).joinedload(Turma.curso),
        )
        .filter(Timetable.id == id)
        .first()
    )
    if timetable is None:
        flash("Alocacao nao encontrada.", "warning")
        return redirect(url_for("main.horarios"))
    if timetable.turma is None:
        flash("Alocacao sem turma vinculada.", "warning")
        return redirect(url_for("main.horarios"))

    turma_rows = _load_turma_timetable_rows(timetable.turma_id)
    completeness = _turma_grade_completeness(timetable.turma, turma_rows)
    if not completeness["is_complete"]:
        flash("Conclua primeiro a grade da turma (disciplinas/tempos/salas) para depois alocar professores.", "warning")
        return redirect(url_for("main.turma_quadro", id=timetable.turma_id))

    workload_index = _build_professor_workload_index(exclude_timetable_id=timetable.id)
    available_professores = _available_professores_for_timetable(timetable, workload_index=workload_index)
    form = ProfessorAssignmentForm()
    form.professor_id.choices = [(professor.id, professor.username) for professor in available_professores]
    if not form.professor_id.choices:
        flash("Nenhum professor apto e disponivel para este horario.", "warning")
        return redirect(url_for("main.turma_quadro", id=timetable.turma_id))

    allowed_ids = {professor_id for professor_id, _ in form.professor_id.choices}
    if form.validate_on_submit():
        if form.professor_id.data not in allowed_ids:
            flash("Professor invalido para esta alocacao.", "warning")
            return redirect(url_for("main.alocar_professor_timetable", id=timetable.id))
        professor = db.session.get(User, form.professor_id.data)
        if professor is None or professor.role != "professor":
            flash("Professor selecionado e invalido.", "warning")
            return redirect(url_for("main.alocar_professor_timetable", id=timetable.id))
        if not professor_can_teach_disciplina(professor, timetable.disciplina_id):
            flash("Professor sem aptidao para a disciplina da alocacao.", "danger")
            return redirect(url_for("main.alocar_professor_timetable", id=timetable.id))
        if not _professor_is_free_for_timetable(professor.id, timetable, exclude_timetable_id=timetable.id):
            flash("Professor indisponivel para este horario.", "danger")
            return redirect(url_for("main.alocar_professor_timetable", id=timetable.id))
        workload_ok, workload_message = _ensure_professor_workload_available(
            professor=professor,
            timetable=timetable,
            workload_index=workload_index,
        )
        if not workload_ok:
            flash(workload_message, "danger")
            return redirect(url_for("main.alocar_professor_timetable", id=timetable.id))

        timetable.professor_id = professor.id
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel salvar a alocacao do professor.", "danger")
            return redirect(url_for("main.alocar_professor_timetable", id=timetable.id))

        flash("Professor alocado com sucesso.", "success")
        return redirect(url_for("main.turma_quadro", id=timetable.turma_id))

    if request.method == "GET":
        if timetable.professor_id in allowed_ids:
            form.professor_id.data = timetable.professor_id
        else:
            form.professor_id.data = form.professor_id.choices[0][0]

    return render_template(
        "timetable_professor_form.html",
        title="Alocar Professor",
        form=form,
        timetable=timetable,
    )


@bp.route("/turma/<int:id>/alocar-professores-lote", methods=["GET", "POST"])
@login_required
@admin_required
def alocar_professores_turma_lote(id):
    turma = db.get_or_404(Turma, id)
    timetables = _load_turma_timetable_rows(turma.id)
    if not timetables:
        flash("A turma ainda nao possui quadro gerado.", "warning")
        return redirect(url_for("main.turma_quadro", id=turma.id))

    completeness = _turma_grade_completeness(turma, timetables)
    if not completeness["is_complete"]:
        flash("Conclua primeiro a grade da turma (disciplinas/tempos/salas) para depois alocar professores.", "warning")
        return redirect(url_for("main.turma_quadro", id=turma.id))

    pending_timetables = [row for row in timetables if row.professor_id is None]
    if not pending_timetables:
        flash("Todos os horarios desta turma ja possuem professor.", "success")
        return redirect(url_for("main.turma_quadro", id=turma.id))

    form = BulkProfessorAssignmentForm()
    options_by_timetable = _build_bulk_professor_options(pending_timetables)
    workload_index = _build_professor_workload_index()
    timetable_by_id = {row.id: row for row in pending_timetables}

    if form.validate_on_submit():
        selected_by_timetable = _extract_bulk_assignment_payload(pending_timetables)
        if not selected_by_timetable:
            flash("Selecione ao menos um professor para alocar em lote.", "warning")
            return redirect(url_for("main.alocar_professores_turma_lote", id=turma.id))

        for timetable in pending_timetables:
            if timetable.id not in selected_by_timetable:
                continue
            selected_professor_id = selected_by_timetable[timetable.id]
            if selected_professor_id is None:
                flash("Selecao de professor invalida em uma das linhas.", "warning")
                return redirect(url_for("main.alocar_professores_turma_lote", id=turma.id))
            allowed_ids = {professor_id for professor_id, _ in options_by_timetable.get(timetable.id, [])}
            if selected_professor_id not in allowed_ids:
                flash("Um professor selecionado nao esta apto/disponivel para o horario informado.", "warning")
                return redirect(url_for("main.alocar_professores_turma_lote", id=turma.id))

        for timetable_id, professor_id in selected_by_timetable.items():
            professor = db.session.get(User, professor_id)
            timetable = timetable_by_id.get(timetable_id)
            if timetable is None or professor is None or professor.role != "professor":
                flash("Dados de alocacao invalidos.", "warning")
                return redirect(url_for("main.alocar_professores_turma_lote", id=turma.id))
            if not professor_can_teach_disciplina(professor, timetable.disciplina_id):
                flash(
                    f"Professor {professor.username} nao e apto para {timetable.disciplina.nome if timetable.disciplina else 'a disciplina'}.",
                    "danger",
                )
                return redirect(url_for("main.alocar_professores_turma_lote", id=turma.id))
            if not _professor_is_free_for_timetable(professor.id, timetable, exclude_timetable_id=timetable.id):
                flash(
                    f"Professor {professor.username} ficou indisponivel para {timetable.dia} {timetable.hora_inicio}-{timetable.hora_fim}.",
                    "danger",
                )
                return redirect(url_for("main.alocar_professores_turma_lote", id=turma.id))
            workload_ok, workload_message = _ensure_professor_workload_available(
                professor=professor,
                timetable=timetable,
                workload_index=workload_index,
            )
            if not workload_ok:
                flash(workload_message, "danger")
                return redirect(url_for("main.alocar_professores_turma_lote", id=turma.id))

        internal_conflict = _has_bulk_internal_professor_conflict(
            selected_by_timetable=selected_by_timetable,
            timetable_by_id=timetable_by_id,
        )
        if internal_conflict:
            professor = db.session.get(User, internal_conflict["professor_id"])
            timetable_a = internal_conflict["timetable_a"]
            timetable_b = internal_conflict["timetable_b"]
            professor_name = professor.username if professor else "Professor"
            flash(
                (
                    f"Conflito na selecao em lote: {professor_name} foi escolhido para dois horarios sobrepostos "
                    f"({timetable_a.dia} {timetable_a.hora_inicio}-{timetable_a.hora_fim} e "
                    f"{timetable_b.dia} {timetable_b.hora_inicio}-{timetable_b.hora_fim})."
                ),
                "danger",
            )
            return redirect(url_for("main.alocar_professores_turma_lote", id=turma.id))

        planned_increments = {}
        for timetable_id, professor_id in selected_by_timetable.items():
            professor = db.session.get(User, professor_id)
            timetable = timetable_by_id.get(timetable_id)
            if professor is None or timetable is None:
                continue
            workload_ok, workload_message = _ensure_professor_workload_available(
                professor=professor,
                timetable=timetable,
                workload_index=workload_index,
                planned_increments=planned_increments,
            )
            if not workload_ok:
                flash(workload_message, "danger")
                return redirect(url_for("main.alocar_professores_turma_lote", id=turma.id))
            turno = _resolve_timetable_turno(timetable)
            plan_for_professor = planned_increments.setdefault(
                professor.id,
                {
                    "total": 0,
                    "by_turno": {turno_value: 0 for turno_value, _ in TURNO_CHOICES},
                },
            )
            plan_for_professor["total"] += 1
            if turno in plan_for_professor["by_turno"]:
                plan_for_professor["by_turno"][turno] += 1

        for timetable_id, professor_id in selected_by_timetable.items():
            timetable_by_id[timetable_id].professor_id = professor_id

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel salvar a alocacao em lote.", "danger")
            return redirect(url_for("main.alocar_professores_turma_lote", id=turma.id))

        flash(f"Alocacao em lote concluida para {len(selected_by_timetable)} horario(s).", "success")
        return redirect(url_for("main.turma_quadro", id=turma.id))

    return render_template(
        "turma_bulk_professor_form.html",
        title="Alocar Professores em Lote",
        form=form,
        turma=turma,
        pending_timetables=pending_timetables,
        options_by_timetable=options_by_timetable,
        field_name_for=_bulk_assignment_field_name,
    )


# CRUD Professores


def _load_professor_disciplina_choices(form):
    disciplinas = Disciplina.query.order_by(Disciplina.nome.asc()).all()
    form.disciplinas_ids.choices = [(disciplina.id, disciplina.nome) for disciplina in disciplinas]
    return disciplinas


def _load_aluno_course_choices(form):
    cursos = Curso.query.order_by(Curso.ativo.desc(), Curso.nome.asc()).all()
    form.curso_id.choices = [
        (curso.id, f"{curso.nome} ({curso.codigo}){' - Inativo' if not curso.ativo else ''}")
        for curso in cursos
    ]
    return cursos

@bp.route("/professores")
@login_required
@admin_required
def professores():
    professores = User.query.filter_by(role="professor").order_by(User.username.asc()).all()
    delete_form = DeleteForm()
    reset_form = ResetPasswordForm()
    return render_template(
        "professores.html",
        professores=professores,
        jornada_label_for=get_professor_workload_label,
        delete_form=delete_form,
        reset_form=reset_form,
    )


@bp.route("/professores/replanejar-automatico", methods=["POST"])
@login_required
@admin_required
def replanejar_professores_automatico():
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.professores"))

    try:
        summary = rebuild_professores_automatico(
            min_disciplinas_por_professor=6,
            extra_professores=0,
        )
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel replanejar automaticamente o corpo docente.", "danger")
        return redirect(url_for("main.professores"))

    flash(
        (
            f"Corpo docente replanejado. Removidos: {summary['removed_professores']} | "
            f"Criados: {summary['created_professores']} | "
            f"Matutino+Vespertino: {summary['profile_counts']['matutino_vespertino']} | "
            f"Vespertino+Noturno: {summary['profile_counts']['vespertino_noturno']}."
        ),
        "success",
    )
    return redirect(url_for("main.professores"))


@bp.route("/professor/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_professor():
    form = ProfessorForm()
    _load_professor_disciplina_choices(form)
    if form.validate_on_submit():
        username = normalize_text(form.username.data)
        duplicate_error = username_exists(username)
        if duplicate_error:
            flash(duplicate_error, "warning")
            return render_template("register.html", title="Novo Professor", form=form)
        user = User(
            username=username,
            email=synthetic_professor_email(username),
            role="professor",
            jornada_turnos=form.jornada_turnos.data or PROFESSOR_DEFAULT_WORKLOAD,
        )
        user.set_password(form.password.data)
        if form.disciplinas_ids.data:
            user.disciplinas_aptas = Disciplina.query.filter(Disciplina.id.in_(form.disciplinas_ids.data)).all()
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel registrar o professor.", "danger")
            return render_template("register.html", title="Novo Professor", form=form)
        flash("Professor registrado com sucesso.", "success")
        return redirect(url_for("main.professores"))
    return render_template("register.html", title="Novo Professor", form=form)

@bp.route("/professor/edit/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_professor(id):
    professor = db.get_or_404(User, id)
    if professor.role != "professor":
        flash("Usuario selecionado nao e professor.", "warning")
        return redirect(url_for("main.professores"))
    form = ProfessorEditForm()
    _load_professor_disciplina_choices(form)
    if form.validate_on_submit():
        username = normalize_text(form.username.data)
        duplicate_error = username_exists(username, exclude_user_id=professor.id)
        if duplicate_error:
            flash(duplicate_error, "warning")
            return render_template("register.html", title="Editar Professor", form=form)
        professor.username = username
        professor.email = synthetic_professor_email(username)
        professor.jornada_turnos = form.jornada_turnos.data or PROFESSOR_DEFAULT_WORKLOAD
        professor.disciplinas_aptas = Disciplina.query.filter(Disciplina.id.in_(form.disciplinas_ids.data)).all()
        if form.password.data:
            professor.set_password(form.password.data)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel editar o professor.", "danger")
            return render_template("register.html", title="Editar Professor", form=form)
        flash("Professor editado com sucesso.", "success")
        return redirect(url_for("main.professores"))
    if request.method == "GET":
        form.username.data = professor.username
        form.jornada_turnos.data = professor.jornada_turnos or PROFESSOR_DEFAULT_WORKLOAD
        form.disciplinas_ids.data = [disciplina.id for disciplina in professor.disciplinas_aptas]
    return render_template("register.html", title="Editar Professor", form=form)

@bp.route("/professor/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_professor(id):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.professores"))
    professor = db.get_or_404(User, id)
    if professor.role != "professor":
        flash("Usuario selecionado nao e professor.", "warning")
        return redirect(url_for("main.professores"))
    related_timetables = Timetable.query.filter_by(professor_id=professor.id).count()
    if related_timetables > 0:
        flash("Nao e possivel deletar professor com alocacoes vinculadas.", "warning")
        return redirect(url_for("main.professores"))
    professor.disciplinas_aptas = []
    db.session.delete(professor)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel deletar o professor.", "danger")
        return redirect(url_for("main.professores"))
    flash("Professor deletado com sucesso.", "success")
    return redirect(url_for("main.professores"))

@bp.route("/professor/reset-password/<int:id>", methods=["POST"])
@login_required
@admin_required
def reset_professor_password(id):
    form = ResetPasswordForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.professores"))
    professor = db.get_or_404(User, id)
    if professor.role != "professor":
        flash("Usuario selecionado nao e professor.", "warning")
        return redirect(url_for("main.professores"))
    default_password = "123456"
    professor.set_password(default_password)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel resetar a senha do professor.", "danger")
        return redirect(url_for("main.professores"))
    flash(
        f"Senha redefinida de {professor.username}: {default_password}.",
        "warning",
    )
    return redirect(url_for("main.professores"))

# CRUD Alunos

@bp.route("/alunos")
@login_required
@admin_required
def alunos():
    alunos = (
        Aluno.query.options(joinedload(Aluno.curso))
        .filter(Aluno.ativo.is_(True))
        .order_by(Aluno.nome.asc())
        .all()
    )
    delete_form = DeleteForm()
    return render_template("alunos.html", alunos=alunos, delete_form=delete_form)

@bp.route("/aluno/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_aluno():
    form = AlunoForm()
    cursos = _load_aluno_course_choices(form)
    if form.validate_on_submit():
        if not cursos:
            flash("Cadastre ao menos um curso antes de cadastrar alunos.", "warning")
            return redirect(url_for("main.cursos"))
        nome = normalize_text(form.nome.data)
        matricula = normalize_text(form.matricula.data)
        curso_id = form.curso_id.data
        if not any(curso.id == curso_id for curso in cursos):
            flash("Curso invalido.", "warning")
            return render_template("aluno_form.html", form=form, title="Novo Aluno")
        existing_aluno = Aluno.query.filter(func.lower(Aluno.matricula) == matricula.lower()).first()
        if existing_aluno and existing_aluno.ativo:
            flash("Ja existe aluno com esta matricula.", "warning")
            return render_template("aluno_form.html", form=form, title="Novo Aluno")
        if existing_aluno and not existing_aluno.ativo:
            existing_aluno.nome = nome
            existing_aluno.curso_id = curso_id
            existing_aluno.ativo = True
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Nao foi possivel reativar o aluno.", "danger")
                return render_template("aluno_form.html", form=form, title="Novo Aluno")
            flash("Aluno reativado com sucesso.", "success")
            return redirect(url_for("main.alunos"))
        aluno = Aluno(nome=nome, matricula=matricula, curso_id=curso_id)
        db.session.add(aluno)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel cadastrar o aluno.", "danger")
            return render_template("aluno_form.html", form=form, title="Novo Aluno")
        flash("Aluno cadastrado com sucesso.", "success")
        return redirect(url_for("main.alunos"))
    return render_template("aluno_form.html", form=form, title="Novo Aluno")

@bp.route("/aluno/edit/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_aluno(id):
    aluno = db.get_or_404(Aluno, id)
    form = AlunoForm()
    cursos = _load_aluno_course_choices(form)
    if form.validate_on_submit():
        if not cursos:
            flash("Cadastre ao menos um curso antes de editar alunos.", "warning")
            return redirect(url_for("main.cursos"))
        nome = normalize_text(form.nome.data)
        matricula = normalize_text(form.matricula.data)
        curso_id = form.curso_id.data
        if not any(curso.id == curso_id for curso in cursos):
            flash("Curso invalido.", "warning")
            return render_template("aluno_form.html", form=form, title="Editar Aluno")
        if aluno_matricula_exists(matricula, exclude_aluno_id=aluno.id):
            flash("Ja existe aluno com esta matricula.", "warning")
            return render_template("aluno_form.html", form=form, title="Editar Aluno")
        aluno.nome = nome
        aluno.matricula = matricula
        aluno.curso_id = curso_id
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel editar o aluno.", "danger")
            return render_template("aluno_form.html", form=form, title="Editar Aluno")
        flash("Aluno editado com sucesso.", "success")
        return redirect(url_for("main.alunos"))
    if request.method == "GET":
        form.nome.data = aluno.nome
        form.matricula.data = aluno.matricula
        form.curso_id.data = aluno.curso_id
    return render_template("aluno_form.html", form=form, title="Editar Aluno")

@bp.route("/aluno/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_aluno(id):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.alunos"))
    aluno = db.get_or_404(Aluno, id)
    if not aluno.ativo:
        flash("Aluno ja esta inativo.", "warning")
        return redirect(url_for("main.alunos"))
    related_matriculas = Matricula.query.filter_by(aluno_id=aluno.id).count()
    if related_matriculas > 0:
        flash("Nao e possivel inativar aluno com turmas alocadas.", "warning")
        return redirect(url_for("main.alunos"))
    aluno.ativo = False
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel inativar o aluno.", "danger")
        return redirect(url_for("main.alunos"))
    flash("Aluno inativado com sucesso.", "success")
    return redirect(url_for("main.alunos"))

# Alocacao de alunos em turmas


def _try_create_matricula(aluno_id, turma_id):
    turma = Turma.query.filter_by(id=turma_id).first()
    if turma is None:
        return False, "Turma inexistente.", "warning"
    aluno = Aluno.query.filter_by(id=aluno_id, ativo=True).first()
    if aluno is None:
        return False, "Aluno inativo ou inexistente.", "warning"
    if aluno.curso_id != turma.curso_id:
        return (
            False,
            "Nao foi possivel alocar: o aluno pertence a outro curso.",
            "warning",
        )
    if aluno_turma_exists(aluno_id, turma_id):
        return False, "Este aluno ja esta alocado nesta turma.", "warning"
    turma_same_semestre = aluno_turma_same_semestre(aluno_id, turma_id)
    if turma_same_semestre is not None:
        return (
            False,
            (
                "Este aluno ja pertence a outra turma no mesmo semestre letivo "
                f"({turma_same_semestre.semestre_letivo} - {turma_same_semestre.codigo})."
            ),
            "warning",
        )
    if turma_capacity_reached(turma_id):
        return False, "Nao foi possivel alocar: capacidade prevista da turma foi atingida.", "warning"
    if aluno_has_schedule_conflict(aluno_id, turma_id):
        return False, "Nao foi possivel alocar: conflito de horario para este aluno.", "warning"

    matricula = Matricula(aluno_id=aluno_id, turma_id=turma_id)
    db.session.add(matricula)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return False, "Nao foi possivel criar a alocacao do aluno.", "danger"

    return True, "Aluno alocado com sucesso.", "success"


@bp.route("/turma/<int:id>/alunos", methods=["GET", "POST"])
@login_required
@admin_required
def turma_alunos(id):
    turma = (
        Turma.query.options(joinedload(Turma.curso))
        .filter(Turma.id == id)
        .first_or_404()
    )
    form = TurmaMatriculaForm()

    matriculas = (
        Matricula.query.options(joinedload(Matricula.aluno))
        .join(Matricula.aluno)
        .filter(Matricula.turma_id == turma.id)
        .order_by(Aluno.nome.asc())
        .all()
    )
    matriculados_ids = {item.aluno_id for item in matriculas}
    alunos_bloqueados_semestre = {
        aluno_id
        for (aluno_id,) in db.session.query(Matricula.aluno_id)
        .join(Turma, Turma.id == Matricula.turma_id)
        .filter(
            Turma.semestre_letivo == turma.semestre_letivo,
            Matricula.turma_id != turma.id,
        )
        .all()
    }
    alunos_disponiveis = (
        Aluno.query.filter(
            Aluno.ativo.is_(True),
            Aluno.curso_id == turma.curso_id,
        )
        .order_by(Aluno.nome.asc())
        .all()
    )
    form.aluno_id.choices = [
        (aluno.id, f"{aluno.nome} ({aluno.matricula})")
        for aluno in alunos_disponiveis
        if aluno.id not in matriculados_ids and aluno.id not in alunos_bloqueados_semestre
    ]

    if form.validate_on_submit():
        if not form.aluno_id.choices:
            flash("Nao ha alunos elegiveis deste curso para matricula nesta turma neste semestre letivo.", "warning")
            return redirect(url_for("main.turma_alunos", id=turma.id))

        allowed_ids = {aluno_id for aluno_id, _ in form.aluno_id.choices}
        if form.aluno_id.data not in allowed_ids:
            flash("Aluno invalido para esta turma.", "warning")
            return redirect(url_for("main.turma_alunos", id=turma.id))

        success, message, category = _try_create_matricula(form.aluno_id.data, turma.id)
        flash(message, category)
        return redirect(url_for("main.turma_alunos", id=turma.id))

    delete_form = DeleteForm()
    return render_template(
        "turma_alunos.html",
        turma=turma,
        form=form,
        delete_form=delete_form,
        matriculas=matriculas,
        vagas_restantes=(
            max((turma.quantidade_alunos or 0) - len(matriculas), 0)
            if turma.quantidade_alunos is not None
            else None
        ),
    )


@bp.route("/turma/<int:turma_id>/matricula/<int:matricula_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_turma_matricula(turma_id, matricula_id):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.turma_alunos", id=turma_id))

    turma = db.get_or_404(Turma, turma_id)
    matricula = db.get_or_404(Matricula, matricula_id)
    if matricula.turma_id != turma.id:
        flash("Matricula nao pertence a turma informada.", "warning")
        return redirect(url_for("main.turma_alunos", id=turma.id))

    db.session.delete(matricula)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel remover a alocacao.", "danger")
        return redirect(url_for("main.turma_alunos", id=turma.id))
    flash("Alocacao removida com sucesso.", "success")
    return redirect(url_for("main.turma_alunos", id=turma.id))


@bp.route("/matriculas")
@login_required
@admin_required
def matriculas():
    matriculas = (
        Matricula.query.options(
            joinedload(Matricula.aluno),
            joinedload(Matricula.turma).joinedload(Turma.curso),
        )
        .join(Matricula.aluno)
        .order_by(Aluno.nome.asc())
        .all()
    )
    delete_form = DeleteForm()
    return render_template("matriculas.html", matriculas=matriculas, delete_form=delete_form)

@bp.route("/matricula/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_matricula():
    form = MatriculaForm()
    form.aluno_id.choices = [
        (a.id, f"{a.nome} ({a.matricula})")
        for a in Aluno.query.filter(Aluno.ativo.is_(True)).order_by(Aluno.nome.asc()).all()
    ]
    turmas = (
        Turma.query.options(joinedload(Turma.curso))
        .order_by(Turma.semestre_letivo.desc(), Turma.curso_id.asc(), Turma.codigo.asc())
        .all()
    )
    form.turma_id.choices = [
        (turma.id, f"{turma.curso.nome if turma.curso else 'Curso'} | {turma.codigo} | {turma.semestre_letivo} | {turma.periodo}o periodo")
        for turma in turmas
    ]
    if form.validate_on_submit():
        if not form.aluno_id.choices or not form.turma_id.choices:
            flash("Cadastre ao menos um aluno e uma turma antes de alocar.", "warning")
            return redirect(url_for("main.matriculas"))
        success, message, category = _try_create_matricula(form.aluno_id.data, form.turma_id.data)
        if not success:
            flash(message, category)
            return render_template("matricula_form.html", title="Nova Alocacao de Aluno", form=form)
        flash(message, category)
        return redirect(url_for("main.matriculas"))
    return render_template("matricula_form.html", title="Nova Alocacao de Aluno", form=form)

@bp.route("/matricula/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_matricula(id):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.matriculas"))
    matricula = db.get_or_404(Matricula, id)
    db.session.delete(matricula)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel remover a alocacao.", "danger")
        return redirect(url_for("main.matriculas"))
    flash("Alocacao removida com sucesso.", "success")
    return redirect(url_for("main.matriculas"))

@bp.route("/timetable/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_timetable():
    form = TimetableForm()
    salas = Sala.query.order_by(Sala.nome.asc()).all()
    professores = User.query.filter_by(role="professor").order_by(User.username.asc()).all()
    disciplinas = Disciplina.query.order_by(Disciplina.nome.asc()).all()
    turmas = (
        Turma.query.options(joinedload(Turma.curso))
        .order_by(Turma.semestre_letivo.desc(), Turma.curso_id.asc(), Turma.codigo.asc())
        .all()
    )

    form.sala_id.choices = [(sala.id, sala.nome) for sala in salas]
    form.professor_id.choices = [(professor.id, professor.username) for professor in professores]
    form.disciplina_id.choices = [(disciplina.id, disciplina.nome) for disciplina in disciplinas]
    form.turma_id.choices = [
        (
            turma.id,
            (
                f"{turma.curso.nome if turma.curso else 'Curso'} | {turma.codigo} | "
                f"{turma.semestre_letivo} | {turma.periodo}o periodo | {get_turno_label(turma.turno)}"
            ),
        )
        for turma in turmas
    ]

    allocation_payload = _build_allocation_payload(
        salas=salas,
        professores=professores,
        disciplinas=disciplinas,
        turmas=turmas,
    )
    workload_index = _build_professor_workload_index()
    professor_by_id = {professor.id: professor for professor in professores}
    sala_by_id = {sala.id: sala for sala in salas}
    turma_by_id = {turma.id: turma for turma in turmas}

    if form.validate_on_submit():
        if not form.sala_id.choices or not form.professor_id.choices or not form.disciplina_id.choices or not form.turma_id.choices:
            flash(
                "Cadastre ao menos uma sala, um professor, uma disciplina e uma turma antes de criar alocacoes.",
                "warning",
            )
            return redirect(url_for("main.admin_dashboard"))

        selected_turma_id = _normalize_turma_selection(form.turma_id.data)
        selected_turma = turma_by_id.get(selected_turma_id)
        if selected_turma is None:
            flash("Turma invalida.", "warning")
            return redirect(url_for("main.new_timetable"))

        allowed_disciplina_ids = set(allowed_disciplina_ids_for_turma(selected_turma))
        if not allowed_disciplina_ids:
            flash("A turma selecionada nao possui disciplinas configuradas na grade para este periodo.", "warning")
            return redirect(url_for("main.new_timetable"))
        if form.disciplina_id.data not in allowed_disciplina_ids:
            flash("Disciplina nao pertence a grade curricular da turma/periodo selecionado.", "danger")
            return redirect(url_for("main.new_timetable"))
        duplicate_disciplina = Timetable.query.filter_by(
            turma_id=selected_turma_id,
            disciplina_id=form.disciplina_id.data,
        ).first()
        if duplicate_disciplina is not None:
            flash("Esta disciplina ja foi alocada no quadro da turma.", "warning")
            return redirect(url_for("main.new_timetable"))
        if form.horario_id.data not in set(allowed_slot_ids_for_turno(selected_turma.turno)):
            flash(
                f"Horario invalido para o turno da turma ({get_turno_label(selected_turma.turno)}).",
                "warning",
            )
            return redirect(url_for("main.new_timetable"))

        slot_start, slot_end = get_shift_bounds(form.horario_id.data)
        if slot_start is None or slot_end is None:
            flash("Horario invalido. Selecione um turno de 1h30 valido.", "warning")
            return redirect(url_for("main.new_timetable"))

        slot_key = _build_slot_key(form.dia.data, form.horario_id.data)
        slot_availability = allocation_payload["availability_by_key"].get(slot_key, {})
        available_room_ids = set(slot_availability.get("sala_ids", []))
        available_professor_ids = set(slot_availability.get("professor_ids", []))
        available_turma_ids = set(slot_availability.get("turma_ids", []))

        if form.sala_id.data not in available_room_ids:
            flash("A sala selecionada nao esta disponivel para este dia e turno.", "danger")
            return redirect(url_for("main.new_timetable"))
        if form.professor_id.data not in available_professor_ids:
            flash("O professor selecionado nao esta disponivel para este dia e turno.", "danger")
            return redirect(url_for("main.new_timetable"))
        if selected_turma_id not in available_turma_ids:
            flash("A turma selecionada nao esta disponivel para este dia e turno.", "danger")
            return redirect(url_for("main.new_timetable"))

        selected_professor = professor_by_id.get(form.professor_id.data)
        if not professor_can_teach_disciplina(selected_professor, form.disciplina_id.data):
            flash("Professor sem aptidao para a disciplina selecionada.", "danger")
            return redirect(url_for("main.new_timetable"))
        workload_probe = Timetable(
            dia=form.dia.data,
            hora_inicio=slot_start,
            hora_fim=slot_end,
            turma_id=selected_turma_id,
        )
        workload_ok, workload_message = _ensure_professor_workload_available(
            professor=selected_professor,
            timetable=workload_probe,
            workload_index=workload_index,
        )
        if not workload_ok:
            flash(workload_message, "danger")
            return redirect(url_for("main.new_timetable"))

        selected_sala = sala_by_id.get(form.sala_id.data)
        alunos_na_turma = Matricula.query.filter_by(turma_id=selected_turma_id).count()
        if selected_sala and alunos_na_turma > selected_sala.capacidade:
            flash("A sala selecionada nao comporta a quantidade de alunos alocados na turma.", "danger")
            return redirect(url_for("main.new_timetable"))

        conflict_message = find_timetable_conflict_with_turma(
            dia=form.dia.data,
            hora_inicio=slot_start,
            hora_fim=slot_end,
            sala_id=form.sala_id.data,
            professor_id=form.professor_id.data,
            turma_id=selected_turma_id,
        )
        if conflict_message:
            flash(conflict_message, "danger")
            return redirect(url_for("main.new_timetable"))

        timetable = Timetable(
            dia=form.dia.data,
            hora_inicio=slot_start,
            hora_fim=slot_end,
            sala_id=form.sala_id.data,
            professor_id=form.professor_id.data,
            disciplina_id=form.disciplina_id.data,
            turma_id=selected_turma_id,
        )
        db.session.add(timetable)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel criar a alocacao.", "danger")
            return redirect(url_for("main.new_timetable"))
        flash("Alocacao criada com sucesso.", "success")
        return redirect(url_for("main.admin_dashboard"))
    return render_template(
        "timetable_form.html",
        form=form,
        title="Nova Alocacao",
        allocation_payload=allocation_payload,
    )

@bp.route("/timetable/edit/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_timetable(id):
    timetable = db.get_or_404(Timetable, id)
    form = TimetableForm()
    salas = Sala.query.order_by(Sala.nome.asc()).all()
    professores = User.query.filter_by(role="professor").order_by(User.username.asc()).all()
    disciplinas = Disciplina.query.order_by(Disciplina.nome.asc()).all()
    turmas = (
        Turma.query.options(joinedload(Turma.curso))
        .order_by(Turma.semestre_letivo.desc(), Turma.curso_id.asc(), Turma.codigo.asc())
        .all()
    )

    form.sala_id.choices = [(sala.id, sala.nome) for sala in salas]
    form.professor_id.choices = [(professor.id, professor.username) for professor in professores]
    form.disciplina_id.choices = [(disciplina.id, disciplina.nome) for disciplina in disciplinas]
    form.turma_id.choices = [
        (
            turma.id,
            (
                f"{turma.curso.nome if turma.curso else 'Curso'} | {turma.codigo} | "
                f"{turma.semestre_letivo} | {turma.periodo}o periodo | {get_turno_label(turma.turno)}"
            ),
        )
        for turma in turmas
    ]

    allocation_payload = _build_allocation_payload(
        salas=salas,
        professores=professores,
        disciplinas=disciplinas,
        turmas=turmas,
        exclude_timetable_id=id,
    )
    workload_index = _build_professor_workload_index(exclude_timetable_id=id)
    professor_by_id = {professor.id: professor for professor in professores}
    sala_by_id = {sala.id: sala for sala in salas}
    turma_by_id = {turma.id: turma for turma in turmas}

    if form.validate_on_submit():
        selected_turma_id = _normalize_turma_selection(form.turma_id.data)
        selected_turma = turma_by_id.get(selected_turma_id)
        if selected_turma is None:
            flash("Turma invalida.", "warning")
            return redirect(url_for("main.edit_timetable", id=id))

        allowed_disciplina_ids = set(allowed_disciplina_ids_for_turma(selected_turma))
        if not allowed_disciplina_ids:
            flash("A turma selecionada nao possui disciplinas configuradas na grade para este periodo.", "warning")
            return redirect(url_for("main.edit_timetable", id=id))
        if form.disciplina_id.data not in allowed_disciplina_ids:
            flash("Disciplina nao pertence a grade curricular da turma/periodo selecionado.", "danger")
            return redirect(url_for("main.edit_timetable", id=id))
        duplicate_disciplina = Timetable.query.filter(
            Timetable.turma_id == selected_turma_id,
            Timetable.disciplina_id == form.disciplina_id.data,
            Timetable.id != id,
        ).first()
        if duplicate_disciplina is not None:
            flash("Esta disciplina ja foi alocada no quadro da turma.", "warning")
            return redirect(url_for("main.edit_timetable", id=id))
        if form.horario_id.data not in set(allowed_slot_ids_for_turno(selected_turma.turno)):
            flash(
                f"Horario invalido para o turno da turma ({get_turno_label(selected_turma.turno)}).",
                "warning",
            )
            return redirect(url_for("main.edit_timetable", id=id))

        slot_start, slot_end = get_shift_bounds(form.horario_id.data)
        if slot_start is None or slot_end is None:
            flash("Horario invalido. Selecione um turno de 1h30 valido.", "warning")
            return redirect(url_for("main.edit_timetable", id=id))

        slot_key = _build_slot_key(form.dia.data, form.horario_id.data)
        slot_availability = allocation_payload["availability_by_key"].get(slot_key, {})
        available_room_ids = set(slot_availability.get("sala_ids", []))
        available_professor_ids = set(slot_availability.get("professor_ids", []))
        available_turma_ids = set(slot_availability.get("turma_ids", []))

        if form.sala_id.data not in available_room_ids:
            flash("A sala selecionada nao esta disponivel para este dia e turno.", "danger")
            return redirect(url_for("main.edit_timetable", id=id))
        if form.professor_id.data not in available_professor_ids:
            flash("O professor selecionado nao esta disponivel para este dia e turno.", "danger")
            return redirect(url_for("main.edit_timetable", id=id))
        if selected_turma_id not in available_turma_ids:
            flash("A turma selecionada nao esta disponivel para este dia e turno.", "danger")
            return redirect(url_for("main.edit_timetable", id=id))

        selected_professor = professor_by_id.get(form.professor_id.data)
        if not professor_can_teach_disciplina(selected_professor, form.disciplina_id.data):
            flash("Professor sem aptidao para a disciplina selecionada.", "danger")
            return redirect(url_for("main.edit_timetable", id=id))
        workload_probe = Timetable(
            dia=form.dia.data,
            hora_inicio=slot_start,
            hora_fim=slot_end,
            turma_id=selected_turma_id,
        )
        workload_ok, workload_message = _ensure_professor_workload_available(
            professor=selected_professor,
            timetable=workload_probe,
            workload_index=workload_index,
        )
        if not workload_ok:
            flash(workload_message, "danger")
            return redirect(url_for("main.edit_timetable", id=id))

        selected_sala = sala_by_id.get(form.sala_id.data)
        alunos_na_turma = Matricula.query.filter_by(turma_id=selected_turma_id).count()
        if selected_sala and alunos_na_turma > selected_sala.capacidade:
            flash("A sala selecionada nao comporta a quantidade de alunos alocados na turma.", "danger")
            return redirect(url_for("main.edit_timetable", id=id))

        conflict_message = find_timetable_conflict_with_turma(
            dia=form.dia.data,
            hora_inicio=slot_start,
            hora_fim=slot_end,
            sala_id=form.sala_id.data,
            professor_id=form.professor_id.data,
            turma_id=selected_turma_id,
            exclude_id=id,
        )
        if conflict_message:
            flash(conflict_message, "danger")
            return redirect(url_for("main.edit_timetable", id=id))
        timetable.dia = form.dia.data
        timetable.hora_inicio = slot_start
        timetable.hora_fim = slot_end
        timetable.sala_id = form.sala_id.data
        timetable.professor_id = form.professor_id.data
        timetable.disciplina_id = form.disciplina_id.data
        timetable.turma_id = selected_turma_id
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel editar a alocacao.", "danger")
            return redirect(url_for("main.edit_timetable", id=id))
        flash("Alocacao editada com sucesso.", "success")
        return redirect(url_for("main.admin_dashboard"))
    if request.method == "GET":
        form.dia.data = timetable.dia
        form.horario_id.data = resolve_shift_slot_id(timetable.hora_inicio, timetable.hora_fim) or NIGHT_SHIFT_ID
        form.sala_id.data = timetable.sala_id
        form.professor_id.data = timetable.professor_id
        form.disciplina_id.data = timetable.disciplina_id
        form.turma_id.data = timetable.turma_id
    return render_template(
        "timetable_form.html",
        form=form,
        title="Editar Alocacao",
        allocation_payload=allocation_payload,
    )

@bp.route("/timetable/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_timetable(id):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.admin_dashboard"))
    timetable = db.get_or_404(Timetable, id)
    related_presencas = Presenca.query.filter_by(timetable_id=timetable.id).count()
    if related_presencas > 0:
        flash("Nao e possivel deletar a alocacao com chamadas registradas.", "warning")
        return redirect(url_for("main.admin_dashboard"))
    db.session.delete(timetable)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel deletar a alocacao.", "danger")
        return redirect(url_for("main.admin_dashboard"))
    flash("Alocacao deletada com sucesso.", "success")
    return redirect(url_for("main.admin_dashboard"))
