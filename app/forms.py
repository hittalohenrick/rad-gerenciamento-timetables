from datetime import datetime, time
import re

from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, PasswordField, SelectField, StringField, SubmitField, TimeField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)


def parse_time(value):
    if isinstance(value, time):
        return value
    return datetime.strptime(value, "%H:%M").time()


def validate_time_range(form, field):
    if form.hora_inicio.data and form.hora_fim.data:
        inicio = parse_time(form.hora_inicio.data)
        fim = parse_time(form.hora_fim.data)
        if inicio >= fim:
            raise ValidationError("A hora de inicio deve ser anterior a hora de fim.")


def validate_password_strength(form, field):
    password = field.data or ""
    if len(password) < 8:
        raise ValidationError("A senha deve ter pelo menos 8 caracteres.")
    if re.search(r"[A-Z]", password) is None:
        raise ValidationError("A senha deve ter ao menos uma letra maiuscula.")
    if re.search(r"[a-z]", password) is None:
        raise ValidationError("A senha deve ter ao menos uma letra minuscula.")
    if re.search(r"[0-9]", password) is None:
        raise ValidationError("A senha deve ter ao menos um numero.")


class LoginForm(FlaskForm):
    username = StringField(
        "Usuario", validators=[DataRequired(), Length(min=2, max=64)], render_kw={"autocomplete": "username"}
    )
    password = PasswordField(
        "Senha", validators=[DataRequired(), Length(min=6, max=128)], render_kw={"autocomplete": "current-password"}
    )
    submit = SubmitField("Entrar")


class RegistrationForm(FlaskForm):
    username = StringField(
        "Usuario", validators=[DataRequired(), Length(min=2, max=64)], render_kw={"autocomplete": "username"}
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)], render_kw={"autocomplete": "email"})
    password = PasswordField(
        "Senha",
        validators=[DataRequired(), Length(min=8, max=128), validate_password_strength],
        render_kw={"autocomplete": "new-password"},
    )
    password2 = PasswordField(
        "Repetir Senha", validators=[DataRequired(), EqualTo("password")], render_kw={"autocomplete": "new-password"}
    )
    role = SelectField(
        "Funcao",
        choices=[("professor", "Professor")],
        validators=[DataRequired()],
        default="professor",
    )
    submit = SubmitField("Registrar")


class ProfessorForm(FlaskForm):
    username = StringField(
        "Login", validators=[DataRequired(), Length(min=2, max=64)], render_kw={"autocomplete": "username"}
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)], render_kw={"autocomplete": "email"})
    password = PasswordField(
        "Senha",
        validators=[DataRequired(), Length(min=8, max=128), validate_password_strength],
        render_kw={"autocomplete": "new-password"},
    )
    password2 = PasswordField(
        "Repetir Senha", validators=[DataRequired(), EqualTo("password")], render_kw={"autocomplete": "new-password"}
    )
    submit = SubmitField("Salvar")


class ProfessorEditForm(FlaskForm):
    username = StringField(
        "Login", validators=[DataRequired(), Length(min=2, max=64)], render_kw={"autocomplete": "username"}
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)], render_kw={"autocomplete": "email"})
    password = PasswordField(
        "Nova Senha (opcional)",
        validators=[Optional(), Length(min=8, max=128), validate_password_strength],
        render_kw={"autocomplete": "new-password"},
    )
    password2 = PasswordField(
        "Repetir Nova Senha", validators=[EqualTo("password")], render_kw={"autocomplete": "new-password"}
    )
    submit = SubmitField("Salvar")


class SalaForm(FlaskForm):
    nome = StringField("Nome da Sala", validators=[DataRequired(), Length(min=2, max=100)])
    capacidade = IntegerField("Capacidade", validators=[DataRequired(), NumberRange(min=1, max=500)])
    submit = SubmitField("Salvar")


class DisciplinaForm(FlaskForm):
    nome = StringField("Nome da Disciplina", validators=[DataRequired(), Length(min=2, max=100)])
    submit = SubmitField("Salvar")


class TimetableForm(FlaskForm):
    dia = SelectField(
        "Dia",
        choices=[
            ("Segunda", "Segunda"),
            ("Terça", "Terça"),
            ("Quarta", "Quarta"),
            ("Quinta", "Quinta"),
            ("Sexta", "Sexta"),
            ("Sábado", "Sábado"),
            ("Domingo", "Domingo"),
        ],
        validators=[DataRequired()],
    )
    hora_inicio = TimeField("Horario Inicio", format="%H:%M", validators=[DataRequired()])
    hora_fim = TimeField("Horario Fim", format="%H:%M", validators=[DataRequired(), validate_time_range])
    sala_id = SelectField(
        "Sala",
        coerce=int,
        validators=[DataRequired()],
        render_kw={
            "data-searchable": "true",
            "data-search-placeholder": "Pesquisar sala...",
        },
    )
    professor_id = SelectField(
        "Professor",
        coerce=int,
        validators=[DataRequired()],
        render_kw={
            "data-searchable": "true",
            "data-search-placeholder": "Pesquisar professor...",
        },
    )
    disciplina_id = SelectField(
        "Disciplina",
        coerce=int,
        validators=[DataRequired()],
        render_kw={
            "data-searchable": "true",
            "data-search-placeholder": "Pesquisar disciplina...",
        },
    )
    submit = SubmitField("Alocar")


class DeleteForm(FlaskForm):
    submit = SubmitField("Deletar")


class AlunoForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(min=2, max=120)])
    matricula = StringField("Matricula", validators=[DataRequired(), Length(min=2, max=30)])
    submit = SubmitField("Salvar")


class MatriculaForm(FlaskForm):
    aluno_id = SelectField(
        "Aluno",
        coerce=int,
        validators=[DataRequired()],
        render_kw={
            "data-searchable": "true",
            "data-search-placeholder": "Pesquisar aluno por nome ou matricula...",
        },
    )
    timetable_id = SelectField(
        "Turma",
        coerce=int,
        validators=[DataRequired()],
        render_kw={
            "data-searchable": "true",
            "data-search-placeholder": "Pesquisar turma...",
        },
    )
    submit = SubmitField("Alocar")


class AttendanceForm(FlaskForm):
    chamada_data = DateField("Data da Chamada", format="%Y-%m-%d", validators=[DataRequired()])
    submit = SubmitField("Salvar Chamada")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Senha Atual", validators=[DataRequired(), Length(max=128)], render_kw={"autocomplete": "current-password"}
    )
    new_password = PasswordField(
        "Nova Senha",
        validators=[DataRequired(), Length(min=8, max=128), validate_password_strength],
        render_kw={"autocomplete": "new-password"},
    )
    new_password2 = PasswordField(
        "Repetir Nova Senha",
        validators=[DataRequired(), EqualTo("new_password")],
        render_kw={"autocomplete": "new-password"},
    )
    submit = SubmitField("Alterar Senha")


class ResetPasswordForm(FlaskForm):
    submit = SubmitField("Resetar Senha")
