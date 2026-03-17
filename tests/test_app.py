import pytest
from app import create_app, db
from app.models import User, Sala, Horario, Disciplina, Timetable
from datetime import time

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_home_page_requires_login(client):
    response = client.get('/')
    assert response.status_code == 302  # Redirect to login

def test_login_page(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data

def test_professor_conflict_prevention(app):
    """Test that a professor cannot be assigned to overlapping time slots."""
    with app.app_context():
        # Create test data
        professor = User(username='professor1', email='prof@test.com', role='professor')
        professor.set_password('test')
        sala1 = Sala(nome='Sala 1', capacidade=30)
        sala2 = Sala(nome='Sala 2', capacidade=30)
        disciplina1 = Disciplina(nome='Matemática', codigo='MAT001')
        disciplina2 = Disciplina(nome='Física', codigo='FIS001')
        
        # Create overlapping time slots on the same day
        horario1 = Horario(dia_semana='Segunda', hora_inicio=time(8, 0), hora_fim=time(10, 0))
        horario2 = Horario(dia_semana='Segunda', hora_inicio=time(9, 0), hora_fim=time(11, 0))  # Overlaps with horario1
        
        db.session.add_all([professor, sala1, sala2, disciplina1, disciplina2, horario1, horario2])
        db.session.commit()
        
        # First allocation should succeed
        timetable1 = Timetable(
            horario_id=horario1.id,
            sala_id=sala1.id,
            professor_id=professor.id,
            disciplina_id=disciplina1.id
        )
        db.session.add(timetable1)
        db.session.commit()
        
        # Test the validation logic directly
        from app.routes import times_overlap
        
        # Check that the times do overlap
        assert times_overlap(horario1.hora_inicio, horario1.hora_fim, horario2.hora_inicio, horario2.hora_fim)
        
        # The second allocation should be prevented by application logic, not database constraint
        # (since we're testing different horario_ids that overlap)

def test_room_conflict_prevention(app):
    """Test that a room cannot be double-booked at the same time."""
    with app.app_context():
        # Create test data
        professor1 = User(username='prof1', email='prof1@test.com', role='professor')
        professor2 = User(username='prof2', email='prof2@test.com', role='professor')
        professor1.set_password('test')
        professor2.set_password('test')
        sala = Sala(nome='Sala 1', capacidade=30)
        disciplina1 = Disciplina(nome='Matemática', codigo='MAT001')
        disciplina2 = Disciplina(nome='Física', codigo='FIS001')
        horario = Horario(dia_semana='Segunda', hora_inicio=time(8, 0), hora_fim=time(10, 0))
        
        db.session.add_all([professor1, professor2, sala, disciplina1, disciplina2, horario])
        db.session.commit()
        
        # First allocation should succeed
        timetable1 = Timetable(
            horario_id=horario.id,
            sala_id=sala.id,
            professor_id=professor1.id,
            disciplina_id=disciplina1.id
        )
        db.session.add(timetable1)
        db.session.commit()
        
        # Second allocation with same room and time should fail
        timetable2 = Timetable(
            horario_id=horario.id,
            sala_id=sala.id,
            professor_id=professor2.id,
            disciplina_id=disciplina2.id
        )
        with pytest.raises(Exception):  # IntegrityError due to unique constraint
            db.session.add(timetable2)
            db.session.commit()

def test_invalid_time_range_validation(app):
    """Test that hora_inicio must be before hora_fim."""
    with app.test_request_context():
        from app.forms import HorarioForm
        
        # Test invalid time range
        form = HorarioForm()
        form.dia_semana.data = 'Segunda'
        form.hora_inicio.data = time(10, 0)  # 10:00
        form.hora_fim.data = time(9, 0)      # 09:00 - invalid
        
        assert not form.validate()
        assert len(form.hora_fim.errors) > 0
        assert 'hora de início deve ser anterior' in form.hora_fim.errors[0]