import random
import string
import unicodedata
from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.forms import get_shift_label, resolve_shift_slot_id
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
    User,
)


DAY_VARIANTS_BY_NORMALIZED = {
    "segunda": {"Segunda"},
    "terca": {"Terca", "Terça"},
    "quarta": {"Quarta"},
    "quinta": {"Quinta"},
    "sexta": {"Sexta"},
    "sabado": {"Sabado", "Sábado"},
    "domingo": {"Domingo"},
}
DAY_CANONICAL_BY_NORMALIZED = {
    "segunda": "Segunda",
    "terca": "Terca",
    "quarta": "Quarta",
    "quinta": "Quinta",
    "sexta": "Sexta",
    "sabado": "Sabado",
    "domingo": "Domingo",
}


def times_overlap(start1, end1, start2, end2):
    """Verifica se dois intervalos de tempo se sobrepoem."""
    return max(start1, start2) < min(end1, end2)


def admin_required_redirect():
    if getattr(current_user, "is_authenticated", False) and current_user.is_admin():
        return None
    flash("Acesso restrito ao administrador.", "danger")
    return redirect(url_for("main.index"))


def professor_required_redirect():
    if getattr(current_user, "is_authenticated", False) and current_user.role == "professor":
        return None
    flash("Acesso restrito aos professores.", "danger")
    return redirect(url_for("main.index"))


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        guard = admin_required_redirect()
        if guard:
            return guard
        return view_func(*args, **kwargs)

    return wrapper


def professor_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        guard = professor_required_redirect()
        if guard:
            return guard
        return view_func(*args, **kwargs)

    return wrapper


def normalize_text(value):
    return (value or "").strip()


def normalize_day_label(value):
    normalized = normalize_text(value).lower()
    normalized = unicodedata.normalize("NFD", normalized)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def canonical_day_label(value):
    normalized = normalize_day_label(value)
    return DAY_CANONICAL_BY_NORMALIZED.get(normalized, normalize_text(value))


def day_label_variants(value):
    normalized = normalize_day_label(value)
    variants = DAY_VARIANTS_BY_NORMALIZED.get(normalized)
    if variants:
        return list(variants)
    return [normalize_text(value)]


def synthetic_professor_email(username):
    return f"{normalize_text(username).lower()}@login.local"


def generate_disciplina_code():
    while True:
        codigo = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Disciplina.query.filter_by(codigo=codigo).first():
            return codigo


def build_timetable_label(timetable):
    disciplina_nome = timetable.disciplina.nome if timetable.disciplina else "Disciplina removida"
    professor_nome = timetable.professor.username if timetable.professor else "Professor removido"
    sala_nome = timetable.sala.nome if timetable.sala else "Sala removida"
    turma_nome = timetable.turma.nome_exibicao if timetable.turma else "Sem turma"
    hora_inicio = timetable.hora_inicio.strftime("%H:%M")
    hora_fim = timetable.hora_fim.strftime("%H:%M")
    shift_id = resolve_shift_slot_id(timetable.hora_inicio, timetable.hora_fim)
    turno_label = get_shift_label(shift_id)
    return (
        f"{timetable.dia} | {hora_inicio}-{hora_fim} | {turno_label} | "
        f"{turma_nome} | {disciplina_nome} | {professor_nome} | {sala_nome}"
    )


def load_timetable_options():
    timetables = (
        Timetable.query.options(
            joinedload(Timetable.sala),
            joinedload(Timetable.professor),
            joinedload(Timetable.disciplina),
            joinedload(Timetable.turma),
        )
        .order_by(Timetable.dia.asc(), Timetable.hora_inicio.asc())
        .all()
    )
    return [(t.id, build_timetable_label(t)) for t in timetables]


def find_timetable_conflict(dia, hora_inicio, hora_fim, sala_id, professor_id, exclude_id=None):
    overlapping_query = Timetable.query.filter(
        Timetable.dia.in_(day_label_variants(dia)),
        Timetable.hora_inicio < hora_fim,
        Timetable.hora_fim > hora_inicio,
    )

    if exclude_id is not None:
        overlapping_query = overlapping_query.filter(Timetable.id != exclude_id)

    room_conflict = overlapping_query.filter(Timetable.sala_id == sala_id).first()
    if room_conflict:
        return "Conflito: a sala ja possui alocacao em horario sobreposto."

    professor_conflict = overlapping_query.filter(Timetable.professor_id == professor_id).first()
    if professor_conflict:
        return "Conflito: professor ja alocado em horario sobreposto."

    return None


def find_timetable_conflict_with_turma(dia, hora_inicio, hora_fim, sala_id, professor_id, turma_id=None, exclude_id=None):
    conflict_message = find_timetable_conflict(
        dia=dia,
        hora_inicio=hora_inicio,
        hora_fim=hora_fim,
        sala_id=sala_id,
        professor_id=professor_id,
        exclude_id=exclude_id,
    )
    if conflict_message:
        return conflict_message

    if turma_id is None:
        return None

    overlapping_query = Timetable.query.filter(
        Timetable.dia.in_(day_label_variants(dia)),
        Timetable.hora_inicio < hora_fim,
        Timetable.hora_fim > hora_inicio,
        Timetable.turma_id == turma_id,
    )

    if exclude_id is not None:
        overlapping_query = overlapping_query.filter(Timetable.id != exclude_id)

    turma_conflict = overlapping_query.first()
    if turma_conflict:
        return "Conflito: a turma ja possui alocacao em horario sobreposto."

    return None


def professor_can_teach_disciplina(professor, disciplina_id):
    if professor is None:
        return False
    return any(disciplina.id == disciplina_id for disciplina in professor.disciplinas_aptas)


