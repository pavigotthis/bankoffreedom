"""Display names persist without granting relationships or privileges."""

import sqlite3

import pytest
from conftest import PASSWORD, csrf, login, post


@pytest.mark.parametrize("role", ["student", "parent"])
def test_signup_name_persists_across_login_and_logout(app, role):
    client = app.test_client()
    assert 'autocomplete="name"' in client.get("/signup").text
    email = role + "-new@example.test"
    result = post(
        client,
        "/signup",
        {
            "email": email,
            "password": PASSWORD,
            "role": role,
            "synthetic": True,
            "name": "  Synthetic नंदा  ",
        },
    )
    assert result.status_code == 200, result.json
    assert client.get("/api/session").json["user"]["name"] == "Synthetic नंदा"
    post(client, "/logout", {})
    login(client, email)
    assert client.get("/api/session").json["user"]["name"] == "Synthetic नंदा"
    conn = sqlite3.connect(app.config["DATABASE"])
    identifier = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()[0]
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM relationships WHERE actor_id=?", (identifier,)
        ).fetchone()[0]
        == 0
    )
    conn.close()


@pytest.mark.parametrize("name", [None, "", "   ", 42, ["name"], "x" * 121, "name\nother"])
def test_signup_requires_valid_name(client, name):
    result = post(
        client,
        "/signup",
        {
            "email": "new-name@example.test",
            "password": PASSWORD,
            "role": "student",
            "synthetic": True,
            "name": name,
        },
    )
    assert result.status_code == 400
    assert client.get("/api/session").json["user"] is None


def test_existing_account_can_add_name_without_changing_others_or_permissions(app):
    student = login(app.test_client(), "student@example.test")
    assert student.get("/api/session").json["user"]["name"] is None
    assert "Add your name" in student.get("/account/name").text
    result = post(
        student,
        "/account/name",
        {"name": "Synthetic Student", "user_id": 5, "role": "admin", "email": "other@example.test"},
    )
    assert result.status_code == 200
    admin = login(app.test_client())
    assert "Synthetic Student" in admin.get("/admin/dashboard").text
    assert student.get("/admin/dashboard").status_code == 403
    parent = login(app.test_client(), "parent@example.test")
    assert (
        parent.post(
            "/account/name", data={"name": "Synthetic Parent", "csrf": csrf(parent)}
        ).status_code
        == 302
    )
    assert "Synthetic Parent" in admin.get("/admin/dashboard").text
    conn = sqlite3.connect(app.config["DATABASE"])
    assert conn.execute("SELECT role,email FROM users WHERE id=1").fetchone() == (
        "student",
        "student@example.test",
    )
    assert conn.execute("SELECT name FROM users WHERE id=5").fetchone()[0] is None
    conn.close()


def test_name_change_requires_owner_session_csrf_and_escapes_html(app):
    client = app.test_client()
    assert post(client, "/account/name", {"name": "Synthetic"}).status_code == 401
    login(client, "student@example.test")
    assert client.post("/account/name", json={"name": "Synthetic"}).status_code == 403
    assert post(client, "/account/name", {"name": "<script>synthetic</script>"}).status_code == 200
    html = login(app.test_client()).get("/admin/dashboard").text
    assert "<script>synthetic</script>" not in html
    assert "&lt;script&gt;synthetic&lt;/script&gt;" in html
