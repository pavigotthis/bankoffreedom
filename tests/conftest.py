"""All accounts and specifications below are SYNTHETIC TEST FIXTURES, not product content."""

import copy
import json
import sqlite3

import pytest
from werkzeug.security import generate_password_hash

from three_du import create_app
from three_du.domain import DEFAULT_CONFIG

PASSWORD = "Fictional-password-123!"


@pytest.fixture
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.sqlite3"),
            "RECOVERY_DIR": str(tmp_path / "recovery"),
        }
    )
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0, result.output
    conn = sqlite3.connect(app.config["DATABASE"])
    accounts = [
        (1, "student@example.test", "student"),
        (2, "parent@example.test", "parent"),
        (3, "mentor@example.test", "mentor"),
        (4, "admin@example.test", "admin"),
        (5, "other@example.test", "student"),
        (6, "stranger@example.test", "mentor"),
        (7, "unlinked@example.test", "parent"),
        (8, "unassigned@example.test", "admin"),
    ]
    password = generate_password_hash(PASSWORD)
    conn.executemany(
        "INSERT INTO users(id,email,password,role) VALUES(?,?,?,?)",
        [(i, e, password, r) for i, e, r in accounts],
    )
    conn.executemany(
        "INSERT INTO stages(student_id,stage) VALUES(?,?)",
        [(i, n) for i in [1, 5] for n in range(1, 9)],
    )
    conn.executemany(
        "INSERT INTO relationships VALUES(?,?,?,?)",
        [
            (2, 1, "parent", "[]"),
            (
                3,
                1,
                "mentor",
                json.dumps(
                    {"stages": [6, 7], "fields": {"6": ["reflection"], "7": ["reflection"]}}
                ),
            ),
            (4, 1, "admin", "[]"),
        ],
    )
    conn.commit()
    conn.close()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def csrf(c):
    return c.get("/api/session").json["csrf"]


def post(c, url, body):
    return c.post(url, json=body, headers={"X-CSRF-Token": csrf(c)})


