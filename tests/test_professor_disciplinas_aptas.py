import re

from app import db
from app.models import Disciplina, User


def _seed_disciplinas():
    disciplinas = [
        Disciplina(nome="Algoritmos", codigo="DISC-A"),
        Disciplina(nome="Banco de Dados", codigo="DISC-B"),
        Disciplina(nome="Redes", codigo="DISC-C"),
    ]
    db.session.add_all(disciplinas)
    db.session.commit()
    return disciplinas


def _assert_checkbox_checked(html: str, disciplina_id: int):
    pattern = rf'<input(?=[^>]*name="disciplinas_ids")(?=[^>]*value="{disciplina_id}")(?=[^>]*checked)[^>]*>'
    assert re.search(pattern, html), f"Disciplina {disciplina_id} deveria estar marcada"


def _assert_checkbox_unchecked(html: str, disciplina_id: int):
    pattern = rf'<input(?=[^>]*name="disciplinas_ids")(?=[^>]*value="{disciplina_id}")[^>]*>'
    match = re.search(pattern, html)
    assert match, f"Checkbox da disciplina {disciplina_id} nao encontrado"
    assert "checked" not in match.group(0), f"Disciplina {disciplina_id} nao deveria estar marcada"


def test_new_professor_allows_multiple_disciplinas(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    disciplinas = _seed_disciplinas()

    login("admin", "Admin1234")
    response = client.post(
        "/professor/new",
        data={
            "username": "prof_multi",
            "password": "123456",
            "password2": "123456",
            "disciplinas_ids": [str(disciplinas[0].id), str(disciplinas[1].id)],
            "submit": "1",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Professor registrado com sucesso." in response.data

    professor = User.query.filter_by(username="prof_multi").first()
    assert professor is not None
    assert {disc.id for disc in professor.disciplinas_aptas} == {disciplinas[0].id, disciplinas[1].id}


def test_edit_professor_preselects_existing_disciplinas(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    disciplinas = _seed_disciplinas()

    professor = user_factory("prof_edit", role="professor", password="123456", email="prof_edit@login.local")
    professor.disciplinas_aptas = [disciplinas[0], disciplinas[1]]
    db.session.commit()

    login("admin", "Admin1234")
    response = client.get(f"/professor/edit/{professor.id}")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    _assert_checkbox_checked(html, disciplinas[0].id)
    _assert_checkbox_checked(html, disciplinas[1].id)
    _assert_checkbox_unchecked(html, disciplinas[2].id)


def test_edit_professor_can_append_new_disciplinas(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    disciplinas = _seed_disciplinas()

    professor = user_factory("prof_append", role="professor", password="123456", email="prof_append@login.local")
    professor.disciplinas_aptas = [disciplinas[0], disciplinas[1]]
    db.session.commit()

    login("admin", "Admin1234")
    response = client.post(
        f"/professor/edit/{professor.id}",
        data={
            "username": "prof_append",
            "disciplinas_ids": [str(disciplinas[0].id), str(disciplinas[1].id), str(disciplinas[2].id)],
            "submit": "1",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Professor editado com sucesso." in response.data

    updated = db.session.get(User, professor.id)
    assert updated is not None
    assert {disc.id for disc in updated.disciplinas_aptas} == {
        disciplinas[0].id,
        disciplinas[1].id,
        disciplinas[2].id,
    }
