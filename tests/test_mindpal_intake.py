"""Synthetic export fixtures exercise import and permissions; never real assessment content."""

import copy
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import login, post, workflow

from three_du.domain import mapping_gaps, step_schema, validate_output
from three_du.mindpal import (
    EMPATHY_CATEGORIES,
    LABELS,
    PARENT_FIELDS,
    STUDENT_FIELDS,
    compiled_instructions,
    parse_export,
)
from three_du.provider import JsonMappingProvider, ProviderFailure, ProviderUnavailable


def export_fixture():
    fields = [
        {
            "id": f"f{i}",
            "label": label,
            "type": "TEXT",
            "order": i,
            "required": label in ["Student Responses", "Parent Responses"],
            "config": None,
        }
        for i, label in enumerate(STUDENT_FIELDS | PARENT_FIELDS)
    ]
    nodes = [{"id": "intake", "label": "Input Collection", "HumanInputNode": {"Fields": fields}}]
    prompts = [
        "Use @[Input - Student](type=WORKFLOW_HUMAN_INPUT_FIELD&workflowHumanInputFieldId=f0). Preserve original statements.",
        "Use student options (SYNTHETIC Explorer, SYNTHETIC Reconsidering) and parent options (SYNTHETIC Collaborator). @[Evidence](type=WORKFLOW_NODE&workflowNodeId=n1)",
        "Map Says, Thinks, Does, Feels, Sees, Hears, Pains, Gains, Functional/Emotional/Social jobs, and explicit/latent/trust/privacy/support needs.",
        "Cover all 18 specified stages. Names intentionally not supplied in this SYNTHETIC fixture.",
    ]
    for i, label in enumerate(LABELS):
        nodes.append(
            {
                "id": f"n{i + 1}",
                "label": label,
                "AgentNode": {
                    "prompt": prompts[i],
                    "Agent": {"system": "SYNTHETIC private instruction", "outputFormat": None},
                },
            }
        )
    nodes.append({"id": "excluded", "label": "SYNTHETIC excluded scoring branch"})
    return {"title": "SYNTHETIC workflow", "Nodes": nodes, "Edges": []}


def imported(app, tmp_path):
    file = tmp_path / "synthetic-export.json"
    file.write_text(json.dumps(export_fixture()))
    result = app.test_cli_runner().invoke(
        args=[
            "import-mindpal",
            str(file),
            "--actor-email",
            "admin@example.test",
            "--reason",
            "SYNTHETIC source import",
        ]
    )
    assert result.exit_code == 0, result.output
    return file


def intake(c, values, action="submit", version=0, key="SYNTHETIC unique request"):
    return post(
        c,
        "/api/students/1/intake",
        {"action": action, "expected_version": version, "request_key": key, "values": values},
    )


def test_import_exact_source_and_partial_gaps(app, client, tmp_path):
    file = imported(app, tmp_path)
    login(client)
    conf = client.get("/api/admin/config").json["configuration"]
    assert conf["student_personas"] == ["SYNTHETIC Explorer", "SYNTHETIC Reconsidering"]
    assert conf["empathy_categories"] == EMPATHY_CATEGORIES
    assert conf["journey_stages"] == []
    assert mapping_gaps(conf, 2) == mapping_gaps(conf, 3) == []
    assert mapping_gaps(conf, 4) == ["eighteen journey_stages"]
    spec = client.get("/api/admin/mapping-specification").json["specification"]
    assert spec["excluded_nodes"] == ["SYNTHETIC excluded scoring branch"]
    assert 'input.intake_fields["Student Responses"]' in compiled_instructions(1, spec)
    result = app.test_cli_runner().invoke(
        args=[
            "import-mindpal",
            str(file),
            "--actor-email",
            "admin@example.test",
            "--reason",
            "SYNTHETIC retry",
        ]
    )
    assert result.exit_code == 0 and "already imported" in result.output
    assert client.get("/api/admin/config").json["version"] == 2
    conn = sqlite3.connect(app.config["DATABASE"])
    assert (
        json.loads(conn.execute("SELECT source_json FROM mapping_imports").fetchone()[0])
        == export_fixture()
    )
    conn.close()


