from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from datetime import datetime, timedelta


def generate_time_choices(step=15):
    choices = []
    current = datetime.strptime('00:00', '%H:%M')
    end = datetime.strptime('23:59', '%H:%M')
    while current <= end:
        value = current.strftime('%H:%M')
        choices.append((value, value))
        current = current + timedelta(minutes=step)
    return choices


def parse_time(value):
    return datetime.strptime(value, '%H:%M').time()


def validate_time_range(form, field):
    if form.hora_inicio.data and form.hora_fim.data:
        inicio = parse_time(form.hora_inicio.data)
        fim = parse_time(form.hora_fim.data)
        if inicio >= fim:
            raise ValidationError('A hora de início deve ser anterior à hora de fim.')

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class RegistrationForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=2, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Repetir Senha', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Função', choices=[('professor', 'Professor'), ('admin', 'Admin')], default='professor')
    submit = SubmitField('Registrar')

class ProfessorForm(FlaskForm):
    username = StringField('Nome', validators=[DataRequired(), Length(min=2, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Salvar')

class SalaForm(FlaskForm):
    nome = StringField('Nome da Sala', validators=[DataRequired()])
    capacidade = IntegerField('Capacidade', validators=[DataRequired()])
    submit = SubmitField('Salvar')

class DisciplinaForm(FlaskForm):
    nome = StringField('Nome da Disciplina', validators=[DataRequired()])
    submit = SubmitField('Salvar')

class TimetableForm(FlaskForm):
    dia = SelectField('Dia', choices=[
        ('Segunda', 'Segunda'), ('Terça', 'Terça'), ('Quarta', 'Quarta'),
        ('Quinta', 'Quinta'), ('Sexta', 'Sexta'), ('Sábado', 'Sábado'), ('Domingo', 'Domingo')
    ], validators=[DataRequired()])
    hora_inicio = SelectField('Horário Início', choices=generate_time_choices(15), validators=[DataRequired()])
    hora_fim = SelectField('Horário Fim', choices=generate_time_choices(15), validators=[DataRequired(), validate_time_range])
    sala_id = SelectField('Sala', coerce=int, validators=[DataRequired()])
    professor_id = SelectField('Professor', coerce=int, validators=[DataRequired()])
    disciplina_id = SelectField('Disciplina', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Alocar')