from datetime import datetime, time

from flask_wtf import FlaskForm
from wtforms import IntegerField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import (
    DataRequired,
    EqualTo,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)

PASSWORD_MIN_LENGTH = 6


def parse_time(value):
    if isinstance(value, time):
        return value
    return datetime.strptime((value or "").strip(), "%H:%M").time()


def parse_date_br(value):
    return datetime.strptime((value or "").strip(), "%d/%m/%Y").date()


def validate_time_24h(form, field):
    try:
        parse_time(field.data)
    except (TypeError, ValueError):
        raise ValidationError("Use o formato 24h HH:MM (ex: 19:00).")


def validate_time_range(form, field):
    if form.hora_inicio.data and form.hora_fim.data:
        try:
            inicio = parse_time(form.hora_inicio.data)
            fim = parse_time(form.hora_fim.data)
        except (TypeError, ValueError):
            return
        if inicio >= fim:
            raise ValidationError("A hora de inicio deve ser anterior a hora de fim.")


def validate_date_br(form, field):
    try:
        parse_date_br(field.data)
    except (TypeError, ValueError):
        raise ValidationError("Use o formato DD/MM/AAAA.")


class LoginForm(FlaskForm):
    username = StringField(
        "Usuario", validators=[DataRequired(), Length(min=2, max=64)], render_kw={"autocomplete": "username"}
    )
    password = PasswordField(
        "Senha", validators=[DataRequired(), Length(min=6, max=128)], render_kw={"autocomplete": "current-password"}
    )
    submit = SubmitField("Entrar")


class ProfessorForm(FlaskForm):
    username = StringField(
        "Login", validators=[DataRequired(), Length(min=2, max=64)], render_kw={"autocomplete": "username"}
    )
    password = PasswordField(
        "Senha",
        validators=[DataRequired(), Length(min=PASSWORD_MIN_LENGTH, max=128)],
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
    password = PasswordField(
        "Nova Senha (opcional)",
        validators=[Optional(), Length(min=PASSWORD_MIN_LENGTH, max=128)],
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
    hora_inicio = StringField(
        "Horario Inicio",
        validators=[DataRequired(), validate_time_24h],
        render_kw={
            "placeholder": "HH:MM",
            "inputmode": "numeric",
            "maxlength": "5",
            "pattern": r"\d{2}:\d{2}",
            "data-time-spinner": "24h",
            "autocomplete": "off",
        },
    )
    hora_fim = StringField(
        "Horario Fim",
        validators=[DataRequired(), validate_time_24h, validate_time_range],
        render_kw={
            "placeholder": "HH:MM",
            "inputmode": "numeric",
            "maxlength": "5",
            "pattern": r"\d{2}:\d{2}",
            "data-time-spinner": "24h",
            "autocomplete": "off",
        },
    )
    sala_id = SelectField(
        "Sala",
        coerce=int,
        validators=[DataRequired()],
    )
    professor_id = SelectField(
        "Professor",
        coerce=int,
        validators=[DataRequired()],
    )
    disciplina_id = SelectField(
        "Disciplina",
        coerce=int,
        validators=[DataRequired()],
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
    )
    timetable_id = SelectField(
        "Turma",
        coerce=int,
        validators=[DataRequired()],
    )
    submit = SubmitField("Alocar")


class AttendanceForm(FlaskForm):
    chamada_data = StringField(
        "Data da Chamada",
        validators=[DataRequired(), validate_date_br],
        render_kw={
            "type": "text",
            "placeholder": "dd/mm/yyyy",
            "inputmode": "numeric",
            "maxlength": "10",
            "pattern": r"\d{2}/\d{2}/\d{4}",
            "autocomplete": "off",
        },
    )
    submit = SubmitField("Salvar Chamada")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Senha Atual", validators=[DataRequired(), Length(max=128)], render_kw={"autocomplete": "current-password"}
    )
    new_password = PasswordField(
        "Nova Senha",
        validators=[DataRequired(), Length(min=PASSWORD_MIN_LENGTH, max=128)],
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
