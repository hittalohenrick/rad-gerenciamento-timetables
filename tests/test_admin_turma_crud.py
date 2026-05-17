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
    db.session.add(Sala(nome="Sala Base CRUD", capacidade=50))
    db.session.commit()
    login("admin", "Admin1234")

    create_response = client.post(
        "/turma/new",
        data={
            "curso_id": str(curso.id),
            "codigo": "ADS-1N",
            "semestre_letivo": "2026.2",
            "periodo": "1",
            "turno": "noturno",
            "quantidade_alunos": "40",
        },
        follow_redirects=True,
    )
    assert create_response.status_code == 200
    assert b"Turma criada com sucesso." in create_response.data

    turma = Turma.query.filter_by(curso_id=curso.id, codigo="ADS-1N", semestre_letivo="2026.2").first()
    assert turma is not None
    assert turma.turno == "noturno"
    assert turma.quantidade_alunos == 40

    update_response = client.post(
        f"/turma/edit/{turma.id}",
        data={
            "curso_id": str(curso.id),
            "codigo": "ADS-1T",
            "semestre_letivo": "2026.2",
            "periodo": "1",
            "turno": "vespertino",
            "quantidade_alunos": "35",
        },
        follow_redirects=True,
    )
    assert update_response.status_code == 200
    assert b"Turma editada com sucesso." in update_response.data

    updated_turma = db.session.get(Turma, turma.id)
    assert updated_turma is not None
    assert updated_turma.codigo == "ADS-1T"
    assert updated_turma.turno == "vespertino"
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


def test_turmas_filter_sem_quadro_and_dashboard_link(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    professor = user_factory("prof_filtro", role="professor", password="123456", email="prof_filtro@login.local")
    curso, disciplina = _setup_course_with_grade()
    sala = Sala(nome="Sala Filtro", capacidade=35)
    turma_sem_quadro = Turma(
        curso_id=curso.id,
        codigo="ADS-SQ",
        semestre_letivo="2026.2",
        periodo=1,
        turno="noturno",
        quantidade_alunos=30,
    )
    turma_com_quadro = Turma(
        curso_id=curso.id,
        codigo="ADS-CQ",
        semestre_letivo="2026.2",
        periodo=1,
        turno="noturno",
        quantidade_alunos=30,
    )
    db.session.add_all([sala, turma_sem_quadro, turma_com_quadro])
    db.session.flush()
    db.session.add(
        Timetable(
            dia="Segunda",
            hora_inicio=time(18, 0),
            hora_fim=time(19, 30),
            sala_id=sala.id,
            professor_id=professor.id,
            disciplina_id=disciplina.id,
            turma_id=turma_com_quadro.id,
        )
    )
    db.session.commit()

    login("admin", "Admin1234")

    dashboard = client.get("/admin")
    assert dashboard.status_code == 200
    assert b"/turmas?f=sem_quadro" in dashboard.data

    filtered = client.get("/turmas?f=sem_quadro")
    assert filtered.status_code == 200
    assert b"Exibindo somente turmas sem quadro gerado." in filtered.data
    assert b"ADS-SQ" in filtered.data
    assert b"ADS-CQ" not in filtered.data


def test_admin_rejects_turma_capacity_above_50(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    curso, _ = _setup_course_with_grade()
    login("admin", "Admin1234")

    response = client.post(
        "/turma/new",
        data={
            "curso_id": str(curso.id),
            "codigo": "ADS-OVER",
            "semestre_letivo": "2026.2",
            "periodo": "1",
            "turno": "noturno",
            "quantidade_alunos": "51",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"A capacidade da turma deve estar entre 0 e 50 alunos." in response.data
    turma = Turma.query.filter_by(codigo="ADS-OVER", semestre_letivo="2026.2").first()
    assert turma is None


def test_admin_allows_turma_capacity_zero(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    curso, _ = _setup_course_with_grade()
    db.session.add(Sala(nome="Sala Zero Cap", capacidade=50))
    db.session.commit()
    login("admin", "Admin1234")

    response = client.post(
        "/turma/new",
        data={
            "curso_id": str(curso.id),
            "codigo": "ADS-ZERO",
            "semestre_letivo": "2026.2",
            "periodo": "1",
            "turno": "noturno",
            "quantidade_alunos": "0",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Turma criada com sucesso." in response.data
    turma = Turma.query.filter_by(codigo="ADS-ZERO", semestre_letivo="2026.2").first()
    assert turma is not None
    assert turma.quantidade_alunos == 0


def test_admin_blocks_new_turma_when_turno_capacity_is_full(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    curso, _ = _setup_course_with_grade()
    db.session.add(Sala(nome="Sala Limite", capacidade=50))
    db.session.add_all(
        [
            Turma(
                curso_id=curso.id,
                codigo="ADS-N-LIM-1",
                semestre_letivo="2026.2",
                periodo=1,
                turno="noturno",
                quantidade_alunos=40,
            ),
            Turma(
                curso_id=curso.id,
                codigo="ADS-N-LIM-2",
                semestre_letivo="2026.2",
                periodo=2,
                turno="noturno",
                quantidade_alunos=40,
            ),
        ]
    )
    db.session.commit()

    login("admin", "Admin1234")

    response = client.post(
        "/turma/new",
        data={
            "curso_id": str(curso.id),
            "codigo": "ADS-N-LIM-3",
            "semestre_letivo": "2026.2",
            "periodo": "3",
            "turno": "noturno",
            "quantidade_alunos": "40",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"limite de capacidade atingido" in response.data
    turma = Turma.query.filter_by(codigo="ADS-N-LIM-3", semestre_letivo="2026.2").first()
    assert turma is None
