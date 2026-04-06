from flask import render_template, redirect, url_for, flash, Blueprint, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.forms import LoginForm, RegistrationForm, ProfessorForm, SalaForm, DisciplinaForm, TimetableForm
from app.models import User, Sala, Disciplina, Timetable
from datetime import datetime
from sqlalchemy.orm import joinedload
import random
import string

bp = Blueprint('main', __name__)

def times_overlap(start1, end1, start2, end2):
    """Verifica se dois intervalos de tempo se sobrepõem."""
    return max(start1, start2) < min(end1, end2)

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
    professores = User.query.filter_by(role='professor').all()
    disciplinas = Disciplina.query.all()
    timetables = Timetable.query.options(
        joinedload(Timetable.sala),
        joinedload(Timetable.professor),
        joinedload(Timetable.disciplina)
    ).all()
    return render_template('admin_dashboard.html', salas=salas, professores=professores, disciplinas=disciplinas, timetables=timetables)

@bp.route('/horarios')
@login_required
def horarios():
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    timetables = Timetable.query.options(
        joinedload(Timetable.sala),
        joinedload(Timetable.professor),
        joinedload(Timetable.disciplina)
    ).all()
    return render_template('horarios.html', timetables=timetables)

@bp.route('/professor')
@login_required
def professor_dashboard():
    timetables = Timetable.query.filter_by(professor_id=current_user.id).options(
        joinedload(Timetable.sala),
        joinedload(Timetable.disciplina)
    ).all()
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

