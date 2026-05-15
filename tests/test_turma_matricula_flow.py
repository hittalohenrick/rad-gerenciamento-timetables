from app import db
from app.models import Aluno, Curso, Matricula, Turma


def _setup_turma(quantidade_alunos=2):
    curso = Curso(nome="Engenharia de Software", codigo="ES", ativo=True, quantidade_periodos=10)
    turma = Turma(
        curso=curso,
        codigo="ES-1N",
        semestre_letivo="2026.1",
        periodo=1,
        turno="noturno",
        quantidade_alunos=quantidade_alunos,
    )
    db.session.add_all([curso, turma])
    db.session.commit()
    return turma


def test_turma_alunos_allows_enrollment_from_turma_screen(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    turma = _setup_turma(quantidade_alunos=2)
    aluno = Aluno(nome="Aluno Turma", matricula="T001")
    db.session.add(aluno)
    db.session.commit()

    login("admin", "Admin1234")

    response_post = client.post(
        f"/turma/{turma.id}/alunos",
        data={"aluno_id": str(aluno.id), "submit": "1"},
        follow_redirects=True,
    )

    assert response_post.status_code == 200
    assert b"Aluno alocado com sucesso." in response_post.data
    assert Matricula.query.filter_by(turma_id=turma.id, aluno_id=aluno.id).count() == 1

    response_get = client.get(f"/turma/{turma.id}/alunos")
    assert response_get.status_code == 200
    assert b"Aluno Turma" in response_get.data


def test_turma_alunos_blocks_when_capacity_is_reached(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    turma = _setup_turma(quantidade_alunos=1)

    aluno_1 = Aluno(nome="Aluno 1", matricula="C001")
    aluno_2 = Aluno(nome="Aluno 2", matricula="C002")
    db.session.add_all([aluno_1, aluno_2])
    db.session.flush()
    db.session.add(Matricula(aluno_id=aluno_1.id, turma_id=turma.id))
    db.session.commit()

    login("admin", "Admin1234")

    response_post = client.post(
        f"/turma/{turma.id}/alunos",
        data={"aluno_id": str(aluno_2.id), "submit": "1"},
        follow_redirects=True,
    )

    assert response_post.status_code == 200
    assert b"capacidade prevista da turma foi atingida" in response_post.data
    assert Matricula.query.filter_by(turma_id=turma.id).count() == 1


def test_turma_alunos_allows_delete_enrollment(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    turma = _setup_turma(quantidade_alunos=2)

    aluno = Aluno(nome="Aluno Remover", matricula="R001")
    db.session.add(aluno)
    db.session.flush()
    matricula = Matricula(aluno_id=aluno.id, turma_id=turma.id)
    db.session.add(matricula)
    db.session.commit()

    login("admin", "Admin1234")

    response_post = client.post(
        f"/turma/{turma.id}/matricula/{matricula.id}/delete",
        data={"submit": "1"},
        follow_redirects=True,
    )

    assert response_post.status_code == 200
    assert b"Alocacao removida com sucesso." in response_post.data
    assert db.session.get(Matricula, matricula.id) is None


def test_matricula_blocks_second_turma_in_same_semestre(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")

    curso = Curso(nome="Ciencia da Computacao", codigo="CC", ativo=True, quantidade_periodos=8)
    turma_a = Turma(
        curso=curso,
        codigo="CC-1A",
        semestre_letivo="2026.1",
        periodo=1,
        turno="noturno",
        quantidade_alunos=40,
    )
    turma_b = Turma(
        curso=curso,
        codigo="CC-1B",
        semestre_letivo="2026.1",
        periodo=1,
        turno="noturno",
        quantidade_alunos=40,
    )
    aluno = Aluno(nome="Aluno Semestre", matricula="SEM001")
    db.session.add_all([curso, turma_a, turma_b, aluno])
    db.session.commit()

    login("admin", "Admin1234")

    first = client.post(
        "/matricula/new",
        data={"aluno_id": str(aluno.id), "turma_id": str(turma_a.id)},
        follow_redirects=True,
    )
    assert first.status_code == 200
    assert b"Aluno alocado com sucesso." in first.data

    second = client.post(
        "/matricula/new",
        data={"aluno_id": str(aluno.id), "turma_id": str(turma_b.id)},
        follow_redirects=True,
    )
    assert second.status_code == 200
    assert b"outra turma no mesmo semestre letivo" in second.data
    assert Matricula.query.filter_by(aluno_id=aluno.id).count() == 1


def test_turma_alunos_hides_students_already_enrolled_in_same_semestre(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")

    curso = Curso(nome="Analise e Desenvolvimento de Sistemas", codigo="ADS", ativo=True, quantidade_periodos=8)
    turma_a = Turma(
        curso=curso,
        codigo="ADS-1A",
        semestre_letivo="2026.1",
        periodo=1,
        turno="noturno",
        quantidade_alunos=40,
    )
    turma_b = Turma(
        curso=curso,
        codigo="ADS-1B",
        semestre_letivo="2026.1",
        periodo=1,
        turno="noturno",
        quantidade_alunos=40,
    )
    aluno_bloqueado = Aluno(nome="Aluno Bloqueado", matricula="BLQ001")
    aluno_livre = Aluno(nome="Aluno Livre", matricula="LVR001")
    db.session.add_all([curso, turma_a, turma_b, aluno_bloqueado, aluno_livre])
    db.session.flush()
    db.session.add(Matricula(aluno_id=aluno_bloqueado.id, turma_id=turma_a.id))
    db.session.commit()

    login("admin", "Admin1234")

    page = client.get(f"/turma/{turma_b.id}/alunos")
    assert page.status_code == 200
    assert b"Aluno Bloqueado" not in page.data
    assert b"Aluno Livre" in page.data
