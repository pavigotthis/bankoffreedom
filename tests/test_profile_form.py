"""Confirmed profile inputs are independent of private mapper setup."""

import json
import sqlite3

from conftest import login, post

from three_du.standalone import MANDATORY


def test_profile_is_inline_without_mapping_and_drafts_restore(app):
    student = login(app.test_client(), "student@example.test")
    html = student.get("/student/stages/1")
    assert html.status_code == 200
    assert "Enter and resume your discovery inputs" not in html.text
    assert "Your saved development notes" not in html.text
    for label in MANDATORY["student"]:
        assert 'name="' + label + '"' in html.text
    assert student.get("/students/1/intake").status_code == 200
    endpoint = "/api/students/1/intake"
    assert (
        post(
            student,
            endpoint,
            dict(
                action="save",
                expected_version=0,
                request_key="draft",
                values={"Academic Information": "SYNTHETIC saved academic input"},
            ),
        ).status_code
        == 200
    )
    assert "SYNTHETIC saved academic input" in student.get("/student/stages/1").text
    assert (
        post(
            student,
            endpoint,
            dict(action="submit", expected_version=1, request_key="incomplete", values={}),
        ).status_code
        == 400
    )
    values = {label: "SYNTHETIC answer" for label in MANDATORY["student"]}
    assert (
        post(
            student,
            endpoint,
            dict(action="submit", expected_version=1, request_key="submit", values=values),
        ).status_code
        == 200
    )
    admin = login(app.test_client())
    assert "SYNTHETIC answer" in admin.get("/admin/students/1").text
    conn = sqlite3.connect(app.config["DATABASE"])
    assert (
        conn.execute("SELECT status FROM stages WHERE student_id=1 AND stage=1").fetchone()[0]
        == "submitted"
    )
    conn.close()
    assert (
        post(
            student,
            "/api/students/1/stages/1",
            {"action": "save", "revision": 2, "draft": {"reflection": "bypass"}},
        ).status_code
        == 409
    )


def test_previous_notes_preserved_and_parent_only_fields(app):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute(
        "UPDATE stages SET draft=? WHERE student_id=1 AND stage=1",
        (json.dumps({"reflection": "SYNTHETIC original note"}),),
    )
    conn.commit()
    conn.close()
    student = login(app.test_client(), "student@example.test")
    assert "SYNTHETIC original note" in student.get("/student/stages/1").text
    assert (
        post(
            student,
            "/api/students/1/intake",
            dict(action="save", expected_version=0, request_key="save", values={}),
        ).status_code
        == 200
    )
    assert "SYNTHETIC original note" in student.get("/student/stages/1").text
    parent = login(app.test_client(), "parent@example.test")
    assert parent.get("/students/1/intake").status_code == 200
    fields = parent.get("/api/students/1/intake").json["fields"]
    assert [f["label"] for f in fields] == MANDATORY["parent"]
    assert "SYNTHETIC original note" not in parent.get("/students/1/intake").text
    assert parent.get("/students/5/intake").status_code == 403
