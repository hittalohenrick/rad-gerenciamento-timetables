from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from app import db
from app.forms import (
    AlunoForm,
    CursoForm,
    DeleteForm,
    DisciplinaForm,
    GradeCurricularForm,
    GradeCurricularItemForm,
    MatriculaForm,
    ProfessorEditForm,
    ProfessorForm,
    ResetPasswordForm,
    SalaForm,
    SHIFT_SLOT_VALUES,
    TimetableForm,
    TurmaForm,
    NIGHT_SHIFT_ID,
    WEEKDAY_VALUES,
    get_shift_bounds,
    get_shift_label,
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
from . import bp
from .helpers import (
    admin_required,
    aluno_has_schedule_conflict,
    aluno_matricula_exists,
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


def _build_slot_key(day_label, slot_id):
    return f"{day_label}|{slot_id}"


def _normalize_turma_selection(raw_turma_id):
    if raw_turma_id in (None, "", 0, "0"):
        return 0
    return int(raw_turma_id)


def _build_timetable_availability(salas, professores, turmas, exclude_timetable_id=None):
    all_room_ids = {sala.id for sala in salas}
    all_professor_ids = {professor.id for professor in professores}
    all_turma_ids = {turma.id for turma in turmas}

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
                busy_professor_ids.add(row.professor_id)
                if row.turma_id is not None:
                    busy_turma_ids.add(row.turma_id)

            key = _build_slot_key(day_label, slot_id)
            availability_by_key[key] = {
                "day": day_label,
                "slot_id": slot_id,
                "slot_label": get_shift_label(slot_id),
                "sala_ids": sorted(all_room_ids.difference(busy_room_ids)),
                "professor_ids": sorted(all_professor_ids.difference(busy_professor_ids)),
                "turma_ids": sorted(all_turma_ids.difference(busy_turma_ids)),
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

    return {
        "availability_by_key": availability_by_key,
        "professor_to_disciplina": {str(key): value for key, value in professor_to_disciplina.items()},
        "disciplina_to_professor": {str(key): value for key, value in disciplina_to_professor.items()},
        "turma_to_disciplina": turma_to_disciplina,
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
    alunos = Aluno.query.order_by(Aluno.nome.asc()).all()
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
        sala = Sala(nome=nome, capacidade=form.capacidade.data)
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
        sala.capacidade = form.capacidade.data
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
        form.capacidade.data = sala.capacidade
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
    turmas = (
        Turma.query.options(joinedload(Turma.curso))
        .order_by(Turma.semestre_letivo.desc(), Turma.curso_id.asc(), Turma.codigo.asc())
        .all()
    )
    delete_form = DeleteForm()
    return render_template("turmas.html", turmas=turmas, delete_form=delete_form)


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
            quantidade_alunos=form.quantidade_alunos.data or None,
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
        turma.quantidade_alunos = form.quantidade_alunos.data or None
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


# CRUD Professores


def _load_professor_disciplina_choices(form):
    disciplinas = Disciplina.query.order_by(Disciplina.nome.asc()).all()
    form.disciplinas_ids.choices = [(disciplina.id, disciplina.nome) for disciplina in disciplinas]
    return disciplinas

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
        delete_form=delete_form,
        reset_form=reset_form,
    )

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
        user = User(username=username, email=synthetic_professor_email(username), role="professor")
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
    alunos = Aluno.query.order_by(Aluno.nome.asc()).all()
    delete_form = DeleteForm()
    return render_template("alunos.html", alunos=alunos, delete_form=delete_form)

@bp.route("/aluno/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_aluno():
    form = AlunoForm()
    if form.validate_on_submit():
        nome = normalize_text(form.nome.data)
        matricula = normalize_text(form.matricula.data)
        if aluno_matricula_exists(matricula):
            flash("Ja existe aluno com esta matricula.", "warning")
            return render_template("aluno_form.html", form=form, title="Novo Aluno")
        aluno = Aluno(nome=nome, matricula=matricula)
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
    if form.validate_on_submit():
        nome = normalize_text(form.nome.data)
        matricula = normalize_text(form.matricula.data)
        if aluno_matricula_exists(matricula, exclude_aluno_id=aluno.id):
            flash("Ja existe aluno com esta matricula.", "warning")
            return render_template("aluno_form.html", form=form, title="Editar Aluno")
        aluno.nome = nome
        aluno.matricula = matricula
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
    related_matriculas = Matricula.query.filter_by(aluno_id=aluno.id).count()
    if related_matriculas > 0:
        flash("Nao e possivel deletar aluno com turmas alocadas.", "warning")
        return redirect(url_for("main.alunos"))
    related_presencas = Presenca.query.filter_by(aluno_id=aluno.id).count()
    if related_presencas > 0:
        flash("Nao e possivel deletar aluno com chamadas registradas.", "warning")
        return redirect(url_for("main.alunos"))
    db.session.delete(aluno)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel deletar o aluno.", "danger")
        return redirect(url_for("main.alunos"))
    flash("Aluno deletado com sucesso.", "success")
    return redirect(url_for("main.alunos"))

# Alocacao de alunos em turmas

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
    form.aluno_id.choices = [(a.id, f"{a.nome} ({a.matricula})") for a in Aluno.query.order_by(Aluno.nome.asc()).all()]
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
        if aluno_turma_exists(form.aluno_id.data, form.turma_id.data):
            flash("Este aluno ja esta alocado nesta turma.", "warning")
            return render_template("matricula_form.html", title="Nova Alocacao de Aluno", form=form)
        if turma_capacity_reached(form.turma_id.data):
            flash("Nao foi possivel alocar: capacidade prevista da turma foi atingida.", "warning")
            return render_template("matricula_form.html", title="Nova Alocacao de Aluno", form=form)
        if aluno_has_schedule_conflict(form.aluno_id.data, form.turma_id.data):
            flash("Nao foi possivel alocar: conflito de horario para este aluno.", "warning")
            return render_template("matricula_form.html", title="Nova Alocacao de Aluno", form=form)
        matricula = Matricula(aluno_id=form.aluno_id.data, turma_id=form.turma_id.data)
        db.session.add(matricula)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel criar a alocacao do aluno.", "danger")
            return render_template("matricula_form.html", title="Nova Alocacao de Aluno", form=form)
        flash("Aluno alocado com sucesso.", "success")
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
    turma_timetable_ids = [
        row.id for row in Timetable.query.with_entities(Timetable.id).filter_by(turma_id=matricula.turma_id).all()
    ]
    has_presencas = 0
    if turma_timetable_ids:
        has_presencas = Presenca.query.filter(
            Presenca.aluno_id == matricula.aluno_id,
            Presenca.timetable_id.in_(turma_timetable_ids),
        ).count()
    if has_presencas > 0:
        flash("Nao e possivel remover alocacao com chamadas registradas.", "warning")
        return redirect(url_for("main.matriculas"))
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
            f"{turma.curso.nome if turma.curso else 'Curso'} | {turma.codigo} | {turma.semestre_letivo} | {turma.periodo}o periodo",
        )
        for turma in turmas
    ]

    allocation_payload = _build_allocation_payload(
        salas=salas,
        professores=professores,
        disciplinas=disciplinas,
        turmas=turmas,
    )
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
            f"{turma.curso.nome if turma.curso else 'Curso'} | {turma.codigo} | {turma.semestre_letivo} | {turma.periodo}o periodo",
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
