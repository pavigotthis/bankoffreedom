import copy
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

from conftest import approve, login, maps, post, publish, workflow

from three_du.domain import PENDING


def initial_publication(app, c):
    login(c)
    run, rid, conf, outputs, eid = workflow(app, c)
    assert approve(c, rid).status_code == 200
    mentor = app.test_client()
    login(mentor, "mentor@example.test")
    assert approve(mentor, rid).status_code == 200
    assert publish(c, rid).status_code == 200
    return run, rid, conf, outputs, eid


def test_initial_two_approvals_exact_version(app, client):
    login(client)
    run, rid, c, _, _ = workflow(app, client)
    assert publish(client, rid).status_code == 409
    mentor = app.test_client()
    login(mentor, "mentor@example.test")
    assert approve(mentor, rid).status_code == 409
    assert approve(client, rid, version=2).status_code == 409
    assert (
        post(
            client,
            f"/api/reports/{rid}/approve",
            {"version": 1, "reason": "SYNTHETIC", "wording_reviewed": False},
        ).status_code
        == 409
    )
    assert approve(client, rid).status_code == 200
    assert publish(client, rid).status_code == 409
    outsider = app.test_client()
    login(outsider, "stranger@example.test")
    assert approve(outsider, rid).status_code == 403
    assert approve(mentor, rid).status_code == 200
    assert publish(client, rid).status_code == 200
    assert publish(client, rid).json["repeated"] is True
    conn = sqlite3.connect(app.config["DATABASE"])
    assert conn.execute("SELECT COUNT(*) FROM publications").fetchone()[0] == 1
    conn.close()


def test_shared_responses_no_private_data(app, client):
    login(client)
    run, rid, c, _, _ = workflow(app, client)
    student = app.test_client()
    parent = app.test_client()
    login(student, "student@example.test")
    login(parent, "parent@example.test")
    for actor in [student, parent]:
        pending = actor.get("/api/students/1/report").json
        assert pending == {"status": "pending", "message": PENDING}
    assert approve(client, rid).status_code == 200
    mentor = app.test_client()
    login(mentor, "mentor@example.test")
    assert approve(mentor, rid).status_code == 200
    assert publish(client, rid).status_code == 200
    s = student.get("/api/students/1/report").json
    p = parent.get("/api/students/1/report").json
    assert (
        s == p and set(s) == {"status", "version", "published_at", "maps"} and len(s["maps"]) == 6
    )
    assert (
        student.get("/api/students/1/progress").json == parent.get("/api/students/1/progress").json
    )
    for forbidden in [
        "supporting_evidence",
        "confidence",
        "assumptions_to_validate",
        "original_statement",
        "SYNTHETIC original statement",
        "snapshot",
        "workflow",
    ]:
        assert forbidden not in json.dumps(s)
    assert b"Your reviewed insights" in parent.get("/parent/students/1").data


def test_edit_is_new_version_no_approval_inheritance(app, client):
    run, rid, c, outputs, eid = initial_publication(app, client)
    edited = post(
        client,
        f"/api/admin/reports/{rid}/edit",
        {
            "expected_version": 1,
            "maps": maps(c, "SYNTHETIC changed summary"),
            "reason": "SYNTHETIC revision",
        },
    )
    assert (
        edited.status_code == 200 and edited.json["version"] == 2 and edited.json["approvals"] == []
    )
    new = edited.json["id"]
    assert publish(client, new, 2).status_code == 409
    parent = app.test_client()
    login(parent, "parent@example.test")
    assert parent.get("/api/students/1/report").json["version"] == 1
    assert approve(client, new, 2).status_code == 200
    # No fresh mentor approval for revision.
    assert publish(client, new, 2).status_code == 200
    assert parent.get("/api/students/1/report").json["version"] == 2
    conn = sqlite3.connect(app.config["DATABASE"])
    assert conn.execute("SELECT COUNT(*) FROM publications").fetchone()[0] == 2
    assert (
        conn.execute("SELECT maps FROM reports WHERE id=?", (rid,)).fetchone()[0]
        != conn.execute("SELECT maps FROM reports WHERE id=?", (new,)).fetchone()[0]
    )
    conn.close()
    assert (
        post(
            client,
            f"/api/admin/reports/{rid}/edit",
            {"expected_version": 1, "maps": maps(c), "reason": "SYNTHETIC conflict"},
        ).status_code
        == 409
    )


def test_edit_initial_requires_new_admin_and_mentor(app, client):
    login(client)
    run, rid, c, _, _ = workflow(app, client)
    approve(client, rid)
    mentor = app.test_client()
    login(mentor, "mentor@example.test")
    approve(mentor, rid)
    new = post(
        client,
        f"/api/admin/reports/{rid}/edit",
        {"expected_version": 1, "maps": maps(c), "reason": "SYNTHETIC edit"},
    ).json["id"]
    assert publish(client, rid).status_code == 409
    assert publish(client, new, 2).status_code == 409
    assert approve(client, new, 2).status_code == 200
    assert publish(client, new, 2).status_code == 409
    assert approve(mentor, new, 2).status_code == 200 and publish(client, new, 2).status_code == 200


