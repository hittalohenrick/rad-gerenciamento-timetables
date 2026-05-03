def test_login_invalid_credentials_show_error(client, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")

    response = client.post(
        "/login",
        data={"username": "admin", "password": "senha-errada"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Usuario ou senha invalidos." in response.data


def test_admin_login_redirects_to_dashboard(login, user_factory):
    user_factory("admin", role="admin", password="Admin1234", email="admin@example.com")

    response = login("admin", "Admin1234")

    assert response.status_code == 200
    assert b"Dashboard Administrativo" in response.data
