from datetime import UTC, datetime

from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash


def utc_now():
    return datetime.now(UTC)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='professor')  # 'admin' or 'professor'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

class Sala(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    capacidade = db.Column(db.Integer, nullable=False)

class Disciplina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    codigo = db.Column(db.String(20), unique=True, nullable=False)

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dia = db.Column(db.String(20), nullable=False)  # e.g., 'Segunda', 'Terça'
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fim = db.Column(db.Time, nullable=False)
    sala_id = db.Column(db.Integer, db.ForeignKey('sala.id'), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplina.id'), nullable=False)

    sala = db.relationship('Sala', backref='timetables')
    professor = db.relationship('User', backref='timetables')
    disciplina = db.relationship('Disciplina', backref='timetables')

    __table_args__ = (
        db.UniqueConstraint('dia', 'hora_inicio', 'hora_fim', 'sala_id', name='unique_dia_horario_sala'),
        db.UniqueConstraint('dia', 'hora_inicio', 'hora_fim', 'professor_id', name='unique_dia_horario_professor'),
    )


class Aluno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    matricula = db.Column(db.String(30), unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)


class Matricula(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetable.id'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    aluno = db.relationship(
        'Aluno',
        backref=db.backref('matriculas', cascade='all, delete-orphan'),
    )
    timetable = db.relationship(
        'Timetable',
        backref=db.backref('matriculas', cascade='all, delete-orphan'),
    )

    __table_args__ = (
        db.UniqueConstraint('aluno_id', 'timetable_id', name='unique_aluno_turma'),
    )


class Presenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    presente = db.Column(db.Boolean, nullable=False, default=False)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetable.id'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    aluno = db.relationship(
        'Aluno',
        backref=db.backref('presencas', cascade='all, delete-orphan'),
    )
    timetable = db.relationship(
        'Timetable',
        backref=db.backref('presencas', cascade='all, delete-orphan'),
    )

    __table_args__ = (
        db.UniqueConstraint('data', 'aluno_id', 'timetable_id', name='unique_presenca_data_aluno_turma'),
    )