def test_upstream_correction_stales_drafts_and_snapshot(app, client):
    login(client)
    run, rid, c, outputs, eid = workflow(app, client)
    approve(client, rid)
    r = post(
        client,
        "/api/admin/students/1/evidence",
        {
            "stakeholder": "student",
            "source": "SYNTHETIC correction",
            "type": "assumption",
            "statement": "SYNTHETIC corrected",
            "corrected_from": eid,
            "reason": "SYNTHETIC correction",
        },
    )
    assert r.status_code == 200
    assert publish(client, rid).status_code == 409
    inspection = client.get(f"/api/admin/runs/{run}").json
    assert inspection["run"]["status"] == "stale" and all(
        s["status"] == "stale" for s in inspection["steps"]
    )
    assert "SYNTHETIC original statement" in inspection["snapshot"]["inputs"]
    # Even re-importing valid old output cannot reactivate an outdated input snapshot.
    assert (
        post(
            client,
            f"/api/admin/runs/{run}/steps/1",
            {
                "expected_attempt": 1,
                "output": outputs[0],
                "summary": "SYNTHETIC",
                "reason": "SYNTHETIC",
            },
        ).status_code
        == 409
    )
    assert b"Run" in client.get("/admin/students/1").data


def test_step_rerun_downstream_only_and_published_survives(app, client):
    run, rid, c, outputs, eid = initial_publication(app, client)
    new = post(
        client,
        f"/api/admin/reports/{rid}/edit",
        {"expected_version": 1, "maps": maps(c), "reason": "SYNTHETIC revision"},
    ).json["id"]
    approve(client, new, 2)
    r = post(
        client,
        f"/api/admin/runs/{run}/steps/2",
        {
            "expected_attempt": 1,
            "output": outputs[1],
            "summary": "SYNTHETIC rerun",
            "reason": "SYNTHETIC",
        },
    )
    assert r.json["status"] == "valid"
    steps = client.get(f"/api/admin/runs/{run}").json["steps"]
    assert [s["status"] for s in steps if s["step"] == 1] == ["valid"]
    assert all(s["status"] == "stale" for s in steps if s["step"] in [3, 4])
    assert publish(client, new, 2).status_code == 409
    p = app.test_client()
    login(p, "parent@example.test")
    assert p.get("/api/students/1/report").json["version"] == 1
    for n in [3, 4]:
        assert (
            post(
                client,
                f"/api/admin/runs/{run}/steps/{n}",
                {
                    "expected_attempt": 1,
                    "output": outputs[n - 1],
                    "summary": "SYNTHETIC rerun",
                    "reason": "SYNTHETIC",
                },
            ).json["status"]
            == "valid"
        )
    # A stale draft does not regain its old approvals after rerun.
    assert publish(client, new, 2).status_code == 409


def test_invalid_output_and_failure_are_retained(app, client):
    run, rid, c, outputs, eid = initial_publication(app, client)
    bad = copy.deepcopy(outputs[0])
    bad["evidence"][0]["evidence_type"] = "fact"
    res = post(
        client,
        f"/api/admin/runs/{run}/steps/1",
        {
            "expected_attempt": 1,
            "output": bad,
            "summary": "SYNTHETIC invalid assumption transform",
            "reason": "SYNTHETIC",
        },
    )
    assert res.json["status"] == "invalid" and "assumption" in res.json["error"]
    assert client.get(f"/api/admin/runs/{run}").json["run"]["status"] == "failed"
    res = post(
        client,
        f"/api/admin/runs/{run}/steps/1",
        {
            "expected_attempt": 2,
            "provider_error": "SYNTHETIC timeout",
            "summary": "SYNTHETIC failure",
            "reason": "SYNTHETIC",
        },
    )
    assert res.json["status"] == "failed"
    student = app.test_client()
    login(student, "student@example.test")
    assert student.get("/api/students/1/report").json["version"] == 1
    assert client.get(f"/api/admin/runs/{run}").json["steps"][-1]["error"] or any(
        s["error"] == "SYNTHETIC timeout"
        for s in client.get(f"/api/admin/runs/{run}").json["steps"]
    )


def test_unconfigured_provider_records_blocked_attempt(app, client):
    login(client)
    run, rid, c, _, _ = workflow(app, client)
    r = post(
        client, f"/api/admin/runs/{run}/generate/1", {"expected_attempt": 1, "reason": "SYNTHETIC"}
    )
    assert r.json["status"] == "blocked"
    steps = client.get(f"/api/admin/runs/{run}").json["steps"]
    assert any(s["status"] == "blocked" and s["output"] is None for s in steps)
    assert publish(client, rid).status_code == 409