def test_import_rejects_nonadmin_and_malformed_source(app, tmp_path):
    file = tmp_path / "bad.json"
    file.write_text("{}")
    runner = app.test_cli_runner()
    args = [
        "import-mindpal",
        str(file),
        "--actor-email",
        "student@example.test",
        "--reason",
        "SYNTHETIC",
    ]
    assert runner.invoke(args=args).exit_code != 0
    args[3] = "admin@example.test"
    assert runner.invoke(args=args).exit_code != 0
    invalid = export_fixture()
    invalid["Nodes"][2]["AgentNode"]["prompt"] = "No explicit persona list"
    with pytest.raises(ValueError):
        parse_export(json.dumps(invalid).encode())


def test_intake_persistence_same_entry_single_resubmission(app, client, tmp_path):
    imported(app, tmp_path)
    login(client, "student@example.test")
    first = intake(client, {"Student Responses": "SYNTHETIC interests"})
    assert first.status_code == 200 and first.json["submissions"] == 1
    # Repeated delivery returns the same persisted submission without consuming another attempt.
    repeat = intake(client, {"Student Responses": "SYNTHETIC interests"})
    assert repeat.json == first.json
    later = app.test_client()
    login(later, "student@example.test")
    assert later.get("/api/students/1/intake").json["entry"]["submitted"] == json.dumps(
        {"Student Responses": "SYNTHETIC interests"}, separators=(",", ":")
    )
    draft = intake(later, {"Student Responses": "SYNTHETIC revised"}, "save", 1, "draft-key")
    assert draft.json["submissions"] == 1
    assert (
        json.loads(later.get("/api/students/1/intake").json["entry"]["submitted"])[
            "Student Responses"
        ]
        == "SYNTHETIC interests"
    )
    revised = intake(
        later, {"Student Responses": "SYNTHETIC revised"}, version=2, key="revised-key"
    )
    assert revised.json["id"] == first.json["id"] and revised.json["submissions"] == 2
    assert (
        intake(
            later, {"Student Responses": "SYNTHETIC third"}, version=3, key="third-key"
        ).status_code
        == 409
    )
    assert later.get("/api/students/1/stages/1").json["status"] == "submitted"
    conn = sqlite3.connect(app.config["DATABASE"])
    assert conn.execute("SELECT COUNT(*) FROM intake_entries").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM intake_versions").fetchone()[0] == 2
    conn.close()


def test_parent_separation_admin_visibility_and_private_spec(app, client, tmp_path):
    imported(app, tmp_path)
    parent = app.test_client()
    login(parent, "parent@example.test")
    assert intake(parent, {"Student Responses": "forged"}).status_code == 400
    response = intake(parent, {"Parent Responses": "SYNTHETIC parent perspective"})
    assert response.status_code == 200
    assert parent.get("/api/students/5/intake").status_code == 403
    assert parent.get("/api/admin/mapping-specification").status_code == 403
    assert parent.get("/students/1/intake").status_code == 200
    assert "SYNTHETIC private instruction" not in parent.get("/api/students/1/report").text
    student = app.test_client()
    login(student, "student@example.test")
    assert student.get("/api/students/1/intake").json["entry"] is None
    login(client)
    page = client.get("/admin/students/1")
    assert page.status_code == 200 and "SYNTHETIC parent perspective" in page.text
    assert "SYNTHETIC private instruction" in page.text
    anonymous = app.test_client()
    assert anonymous.get("/api/students/1/intake").status_code == 401
    mentor = app.test_client()
    login(mentor, "mentor@example.test")
    assert mentor.get("/api/students/1/intake").status_code == 403


def test_concurrent_resubmission_uses_one_allowance(app, tmp_path):
    imported(app, tmp_path)
    first = app.test_client()
    login(first, "student@example.test")
    intake(first, {"Student Responses": "SYNTHETIC first"})
    clients = [app.test_client(), app.test_client()]
    for client in clients:
        login(client, "student@example.test")

    def submit(i):
        return intake(
            clients[i],
            {"Student Responses": f"SYNTHETIC revision {i}"},
            version=1,
            key=f"concurrent-{i}",
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit, [0, 1])) == [200, 409]


