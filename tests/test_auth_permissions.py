import json
import sqlite3
from pathlib import Path

import pytest
from conftest import PASSWORD, login, post

from three_du import create_app


@pytest.mark.parametrize("role", ["admin", "mentor"])
def test_signup_cannot_grant_privilege(client, role):
    r = post(
        client,
        "/signup",
        {"email": "new@example.test", "password": PASSWORD, "role": role, "synthetic": True},
    )
    assert r.status_code == 403


def test_signup_login_logout_persistence(app, client):
    r = post(
        client,
        "/signup",
        {"email": "new@example.test", "password": PASSWORD, "role": "student", "synthetic": True},
    )
    assert r.status_code == 200 and client.get("/portal").location.endswith("/student/stages/1")
    uid = client.get("/api/session").json["user"]["id"]
    r = post(
        client,
        f"/api/students/{uid}/stages/1",
        {"action": "save", "revision": 0, "draft": {"reflection": "Fictional draft"}},
    )
    assert r.json["completed"] is False
    assert post(client, "/logout", {}).status_code == 200
    assert client.get(f"/api/students/{uid}/stages/1").status_code == 401
    # A new application instance and independent browser session read the persisted database.
    other = create_app(dict(app.config)).test_client()
    login(other, "new@example.test")
    assert other.get(f"/api/students/{uid}/stages/1").json["draft"] == {
        "reflection": "Fictional draft"
    }


@pytest.mark.parametrize(
    "email,role",
    [
        ("student@example.test", "student"),
        ("parent@example.test", "parent"),
        ("mentor@example.test", "mentor"),
        ("admin@example.test", "admin"),
    ],
)
def test_role_routing(client, email, role):
    login(client, email)
    assert client.get("/portal/" + role).status_code in (200, 302)
    for other in {"student", "parent", "mentor", "admin"} - {role}:
        assert client.get("/portal/" + other).status_code == 403


def test_recovery_single_use_revokes_sessions(app, client):
    login(client, "student@example.test")
    second = app.test_client()
    login(second, "student@example.test")
    recover = app.test_client()
    a = post(recover, "/recover", {"email": "student@example.test"})
    b = post(recover, "/recover", {"email": "missing@example.test"})
    assert a.json == b.json and "token" not in str(a.json)
    letter = json.loads(next(Path(app.config["RECOVERY_DIR"]).glob("*.json")).read_text())
    token = letter["path"].split("token=")[1]
    assert (
        post(recover, "/reset", {"token": token, "password": "New-fictional-password!"}).status_code
        == 200
    )
    assert second.get("/api/students/1/progress").status_code == 401
    assert (
        post(
            recover, "/reset", {"token": token, "password": "Another-fictional-password!"}
        ).status_code
        == 400
    )
    assert (
        post(recover, "/login", {"email": "student@example.test", "password": PASSWORD}).status_code
        == 401
    )
    assert (
        post(
            recover,
            "/login",
            {"email": "student@example.test", "password": "New-fictional-password!"},
        ).status_code
        == 200
    )


def test_recovery_expired(app, client):
    post(client, "/recover", {"email": "student@example.test"})
    token = json.loads(next(Path(app.config["RECOVERY_DIR"]).glob("*.json")).read_text())[
        "path"
    ].split("token=")[1]
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("UPDATE recovery SET expires=0")
    conn.commit()
    conn.close()
    assert (
        post(client, "/reset", {"token": token, "password": "Fictional-new-password!"}).status_code
        == 400
    )


def test_csrf_and_cookie(client):
    client.get("/login")
    r = client.post("/login", json={"email": "admin@example.test", "password": PASSWORD})
    assert r.status_code == 403
    r = login(client).get("/api/session")
    assert r.headers["Cache-Control"] == "no-store"
    fresh = client.application.test_client().get("/login")
    cookie = fresh.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert client.get("/").headers["Content-Security-Policy"].startswith("default-src 'self'")


@pytest.mark.parametrize(
    "email",
    [
        "student@example.test",
        "parent@example.test",
        "mentor@example.test",
        "stranger@example.test",
        "unassigned@example.test",
    ],
)
def test_admin_record_denied(client, email):
    login(client, email)
    assert client.get("/admin/students/1").status_code == 403
    assert client.get("/api/admin/students/1").status_code == 403


@pytest.mark.parametrize("email", ["parent@example.test", "unlinked@example.test"])
def test_parent_boundaries(client, email):
    login(client, email)
    assert client.get("/api/students/1/progress").status_code == (
        200 if email.startswith("parent") else 403
    )
    for path in [
        "/api/students/5/report",
        "/api/students/5/progress",
        "/api/students/1/stages/1",
        "/student/stages/1",
        "/api/mentor/students/1",
    ]:
        assert client.get(path).status_code == 403
    assert client.get("/parent/students/1").status_code == (
        200 if email.startswith("parent") else 403
    )


