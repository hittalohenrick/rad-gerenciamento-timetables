from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app import db
from app.forms import ChangePasswordForm, LoginForm, RegistrationForm
from app.models import User

from . import bp
from .helpers import admin_required_redirect, normalize_text, username_or_email_exists


@bp.before_app_request
def enforce_password_change():
    if not current_user.is_authenticated:
        return None

    if not current_user.must_change_password:
        return None

    allowed_endpoints = {"main.change_password", "main.logout", "main.login", "static"}
    endpoint = request.endpoint or ""
    if endpoint in allowed_endpoints:
        return None

    flash("Voce precisa alterar sua senha antes de continuar.", "warning")
    return redirect(url_for("main.change_password"))


@bp.route("/")
@login_required
def index():
    if current_user.is_admin():
        return redirect(url_for("main.admin_dashboard"))
    return redirect(url_for("main.professor_dashboard"))


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

        user = User(username=username, email=email, role="professor", must_change_password=True)
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


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Senha atual invalida.", "danger")
            return render_template("change_password.html", title="Alterar Senha", form=form)

        if current_user.check_password(form.new_password.data):
            flash("A nova senha deve ser diferente da senha atual.", "warning")
            return render_template("change_password.html", title="Alterar Senha", form=form)

        current_user.set_password(form.new_password.data)
        current_user.must_change_password = False

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Nao foi possivel atualizar a senha.", "danger")
            return render_template("change_password.html", title="Alterar Senha", form=form)

        flash("Senha alterada com sucesso.", "success")
        return redirect(url_for("main.index"))

    return render_template("change_password.html", title="Alterar Senha", form=form)
