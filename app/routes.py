import random
import string

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app import db
from app.forms import (
    DeleteForm,
    DisciplinaForm,
    LoginForm,
    ProfessorForm,
    RegistrationForm,
    SalaForm,
    TimetableForm,
    parse_time,
)
from app.models import Disciplina, Sala, Timetable, User

bp = Blueprint("main", __name__)


def times_overlap(start1, end1, start2, end2):
    """Verifica se dois intervalos de tempo se sobrepoem."""
    return max(start1, start2) < min(end1, end2)


def admin_required_redirect():
    if current_user.is_admin():
        return None
    logout_user()
    flash("Acesso negado.", "danger")
    return redirect(url_for("main.login"))


def normalize_text(value):
    return (value or "").strip()


def generate_disciplina_code():
    while True:
        codigo = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Disciplina.query.filter_by(codigo=codigo).first():
            return codigo


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


def username_or_email_exists(username, email, exclude_user_id=None):
    query = User.query
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)

    existing_username = query.filter(func.lower(User.username) == username.lower()).first()
    if existing_username:
        return "Ja existe usuario com este nome."

    existing_email = query.filter(func.lower(User.email) == email.lower()).first()
    if existing_email:
        return "Ja existe usuario com este email."

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


@bp.route("/")
@login_required
def index():
    if not current_user.is_admin():
        logout_user()
        flash("Apenas o admin pode acessar este sistema.", "danger")
        return redirect(url_for("main.login"))
    return redirect(url_for("main.admin_dashboard"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        username = normalize_text(form.username.data)
        user = User.query.filter(func.lower(User.username) == username.lower()).first()

        if user is None or not user.check_password(form.password.data):
            flash("Usuario ou senha invalidos.", "danger")
            return redirect(url_for("main.login"))

        if not user.is_admin():
            flash("Apenas o admin pode fazer login neste sistema.", "danger")
            return redirect(url_for("main.login"))

        login_user(user)
        return redirect(url_for("main.index"))

    return render_template("login.html", title="Login", form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


@bp.route("/register", methods=["GET", "POST"])
@login_required
def register():
    guard = admin_required_redirect()
    if guard:
        return guard

    form = RegistrationForm()
    if form.validate_on_submit():
        username = normalize_text(form.username.data)
        email = normalize_text(form.email.data)

        duplicate_error = username_or_email_exists(username, email)
        if duplicate_error:
            flash(duplicate_error, "warning")
            return render_template("register.html", title="Registrar Usuario", form=form)

        user = User(username=username, email=email, role="professor")
        user.set_password(form.password.data)

        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel registrar o usuario por conflito de dados.", "danger")
            return render_template("register.html", title="Registrar Usuario", form=form)

        flash("Usuario registrado com sucesso.", "success")
        return redirect(url_for("main.admin_dashboard"))

    return render_template("register.html", title="Registrar Usuario", form=form)


@bp.route("/admin")
@login_required
def admin_dashboard():
    guard = admin_required_redirect()
    if guard:
        return guard

    salas = Sala.query.order_by(Sala.nome.asc()).all()
    professores = User.query.filter_by(role="professor").order_by(User.username.asc()).all()
    disciplinas = Disciplina.query.order_by(Disciplina.nome.asc()).all()
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
        timetables=timetables,
        delete_form=delete_form,
    )


@bp.route("/horarios")
@login_required
def horarios():
    guard = admin_required_redirect()
    if guard:
        return guard

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


@bp.route("/professor")
@login_required
def professor_dashboard():
    guard = admin_required_redirect()
    if guard:
        return guard
    return redirect(url_for("main.admin_dashboard"))


# CRUD Salas
@bp.route("/salas")
@login_required
def salas():
    guard = admin_required_redirect()
    if guard:
        return guard

    salas = Sala.query.order_by(Sala.nome.asc()).all()
    delete_form = DeleteForm()
    return render_template("salas.html", salas=salas, delete_form=delete_form)


@bp.route("/sala/new", methods=["GET", "POST"])
@login_required
def new_sala():
    guard = admin_required_redirect()
    if guard:
        return guard

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
def edit_sala(id):
    guard = admin_required_redirect()
    if guard:
        return guard

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
def delete_sala(id):
    guard = admin_required_redirect()
    if guard:
        return guard

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
def disciplinas():
    guard = admin_required_redirect()
    if guard:
        return guard

    disciplinas = Disciplina.query.order_by(Disciplina.nome.asc()).all()
    delete_form = DeleteForm()
    return render_template("disciplinas.html", disciplinas=disciplinas, delete_form=delete_form)


@bp.route("/disciplina/new", methods=["GET", "POST"])
@login_required
def new_disciplina():
    guard = admin_required_redirect()
    if guard:
        return guard

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
def edit_disciplina(id):
    guard = admin_required_redirect()
    if guard:
        return guard

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
def delete_disciplina(id):
    guard = admin_required_redirect()
    if guard:
        return guard

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
def professores():
    guard = admin_required_redirect()
    if guard:
        return guard

    professores = User.query.filter_by(role="professor").order_by(User.username.asc()).all()
    delete_form = DeleteForm()
    return render_template("professores.html", professores=professores, delete_form=delete_form)


@bp.route("/professor/new", methods=["GET", "POST"])
@login_required
def new_professor():
    guard = admin_required_redirect()
    if guard:
        return guard

    form = ProfessorForm()
    if form.validate_on_submit():
        username = normalize_text(form.username.data)
        email = normalize_text(form.email.data)

        duplicate_error = username_or_email_exists(username, email)
        if duplicate_error:
            flash(duplicate_error, "warning")
            return render_template("register.html", title="Novo Professor", form=form)

        user = User(username=username, email=email, role="professor")
        user.set_password("professor123")
        db.session.add(user)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel registrar o professor.", "danger")
            return render_template("register.html", title="Novo Professor", form=form)

        flash("Professor registrado com sucesso (senha padrao: professor123).", "success")
        return redirect(url_for("main.professores"))

    return render_template("register.html", title="Novo Professor", form=form)


@bp.route("/professor/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_professor(id):
    guard = admin_required_redirect()
    if guard:
        return guard

    professor = db.get_or_404(User, id)
    if professor.role != "professor":
        flash("Usuario selecionado nao e professor.", "warning")
        return redirect(url_for("main.professores"))

    form = ProfessorForm()
    if form.validate_on_submit():
        username = normalize_text(form.username.data)
        email = normalize_text(form.email.data)

        duplicate_error = username_or_email_exists(username, email, exclude_user_id=professor.id)
        if duplicate_error:
            flash(duplicate_error, "warning")
            return render_template("register.html", title="Editar Professor", form=form)

        professor.username = username
        professor.email = email

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
        form.email.data = professor.email

    return render_template("register.html", title="Editar Professor", form=form)


@bp.route("/professor/delete/<int:id>", methods=["POST"])
@login_required
def delete_professor(id):
    guard = admin_required_redirect()
    if guard:
        return guard

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


@bp.route("/timetable/new", methods=["GET", "POST"])
@login_required
def new_timetable():
    guard = admin_required_redirect()
    if guard:
        return guard

    form = TimetableForm()
    form.sala_id.choices = [(s.id, s.nome) for s in Sala.query.order_by(Sala.nome.asc()).all()]
    form.professor_id.choices = [
        (p.id, p.username) for p in User.query.filter_by(role="professor").order_by(User.username.asc()).all()
    ]
    form.disciplina_id.choices = [
        (d.id, d.nome) for d in Disciplina.query.order_by(Disciplina.nome.asc()).all()
    ]

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
def edit_timetable(id):
    guard = admin_required_redirect()
    if guard:
        return guard

    timetable = db.get_or_404(Timetable, id)
    form = TimetableForm()
    form.sala_id.choices = [(s.id, s.nome) for s in Sala.query.order_by(Sala.nome.asc()).all()]
    form.professor_id.choices = [
        (p.id, p.username) for p in User.query.filter_by(role="professor").order_by(User.username.asc()).all()
    ]
    form.disciplina_id.choices = [
        (d.id, d.nome) for d in Disciplina.query.order_by(Disciplina.nome.asc()).all()
    ]

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
        form.hora_inicio.data = timetable.hora_inicio
        form.hora_fim.data = timetable.hora_fim
        form.sala_id.data = timetable.sala_id
        form.professor_id.data = timetable.professor_id
        form.disciplina_id.data = timetable.disciplina_id

    return render_template("timetable_form.html", form=form, title="Editar Alocacao")


@bp.route("/timetable/delete/<int:id>", methods=["POST"])
@login_required
def delete_timetable(id):
    guard = admin_required_redirect()
    if guard:
        return guard

    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Requisicao invalida.", "danger")
        return redirect(url_for("main.admin_dashboard"))

    timetable = db.get_or_404(Timetable, id)
    db.session.delete(timetable)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nao foi possivel deletar a alocacao.", "danger")
        return redirect(url_for("main.admin_dashboard"))

    flash("Alocacao deletada com sucesso.", "success")
    return redirect(url_for("main.admin_dashboard"))
