"""Synthetic standalone contracts; never production mapping prompts."""

import io
import json
import sqlite3

import pytest
from conftest import csrf, login, maps, post

from three_du.domain import MAP_KEYS, STAGES, validate_maps
from three_du.standalone import MANDATORY, STEP_IDS, parse_configuration


def contract():
    fields = [
        dict(
            id=label.lower().replace(" ", "_"),
            label=label,
            type="text",
            author_scope=role,
            required_for_submission=True,
            activation="blocked_pending_educator_scope"
            if role == "educator"
            else "approved_scope_required",
        )
        for role, labels in MANDATORY.items()
        for label in labels
    ]
    fields.append(
        dict(
            id="previous_interaction_notes",
            label="Previous Interaction Notes",
            type="text",
            author_scope=["involved_mentor", "authorized_educator", "assigned_admin"],
            required_for_submission=False,
        )
    )
    return dict(
        format="3du.mapping.configuration",
        schema_version=1,
        runtime=dict(mindpal_required=False),
        steps=[
            dict(
                id=k,
                order=i + 1,
                depends_on=STEP_IDS[:i],
                label="SYNTHETIC " + k,
                system_instructions="SYNTHETIC private system instructions",
                task_instructions="SYNTHETIC private task instructions",
            )
            for i, k in enumerate(STEP_IDS)
        ],
        definitions={
            k: [f"SYNTHETIC {k} {i}" for i in range(n)]
            for k, n in [
                ("student_personas", 8),
                ("parent_personas", 5),
                ("empathy_categories", 17),
                ("evidence_types", 10),
                ("internal_journey_stages", 18),
                ("journey_stage_fields", 16),
                ("journey_markers", 6),
            ]
        },
        inputs=fields,
        public_report=dict(
            output_keys=MAP_KEYS,
            view_only=True,
            identical_version_and_content=True,
            expose_full_eighteen_stage_map=False,
            evidence_classifier_public=False,
        ),
        publication=dict(
            initial_approval_order=["assigned_admin", "involved_mentor"],
            later_approvals=["assigned_admin"],
            same_exact_version_required=True,
            no_mentor_bypass=True,
        ),
        portal=dict(stage_names=STAGES, always_accessible_stage=9),
        submission=dict(maximum_submissions_per_entry=2, resubmission_updates_existing_entry=True),
        unresolved=["SYNTHETIC professional-note applicability"],
        excluded=["career_fit"],
    )


def install(app, tmp_path):
    raw = json.dumps(contract()).encode()
    path = tmp_path / "synthetic-config.json"
    path.write_bytes(raw)
    runner = app.test_cli_runner()
    grant = runner.invoke(
        args=[
            "grant-mapping-setup",
            "--actor-email",
            "admin@example.test",
            "--authorized-by",
            "admin@example.test",
            "--reason",
            "SYNTHETIC authorization",
        ]
    )
    assert grant.exit_code == 0, grant.output
    result = runner.invoke(
        args=[
            "import-3du-mapping",
            str(path),
            "--actor-email",
            "admin@example.test",
            "--reason",
            "SYNTHETIC owner-approved bootstrap",
        ]
    )
    assert result.exit_code == 0, result.output
    return path


@pytest.mark.parametrize(
    "mutation",
    [
        lambda c: c["runtime"].update(mindpal_required=True),
        lambda c: c["public_report"].update(expose_full_eighteen_stage_map=True),
        lambda c: c["public_report"].update(output_keys=[]),
        lambda c: c["publication"].update(initial_approval_order=["assigned_admin"]),
        lambda c: c["inputs"][0].update(required_for_submission=False),
        lambda c: c["submission"].update(maximum_submissions_per_entry=3),
        lambda c: c["steps"].reverse(),
    ],
)
def test_invalid_contract_rejected(mutation):
    c = contract()
    mutation(c)
    with pytest.raises(ValueError):
        parse_configuration(json.dumps(c).encode())