def test_configuration_change_stales_work_and_validates_enumerations(app, client):
    login(client)
    run, rid, c, _, _ = workflow(app, client)
    old = client.get("/api/admin/config").json
    bad = copy.deepcopy(c)
    bad["journey_stages"] = bad["journey_stages"][:9]
    assert (
        post(
            client,
            "/api/admin/config",
            {"version": old["version"], "configuration": bad, "reason": "SYNTHETIC"},
        ).status_code
        == 400
    )
    assert (
        post(
            client,
            "/api/admin/config",
            {"version": old["version"], "configuration": c, "reason": "SYNTHETIC approved update"},
        ).status_code
        == 200
    )
    assert (
        post(
            client,
            "/api/admin/config",
            {"version": old["version"], "configuration": c, "reason": "SYNTHETIC conflict"},
        ).status_code
        == 409
    )
    assert publish(client, rid).status_code == 409


def test_mentor_cannot_edit_or_regenerate_real_record(app, client):
    login(client)
    run, rid, c, _, _ = workflow(app, client)
    login(client, "mentor@example.test")
    for url, body in [
        (f"/api/admin/reports/{rid}/edit", {"maps": maps(c), "reason": "SYNTHETIC"}),
        (f"/api/admin/runs/{run}/generate/1", {"reason": "SYNTHETIC"}),
        (f"/api/admin/runs/{run}/steps/1", {"reason": "SYNTHETIC"}),
        (f"/api/admin/reports/{rid}/publish", {"version": 1, "reason": "SYNTHETIC"}),
    ]:
        assert post(client, url, body).status_code == 403


def test_approval_duplicates_and_concurrent_publication_atomic(app, client):
    login(client)
    run, rid, c, _, _ = workflow(app, client)
    assert approve(client, rid).status_code == 200 and approve(client, rid).status_code == 200
    mentor = app.test_client()
    login(mentor, "mentor@example.test")
    approve(mentor, rid)
    actors = [app.test_client(), app.test_client()]
    for a in actors:
        login(a)
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda a: publish(a, rid).status_code, actors))
    assert statuses == [200, 200]
    conn = sqlite3.connect(app.config["DATABASE"])
    assert conn.execute("SELECT COUNT(*) FROM publications").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM approvals WHERE role='admin'").fetchone()[0] == 1
    conn.close()


def test_revoked_involvement_removes_access_and_approval_eligibility(app, client):
    login(client)
    run, rid, c, _, _ = workflow(app, client)
    approve(client, rid)
    mentor = app.test_client()
    login(mentor, "mentor@example.test")
    approve(mentor, rid)
    result = app.test_cli_runner().invoke(
        args=[
            "revoke",
            "--actor-email",
            "mentor@example.test",
            "--student-email",
            "student@example.test",
            "--reason",
            "SYNTHETIC revocation",
        ]
    )
    assert result.exit_code == 0
    assert (
        mentor.get("/mentor/students/1").status_code == 403
        and publish(client, rid).status_code == 409
    )


def test_map_structure_no_internal_fields(app, client):
    login(client)
    run, rid, c, _, _ = workflow(app, client)
    bad = maps(c)
    bad["student_persona"]["confidence"] = 0.9
    assert (
        post(
            client, f"/api/admin/runs/{run}/reports", {"maps": bad, "reason": "SYNTHETIC"}
        ).status_code
        == 400
    )
    bad = maps(c)
    bad["student_journey"]["items"] = bad["student_journey"]["items"][:9]
    assert (
        post(
            client, f"/api/admin/runs/{run}/reports", {"maps": bad, "reason": "SYNTHETIC"}
        ).status_code
        == 400
    )


def test_readiness_reviews_require_current_source_evidence(app, client):
    from conftest import completed, configure

    login(client)
    configure(app)
    completed(app)
    evidence = post(
        client,
        "/api/admin/students/1/evidence",
        {
            "stakeholder": "student",
            "source": "SYNTHETIC fixture",
            "type": "assumption",
            "statement": "SYNTHETIC assumption",
            "reason": "SYNTHETIC",
        },
    ).json["id"]
    snap = post(client, "/api/admin/students/1/snapshot", {"reason": "SYNTHETIC"}).json["id"]
    body = {"kind": "assessments", "evidence_ids": [evidence], "reason": "SYNTHETIC"}
    assert post(client, f"/api/admin/snapshots/{snap}/readiness", body).status_code == 400
    r = post(client, "/api/admin/students/1/runs", {"reason": "SYNTHETIC"})
    assert r.json["status"] == "blocked" and any(
        "mentor_interview" in gap for gap in r.json["gaps"]
    )
    parent = app.test_client()
    login(parent, "parent@example.test")
    assert post(parent, f"/api/admin/snapshots/{snap}/readiness", body).status_code == 403
    post(
        client,
        "/api/admin/students/1/evidence",
        {
            "stakeholder": "mentor",
            "source": "SYNTHETIC fixture",
            "type": "mentor note",
            "statement": "SYNTHETIC new note",
            "reason": "SYNTHETIC",
        },
    )
    assert post(client, f"/api/admin/snapshots/{snap}/readiness", body).status_code == 409


def test_stage_eight_access_is_separate_from_publication(app, client):
    from conftest import completed

    completed(app)
    login(client, "student@example.test")
    r = client.get("/student/stages/8")
    assert r.status_code == 200 and PENDING.encode() in r.data
    assert client.get("/api/students/1/report").json["status"] == "pending"
