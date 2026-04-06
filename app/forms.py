from datetime import datetime, time

from flask_wtf import FlaskForm
from wtforms import IntegerField, PasswordField, SelectField, StringField, SubmitField, TimeField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, ValidationError


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


class LoginForm(FlaskForm):
    username = StringField("Usuario", validators=[DataRequired(), Length(min=2, max=64)])
    password = PasswordField("Senha", validators=[DataRequired(), Length(min=6, max=128)])
    submit = SubmitField("Entrar")


class RegistrationForm(FlaskForm):
    username = StringField("Usuario", validators=[DataRequired(), Length(min=2, max=64)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Senha", validators=[DataRequired(), Length(min=6, max=128)])
    password2 = PasswordField("Repetir Senha", validators=[DataRequired(), EqualTo("password")])
    role = SelectField(
        "Funcao",
        choices=[("professor", "Professor")],
        validators=[DataRequired()],
        default="professor",
    )
    submit = SubmitField("Registrar")


class ProfessorForm(FlaskForm):
    username = StringField("Nome", validators=[DataRequired(), Length(min=2, max=64)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
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
    sala_id = SelectField("Sala", coerce=int, validators=[DataRequired()])
    professor_id = SelectField("Professor", coerce=int, validators=[DataRequired()])
    disciplina_id = SelectField("Disciplina", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Alocar")


class DeleteForm(FlaskForm):
    submit = SubmitField("Deletar")
