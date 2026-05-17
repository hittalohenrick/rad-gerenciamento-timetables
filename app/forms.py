from datetime import datetime, time

from flask_wtf import FlaskForm
from wtforms import IntegerField, PasswordField, SelectField, SelectMultipleField, StringField, SubmitField
from wtforms.validators import (
    DataRequired,
    EqualTo,
    InputRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)

PASSWORD_MIN_LENGTH = 6
FIXED_SALA_CAPACITY = 50
MAX_TURMA_CAPACITY = 50
WEEKDAY_CHOICES = [
    ("Segunda", "Segunda"),
    ("Terca", "Terca"),
    ("Quarta", "Quarta"),
    ("Quinta", "Quinta"),
    ("Sexta", "Sexta"),
    ("Sabado", "Sabado"),
    ("Domingo", "Domingo"),
]
WEEKDAY_VALUES = [value for value, _ in WEEKDAY_CHOICES]
SHIFT_SLOTS = [
    ("manha_0700_0830", "Manha 1 (07:00 - 08:30)", time(7, 0), time(8, 30)),
    ("manha_0900_1030", "Manha 2 (09:00 - 10:30)", time(9, 0), time(10, 30)),
    ("tarde_1300_1430", "Tarde 1 (13:00 - 14:30)", time(13, 0), time(14, 30)),
    ("tarde_1500_1630", "Tarde 2 (15:00 - 16:30)", time(15, 0), time(16, 30)),
    ("noite_1800_1930", "Noite 1 (18:00 - 19:30)", time(18, 0), time(19, 30)),
    ("noite_2000_2130", "Noite 2 (20:00 - 21:30)", time(20, 0), time(21, 30)),
]
SHIFT_SLOT_CHOICES = [(slot_id, label) for slot_id, label, _, _ in SHIFT_SLOTS]
SHIFT_SLOT_VALUES = [slot_id for slot_id, *_ in SHIFT_SLOTS]
SHIFT_SLOT_MAP = {
    slot_id: {"label": label, "start": start, "end": end}
    for slot_id, label, start, end in SHIFT_SLOTS
}
TURNO_CHOICES = [
    ("matutino", "Matutino"),
    ("vespertino", "Vespertino"),
    ("noturno", "Noturno"),
]
TURNOS_VALIDOS = [value for value, _ in TURNO_CHOICES]
PROFESSOR_WORKLOAD_CHOICES = [
    ("matutino_vespertino", "Matutino + Vespertino"),
    ("vespertino_noturno", "Vespertino + Noturno"),
]
PROFESSOR_WORKLOAD_TURNOS = {
    "matutino_vespertino": ["matutino", "vespertino"],
    "vespertino_noturno": ["vespertino", "noturno"],
}
PROFESSOR_DEFAULT_WORKLOAD = "vespertino_noturno"
SLOT_IDS_BY_TURNO = {
    "matutino": ["manha_0700_0830", "manha_0900_1030"],
    "vespertino": ["tarde_1300_1430", "tarde_1500_1630"],
    "noturno": ["noite_1800_1930", "noite_2000_2130"],
}
NIGHT_SHIFT_ID = "noite_1800_1930"
NIGHT_SHIFT_START = SHIFT_SLOT_MAP[NIGHT_SHIFT_ID]["start"]
NIGHT_SHIFT_END = SHIFT_SLOT_MAP[NIGHT_SHIFT_ID]["end"]
NIGHT_SHIFT_CHOICES = [(NIGHT_SHIFT_ID, SHIFT_SLOT_MAP[NIGHT_SHIFT_ID]["label"])]


def get_shift_bounds(slot_id):
    slot = SHIFT_SLOT_MAP.get(slot_id)
    if not slot:
        return None, None
    return slot["start"], slot["end"]


def get_shift_label(slot_id):
    slot = SHIFT_SLOT_MAP.get(slot_id)
    if not slot:
        return "Horario personalizado"
    return slot["label"]


def get_turno_label(turno):
    labels_by_turno = dict(TURNO_CHOICES)
    return labels_by_turno.get(turno, "Nao definido")


def get_professor_workload_label(profile_key):
    labels_by_profile = dict(PROFESSOR_WORKLOAD_CHOICES)
    return labels_by_profile.get(profile_key, "Nao definido")


def allowed_slot_ids_for_turno(turno):
    return list(SLOT_IDS_BY_TURNO.get(turno, SLOT_IDS_BY_TURNO["noturno"]))


def resolve_shift_slot_id(hora_inicio, hora_fim):
    for slot_id, slot in SHIFT_SLOT_MAP.items():
        if slot["start"] == hora_inicio and slot["end"] == hora_fim:
            return slot_id
    return None


