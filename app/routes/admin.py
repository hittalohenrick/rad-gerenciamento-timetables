from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from app import db
from app.forms import (
    AlunoForm,
    DeleteForm,
    DisciplinaForm,
    MatriculaForm,
    ResetPasswordForm,
    ProfessorEditForm,
    ProfessorForm,
    SalaForm,
    TimetableForm,
    parse_time,
)
from app.models import Aluno, Disciplina, Matricula, Presenca, Sala, Timetable, User
from . import bp
from .helpers import (
    admin_required,
    aluno_has_schedule_conflict,
    aluno_matricula_exists,
    aluno_turma_exists,
    disciplina_name_exists,
    find_timetable_conflict,
    generate_disciplina_code,
    load_timetable_options,
    normalize_text,
    sala_name_exists,
    synthetic_professor_email,
    timetable_capacity_reached,
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


def _build_admin_insights(salas, professores, timetables):
    total_salas = len(salas)
    matriculas_por_turma = dict(
        db.session.query(Matricula.timetable_id, func.count(Matricula.id))
        .group_by(Matricula.timetable_id)
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
        matriculados = int(matriculas_por_turma.get(timetable.id, 0))
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

    total_matriculas = sum(matriculas_por_turma.values())
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
    salas = Sala.query.order_by(Sala.nome.asc()).all()
    professores = User.query.filter_by(role="professor").order_by(User.username.asc()).all()
    disciplinas = Disciplina.query.order_by(Disciplina.nome.asc()).all()
    alunos = Aluno.query.order_by(Aluno.nome.asc()).all()
    timetables = (
        Timetable.query.options(
            joinedload(Timetable.sala),
            joinedload(Timetable.professor),
            joinedload(Timetable.disciplina),
        )
        .order_by(Timetable.dia.asc(), Timetable.hora_inicio.asc())
        .all()
    )
    return {
        "salas": salas,
        "professores": professores,
        "disciplinas": disciplinas,
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
    db.session.delete(disciplina)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel deletar a disciplina.", "danger")
        return redirect(url_for("main.disciplinas"))
    flash("Disciplina deletada com sucesso.", "success")
    return redirect(url_for("main.disciplinas"))

# CRUD Professores

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
    if form.validate_on_submit():
        username = normalize_text(form.username.data)
        duplicate_error = username_exists(username)
        if duplicate_error:
            flash(duplicate_error, "warning")
            return render_template("register.html", title="Novo Professor", form=form)
        user = User(username=username, email=synthetic_professor_email(username), role="professor")
        user.set_password(form.password.data)
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
    if form.validate_on_submit():
        username = normalize_text(form.username.data)
        duplicate_error = username_exists(username, exclude_user_id=professor.id)
        if duplicate_error:
            flash(duplicate_error, "warning")
            return render_template("register.html", title="Editar Professor", form=form)
        professor.username = username
        professor.email = synthetic_professor_email(username)
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
            joinedload(Matricula.timetable).joinedload(Timetable.sala),
            joinedload(Matricula.timetable).joinedload(Timetable.professor),
            joinedload(Matricula.timetable).joinedload(Timetable.disciplina),
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
    form.timetable_id.choices = load_timetable_options()
    if form.validate_on_submit():
        if not form.aluno_id.choices or not form.timetable_id.choices:
            flash("Cadastre ao menos um aluno e uma turma antes de alocar.", "warning")
            return redirect(url_for("main.matriculas"))
        if aluno_turma_exists(form.aluno_id.data, form.timetable_id.data):
            flash("Este aluno ja esta alocado nesta turma.", "warning")
            return render_template("matricula_form.html", title="Nova Alocacao de Aluno", form=form)
        if timetable_capacity_reached(form.timetable_id.data):
            flash("Nao foi possivel alocar: capacidade da sala ja foi atingida.", "warning")
            return render_template("matricula_form.html", title="Nova Alocacao de Aluno", form=form)
        if aluno_has_schedule_conflict(form.aluno_id.data, form.timetable_id.data):
            flash("Nao foi possivel alocar: conflito de horario para este aluno.", "warning")
            return render_template("matricula_form.html", title="Nova Alocacao de Aluno", form=form)
        matricula = Matricula(aluno_id=form.aluno_id.data, timetable_id=form.timetable_id.data)
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
    has_presencas = Presenca.query.filter_by(
        aluno_id=matricula.aluno_id,
        timetable_id=matricula.timetable_id,
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
    form.sala_id.choices = [(s.id, s.nome) for s in Sala.query.order_by(Sala.nome.asc()).all()]
    form.professor_id.choices = [
        (p.id, p.username) for p in User.query.filter_by(role="professor").order_by(User.username.asc()).all()
    ]
    form.disciplina_id.choices = [(d.id, d.nome) for d in Disciplina.query.order_by(Disciplina.nome.asc()).all()]
    if form.validate_on_submit():
        if not form.sala_id.choices or not form.professor_id.choices or not form.disciplina_id.choices:
            flash(
                "Cadastre ao menos uma sala, um professor e uma disciplina antes de criar alocacoes.",
                "warning",
            )
            return redirect(url_for("main.admin_dashboard"))
        hora_inicio = parse_time(form.hora_inicio.data)
        hora_fim = parse_time(form.hora_fim.data)
        conflict_message = find_timetable_conflict(
            dia=form.dia.data,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
            sala_id=form.sala_id.data,
            professor_id=form.professor_id.data,
        )
        if conflict_message:
            flash(conflict_message, "danger")
            return redirect(url_for("main.new_timetable"))
        timetable = Timetable(
            dia=form.dia.data,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
            sala_id=form.sala_id.data,
            professor_id=form.professor_id.data,
            disciplina_id=form.disciplina_id.data,
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
    return render_template("timetable_form.html", form=form, title="Nova Alocacao")

@bp.route("/timetable/edit/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_timetable(id):
    timetable = db.get_or_404(Timetable, id)
    form = TimetableForm()
    form.sala_id.choices = [(s.id, s.nome) for s in Sala.query.order_by(Sala.nome.asc()).all()]
    form.professor_id.choices = [
        (p.id, p.username) for p in User.query.filter_by(role="professor").order_by(User.username.asc()).all()
    ]
    form.disciplina_id.choices = [(d.id, d.nome) for d in Disciplina.query.order_by(Disciplina.nome.asc()).all()]
    if form.validate_on_submit():
        hora_inicio = parse_time(form.hora_inicio.data)
        hora_fim = parse_time(form.hora_fim.data)
        conflict_message = find_timetable_conflict(
            dia=form.dia.data,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
            sala_id=form.sala_id.data,
            professor_id=form.professor_id.data,
            exclude_id=id,
        )
        if conflict_message:
            flash(conflict_message, "danger")
            return redirect(url_for("main.edit_timetable", id=id))
        timetable.dia = form.dia.data
        timetable.hora_inicio = hora_inicio
        timetable.hora_fim = hora_fim
        timetable.sala_id = form.sala_id.data
        timetable.professor_id = form.professor_id.data
        timetable.disciplina_id = form.disciplina_id.data
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
        form.hora_inicio.data = timetable.hora_inicio.strftime("%H:%M")
        form.hora_fim.data = timetable.hora_fim.strftime("%H:%M")
        form.sala_id.data = timetable.sala_id
        form.professor_id.data = timetable.professor_id
        form.disciplina_id.data = timetable.disciplina_id
    return render_template("timetable_form.html", form=form, title="Editar Alocacao")

@bp.route("/timetable/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_timetable(id):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.admin_dashboard"))
    timetable = db.get_or_404(Timetable, id)
    related_matriculas = Matricula.query.filter_by(timetable_id=timetable.id).count()
    if related_matriculas > 0:
        flash("Nao e possivel deletar a turma com alunos alocados.", "warning")
        return redirect(url_for("main.admin_dashboard"))
    related_presencas = Presenca.query.filter_by(timetable_id=timetable.id).count()
    if related_presencas > 0:
        flash("Nao e possivel deletar a turma com chamadas registradas.", "warning")
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
