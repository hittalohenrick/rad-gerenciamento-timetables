import random
import string
from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.models import Aluno, Disciplina, Matricula, Sala, Timetable, User


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
    hora_inicio = timetable.hora_inicio.strftime("%H:%M")
    hora_fim = timetable.hora_fim.strftime("%H:%M")
    return (
        f"{timetable.dia} | {hora_inicio}-{hora_fim} | "
        f"{disciplina_nome} | {professor_nome} | {sala_nome}"
    )


def load_timetable_options():
    timetables = (
        Timetable.query.options(
            joinedload(Timetable.sala),
            joinedload(Timetable.professor),
            joinedload(Timetable.disciplina),
        )
        .order_by(Timetable.dia.asc(), Timetable.hora_inicio.asc())
        .all()
    )
    return [(t.id, build_timetable_label(t)) for t in timetables]


def find_timetable_conflict(dia, hora_inicio, hora_fim, sala_id, professor_id, exclude_id=None):
    overlapping_query = Timetable.query.filter(
        Timetable.dia == dia,
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


def aluno_matricula_exists(matricula, exclude_aluno_id=None):
    query = Aluno.query
    if exclude_aluno_id is not None:
        query = query.filter(Aluno.id != exclude_aluno_id)

    existing_aluno = query.filter(func.lower(Aluno.matricula) == matricula.lower()).first()
    return existing_aluno is not None


def aluno_turma_exists(aluno_id, timetable_id):
    return Matricula.query.filter_by(aluno_id=aluno_id, timetable_id=timetable_id).first() is not None


def timetable_capacity_reached(timetable_id):
    timetable = Timetable.query.options(joinedload(Timetable.sala)).filter(Timetable.id == timetable_id).first()
    if timetable is None or timetable.sala is None:
        return False

    current_students = Matricula.query.filter_by(timetable_id=timetable_id).count()
    return current_students >= timetable.sala.capacidade


def aluno_has_schedule_conflict(aluno_id, timetable_id):
    target_timetable = Timetable.query.filter_by(id=timetable_id).first()
    if target_timetable is None:
        return False

    return (
        Matricula.query.join(Timetable, Matricula.timetable_id == Timetable.id)
        .filter(
            Matricula.aluno_id == aluno_id,
            Timetable.id != timetable_id,
            Timetable.dia == target_timetable.dia,
            Timetable.hora_inicio < target_timetable.hora_fim,
            Timetable.hora_fim > target_timetable.hora_inicio,
        )
        .first()
        is not None
    )