def test_partial_specs_allow_first_steps_but_not_journey_or_report(app, client, tmp_path):
    login(client)
    rid, report, conf, outputs, _ = workflow(app, client)
    # Current run remains valid with a partial mapping config; only step 4 has an unmet enumeration.
    conn = sqlite3.connect(app.config["DATABASE"])
    conf["journey_stages"] = []
    conn.execute("UPDATE settings SET body=?", (json.dumps(conf),))
    conn.commit()
    conn.close()
    response = post(
        client,
        f"/api/admin/runs/{rid}/steps/1",
        {
            "expected_attempt": 1,
            "reason": "SYNTHETIC",
            "summary": "SYNTHETIC classifier",
            "output": outputs[0],
        },
    )
    assert response.json["status"] == "valid"
    assert (
        post(
            client,
            f"/api/admin/runs/{rid}/generate/4",
            {"expected_attempt": 1, "reason": "SYNTHETIC"},
        ).status_code
        == 409
    )
    assert (
        post(
            client, f"/api/admin/runs/{rid}/reports", {"from_workflow": True, "reason": "SYNTHETIC"}
        ).status_code
        == 409
    )


def test_provider_generation_validates_output_and_private_context(app, client):
    login(client)
    rid, _, conf, outputs, _ = workflow(app, client)

    class Provider:
        def generate(self, step, incoming, spec):
            assert "snapshot" in incoming and "upstream" in incoming
            assert "output_schema" in spec
            return copy.deepcopy(outputs[0])

    app.config["MAPPING_PROVIDER"] = Provider()
    result = post(
        client, f"/api/admin/runs/{rid}/generate/1", {"expected_attempt": 1, "reason": "SYNTHETIC"}
    )
    assert result.json["status"] == "valid"

    class BadProvider:
        def generate(self, *args):
            return {"invented": "SYNTHETIC invalid output"}

    app.config["MAPPING_PROVIDER"] = BadProvider()
    result = post(
        client, f"/api/admin/runs/{rid}/generate/1", {"expected_attempt": 2, "reason": "SYNTHETIC"}
    )
    assert result.json["status"] == "invalid"
    assert (
        post(
            client, f"/api/admin/runs/{rid}/reports", {"from_workflow": True, "reason": "SYNTHETIC"}
        ).status_code
        == 409
    )


def test_provider_response_and_secrets_are_not_leaked(monkeypatch):
    monkeypatch.setenv("MAPPING_API_KEY", "SYNTHETIC secret")
    monkeypatch.setenv("MAPPING_MODEL", "SYNTHETIC model")
    monkeypatch.setenv("MAPPING_ENDPOINT", "http://unsafe.example.test")
    with pytest.raises(ProviderUnavailable):
        JsonMappingProvider().generate(1, {}, {})
    monkeypatch.setenv("MAPPING_ENDPOINT", "https://api.example.test/generate")

    class Broken:
        def open(self, request, timeout):
            import urllib.error

            assert timeout == 45
            raise urllib.error.HTTPError(request.full_url, 403, "SYNTHETIC secret", None, None)

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: Broken())
    spec = parse_export(json.dumps(export_fixture()).encode())
    spec["output_schema"] = {}
    with pytest.raises(ProviderFailure) as exc:
        JsonMappingProvider().generate(1, {}, spec)
    assert "403" in str(exc.value) and "SYNTHETIC secret" not in str(exc.value)


def test_six_map_preview_excludes_internal_trace(app, client):
    login(client)
    rid, _, _, _, _ = workflow(app, client)
    response = post(
        client,
        f"/api/admin/runs/{rid}/reports",
        {"from_workflow": True, "reason": "SYNTHETIC human preview"},
    )
    assert response.status_code == 200
    conn = sqlite3.connect(app.config["DATABASE"])
    origin, maps = conn.execute(
        "SELECT origin,maps FROM reports WHERE id=?", (response.json["id"],)
    ).fetchone()
    assert origin == "generated"
    assert len(json.loads(maps)) == 6
    assert not any(
        key in maps for key in ["supporting_evidence", "confidence", "assumptions_to_validate"]
    )
    conn.close()


