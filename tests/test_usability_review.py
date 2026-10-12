"""Usability improvements retain the existing authorization and publication rules."""

from conftest import completed, csrf, login


def test_signup_error_keeps_safe_details_and_clears_password(client):
    response = client.post(
        "/signup",
        data={
            "csrf": csrf(client),
            "name": "Synthetic Parent",
            "email": "parent-new@example.test",
            "role": "parent",
            "synthetic": "yes",
            "password": "short",
        },
    )
    assert response.status_code == 400
    assert 'value="Synthetic Parent"' in response.text
    assert 'value="parent-new@example.test"' in response.text
    assert 'value="parent" selected' in response.text
    assert 'role="alert"' in response.text
    assert 'value="short"' not in response.text
    assert "Show password" in response.text


def test_login_error_stays_on_form_and_preserves_email(client):
    response = client.post(
        "/login",
        data={
            "csrf": csrf(client),
            "email": "student@example.test",
            "password": "wrong-SYNTHETIC-password",
        },
    )
    assert response.status_code == 401
    assert 'value="student@example.test"' in response.text
    assert 'name="password"' in response.text
    assert "wrong-SYNTHETIC-password" not in response.text


def test_profile_progress_and_read_only_report_stage(app):
    student = login(app.test_client(), "student@example.test")
    profile = student.get("/student/stages/1").text
    assert "Not started" in profile
    assert "Next stage locked until completion approval" in profile
    assert 'aria-current="step"' in profile
    assert "student@example.test" in profile
    track = student.get("/student/stages/9").text
    assert "0 of 8 stages completed" in track
    assert "Continue your next available step" in track
    parent = login(app.test_client(), "parent@example.test")
    shared = parent.get("/parent/students/1").text
    assert "0 of 8 stages completed" in shared
    assert "Continue your next available step" not in shared
    completed(app)
    report_page = student.get("/student/stages/8").text
    assert 'class="stage-form' not in report_page
    assert "Your saved development notes" not in report_page
    assert "Your mentor and the 3DU team are reviewing your insights" in report_page


def test_mentor_daily_forms_are_labelled_and_unavailable_input_link_hidden(app):
    mentor = login(app.test_client(), "mentor@example.test")
    page = mentor.get("/mentor/students/1").text
    assert 'class="json-form' not in page
    assert 'name="reason"' in page
    assert 'name="text"' in page
    assert 'name="revision"' in page
    assert 'href="/mentor/students/1/inputs"' not in page
    assert mentor.get("/mentor/students/1/inputs").status_code == 409


def test_ungranted_admin_setup_link_hidden_and_server_denies(app):
    admin = login(app.test_client())
    assert 'href="/admin/setup/mapping"' not in admin.get("/admin/dashboard").text
    assert 'href="/admin/setup/mapping"' not in admin.get("/admin/students/1").text
    assert admin.get("/admin/setup/mapping").status_code == 403
    assert admin.get("/api/session").json["user"]["role"] == "admin"


def test_labelled_report_editor_accepts_ajax_fields_without_raw_json_editing(app):
    from conftest import maps, post, workflow

    admin = login(app.test_client())
    _, report_id, configuration, _, _ = workflow(app, admin)
    values = {
        "browser_editor": "1",
        "expected_version": 1,
        "reason": "SYNTHETIC shared wording edit",
    }
    for key, value in maps(configuration).items():
        values[key + "_summary"] = "SYNTHETIC changed shared wording"
        for index, item in enumerate(value["items"]):
            values[key + "_item_" + str(index)] = item["text"]
    response = post(admin, f"/api/admin/reports/{report_id}/edit", values)
    assert response.status_code == 200, response.json
    assert response.json["version"] == 2 and response.json["approvals"] == []