def test_bootstrap_repeatability_privacy_and_mandatory_intake(app, tmp_path):
    path = install(app, tmp_path)
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "import-3du-mapping",
            str(path),
            "--actor-email",
            "admin@example.test",
            "--reason",
            "SYNTHETIC repeat",
        ]
    )
    assert result.exit_code == 0
    conn = sqlite3.connect(app.config["DATABASE"])
    assert conn.execute("SELECT COUNT(*) FROM mapping_imports").fetchone()[0] == 1
    conn.close()
    student = login(app.test_client(), "student@example.test")
    assert student.get("/admin/setup/mapping").status_code == 403
    assert student.get("/api/admin/mapping-specification").status_code == 403
    endpoint = "/api/students/1/intake"
    save = post(
        student, endpoint, dict(action="save", expected_version=0, request_key="save", values={})
    )
    assert save.status_code == 200
    invalid = post(
        student, endpoint, dict(action="submit", expected_version=1, request_key="bad", values={})
    )
    assert invalid.status_code == 400 and "Student Responses" in invalid.json["error"]
    values = {label: "SYNTHETIC unknown" for label in MANDATORY["student"]}
    valid = post(
        student,
        endpoint,
        dict(action="submit", expected_version=1, request_key="good", values=values),
    )
    assert valid.status_code == 200, valid.json
    assert "system instructions" not in json.dumps(student.get(endpoint).json)
    parent = login(app.test_client(), "parent@example.test")
    assert (
        post(
            parent,
            endpoint,
            dict(
                action="submit",
                expected_version=0,
                request_key="parent",
                values={"Parent Responses": "SYNTHETIC"},
            ),
        ).status_code
        == 400
    )
    assert all(f["label"] in MANDATORY["parent"] for f in parent.get(endpoint).json["fields"])
    admin = login(app.test_client())
    assert "SYNTHETIC unknown" in admin.get("/admin/students/1").text
    assert "Professional-note applicability" in admin.get("/admin/students/1").text