def test_import_profile_schema_keeps_source_persona_details(app, client, tmp_path):
    imported(app, tmp_path)
    login(client)
    conf = client.get("/api/admin/config").json["configuration"]
    schema = step_schema(2, conf)
    assert "trust_requirements" in schema["properties"]["parent"]["required"]
    trace = {
        "supporting_evidence": [],
        "confidence": 0.2,
        "missing_evidence": ["SYNTHETIC gap"],
        "assumptions_to_validate": [],
        "selected_hypothesis": None,
        "alternatives": [],
        "needs": [],
        "barriers": [],
        "goals": [],
        "pain_points": [],
        "behavioral_traits": [],
        "trust_requirements": [],
    }
    validate_output(2, conf, {"student": trace, "parent": trace}, [])
    wrong = copy.deepcopy(trace)
    wrong["selected_hypothesis"] = "SYNTHETIC Collaborator"
    with pytest.raises(ValueError, match="requires evidence"):
        validate_output(2, conf, {"student": trace, "parent": wrong}, [])


def test_generation_rechecks_evidence_after_provider_returns(app, client):
    login(client)
    rid, _, _, outputs, eid = workflow(app, client)

    class ChangingProvider:
        def generate(self, *args):
            conn = sqlite3.connect(app.config["DATABASE"])
            conn.execute(
                "UPDATE evidence SET statement='SYNTHETIC changed during provider call' WHERE id=?",
                (eid,),
            )
            conn.commit()
            conn.close()
            return outputs[0]

    app.config["MAPPING_PROVIDER"] = ChangingProvider()
    response = post(
        client, f"/api/admin/runs/{rid}/generate/1", {"expected_attempt": 1, "reason": "SYNTHETIC"}
    )
    assert response.status_code == 409
    assert len(client.get(f"/api/admin/runs/{rid}").json["steps"]) == 4


def test_required_intake_validation_does_not_consume_allowance(app, client, tmp_path):
    imported(app, tmp_path)
    login(client, "student@example.test")
    result = intake(client, {}, key="missing-required")
    assert result.status_code == 400
    assert client.get("/api/students/1/intake").json["entry"] is None
    first = intake(client, {"Student Responses": "SYNTHETIC valid"}, key="valid")
    assert first.json["submissions"] == 1


def test_parent_resubmission_is_separate_from_student_stage_completion(app, tmp_path):
    imported(app, tmp_path)
    client = app.test_client()
    login(client, "parent@example.test")
    assert intake(client, {"Parent Responses": "SYNTHETIC first parent view"}).status_code == 200
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("UPDATE stages SET status='complete' WHERE student_id=1 AND stage=1")
    conn.commit()
    conn.close()
    result = intake(
        client,
        {"Parent Responses": "SYNTHETIC revised parent view"},
        version=1,
        key="parent-revision",
    )
    assert result.status_code == 200 and result.json["submissions"] == 2


def test_reused_request_key_cannot_silently_discard_changed_content(app, client, tmp_path):
    imported(app, tmp_path)
    login(client, "student@example.test")
    assert intake(client, {"Student Responses": "SYNTHETIC original"}).status_code == 200
    result = intake(client, {"Student Responses": "SYNTHETIC changed"})
    assert result.status_code == 409
    entry = client.get("/api/students/1/intake").json["entry"]
    assert entry["submissions"] == 1
    assert "SYNTHETIC original" in entry["submitted"]


