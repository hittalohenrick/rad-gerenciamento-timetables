from flask import render_template, redirect, url_for, flash, Blueprint
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.forms import LoginForm, RegistrationForm, SalaForm, HorarioForm, DisciplinaForm, TimetableForm
from app.models import User, Sala, Horario, Disciplina, Timetable

bp = Blueprint('main', __name__)

@bp.route('/')
@login_required
def index():
    if current_user.is_admin():
        return redirect(url_for('main.admin_dashboard'))
    else:
        return redirect(url_for('main.professor_dashboard'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuário ou senha inválidos')
            return redirect(url_for('main.login'))
        login_user(user)
        return redirect(url_for('main.index'))
    return render_template('login.html', title='Login', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role=form.role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Usuário registrado com sucesso')
        return redirect(url_for('main.admin_dashboard'))
    return render_template('register.html', title='Registrar Usuário', form=form)

@bp.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    salas = Sala.query.all()
    horarios = Horario.query.all()
    professores = User.query.filter_by(role='professor').all()
    disciplinas = Disciplina.query.all()
    timetables = Timetable.query.all()
    return render_template('admin_dashboard.html', salas=salas, horarios=horarios, professores=professores, disciplinas=disciplinas, timetables=timetables)

@bp.route('/professor')
@login_required
def professor_dashboard():
    timetables = Timetable.query.filter_by(professor_id=current_user.id).all()
    return render_template('professor_dashboard.html', timetables=timetables)

# CRUD Salas
@bp.route('/salas')
@login_required
def salas():
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    salas = Sala.query.all()
    return render_template('salas.html', salas=salas)

@bp.route('/sala/new', methods=['GET', 'POST'])
@login_required
def new_sala():
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    form = SalaForm()
    if form.validate_on_submit():
        sala = Sala(nome=form.nome.data, capacidade=form.capacidade.data)
        db.session.add(sala)
        db.session.commit()
        flash('Sala criada com sucesso')
        return redirect(url_for('main.salas'))
    return render_template('sala_form.html', form=form, title='Nova Sala')

# CRUD Horarios
@bp.route('/horarios')
@login_required
def horarios():
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    horarios = Horario.query.all()
    return render_template('horarios.html', horarios=horarios)

@bp.route('/horario/new', methods=['GET', 'POST'])
@login_required
def new_horario():
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    form = HorarioForm()
    if form.validate_on_submit():
        horario = Horario(dia_semana=form.dia_semana.data, hora_inicio=form.hora_inicio.data, hora_fim=form.hora_fim.data)
        db.session.add(horario)
        db.session.commit()
        flash('Horário criado com sucesso')
        return redirect(url_for('main.horarios'))
    return render_template('horario_form.html', form=form, title='Novo Horário')

# CRUD Disciplinas
@bp.route('/disciplinas')
@login_required
def disciplinas():
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    disciplinas = Disciplina.query.all()
    return render_template('disciplinas.html', disciplinas=disciplinas)

@bp.route('/disciplina/new', methods=['GET', 'POST'])
@login_required
def new_disciplina():
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    form = DisciplinaForm()
    if form.validate_on_submit():
        disciplina = Disciplina(nome=form.nome.data, codigo=form.codigo.data)
        db.session.add(disciplina)
        db.session.commit()
        flash('Disciplina criada com sucesso')
        return redirect(url_for('main.disciplinas'))
    return render_template('disciplina_form.html', form=form, title='Nova Disciplina')

# CRUD Professores
@bp.route('/professores')
@login_required
def professores():
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    professores = User.query.filter_by(role='professor').all()
    return render_template('professores.html', professores=professores)

@bp.route('/timetable/new', methods=['GET', 'POST'])
@login_required
def new_timetable():
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    form = TimetableForm()
    form.horario_id.choices = [(h.id, f"{h.dia_semana} {h.hora_inicio}-{h.hora_fim}") for h in Horario.query.all()]
    form.sala_id.choices = [(s.id, s.nome) for s in Sala.query.all()]
    form.professor_id.choices = [(p.id, p.username) for p in User.query.filter_by(role='professor').all()]
    form.disciplina_id.choices = [(d.id, d.nome) for d in Disciplina.query.all()]
    if form.validate_on_submit():
        # Verificar conflito
        existing = Timetable.query.filter_by(horario_id=form.horario_id.data, sala_id=form.sala_id.data).first()
        if existing:
            flash('Conflito: Horário e sala já alocados')
            return redirect(url_for('main.new_timetable'))
        timetable = Timetable(
            horario_id=form.horario_id.data,
            sala_id=form.sala_id.data,
            professor_id=form.professor_id.data,
            disciplina_id=form.disciplina_id.data
        )
        db.session.add(timetable)
        db.session.commit()
        flash('Alocação criada com sucesso')
        return redirect(url_for('main.admin_dashboard'))
    return render_template('timetable_form.html', form=form, title='Nova Alocação')