def test_mentor_scope_and_mutations(client):
    login(client, "mentor@example.test")
    d = client.get("/api/mentor/students/1").json
    assert [s["stage"] for s in d["work"]] == [6, 7] and "evidence" not in d
    assert client.get("/api/mentor/students/5").status_code == 403
    for p in [
        "/api/admin/config",
        "/api/admin/students/1/evidence",
        "/api/admin/students/1/runs",
        "/api/admin/runs/1/reports",
    ]:
        # missing run is 404; existing admin resources are inaccessible.
        assert post(client, p, {}).status_code in (403, 404)
    assert (
        post(
            client,
            "/api/students/1/notes",
            {"kind": "session", "text": "SYNTHETIC session", "reason": "SYNTHETIC"},
        ).status_code
        == 200
    )
    assert (
        post(
            client,
            "/api/students/1/notes",
            {"kind": "information-request", "text": "SYNTHETIC request", "reason": "SYNTHETIC"},
        ).status_code
        == 403
    )


def test_default_mentor_restriction(app, client):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("UPDATE relationships SET scopes='[]' WHERE kind='mentor'")
    conn.commit()
    conn.close()
    login(client, "mentor@example.test")
    assert client.get("/api/mentor/students/1").json["work"] == []
    assert b"Raw work access is restricted" in client.get("/mentor/students/1").data


def test_no_live_collection(app):
    app.config["SYNTHETIC_ONLY"] = False
    c = app.test_client()
    assert (
        post(
            c,
            "/signup",
            {
                "email": "real@example.test",
                "password": PASSWORD,
                "role": "student",
                "synthetic": True,
            },
        ).status_code
        == 409
    )


def test_support_and_render_all_roles(client):
    for email, path in [
        ("student@example.test", "/student/stages/1"),
        ("parent@example.test", "/parent/students/1"),
        ("mentor@example.test", "/mentor/students/1"),
        ("admin@example.test", "/admin/students/1"),
    ]:
        login(client, email)
        r = client.get(path)
        assert r.status_code == 200
        assert b"mailto:prashasawan@gmail.com" in r.data and b"tel:" not in r.data
        assert b"phone support unavailable" in r.data


def test_stage_scope_does_not_grant_unspecified_fields(app, client):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute(
        "UPDATE stages SET draft=? WHERE student_id=1 AND stage=6",
        (json.dumps({"reflection": "SYNTHETIC permitted", "private": "SYNTHETIC private"}),),
    )
    conn.execute(
        "UPDATE relationships SET scopes=? WHERE kind=?",
        (json.dumps({"stages": [6], "fields": {}}), "mentor"),
    )
    conn.commit()
    conn.close()
    login(client, "mentor@example.test")
    assert client.get("/api/mentor/students/1").json["work"][0]["draft"] == {}
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute(
        "UPDATE relationships SET scopes=? WHERE kind=?",
        (json.dumps({"stages": [6], "fields": {"6": ["reflection"]}}), "mentor"),
    )
    conn.commit()
    conn.close()
    assert client.get("/api/mentor/students/1").json["work"][0]["draft"] == {
        "reflection": "SYNTHETIC permitted"
    }
    assert b"SYNTHETIC private" not in client.get("/mentor/students/1").data


def test_malformed_credentials_rejected(client):
    for route in ["/login", "/signup", "/recover"]:
        assert (
            post(
                client,
                route,
                {"email": ["not text"], "password": 123, "role": "student", "synthetic": True},
            ).status_code
            == 400
        )


def test_policy_switch_cannot_enable_live_writes(app, client):
    login(client, "student@example.test")
    app.config["SYNTHETIC_ONLY"] = False
    assert (
        post(
            client,
            "/api/students/1/stages/1",
            {"action": "save", "revision": 0, "draft": {"reflection": "real data"}},
        ).status_code
        == 409
    )


def test_template_compilation_and_repeatable_migrations(app):
    with app.app_context():
        for name in app.jinja_env.list_templates():
            app.jinja_env.get_template(name)
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0
    conn = sqlite3.connect(app.config["DATABASE"])
    assert conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 8
    conn.close()


def test_mentor_cannot_approve_fields_outside_review_scope(app, client):
    from conftest import configure

    configure(app)
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute(
        "UPDATE stages SET status='submitted',draft=? WHERE student_id=1 AND stage=6",
        (json.dumps({"reflection": "SYNTHETIC"}),),
    )
    conn.execute(
        "UPDATE relationships SET scopes=? WHERE kind=?",
        (json.dumps({"stages": [6], "fields": {}}), "mentor"),
    )
    conn.commit()
    conn.close()
    login(client, "mentor@example.test")
    assert (
        post(
            client, "/api/students/1/stages/6/approve", {"revision": 0, "reason": "SYNTHETIC"}
        ).status_code
        == 403
    )
