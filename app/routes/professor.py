from datetime import date, datetime, timedelta
import unicodedata

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app import db
from app.forms import AttendanceForm
from app.models import Matricula, Presenca, Timetable

from . import bp
from .helpers import normalize_text, professor_required_redirect


DAY_TO_WEEKDAY = {
    "segunda": 0,
    "terca": 1,
    "quarta": 2,
    "quinta": 3,
    "sexta": 4,
    "sabado": 5,
    "domingo": 6,
}
WEEKDAY_TO_LABEL = {
    0: "Segunda",
    1: "Terca",
    2: "Quarta",
    3: "Quinta",
    4: "Sexta",
    5: "Sabado",
    6: "Domingo",
}


def normalize_day_label(value: str) -> str:
    normalized = normalize_text(value).lower()
    normalized = unicodedata.normalize("NFD", normalized)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def timetable_weekday(timetable_day: str) -> int | None:
    return DAY_TO_WEEKDAY.get(normalize_day_label(timetable_day))


def suggested_attendance_date(timetable_day: str) -> date:
    class_weekday = timetable_weekday(timetable_day)
    if class_weekday is None:
        return date.today()

    today = date.today()
    days_ago = (today.weekday() - class_weekday) % 7
    return today - timedelta(days=days_ago)


def validate_attendance_date(selected_date: date, timetable_day: str) -> str | None:
    if selected_date > date.today():
        return "Nao e permitido registrar chamada em data futura."

    class_weekday = timetable_weekday(timetable_day)
    if class_weekday is None:
        return None

    if selected_date.weekday() != class_weekday:
        expected_label = WEEKDAY_TO_LABEL.get(class_weekday, timetable_day)
        return f"A data da chamada deve corresponder ao dia da turma ({expected_label})."

    return None


def build_attendance_history(timetable_id: int) -> list[dict[str, object]]:
    rows = (
        db.session.query(
            Presenca.data.label("data"),
            func.sum(case((Presenca.presente.is_(True), 1), else_=0)).label("presentes"),
            func.count(Presenca.id).label("total"),
        )
        .filter(Presenca.timetable_id == timetable_id)
        .group_by(Presenca.data)
        .order_by(Presenca.data.desc())
        .limit(12)
        .all()
    )

    history: list[dict[str, object]] = []
    for row in rows:
        total = int(row.total or 0)
        presentes = int(row.presentes or 0)
        faltas = max(total - presentes, 0)
        percentual = round((presentes / total) * 100, 1) if total else 0.0
        history.append(
            {
                "data": row.data,
                "presentes": presentes,
                "faltas": faltas,
                "percentual": percentual,
            }
        )

    return history


@bp.route("/professor")
@login_required
def professor_dashboard():
    guard = professor_required_redirect()
    if guard:
        return guard

    timetables = (
        Timetable.query.options(
            joinedload(Timetable.sala),
            joinedload(Timetable.disciplina),
            joinedload(Timetable.matriculas).joinedload(Matricula.aluno),
        )
        .filter(Timetable.professor_id == current_user.id)
        .order_by(Timetable.dia.asc(), Timetable.hora_inicio.asc())
        .all()
    )

    return render_template("professor_dashboard.html", timetables=timetables)


@bp.route("/professor/turma/<int:timetable_id>/chamada", methods=["GET", "POST"])
@login_required
def professor_attendance(timetable_id):
    guard = professor_required_redirect()
    if guard:
        return guard

    timetable = (
        Timetable.query.options(
            joinedload(Timetable.sala),
            joinedload(Timetable.disciplina),
            joinedload(Timetable.matriculas).joinedload(Matricula.aluno),
        )
        .filter(Timetable.id == timetable_id, Timetable.professor_id == current_user.id)
        .first()
    )

    if timetable is None:
        flash("Turma nao encontrada para este professor.", "warning")
        return redirect(url_for("main.professor_dashboard"))

    matriculas = sorted(timetable.matriculas, key=lambda item: item.aluno.nome.lower())
    if not matriculas:
        flash("Esta turma ainda nao possui alunos alocados.", "warning")
        return redirect(url_for("main.professor_dashboard"))

    form = AttendanceForm()
    recommended_date = suggested_attendance_date(timetable.dia)

    if request.method == "GET":
        date_param = normalize_text(request.args.get("data"))
        if date_param:
            try:
                form.chamada_data.data = datetime.strptime(date_param, "%Y-%m-%d").date()
            except ValueError:
                flash("Data invalida. Use o formato AAAA-MM-DD.", "warning")
                form.chamada_data.data = recommended_date

    if form.chamada_data.data is None:
        form.chamada_data.data = recommended_date

    selected_date = form.chamada_data.data

    if form.validate_on_submit():
        selected_date = form.chamada_data.data
        date_error = validate_attendance_date(selected_date, timetable.dia)

        if date_error:
            flash(date_error, "warning")
            selected_date = recommended_date
            form.chamada_data.data = selected_date
        else:
            selected_ids = set()
            for raw_id in request.form.getlist("presentes"):
                if raw_id.isdigit():
                    selected_ids.add(int(raw_id))

            allowed_ids = {matricula.aluno_id for matricula in matriculas}
            selected_ids = selected_ids.intersection(allowed_ids)

            presencas_atuais = Presenca.query.filter_by(timetable_id=timetable.id, data=selected_date).all()
            presencas_por_aluno = {presenca.aluno_id: presenca for presenca in presencas_atuais}

            for matricula in matriculas:
                presente = matricula.aluno_id in selected_ids
                presenca = presencas_por_aluno.get(matricula.aluno_id)

                if presenca is None:
                    db.session.add(
                        Presenca(
                            data=selected_date,
                            presente=presente,
                            aluno_id=matricula.aluno_id,
                            timetable_id=timetable.id,
                        )
                    )
                else:
                    presenca.presente = presente

            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Nao foi possivel salvar a chamada.", "danger")
                return redirect(url_for("main.professor_attendance", timetable_id=timetable.id))

            flash("Chamada salva com sucesso.", "success")
            return redirect(
                url_for(
                    "main.professor_attendance",
                    timetable_id=timetable.id,
                    data=selected_date.isoformat(),
                )
            )

    # Mantem coerencia tambem em navegacao via query string.
    get_date_error = validate_attendance_date(selected_date, timetable.dia)
    if request.method == "GET" and get_date_error:
        flash(get_date_error, "warning")
        selected_date = recommended_date
        form.chamada_data.data = selected_date

    presencas_dia = Presenca.query.filter_by(timetable_id=timetable.id, data=selected_date).all()
    present_ids = {presenca.aluno_id for presenca in presencas_dia if presenca.presente}

    total_alunos = len(matriculas)
    total_presentes = len(present_ids)
    total_faltas = total_alunos - total_presentes
    percentual_presenca = round((total_presentes / total_alunos) * 100, 1) if total_alunos else 0.0
    attendance_history = build_attendance_history(timetable.id)

    return render_template(
        "professor_attendance.html",
        form=form,
        timetable=timetable,
        matriculas=matriculas,
        present_ids=present_ids,
        total_alunos=total_alunos,
        total_presentes=total_presentes,
        total_faltas=total_faltas,
        percentual_presenca=percentual_presenca,
        attendance_history=attendance_history,
        selected_date=selected_date,
        expected_day_label=WEEKDAY_TO_LABEL.get(timetable_weekday(timetable.dia), timetable.dia),
    )
