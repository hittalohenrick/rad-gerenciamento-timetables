from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, TimeField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo

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

class SalaForm(FlaskForm):
    nome = StringField('Nome da Sala', validators=[DataRequired()])
    capacidade = IntegerField('Capacidade', validators=[DataRequired()])
    submit = SubmitField('Salvar')

class HorarioForm(FlaskForm):
    dia_semana = SelectField('Dia da Semana', choices=[
        ('Segunda', 'Segunda'), ('Terça', 'Terça'), ('Quarta', 'Quarta'),
        ('Quinta', 'Quinta'), ('Sexta', 'Sexta'), ('Sábado', 'Sábado'), ('Domingo', 'Domingo')
    ], validators=[DataRequired()])
    hora_inicio = TimeField('Hora Início', validators=[DataRequired()])
    hora_fim = TimeField('Hora Fim', validators=[DataRequired()])
    submit = SubmitField('Salvar')

class DisciplinaForm(FlaskForm):
    nome = StringField('Nome da Disciplina', validators=[DataRequired()])
    codigo = StringField('Código', validators=[DataRequired(), Length(max=20)])
    submit = SubmitField('Salvar')

class TimetableForm(FlaskForm):
    horario_id = SelectField('Horário', coerce=int, validators=[DataRequired()])
    sala_id = SelectField('Sala', coerce=int, validators=[DataRequired()])
    professor_id = SelectField('Professor', coerce=int, validators=[DataRequired()])
    disciplina_id = SelectField('Disciplina', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Alocar')