def prompt_fixture():
    from three_du.mindpal import JOURNEY_FIELDS

    bullets = lambda values: "\n".join("- " + value for value in values)
    stages = "\n".join(f"{i}. SYNTHETIC analytical stage {i}" for i in range(1, 19))
    return (
        "# 1. Required inputs\nAllow blank inputs.\n"
        "# 2. Node 1: Evidence Classifier\nEvidence types:\n"
        + bullets(
            [
                "Stated fact",
                "Stated preference",
                "Observed behaviour",
                "Direct quotation",
                "Constraint",
                "Parent expectation",
                "Student expectation",
                "Assumption",
                "Contradiction",
                "Missing evidence",
            ]
        )
        + "\nOutput a table and structured JSON.\n"
        "# 3. Node 2: Persona Identifier\nStudent persona options:\n"
        + bullets(["SYNTHETIC Explorer", "SYNTHETIC Reconsidering"])
        + "\nParent persona options:\n- SYNTHETIC Collaborator\nFor each selected persona show:\n- Goals\n"
        "# 4. Node 3: Empathy and Need Mapper\nInclude:\n"
        + bullets(EMPATHY_CATEGORIES + ["Digital-service needs"])
        + "\nFor every insight show:\n- Source\nSeparate these concepts:\n"
        + bullets(
            [
                "Warmth",
                "Engagement",
                "Discovery quality",
                "Convenience",
                "Parent transparency",
                "Student privacy",
            ]
        )
        + "\nDefine warmth as:\n- Psychological safety\n- Continuity across interactions\n"
        "# 5. Node 4: User-Journey Mapper\nUse these stages:\n"
        + stages
        + "\nFor every stage show:\n"
        + bullets(JOURNEY_FIELDS)
        + "\nMark:\n- SYNTHETIC human intervention marker\n"
        "# 6. Node 5: Career Evidence Normaliser\nEXCLUDED SYNTHETIC SCORING INSTRUCTION\n"
    )


def test_supplement_resolves_stages_and_keeps_other_prompt_instructions_inert(
    app, client, tmp_path
):
    from three_du.mindpal import supplement_mapping

    file = imported(app, tmp_path)
    prompt = tmp_path / "synthetic-prompt.txt"
    prompt.write_text(prompt_fixture())
    spec = supplement_mapping(parse_export(file.read_bytes()), prompt.read_bytes())
    assert len(spec["journey_stages"]) == 18
    assert all(not field["required"] for field in spec["fields"])
    assert "Digital-service needs" in spec["empathy_categories"]
    assert "EXCLUDED SYNTHETIC SCORING" not in json.dumps(spec["steps"])
    result = app.test_cli_runner().invoke(
        args=[
            "import-mindpal",
            str(file),
            "--mapping-prompt",
            str(prompt),
            "--actor-email",
            "admin@example.test",
            "--reason",
            "SYNTHETIC supplied mapping definitions",
        ]
    )
    assert result.exit_code == 0, result.output
    login(client)
    conf = client.get("/api/admin/config").json["configuration"]
    assert mapping_gaps(conf) == []
    assert conf["readiness"] is None
    student = app.test_client()
    login(student, "student@example.test")
    blank = intake(student, {})
    assert blank.status_code == 200
    assert student.get("/api/students/1/report").json["status"] == "pending"
    conn = sqlite3.connect(app.config["DATABASE"])
    assert (
        "EXCLUDED SYNTHETIC SCORING"
        in conn.execute(
            "SELECT source_prompt FROM mapping_imports ORDER BY id DESC LIMIT 1"
        ).fetchone()[0]
    )
    assert conn.execute("SELECT config_version FROM intake_entries").fetchone()[0] == 3
    conn.close()


def test_supplement_rejects_incomplete_or_conflicting_stage_lists(tmp_path):
    from three_du.mindpal import supplement_mapping

    spec = parse_export(json.dumps(export_fixture()).encode())
    prompt = prompt_fixture().replace(
        "18. SYNTHETIC analytical stage 18", "19. SYNTHETIC analytical stage 18"
    )
    with pytest.raises(ValueError, match="eighteen"):
        supplement_mapping(spec, prompt.encode())
    prompt = prompt_fixture().replace("SYNTHETIC Collaborator", "SYNTHETIC invented persona")
    with pytest.raises(ValueError, match="conflict"):
        supplement_mapping(spec, prompt.encode())