def parse_date_br(value):
    return datetime.strptime((value or "").strip(), "%d/%m/%Y").date()


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
    disciplinas_ids = SelectMultipleField(
        "Disciplinas Aptas",
        coerce=int,
        validators=[DataRequired()],
        render_kw={"data-searchable": "true", "size": "8"},
    )
    jornada_turnos = SelectField(
        "Jornada de Turnos",
        choices=PROFESSOR_WORKLOAD_CHOICES,
        validators=[DataRequired()],
        default=PROFESSOR_DEFAULT_WORKLOAD,
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
    disciplinas_ids = SelectMultipleField(
        "Disciplinas Aptas",
        coerce=int,
        validators=[DataRequired()],
        render_kw={"data-searchable": "true", "size": "8"},
    )
    jornada_turnos = SelectField(
        "Jornada de Turnos",
        choices=PROFESSOR_WORKLOAD_CHOICES,
        validators=[DataRequired()],
        default=PROFESSOR_DEFAULT_WORKLOAD,
    )
    submit = SubmitField("Salvar")


class SalaForm(FlaskForm):
    nome = StringField("Nome da Sala", validators=[DataRequired(), Length(min=2, max=100)])
    submit = SubmitField("Salvar")


class DisciplinaForm(FlaskForm):
    nome = StringField("Nome da Disciplina", validators=[DataRequired(), Length(min=2, max=100)])
    submit = SubmitField("Salvar")


class CursoForm(FlaskForm):
    nome = StringField("Nome do Curso", validators=[DataRequired(), Length(min=2, max=120)])
    codigo = StringField("Codigo do Curso", validators=[DataRequired(), Length(min=2, max=20)])
    quantidade_periodos = IntegerField(
        "Quantidade de Periodos",
        validators=[DataRequired(), NumberRange(min=1, max=16)],
        default=8,
    )
    submit = SubmitField("Salvar")


class GradeCurricularForm(FlaskForm):
    nome = StringField("Nome da Grade", validators=[DataRequired(), Length(min=2, max=120)])
    curso_id = SelectField("Curso", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Salvar")


class GradeCurricularItemForm(FlaskForm):
    disciplina_id = SelectField("Disciplina", coerce=int, validators=[DataRequired()])
    periodo = IntegerField("Periodo", validators=[DataRequired(), NumberRange(min=1, max=16)])
    submit = SubmitField("Salvar")


class TurmaForm(FlaskForm):
    curso_id = SelectField("Curso", coerce=int, validators=[DataRequired()])
    codigo = StringField("Codigo da Turma", validators=[DataRequired(), Length(min=2, max=30)])
    semestre_letivo = StringField("Semestre Letivo", validators=[DataRequired(), Length(min=4, max=20)])
    periodo = IntegerField("Periodo", validators=[DataRequired(), NumberRange(min=1, max=16)])
    turno = SelectField("Turno", choices=TURNO_CHOICES, validators=[DataRequired()], default="noturno")
    quantidade_alunos = IntegerField(
        "Quantidade de Alunos (0 a 50)",
        validators=[
            InputRequired(),
            NumberRange(
                min=0,
                max=MAX_TURMA_CAPACITY,
                message=f"A capacidade da turma deve estar entre 0 e {MAX_TURMA_CAPACITY} alunos.",
            ),
        ],
    )
    submit = SubmitField("Salvar")


class TimetableForm(FlaskForm):
    dia = SelectField(
        "Dia",
        choices=WEEKDAY_CHOICES,
        validators=[DataRequired()],
    )
    horario_id = SelectField(
        "Horario",
        choices=SHIFT_SLOT_CHOICES,
        validators=[DataRequired()],
        default=SHIFT_SLOT_CHOICES[0][0],
    )
    turma_id = SelectField(
        "Turma",
        coerce=int,
        validators=[DataRequired()],
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


class ProfessorAssignmentForm(FlaskForm):
    professor_id = SelectField(
        "Professor",
        coerce=int,
        validators=[DataRequired()],
    )
    submit = SubmitField("Salvar Professor")


class BulkProfessorAssignmentForm(FlaskForm):
    submit = SubmitField("Salvar Alocacao em Lote")


class DeleteForm(FlaskForm):
    submit = SubmitField("Deletar")


class AlunoForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(min=2, max=120)])
    matricula = StringField("Matricula", validators=[DataRequired(), Length(min=2, max=30)])
    curso_id = SelectField("Curso", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Salvar")


class MatriculaForm(FlaskForm):
    aluno_id = SelectField(
        "Aluno",
        coerce=int,
        validators=[DataRequired()],
    )
    turma_id = SelectField(
        "Turma",
        coerce=int,
        validators=[DataRequired()],
    )
    submit = SubmitField("Alocar")


class TurmaMatriculaForm(FlaskForm):
    aluno_id = SelectField(
        "Aluno",
        coerce=int,
        validators=[DataRequired()],
        render_kw={"data-searchable": "true"},
    )
    submit = SubmitField("Matricular Aluno")


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