def username_exists(username, exclude_user_id=None):
    query = User.query
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)

    existing_username = query.filter(func.lower(User.username) == username.lower()).first()
    if existing_username:
        return "Ja existe usuario com este nome."

    return None


def sala_name_exists(nome, exclude_sala_id=None):
    query = Sala.query
    if exclude_sala_id is not None:
        query = query.filter(Sala.id != exclude_sala_id)

    existing_sala = query.filter(func.lower(Sala.nome) == nome.lower()).first()
    return existing_sala is not None


def disciplina_name_exists(nome, exclude_disciplina_id=None):
    query = Disciplina.query
    if exclude_disciplina_id is not None:
        query = query.filter(Disciplina.id != exclude_disciplina_id)

    existing_disciplina = query.filter(func.lower(Disciplina.nome) == nome.lower()).first()
    return existing_disciplina is not None


def turma_nome_semestre_exists(nome, semestre, exclude_turma_id=None):
    # Backward compatibility helper (no longer used in new model).
    query = Turma.query
    if exclude_turma_id is not None:
        query = query.filter(Turma.id != exclude_turma_id)
    return (
        query.filter(
            func.lower(Turma.codigo) == nome.lower(),
            func.lower(Turma.semestre_letivo) == semestre.lower(),
        ).first()
        is not None
    )


def turma_codigo_semestre_exists(curso_id, codigo, semestre_letivo, exclude_turma_id=None):
    query = Turma.query.filter(Turma.curso_id == curso_id)
    if exclude_turma_id is not None:
        query = query.filter(Turma.id != exclude_turma_id)
    return (
        query.filter(
            func.lower(Turma.codigo) == codigo.lower(),
            func.lower(Turma.semestre_letivo) == semestre_letivo.lower(),
        ).first()
        is not None
    )


def curso_name_exists(nome, exclude_curso_id=None):
    query = Curso.query
    if exclude_curso_id is not None:
        query = query.filter(Curso.id != exclude_curso_id)
    return query.filter(func.lower(Curso.nome) == nome.lower()).first() is not None


def curso_codigo_exists(codigo, exclude_curso_id=None):
    query = Curso.query
    if exclude_curso_id is not None:
        query = query.filter(Curso.id != exclude_curso_id)
    return query.filter(func.lower(Curso.codigo) == codigo.lower()).first() is not None


def grade_nome_exists(curso_id, nome, exclude_grade_id=None):
    query = GradeCurricular.query.filter(GradeCurricular.curso_id == curso_id)
    if exclude_grade_id is not None:
        query = query.filter(GradeCurricular.id != exclude_grade_id)
    return query.filter(func.lower(GradeCurricular.nome) == nome.lower()).first() is not None


def grade_item_exists(grade_id, disciplina_id, exclude_item_id=None):
    query = GradeCurricularItem.query.filter(
        GradeCurricularItem.grade_id == grade_id,
        GradeCurricularItem.disciplina_id == disciplina_id,
    )
    if exclude_item_id is not None:
        query = query.filter(GradeCurricularItem.id != exclude_item_id)
    return query.first() is not None


def active_grade_for_curso(curso_id):
    return (
        GradeCurricular.query.filter_by(curso_id=curso_id, ativa=True)
        .order_by(GradeCurricular.id.desc())
        .first()
    )


def allowed_disciplina_ids_for_turma(turma):
    if turma is None:
        return []
    grade = active_grade_for_curso(turma.curso_id)
    if grade is None:
        return []
    rows = (
        GradeCurricularItem.query.with_entities(GradeCurricularItem.disciplina_id)
        .filter(
            GradeCurricularItem.grade_id == grade.id,
            GradeCurricularItem.periodo == turma.periodo,
        )
        .all()
    )
    return sorted({row.disciplina_id for row in rows})


def aluno_matricula_exists(matricula, exclude_aluno_id=None):
    query = Aluno.query
    if exclude_aluno_id is not None:
        query = query.filter(Aluno.id != exclude_aluno_id)

    existing_aluno = query.filter(func.lower(Aluno.matricula) == matricula.lower()).first()
    return existing_aluno is not None


def aluno_turma_exists(aluno_id, turma_id):
    return Matricula.query.filter_by(aluno_id=aluno_id, turma_id=turma_id).first() is not None


def turma_capacity_reached(turma_id):
    turma = Turma.query.filter_by(id=turma_id).first()
    if turma is None or turma.quantidade_alunos is None:
        return False

    current_students = Matricula.query.filter_by(turma_id=turma_id).count()
    return current_students >= turma.quantidade_alunos


def timetable_capacity_reached(timetable_id):
    timetable = Timetable.query.options(joinedload(Timetable.sala)).filter(Timetable.id == timetable_id).first()
    if timetable is None or timetable.sala is None or timetable.turma_id is None:
        return False

    current_students = Matricula.query.filter_by(turma_id=timetable.turma_id).count()
    return current_students >= timetable.sala.capacidade


def aluno_has_schedule_conflict(aluno_id, turma_id):
    target_timetables = Timetable.query.filter_by(turma_id=turma_id).all()
    if not target_timetables:
        return False

    existing_turmas = Matricula.query.filter(
        Matricula.aluno_id == aluno_id,
        Matricula.turma_id != turma_id,
    ).all()
    existing_turma_ids = [row.turma_id for row in existing_turmas]
    if not existing_turma_ids:
        return False

    existing_timetables = Timetable.query.filter(Timetable.turma_id.in_(existing_turma_ids)).all()
    for target in target_timetables:
        for existing in existing_timetables:
            if existing.dia not in day_label_variants(target.dia):
                continue
            if existing.hora_inicio < target.hora_fim and existing.hora_fim > target.hora_inicio:
                return True

    return False
