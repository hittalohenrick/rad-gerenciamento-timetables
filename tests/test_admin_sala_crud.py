from app import db
from app.models import Sala


def test_admin_full_sala_crud_flow(client, login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")
    login("admin", "Admin1234")

    create_response = client.post(
        "/sala/new",
        data={"nome": "Lab 01", "capacidade": "30"},
        follow_redirects=True,
    )
    assert create_response.status_code == 200
    assert b"Sala criada com sucesso." in create_response.data

    sala = Sala.query.filter_by(nome="Lab 01").first()
    assert sala is not None
    assert sala.capacidade == 30

    update_response = client.post(
        f"/sala/edit/{sala.id}",
        data={"nome": "Lab 02", "capacidade": "40"},
        follow_redirects=True,
    )
    assert update_response.status_code == 200
    assert b"Sala editada com sucesso." in update_response.data

    updated_sala = db.session.get(Sala, sala.id)
    assert updated_sala is not None
    assert updated_sala.nome == "Lab 02"
    assert updated_sala.capacidade == 40

    delete_response = client.post(
        f"/sala/delete/{sala.id}",
        data={"submit": "1"},
        follow_redirects=True,
    )
    assert delete_response.status_code == 200
    assert b"Sala deletada com sucesso." in delete_response.data
    assert db.session.get(Sala, sala.id) is None
