from app.models import User


def test_admin_course_form_shows_quantidade_periodos(client):
    admin = User(username="admin", email="admin@example.com", role="admin")
    admin.set_password("Admin1234")

    from app import db

    db.session.add(admin)
    db.session.commit()

    client.post(
        "/login",
        data={"username": "admin", "password": "Admin1234"},
        follow_redirects=True,
    )

    response = client.get("/curso/new")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "name=\"quantidade_periodos\"" in html
    assert "Quantidade de Periodos" in html
