from datetime import time

from app import db
from app.models import Curso, Disciplina, GradeCurricular, GradeCurricularItem, Sala, Timetable, Turma, User


def _seed_grade_base():
    curso = Curso(nome="Engenharia de Software", codigo="ES-AUTO", ativo=True, quantidade_periodos=10)
    db.session.add(curso)
    db.session.flush()

    disciplinas = []
    for idx in range(1, 7):
        disciplina = Disciplina(nome=f"Disciplina Auto {idx}", codigo=f"AUTO{idx:03d}")
        disciplinas.append(disciplina)
    db.session.add_all(disciplinas)
    db.session.flush()

    grade = GradeCurricular(nome="Grade Auto ES", curso_id=curso.id, ativa=True)
    db.session.add(grade)
    db.session.flush()

    for disciplina in disciplinas[:5]:
        db.session.add(GradeCurricularItem(grade_id=grade.id, disciplina_id=disciplina.id, periodo=1))

    turma_m = Turma(
        curso_id=curso.id,
        codigo="ES-M1",
        semestre_letivo="2026.1",
        periodo=1,
        turno="matutino",
        quantidade_alunos=40,
        ativa=True,
    )
    turma_n = Turma(
        curso_id=curso.id,
        codigo="ES-N1",
        semestre_letivo="2026.1",
        periodo=1,
        turno="noturno",
        quantidade_alunos=40,
        ativa=True,
    )
    db.session.add_all([turma_m, turma_n])
    db.session.commit()
    return disciplinas, turma_m, turma_n


def test_replanejar_professores_automatico_recria_quadro(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    professor_antigo = user_factory("prof_antigo", role="professor", password="123456", email="antigo@login.local")
    disciplinas, turma_m, _ = _seed_grade_base()

    sala = Sala(nome="Auto Sala", capacidade=50)
    db.session.add(sala)
    db.session.flush()

    professor_antigo.disciplinas_aptas = [disciplinas[0]]
    db.session.add(
        Timetable(
            dia="Segunda",
            hora_inicio=time(7, 0),
            hora_fim=time(8, 30),
            sala_id=sala.id,
            professor_id=professor_antigo.id,
            disciplina_id=disciplinas[0].id,
            turma_id=turma_m.id,
        )
    )
    db.session.commit()

    login("admin", "Admin1234")
    response = client.post(
        "/professores/replanejar-automatico",
        data={"submit": "1"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Corpo docente replanejado." in response.data

    novos = User.query.filter_by(role="professor").all()
    assert len(novos) == 2
    jornadas = sorted([prof.jornada_turnos for prof in novos])
    assert jornadas == ["matutino_vespertino", "vespertino_noturno"]
    minimo_esperado = min(
        6,
        db.session.query(Disciplina)
        .join(GradeCurricularItem, GradeCurricularItem.disciplina_id == Disciplina.id)
        .join(GradeCurricular, GradeCurricular.id == GradeCurricularItem.grade_id)
        .filter(GradeCurricular.ativa.is_(True))
        .distinct()
        .count(),
    )
    assert all(len(prof.disciplinas_aptas) >= minimo_esperado for prof in novos)

    timetable = Timetable.query.first()
    assert timetable is not None
    assert timetable.professor_id is None
