from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required
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

@bp.route("/admin")
@login_required
@admin_required
def admin_dashboard():
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
    delete_form = DeleteForm()
    return render_template(
        "admin_dashboard.html",
        salas=salas,
        professores=professores,
        disciplinas=disciplinas,
        alunos=alunos,
        timetables=timetables,
        matriculas_count=Matricula.query.count(),
        delete_form=delete_form,
    )

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