def test_full_supplied_four_step_contract_can_publish_only_after_both_approvals(
    app, client, tmp_path
):
    from conftest import approve, publish

    login(client)
    _, _, _, original, _ = workflow(app, client)
    export = tmp_path / "full-fixture.json"
    export.write_text(json.dumps(export_fixture()))
    prompt = tmp_path / "full-fixture-prompt.txt"
    prompt.write_text(prompt_fixture())
    result = app.test_cli_runner().invoke(
        args=[
            "import-mindpal",
            str(export),
            "--mapping-prompt",
            str(prompt),
            "--actor-email",
            "admin@example.test",
            "--reason",
            "SYNTHETIC integration",
        ]
    )
    assert result.exit_code == 0, result.output
    conf = client.get("/api/admin/config").json["configuration"]
    conn = sqlite3.connect(app.config["DATABASE"])
    snap = conn.execute("SELECT id FROM snapshots ORDER BY id DESC LIMIT 1").fetchone()[0]
    fact = conn.execute("SELECT id FROM evidence WHERE stakeholder='mentor'").fetchone()[0]
    conn.close()
    for kind in ["assessments", "mentor_interview", "activities"]:
        assert (
            post(
                client,
                f"/api/admin/snapshots/{snap}/readiness",
                {"kind": kind, "evidence_ids": [fact], "reason": "SYNTHETIC criteria review"},
            ).status_code
            == 200
        )
    run = post(client, "/api/admin/students/1/runs", {"reason": "SYNTHETIC"})
    assert run.json["status"] == "pending"
    rid = run.json["id"]
    out = copy.deepcopy(original[0])
    out["evidence"][0]["evidence_type"] = "Assumption"
    out["evidence"][1]["evidence_type"] = "Stated fact"
    trace = {
        "supporting_evidence": [],
        "confidence": 0.1,
        "missing_evidence": ["SYNTHETIC limitation"],
        "assumptions_to_validate": [],
    }
    persona = dict(
        trace,
        selected_hypothesis=None,
        alternatives=[],
        needs=[],
        barriers=[],
        **{key: [] for key in conf["mapping_details"]["persona_details"]},
    )
    empathy = {
        role: [
            dict(
                trace,
                category=category,
                insight_basis="missing evidence",
                source="SYNTHETIC",
                text="SYNTHETIC reviewed text",
                validation_status="needs validation",
            )
            for category in conf["empathy_categories"]
        ]
        for role in ["student", "parent"]
    }
    empathy["factors"] = {
        role: {
            key: dict(
                trace,
                text="SYNTHETIC private factor",
                source="SYNTHETIC",
                validation_status="needs validation",
            )
            for key in conf["mapping_details"]["empathy_factors"]
        }
        for role in ["student", "parent"]
    }
    journey = {
        role: [
            dict(
                trace,
                stage=stage,
                fields={key: "SYNTHETIC reviewed journey" for key in conf["journey_fields"]},
            )
            for stage in conf["journey_stages"]
        ]
        for role in ["student", "parent"]
    }
    outputs = [out, {"student": persona, "parent": persona}, empathy, journey]

    class Provider:
        def generate(self, step, incoming, spec):
            assert len(spec["steps"]) == 4
            assert "EXCLUDED SYNTHETIC SCORING" not in json.dumps(spec["steps"])
            return outputs[step - 1]

    app.config["MAPPING_PROVIDER"] = Provider()
    for n in range(1, 5):
        generated = post(
            client,
            f"/api/admin/runs/{rid}/generate/{n}",
            {"expected_attempt": 0, "reason": "SYNTHETIC"},
        )
        assert generated.json["status"] == "valid", generated.json
    report = post(
        client,
        f"/api/admin/runs/{rid}/reports",
        {"from_workflow": True, "reason": "SYNTHETIC reviewed preview"},
    )
    assert report.status_code == 200
    version = report.json["version"]
    report_id = report.json["id"]
    assert publish(client, report_id, version).status_code == 409
    assert approve(client, report_id, version).status_code == 200
    assert publish(client, report_id, version).status_code == 409
    mentor = app.test_client()
    login(mentor, "mentor@example.test")
    assert approve(mentor, report_id, version).status_code == 200
    assert publish(client, report_id, version).status_code == 200
    student, parent = app.test_client(), app.test_client()
    login(student, "student@example.test")
    login(parent, "parent@example.test")
    public = student.get("/api/students/1/report").json
    assert public == parent.get("/api/students/1/report").json
    assert len(public["maps"]["student_journey"]["items"]) == 18
    assert "private factor" not in json.dumps(public)
    assert "confidence" not in json.dumps(public)
    assert "fit_score" not in json.dumps(public)


