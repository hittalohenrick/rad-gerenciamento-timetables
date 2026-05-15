from datetime import UTC, datetime

from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash


def utc_now():
    return datetime.now(UTC)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


professor_disciplina = db.Table(
    "professor_disciplina",
    db.Column("professor_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("disciplina_id", db.Integer, db.ForeignKey("disciplina.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='professor')  # 'admin' or 'professor'
    disciplinas_aptas = db.relationship(
        "Disciplina",
        secondary=professor_disciplina,
        lazy="select",
        backref=db.backref("professores_aptos", lazy="select"),
    )

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


class Curso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    codigo = db.Column(db.String(20), nullable=False, unique=True)
    quantidade_periodos = db.Column(db.Integer, nullable=False, default=8)
    ativo = db.Column(db.Boolean, nullable=False, default=True)


class Disciplina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    codigo = db.Column(db.String(20), unique=True, nullable=False)


class GradeCurricular(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey("curso.id"), nullable=False)
    ativa = db.Column(db.Boolean, nullable=False, default=True)

    curso = db.relationship("Curso", backref=db.backref("grades_curriculares", lazy="select"))

    __table_args__ = (
        db.UniqueConstraint("curso_id", "nome", name="unique_grade_por_curso"),
    )


class GradeCurricularItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    grade_id = db.Column(db.Integer, db.ForeignKey("grade_curricular.id"), nullable=False)
    disciplina_id = db.Column(db.Integer, db.ForeignKey("disciplina.id"), nullable=False)
    periodo = db.Column(db.Integer, nullable=False)

    grade = db.relationship(
        "GradeCurricular",
        backref=db.backref("itens", cascade="all, delete-orphan", lazy="select"),
    )
    disciplina = db.relationship("Disciplina", backref=db.backref("grade_itens", lazy="select"))

    __table_args__ = (
        db.UniqueConstraint("grade_id", "disciplina_id", name="unique_disciplina_por_grade"),
    )


class Turma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey("curso.id"), nullable=False)
    codigo = db.Column(db.String(30), nullable=False)
    semestre_letivo = db.Column(db.String(20), nullable=False)
    periodo = db.Column(db.Integer, nullable=False)
    turno = db.Column(db.String(20), nullable=False, default="noturno")
    quantidade_alunos = db.Column(db.Integer, nullable=True)
    ativa = db.Column(db.Boolean, nullable=False, default=True)

    curso = db.relationship("Curso", backref=db.backref("turmas", lazy="select"))

    @property
    def nome_exibicao(self):
        return f"{self.curso.nome if self.curso else 'Curso'} {self.codigo} ({self.semestre_letivo})"

    __table_args__ = (
        db.UniqueConstraint("curso_id", "codigo", "semestre_letivo", name="unique_turma_codigo_semestre"),
    )


class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dia = db.Column(db.String(20), nullable=False)  # e.g., 'Segunda', 'Terça'
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fim = db.Column(db.Time, nullable=False)
    sala_id = db.Column(db.Integer, db.ForeignKey('sala.id'), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplina.id'), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey("turma.id"), nullable=False)

    sala = db.relationship('Sala', backref='timetables')
    professor = db.relationship('User', backref='timetables')
    disciplina = db.relationship('Disciplina', backref='timetables')
    turma = db.relationship('Turma', backref='timetables')

    __table_args__ = (
        db.UniqueConstraint('dia', 'hora_inicio', 'hora_fim', 'sala_id', name='unique_dia_horario_sala'),
        db.UniqueConstraint('dia', 'hora_inicio', 'hora_fim', 'professor_id', name='unique_dia_horario_professor'),
        db.UniqueConstraint('dia', 'hora_inicio', 'hora_fim', 'turma_id', name='unique_dia_horario_turma'),
    )


class Aluno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    matricula = db.Column(db.String(30), unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)


class Matricula(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey('turma.id'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    aluno = db.relationship(
        'Aluno',
        backref=db.backref('matriculas', cascade='all, delete-orphan'),
    )
    turma = db.relationship(
        'Turma',
        backref=db.backref('matriculas', cascade='all, delete-orphan'),
    )

    __table_args__ = (
        db.UniqueConstraint('aluno_id', 'turma_id', name='unique_aluno_turma'),
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
