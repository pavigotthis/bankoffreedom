import json
import sqlite3
from pathlib import Path

import pytest
from conftest import PASSWORD, approve, login, post, publish, workflow

from three_du import create_app


def admin_login(client, email="admin@example.test"):
    return post(client, "/admin/login", {"email": email, "password": PASSWORD})


def test_dedicated_login_persistent_role_and_dashboard(client):
    assert b"Admin Login" in client.get("/").data
    page = client.get("/admin/login")
    assert page.status_code == 200 and b"Show password" in page.data and b"/recover" in page.data
    result = admin_login(client)
    assert result.status_code == 200 and result.json["redirect"] == "/admin/dashboard"
    page = client.get("/admin/dashboard")
    assert page.status_code == 200 and b"Admin dashboard" in page.data
    assert b"student@example.test" in page.data and b"other@example.test" not in page.data
    assert b"parent@example.test" in page.data and b"mentor@example.test" in page.data
    for anchor in [b"#work", b"#sources", b"#workflow", b"#reports", b"#history"]:
        assert anchor in page.data
    assert client.get("/portal").location.endswith("/admin/dashboard")
    assert client.get("/admin/login").location.endswith("/admin/dashboard")
    assert client.get("/api/admin/students/1/relationships").status_code == 200
    assert client.get("/api/admin/students/5/relationships").status_code == 403


def test_html_admin_login_redirect_and_wrong_password(client):
    csrf = client.get("/api/session").json["csrf"]
    result = client.post(
        "/admin/login", data={"csrf": csrf, "email": "admin@example.test", "password": PASSWORD}
    )
    assert result.status_code == 302 and result.location.endswith("/admin/dashboard")
    post(client, "/logout", {})
    assert (
        post(
            client, "/admin/login", {"email": "admin@example.test", "password": "wrong"}
        ).status_code
        == 401
    )
    assert client.get("/api/session").json["user"] is None


@pytest.mark.parametrize(
    "email", ["student@example.test", "parent@example.test", "mentor@example.test"]
)
def test_nonadmins_cannot_enter_admin_login_or_dashboard(client, email):
    assert admin_login(client, email).status_code == 403
    assert client.get("/api/session").json["user"] is None
    login(client, email)
    for path in ["/admin/login", "/admin/dashboard", "/admin/students/1"]:
        assert client.get(path).status_code == 403
    assert client.get("/api/admin/config").status_code == 403
    assert post(client, "/api/admin/reports/999/publish", {}).status_code == 403


@pytest.mark.parametrize("path", ["/admin/dashboard", "/admin/students/1"])
def test_anonymous_admin_pages_redirect_to_login(client, path):
    response = client.get(path)
    assert response.status_code == 302 and response.location.startswith("/admin/login")


def test_anonymous_all_admin_backend_operations_denied(client):
    for path in [
        "/api/admin/config",
        "/api/admin/students/1",
        "/api/admin/students/1/relationships",
        "/api/admin/runs/99",
        "/api/admin/schemas/steps/1",
    ]:
        assert client.get(path).status_code == 401
    # Namespace guard runs before CSRF and nonexistent record lookup.
    for path in [
        "/api/admin/config",
        "/api/admin/students/1/evidence",
        "/api/admin/students/1/snapshot",
        "/api/admin/students/1/runs",
        "/api/admin/snapshots/99/readiness",
        "/api/admin/runs/99/steps/1",
        "/api/admin/runs/99/generate/1",
        "/api/admin/runs/99/reports",
        "/api/admin/reports/99/edit",
        "/api/admin/reports/99/publish",
    ]:
        assert client.post(path, json={}).status_code == 401


def test_admin_logout_and_session_expiry(app, client):
    admin_login(client)
    assert post(client, "/logout", {}).status_code == 200
    assert client.get("/admin/dashboard").status_code == 302
    admin_login(client)
    connection = sqlite3.connect(app.config["DATABASE"])
    connection.execute("UPDATE sessions SET expires=0 WHERE user_id=4")
    connection.commit()
    connection.close()
    response = client.get("/admin/dashboard")
    assert response.status_code == 302 and response.location == "/admin/login?expired=1"
    assert b"Your session expired" in client.get(response.location).data
    assert client.get("/api/admin/config").status_code == 401
    assert admin_login(client).status_code == 200
    assert client.get("/admin/dashboard").status_code == 200


def test_admin_recovery_maintains_role(app, client):
    post(client, "/recover", {"email": "admin@example.test"})
    message = json.loads(next(Path(app.config["RECOVERY_DIR"]).glob("*.json")).read_text())
    token = message["path"].split("token=")[1]
    password = "SYNTHETIC-reset-admin-password!"
    assert post(client, "/reset", {"token": token, "password": password}).status_code == 200
    result = post(client, "/admin/login", {"email": "admin@example.test", "password": password})
    assert result.json["redirect"] == "/admin/dashboard"
    assert client.get("/api/session").json["user"]["role"] == "admin"


def test_provision_first_admin_then_authenticate(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "first.sqlite3")})
    runner = app.test_cli_runner()
    assert runner.invoke(args=["init-db"]).exit_code == 0
    assert (
        runner.invoke(
            args=[
                "provision",
                "--email",
                "first@synthetic.test",
                "--role",
                "admin",
                "--reason",
                "SYNTHETIC authorized first administrator",
                "--password",
                PASSWORD,
            ]
        ).exit_code
        == 0
    )
    connection = sqlite3.connect(app.config["DATABASE"])
    saved = connection.execute("SELECT password,role FROM users").fetchone()
    connection.close()
    assert saved[0] != PASSWORD and saved[1] == "admin"
    client = app.test_client()
    assert admin_login(client, "first@synthetic.test").status_code == 200
    assert b"No assigned students yet" in client.get("/admin/dashboard").data
    assert (
        post(
            client,
            "/signup",
            {
                "email": "attacker@synthetic.test",
                "role": "admin",
                "password": PASSWORD,
                "synthetic": True,
            },
        ).status_code
        == 403
    )


def test_admin_dashboard_connected_to_full_review_and_publication(app, client):
    assert admin_login(client).status_code == 200
    run, report, _, _, _ = workflow(app, client)
    page = client.get("/admin/students/1")
    assert page.status_code == 200
    for content in [
        b"Parent links and mentor involvement",
        b"Four-step mapping workflow",
        b"Version-specific review",
        b"Approval, publication and version history",
    ]:
        assert content in page.data
    assert approve(client, report).status_code == 200
    assert publish(client, report).status_code == 409
    mentor = app.test_client()
    login(mentor, "mentor@example.test")
    assert approve(mentor, report).status_code == 200
    assert publish(client, report).status_code == 200
