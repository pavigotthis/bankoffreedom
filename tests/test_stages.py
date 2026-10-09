import json
import sqlite3

from conftest import configure, login, post

from three_du.domain import LOCKED


def test_sequencing_open_save_submit_next_do_not_complete(app, client):
    login(client, "student@example.test")
    p = client.get("/api/students/1/progress").json
    assert len(p["stages"]) == 9 and p["stages"][0]["available"] and p["stages"][8]["available"]
    assert all(not s["available"] for s in p["stages"][1:8])
    assert client.get("/student/stages/1").status_code == 200
    assert client.get("/student/stages/2").status_code == 403
    r = client.get("/api/students/1/stages/2")
    assert (
        r.status_code == 403
        and r.json["error"] == LOCKED
        and r.json["next_action"] == "/student/stages/1"
    )
    assert (
        post(
            client, "/api/students/1/stages/2", {"action": "save", "revision": 0, "draft": {}}
        ).status_code
        == 403
    )
    for action, rev in [("save", 0), ("submit", 1)]:
        r = post(
            client,
            "/api/students/1/stages/1",
            {"action": action, "revision": rev, "draft": {"reflection": "SYNTHETIC note"}},
        )
        assert r.json["completed"] is False
    assert client.get("/student/stages/2").status_code == 403
    assert client.get("/student/stages/9").status_code == 200
    configure(app)
    login(client)
    r = post(
        client, "/api/students/1/stages/1/approve", {"revision": 2, "reason": "SYNTHETIC approval"}
    )
    assert r.status_code == 200
    login(client, "student@example.test")
    p = client.get("/api/students/1/progress").json
    assert p["stages"][1]["available"] and not p["stages"][2]["available"]
    assert client.get("/student/stages/1").status_code == 200
    assert (
        post(
            client,
            "/api/students/1/stages/1",
            {"action": "save", "revision": 3, "draft": {"reflection": "overwrite"}},
        ).status_code
        == 409
    )
    assert client.get("/api/students/1/stages/1").json["draft"]["reflection"] == "SYNTHETIC note"


def test_defaults_block_completion_and_generation(client):
    login(client)
    assert (
        post(
            client, "/api/students/1/stages/1/approve", {"revision": 0, "reason": "SYNTHETIC"}
        ).status_code
        == 409
    )
    assert post(client, "/api/admin/students/1/runs", {"reason": "SYNTHETIC"}).status_code == 409
    post(client, "/api/admin/students/1/snapshot", {"reason": "SYNTHETIC"})
    run = post(client, "/api/admin/students/1/runs", {"reason": "SYNTHETIC"}).json
    assert run["status"] == "blocked" and "student_personas" in run["gaps"]
    assert client.get(f"/api/admin/runs/{run['id']}").json["steps"][0]["status"] == "blocked"


def test_concurrent_drafts_and_revision_review(app, client):
    login(client, "student@example.test")
    body = {"action": "save", "revision": 0, "draft": {"reflection": "first"}}
    assert post(client, "/api/students/1/stages/1", body).status_code == 200
    body["draft"]["reflection"] = "conflicting"
    assert post(client, "/api/students/1/stages/1", body).status_code == 409
    assert client.get("/api/students/1/stages/1").json["draft"]["reflection"] == "first"
    configure(app)
    login(client)
    assert (
        post(
            client, "/api/students/1/stages/1/approve", {"revision": 0, "reason": "SYNTHETIC"}
        ).status_code
        == 409
    )
    assert (
        post(
            client, "/api/students/1/stages/1/approve", {"revision": 1, "reason": "SYNTHETIC"}
        ).status_code
        == 409
    )


def test_admin_at_any_time_does_not_unlock_over_previous(app, client):
    c = configure(app)
    c["stage_rules"]["7"]["requires_submission"] = False
    c["stage_rules"]["7"]["required_draft_fields"] = []
    conn = sqlite3.connect(app.config["DATABASE"])

    conn.execute("UPDATE settings SET body=?", (json.dumps(c),))
    conn.commit()
    conn.close()
    login(client)
    assert (
        post(
            client,
            "/api/students/1/stages/7/approve",
            {"revision": 0, "reason": "SYNTHETIC approved criterion permits completion"},
        ).status_code
        == 200
    )
    login(client, "student@example.test")
    assert client.get("/api/students/1/progress").json["stages"][7]["available"] is False
    assert client.get("/api/students/1/report").json["status"] == "pending"


def test_mentor_completion_requires_involvement_scope_criteria(app, client):
    configure(app)
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute(
        "UPDATE stages SET status='submitted',draft='{\"reflection\":\"SYNTHETIC\"}' WHERE student_id=1"
    )
    conn.commit()
    conn.close()
    login(client, "mentor@example.test")
    assert (
        post(
            client, "/api/students/1/stages/1/approve", {"revision": 0, "reason": "SYNTHETIC"}
        ).status_code
        == 403
    )
    assert (
        post(
            client, "/api/students/1/stages/6/approve", {"revision": 0, "reason": "SYNTHETIC"}
        ).status_code
        == 200
    )
    login(client, "stranger@example.test")
    assert (
        post(
            client, "/api/students/1/stages/7/approve", {"revision": 0, "reason": "SYNTHETIC"}
        ).status_code
        == 403
    )
