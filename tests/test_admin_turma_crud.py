from datetime import time

from app import db
from app.models import (
    Curso,
    Disciplina,
    GradeCurricular,
    GradeCurricularItem,
    Sala,
    Timetable,
    Turma,
)


def _setup_course_with_grade():
    curso = Curso(nome="Analise e Desenvolvimento de Sistemas", codigo="ADS", ativo=True, quantidade_periodos=8)
    disciplina = Disciplina(nome="Matematica", codigo="MAT001")
    db.session.add_all([curso, disciplina])
    db.session.flush()

    grade = GradeCurricular(nome="Grade ADS 2026", curso_id=curso.id, ativa=True)
    db.session.add(grade)
    db.session.flush()

    db.session.add(GradeCurricularItem(grade_id=grade.id, disciplina_id=disciplina.id, periodo=1))
    db.session.commit()
    return curso, disciplina


def test_admin_full_turma_crud_flow(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    curso, _ = _setup_course_with_grade()
    login("admin", "Admin1234")

    create_response = client.post(
        "/turma/new",
        data={
            "curso_id": str(curso.id),
            "codigo": "ADS-1N",
            "semestre_letivo": "2026.2",
            "periodo": "1",
            "quantidade_alunos": "40",
        },
        follow_redirects=True,
    )
    assert create_response.status_code == 200
    assert b"Turma criada com sucesso." in create_response.data

    turma = Turma.query.filter_by(curso_id=curso.id, codigo="ADS-1N", semestre_letivo="2026.2").first()
    assert turma is not None
    assert turma.quantidade_alunos == 40

    update_response = client.post(
        f"/turma/edit/{turma.id}",
        data={
            "curso_id": str(curso.id),
            "codigo": "ADS-1T",
            "semestre_letivo": "2026.2",
            "periodo": "1",
            "quantidade_alunos": "35",
        },
        follow_redirects=True,
    )
    assert update_response.status_code == 200
    assert b"Turma editada com sucesso." in update_response.data

    updated_turma = db.session.get(Turma, turma.id)
    assert updated_turma is not None
    assert updated_turma.codigo == "ADS-1T"
    assert updated_turma.quantidade_alunos == 35

    delete_response = client.post(
        f"/turma/delete/{turma.id}",
        data={"submit": "1"},
        follow_redirects=True,
    )
    assert delete_response.status_code == 200
    assert b"Turma deletada com sucesso." in delete_response.data
    assert db.session.get(Turma, turma.id) is None


def test_admin_blocks_turma_delete_with_timetable(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    professor = user_factory("prof_turma", role="professor", password="123456", email="prof_turma@login.local")
    curso, disciplina = _setup_course_with_grade()
    sala = Sala(nome="Sala Turma", capacidade=30)
    turma = Turma(
        curso_id=curso.id,
        codigo="ADS-2N",
        semestre_letivo="2026.2",
        periodo=1,
        quantidade_alunos=25,
    )
    db.session.add_all([sala, disciplina, turma])
    db.session.commit()

    db.session.add(
        Timetable(
            dia="Segunda",
            hora_inicio=time(7, 30),
            hora_fim=time(9, 0),
            sala_id=sala.id,
            professor_id=professor.id,
            disciplina_id=disciplina.id,
            turma_id=turma.id,
        )
    )
    db.session.commit()

    login("admin", "Admin1234")
    response = client.post(
        f"/turma/delete/{turma.id}",
        data={"submit": "1"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Nao e possivel deletar turma com alocacoes vinculadas." in response.data
    assert db.session.get(Turma, turma.id) is not None