def login(c, email="admin@example.test"):
    r = post(c, "/login", {"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.json
    return c


def configure(app):
    c = copy.deepcopy(DEFAULT_CONFIG)
    # SYNTHETIC ONLY: no fixture enum is a production specification.
    c.update(
        student_personas=["SYNTHETIC student hypothesis"],
        parent_personas=["SYNTHETIC parent hypothesis"],
        empathy_categories=["SYNTHETIC category"],
        journey_stages=[f"SYNTHETIC journey {i}" for i in range(1, 19)],
        journey_fields=["SYNTHETIC field"],
    )
    c["stage_rules"] = {
        str(n): {
            "approvers": ["admin", "mentor"],
            "requires_submission": True,
            "required_draft_fields": ["reflection"],
            "description": "SYNTHETIC test completion rule",
        }
        for n in range(1, 9)
    }
    c["readiness"] = {
        "required_stages": [2, 6, 7],
        "assessment_criterion": "SYNTHETIC assessment completion",
        "mentor_interview_criterion": "SYNTHETIC interview completion",
        "activity_criterion": "SYNTHETIC activity completion",
    }
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("UPDATE settings SET body=? WHERE id=1", (json.dumps(c),))
    conn.commit()
    conn.close()
    return c


def completed(app):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute(
        "UPDATE stages SET status='complete',draft=? WHERE student_id=1",
        (json.dumps({"reflection": "SYNTHETIC work"}),),
    )
    conn.commit()
    conn.close()


def maps(c, summary="SYNTHETIC provisional summary"):
    result = {}
    for role in ["student", "parent"]:
        result[role + "_persona"] = {"summary": summary, "items": []}
        for suffix, options in [
            ("empathy", c["empathy_categories"]),
            ("journey", c["journey_stages"]),
        ]:
            result[role + "_" + suffix] = {
                "summary": summary,
                "items": [{"label": x, "text": "SYNTHETIC reviewed wording"} for x in options],
            }
    return result


def workflow(app, c):
    conf = configure(app)
    completed(app)
    eid = post(
        c,
        "/api/admin/students/1/evidence",
        {
            "stakeholder": "student",
            "source": "SYNTHETIC fixture",
            "type": "assumption",
            "statement": "SYNTHETIC original statement",
            "reason": "SYNTHETIC test",
        },
    ).json["id"]
    snap = post(c, "/api/admin/students/1/snapshot", {"reason": "SYNTHETIC test"})
    assert snap.status_code == 200, snap.json
    fact = post(
        c,
        "/api/admin/students/1/evidence",
        {
            "stakeholder": "mentor",
            "source": "SYNTHETIC fixture",
            "type": "mentor note",
            "statement": "SYNTHETIC readiness completion evidence",
            "reason": "SYNTHETIC test",
        },
    ).json["id"]
    snap = post(c, "/api/admin/students/1/snapshot", {"reason": "SYNTHETIC test"})
    for kind in ["assessments", "mentor_interview", "activities"]:
        review = post(
            c,
            f"/api/admin/snapshots/{snap.json['id']}/readiness",
            {"kind": kind, "evidence_ids": [fact], "reason": "SYNTHETIC criteria checked"},
        )
        assert review.status_code == 200, review.json
    run = post(c, "/api/admin/students/1/runs", {"reason": "SYNTHETIC test"})
    assert run.status_code == 200, run.json
    rid = run.json["id"]
    trace = {
        "supporting_evidence": [eid],
        "confidence": 0.5,
        "missing_evidence": [],
        "assumptions_to_validate": ["SYNTHETIC assumption"],
    }
    outputs = [
        {
            "evidence": [
                {
                    "evidence_id": eid,
                    "original_statement": "SYNTHETIC original statement",
                    "stakeholder": "student",
                    "source": "SYNTHETIC fixture",
                    "evidence_type": "assumption",
                    "career_dimension": "SYNTHETIC dimension",
                    "sentiment": "SYNTHETIC sentiment",
                    "confidence": 0.5,
                    "contradiction_status": "SYNTHETIC unreviewed",
                },
                {
                    "evidence_id": fact,
                    "original_statement": "SYNTHETIC readiness completion evidence",
                    "stakeholder": "mentor",
                    "source": "SYNTHETIC fixture",
                    "evidence_type": "fact",
                    "career_dimension": "SYNTHETIC dimension",
                    "sentiment": "SYNTHETIC sentiment",
                    "confidence": 0.5,
                    "contradiction_status": "SYNTHETIC unreviewed",
                },
            ],
            "gaps": ["SYNTHETIC limitation"],
        }
    ]
    outputs.append(
        {
            r: dict(
                trace,
                selected_hypothesis=conf[r + "_personas"][0],
                alternatives=[],
                needs=[],
                barriers=[],
            )
            for r in ["student", "parent"]
        }
    )
    outputs.append(
        {
            r: [
                dict(
                    trace,
                    category=x,
                    source="SYNTHETIC fixture",
                    text="SYNTHETIC text",
                    validation_status="needs validation",
                )
                for x in conf["empathy_categories"]
            ]
            for r in ["student", "parent"]
        }
    )
    outputs.append(
        {
            r: [
                dict(trace, stage=x, fields={k: "SYNTHETIC text" for k in conf["journey_fields"]})
                for x in conf["journey_stages"]
            ]
            for r in ["student", "parent"]
        }
    )
    for n, out in enumerate(outputs, 1):
        res = post(
            c,
            f"/api/admin/runs/{rid}/steps/{n}",
            {
                "expected_attempt": 0,
                "output": out,
                "summary": "SYNTHETIC inspectable transformation",
                "reason": "SYNTHETIC test",
            },
        )
        assert res.status_code == 200 and res.json["status"] == "valid", res.json
    report = post(
        c, f"/api/admin/runs/{rid}/reports", {"maps": maps(conf), "reason": "SYNTHETIC test"}
    )
    assert report.status_code == 200, report.json
    return rid, report.json["id"], conf, outputs, eid


def approve(c, rid, version=1):
    return post(
        c,
        f"/api/reports/{rid}/approve",
        {"version": version, "wording_reviewed": True, "reason": "SYNTHETIC human review"},
    )


def publish(c, rid, version=1):
    return post(
        c,
        f"/api/admin/reports/{rid}/publish",
        {"version": version, "reason": "SYNTHETIC publication"},
    )