def test_unrelated_intake_does_not_reveal_student_existence(app, client, tmp_path):
    imported(app, tmp_path)
    login(client, "parent@example.test")
    existing = client.get("/api/students/5/intake")
    absent = client.get("/api/students/99999/intake")
    assert existing.status_code == absent.status_code == 403
    assert existing.json == absent.json


def test_missing_parent_evidence_cannot_force_a_persona(app, client, tmp_path):
    imported(app, tmp_path)
    login(client)
    conf = client.get("/api/admin/config").json["configuration"]
    trace = {
        "supporting_evidence": [],
        "confidence": 0.1,
        "missing_evidence": ["SYNTHETIC missing data"],
        "assumptions_to_validate": [],
        "selected_hypothesis": None,
        "alternatives": [],
        "needs": [],
        "barriers": [],
        "goals": [],
        "pain_points": [],
        "behavioral_traits": [],
        "trust_requirements": [],
    }
    parent = copy.deepcopy(trace)
    parent.update(selected_hypothesis="SYNTHETIC Collaborator", supporting_evidence=[1])
    records = [{"id": 1, "stakeholder": "parent", "type": "missing evidence", "statement": ""}]
    with pytest.raises(ValueError, match="requires evidence"):
        validate_output(2, conf, {"student": trace, "parent": parent}, records)


def test_profile_review_uses_submitted_intake_and_legacy_api_cannot_bypass_limit(
    app, client, tmp_path
):
    imported(app, tmp_path)
    student = app.test_client()
    login(student, "student@example.test")
    first = intake(student, {"Student Responses": "SYNTHETIC submitted profile"})
    assert first.status_code == 200
    stage_before = student.get("/api/students/1/stages/1").json
    assert stage_before["draft"]["Student Responses"] == "SYNTHETIC submitted profile"
    assert (
        intake(
            student, {"Student Responses": "SYNTHETIC unsent revision"}, "save", 1, "revision-draft"
        ).status_code
        == 200
    )
    assert student.get("/api/students/1/stages/1").json == stage_before
    assert (
        post(
            student,
            "/api/students/1/stages/1",
            {
                "action": "submit",
                "revision": stage_before["revision"],
                "draft": {"Student Responses": "SYNTHETIC bypass"},
            },
        ).status_code
        == 409
    )
    conn = sqlite3.connect(app.config["DATABASE"])
    conf = json.loads(conn.execute("SELECT body FROM settings").fetchone()[0])
    conf["stage_rules"]["1"] = {
        "approvers": ["admin"],
        "requires_submission": True,
        "required_draft_fields": ["Student Responses"],
        "description": "SYNTHETIC configured profile criterion",
    }
    conn.execute("UPDATE settings SET body=?", (json.dumps(conf),))
    conn.commit()
    conn.close()
    login(client)
    approved = client.post(
        "/api/students/1/stages/1/approve",
        data={
            "csrf": client.get("/api/session").json["csrf"],
            "revision": str(stage_before["revision"]),
            "reason": "SYNTHETIC exact submitted profile review",
        },
    )
    assert approved.status_code == 200 and approved.json["status"] == "complete"
    assert student.get("/api/students/1/progress").json["stages"][1]["available"]
    assert (
        intake(
            student,
            {"Student Responses": "SYNTHETIC post-completion edit"},
            "save",
            2,
            "after-completion",
        ).status_code
        == 409
    )