def test_setup_capability_and_browser_state_transitions(app, tmp_path):
    admin = login(app.test_client())
    assert admin.get("/admin/setup/mapping").status_code == 403
    install(app, tmp_path)
    assert admin.get("/admin/setup/mapping").status_code == 200
    response = admin.post(
        "/api/admin/setup/mapping",
        data={
            "csrf": csrf(admin),
            "reason": "SYNTHETIC owner revision",
            "configuration": (io.BytesIO(json.dumps(contract()).encode()), "config.json"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    url = "/api/admin/setup/mapping/1/"
    assert (
        admin.post(url + "activate", data={"csrf": csrf(admin), "reason": "SYNTHETIC"}).status_code
        == 409
    )
    assert (
        admin.post(
            url + "validate", data={"csrf": csrf(admin), "reason": "SYNTHETIC validation"}
        ).status_code
        == 302
    )
    assert (
        admin.post(url + "approve", data={"csrf": csrf(admin), "reason": "SYNTHETIC"}).status_code
        == 400
    )
    assert (
        admin.post(
            url + "approve",
            data={
                "csrf": csrf(admin),
                "reason": "SYNTHETIC owner approval",
                "owner_approved": "yes",
            },
        ).status_code
        == 302
    )
    assert (
        admin.post(
            url + "activate", data={"csrf": csrf(admin), "reason": "SYNTHETIC activation"}
        ).status_code
        == 302
    )
    stranger = login(app.test_client(), "unassigned@example.test")
    assert stranger.get("/admin/setup/mapping").status_code == 403
    configuration = admin.get("/api/admin/config").json
    assert (
        post(
            stranger,
            "/api/admin/config",
            dict(
                version=configuration["version"],
                configuration=configuration["configuration"],
                reason="SYNTHETIC bypass",
            ),
        ).status_code
        == 403
    )


def test_mentor_notes_are_mandatory_private_persistent_and_scoped(app, tmp_path):
    install(app, tmp_path)
    mentor = login(app.test_client(), "mentor@example.test")
    endpoint = "/mentor/students/1/inputs"
    assert mentor.get(endpoint).status_code == 200
    assert (
        mentor.post(
            endpoint,
            data={
                "csrf": csrf(mentor),
                "expected_version": "0",
                "action": "save",
                "Mentor Notes": "",
            },
        ).status_code
        == 302
    )
    assert (
        mentor.post(
            endpoint,
            data={
                "csrf": csrf(mentor),
                "expected_version": "1",
                "action": "submit",
                "Mentor Notes": "",
            },
        ).status_code
        == 400
    )
    assert (
        mentor.post(
            endpoint,
            data={
                "csrf": csrf(mentor),
                "expected_version": "1",
                "action": "submit",
                "Mentor Notes": "SYNTHETIC private mentor statement",
            },
        ).status_code
        == 302
    )
    assert "SYNTHETIC private mentor statement" in mentor.get(endpoint).text
    assert (
        mentor.post(
            endpoint,
            data={
                "csrf": csrf(mentor),
                "expected_version": "1",
                "action": "submit",
                "Mentor Notes": "stale",
            },
        ).status_code
        == 409
    )
    for email in [
        "student@example.test",
        "parent@example.test",
        "stranger@example.test",
        "admin@example.test",
    ]:
        client = login(app.test_client(), email)
        assert client.get(endpoint).status_code == 403
    admin = login(app.test_client())
    assert "SYNTHETIC private mentor statement" in admin.get("/admin/students/1").text
    conn = sqlite3.connect(app.config["DATABASE"])
    assert conn.execute("SELECT COUNT(*) FROM professional_versions").fetchone()[0] == 1
    conn.close()


def test_shared_journeys_are_summary_only_and_legacy_arrays_not_exposed(app, tmp_path):
    install(app, tmp_path)
    admin = login(app.test_client())
    c = admin.get("/api/admin/config").json["configuration"]
    full = maps(c)
    with pytest.raises(ValueError):
        validate_maps(c, full)
    for role in ["student", "parent"]:
        full[role + "_journey"]["items"] = []
    assert validate_maps(c, full) == full
    # Isolated synthetic historical publication fixture; no production approval bypass.
    historical = maps(c)
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute(
        "INSERT INTO snapshots(id,student_id,version,inputs,created) VALUES(1,1,1,'{}','SYNTHETIC')"
    )
    conn.execute(
        "INSERT INTO runs(id,student_id,snapshot_id,config_version,status,created) VALUES(1,1,1,1,'complete','SYNTHETIC')"
    )
    conn.execute(
        "INSERT INTO reports(id,student_id,run_id,version,origin,maps,status,created) VALUES(1,1,1,1,'generated',?,'published','SYNTHETIC')",
        (json.dumps(historical),),
    )
    conn.execute(
        "INSERT INTO publications(student_id,report_id,actor_id,created) VALUES(1,1,4,'SYNTHETIC')"
    )
    conn.commit()
    conn.close()
    student = login(app.test_client(), "student@example.test")
    parent = login(app.test_client(), "parent@example.test")
    a = student.get("/api/students/1/report").json
    b = parent.get("/api/students/1/report").json
    assert a == b and len(a["maps"]) == 6
    assert a["maps"]["student_journey"]["items"] == []
    assert "SYNTHETIC internal_journey_stages" not in json.dumps(a)
    assert "SYNTHETIC private system" not in json.dumps(a)


def test_browser_report_editor_versions_content_and_clears_approvals(app):
    from conftest import approve, workflow

    admin = login(app.test_client())
    _, report_id, configuration, _, _ = workflow(app, admin)
    assert approve(admin, report_id).status_code == 200
    values = {
        "csrf": csrf(admin),
        "browser_editor": "1",
        "expected_version": "1",
        "reason": "SYNTHETIC wording correction",
    }
    for key, value in maps(configuration).items():
        values[key + "_summary"] = "SYNTHETIC revised shared summary"
        for index, item in enumerate(value["items"]):
            values[key + "_item_" + str(index)] = item["text"]
    result = admin.post(f"/api/admin/reports/{report_id}/edit", data=values)
    assert result.status_code == 302
    conn = sqlite3.connect(app.config["DATABASE"])
    new_id, version = conn.execute(
        "SELECT id,version FROM reports ORDER BY version DESC LIMIT 1"
    ).fetchone()
    assert version == 2
    assert (
        conn.execute("SELECT COUNT(*) FROM approvals WHERE report_id=?", (new_id,)).fetchone()[0]
        == 0
    )
    conn.close()


def test_private_backup_preserves_persistent_accounts(app):
    from pathlib import Path

    result = app.test_cli_runner().invoke(args=["backup-db"])
    assert result.exit_code == 0, result.output
    backups = list((Path(app.config["DATABASE"]).parent / "backups").glob("*.sqlite3"))
    assert len(backups) == 1
    conn = sqlite3.connect(backups[0])
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 8
    conn.close()
    assert backups[0].stat().st_mode & 0o777 == 0o600