@bp.route('/sala/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_sala(id):
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    sala = Sala.query.get_or_404(id)
    form = SalaForm()
    if form.validate_on_submit():
        sala.nome = form.nome.data
        sala.capacidade = form.capacidade.data
        db.session.commit()
        flash('Sala editada com sucesso')
        return redirect(url_for('main.salas'))
    elif request.method == 'GET':
        form.nome.data = sala.nome
        form.capacidade.data = sala.capacidade
    return render_template('sala_form.html', form=form, title='Editar Sala')

@bp.route('/sala/delete/<int:id>')
@login_required
def delete_sala(id):
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    sala = Sala.query.get_or_404(id)
    db.session.delete(sala)
    db.session.commit()
    flash('Sala deletada com sucesso')
    return redirect(url_for('main.salas'))

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
        # Gerar código automático
        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        while Disciplina.query.filter_by(codigo=codigo).first():
            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        disciplina = Disciplina(nome=form.nome.data, codigo=codigo)
        db.session.add(disciplina)
        db.session.commit()
        flash('Disciplina criada com sucesso')
        return redirect(url_for('main.disciplinas'))
    return render_template('disciplina_form.html', form=form, title='Nova Disciplina')

@bp.route('/disciplina/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_disciplina(id):
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    disciplina = Disciplina.query.get_or_404(id)
    form = DisciplinaForm()
    if form.validate_on_submit():
        disciplina.nome = form.nome.data
        db.session.commit()
        flash('Disciplina editada com sucesso')
        return redirect(url_for('main.disciplinas'))
    elif request.method == 'GET':
        form.nome.data = disciplina.nome
    return render_template('disciplina_form.html', form=form, title='Editar Disciplina')

@bp.route('/disciplina/delete/<int:id>')
@login_required
def delete_disciplina(id):
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    disciplina = Disciplina.query.get_or_404(id)
    db.session.delete(disciplina)
    db.session.commit()
    flash('Disciplina deletada com sucesso')
    return redirect(url_for('main.disciplinas'))

# CRUD Professores
@bp.route('/professores')
@login_required
def professores():
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    professores = User.query.filter_by(role='professor').all()
    return render_template('professores.html', professores=professores)

@bp.route('/professor/new', methods=['GET', 'POST'])
@login_required
def new_professor():
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    form = ProfessorForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role='professor')
        # Senha padrão gerada (pode ser alterada após criação ou por outro procedimento seguro)
        user.set_password('professor123')
        db.session.add(user)
        db.session.commit()
        flash('Professor registrado com sucesso (senha padrão: professor123)')
        return redirect(url_for('main.professores'))
    return render_template('register.html', title='Novo Professor', form=form)

@bp.route('/professor/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_professor(id):
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    professor = User.query.get_or_404(id)
    if professor.role != 'professor':
        flash('Usuário não é professor')
        return redirect(url_for('main.professores'))
    form = ProfessorForm()
    if form.validate_on_submit():
        professor.username = form.username.data
        professor.email = form.email.data
        db.session.commit()
        flash('Professor editado com sucesso')
        return redirect(url_for('main.professores'))
    elif request.method == 'GET':
        form.username.data = professor.username
        form.email.data = professor.email
    return render_template('register.html', title='Editar Professor', form=form)

@bp.route('/professor/delete/<int:id>')
@login_required
def delete_professor(id):
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    professor = User.query.get_or_404(id)
    if professor.role != 'professor':
        flash('Usuário não é professor')
        return redirect(url_for('main.professores'))
    db.session.delete(professor)
    db.session.commit()
    flash('Professor deletado com sucesso')
    return redirect(url_for('main.professores'))

@bp.route('/timetable/new', methods=['GET', 'POST'])
@login_required
def new_timetable():
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    form = TimetableForm()
    form.sala_id.choices = [(s.id, s.nome) for s in Sala.query.all()]
    form.professor_id.choices = [(p.id, p.username) for p in User.query.filter_by(role='professor').all()]
    form.disciplina_id.choices = [(d.id, d.nome) for d in Disciplina.query.all()]
    if form.validate_on_submit():
        hora_inicio = datetime.strptime(form.hora_inicio.data, '%H:%M').time()
        hora_fim = datetime.strptime(form.hora_fim.data, '%H:%M').time()

        # Verificar conflito de sala
        existing_sala = Timetable.query.filter_by(
            dia=form.dia.data,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
            sala_id=form.sala_id.data
        ).first()
        if existing_sala:
            flash('Conflito: Horário e sala já alocados')
            return redirect(url_for('main.new_timetable'))

        # Verificar conflito de professor
        timetables_professor = Timetable.query.filter_by(professor_id=form.professor_id.data).all()

        for tt in timetables_professor:
            if tt.dia == form.dia.data:
                if times_overlap(tt.hora_inicio, tt.hora_fim, hora_inicio, hora_fim):
                    flash('Conflito: Professor já alocado em outro horário que se sobrepõe neste dia')
                    return redirect(url_for('main.new_timetable'))

        timetable = Timetable(
            dia=form.dia.data,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
            sala_id=form.sala_id.data,
            professor_id=form.professor_id.data,
            disciplina_id=form.disciplina_id.data
        )
        db.session.add(timetable)
        db.session.commit()
        flash('Alocação criada com sucesso')
        return redirect(url_for('main.admin_dashboard'))
    return render_template('timetable_form.html', form=form, title='Nova Alocação')

@bp.route('/timetable/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_timetable(id):
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    timetable = Timetable.query.get_or_404(id)
    form = TimetableForm()
    form.sala_id.choices = [(s.id, s.nome) for s in Sala.query.all()]
    form.professor_id.choices = [(p.id, p.username) for p in User.query.filter_by(role='professor').all()]
    form.disciplina_id.choices = [(d.id, d.nome) for d in Disciplina.query.all()]
    if form.validate_on_submit():
        hora_inicio = datetime.strptime(form.hora_inicio.data, '%H:%M').time()
        hora_fim = datetime.strptime(form.hora_fim.data, '%H:%M').time()

        # Verificar conflito de sala (exceto o atual)
        existing_sala = Timetable.query.filter(
            Timetable.dia == form.dia.data,
            Timetable.hora_inicio == hora_inicio,
            Timetable.hora_fim == hora_fim,
            Timetable.sala_id == form.sala_id.data,
            Timetable.id != id
        ).first()
        if existing_sala:
            flash('Conflito: Horário e sala já alocados')
            return redirect(url_for('main.edit_timetable', id=id))
        
        # Verificar conflito de professor
        timetables_professor = Timetable.query.filter(
            Timetable.professor_id == form.professor_id.data,
            Timetable.id != id
        ).all()
        
        for tt in timetables_professor:
            if tt.dia == form.dia.data:
                if times_overlap(tt.hora_inicio, tt.hora_fim, hora_inicio, hora_fim):
                    flash('Conflito: Professor já alocado em outro horário que se sobrepõe neste dia')
                    return redirect(url_for('main.edit_timetable', id=id))
        
        timetable.dia = form.dia.data
        timetable.hora_inicio = hora_inicio
        timetable.hora_fim = hora_fim
        timetable.sala_id = form.sala_id.data
        timetable.professor_id = form.professor_id.data
        timetable.disciplina_id = form.disciplina_id.data
        db.session.commit()
        flash('Alocação editada com sucesso')
        return redirect(url_for('main.admin_dashboard'))
    elif request.method == 'GET':
        form.dia.data = timetable.dia
        form.hora_inicio.data = timetable.hora_inicio.strftime('%H:%M')
        form.hora_fim.data = timetable.hora_fim.strftime('%H:%M')
        form.sala_id.data = timetable.sala_id
        form.professor_id.data = timetable.professor_id
        form.disciplina_id.data = timetable.disciplina_id
    return render_template('timetable_form.html', form=form, title='Editar Alocação')

@bp.route('/timetable/delete/<int:id>')
@login_required
def delete_timetable(id):
    if not current_user.is_admin():
        flash('Acesso negado')
        return redirect(url_for('main.index'))
    timetable = Timetable.query.get_or_404(id)
    db.session.delete(timetable)
    db.session.commit()
    flash('Alocação deletada com sucesso')
    return redirect(url_for('main.admin_dashboard'))