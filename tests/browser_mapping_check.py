"""Chromium mapping checks with supplied private sources and isolated synthetic records."""

import argparse
import os
import socket
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--export", required=True)
parser.add_argument("--prompt", required=True)
args = parser.parse_args()
EXPORT = args.export
with tempfile.TemporaryDirectory(prefix="mapping-browser-") as t:
    env = dict(
        os.environ,
        DATABASE_PATH=t + "/test.sqlite3",
        RECOVERY_DIR=t + "/recovery",
        SYNTHETIC_ONLY="1",
    )
    base = [str(ROOT / ".venv/bin/python"), "-m", "flask", "--app", "three_du:create_app"]

    def cli(*args):
        r = subprocess.run(base + list(args), cwd=ROOT, env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr + r.stdout

    cli("init-db")
    password = "SYNTHETIC-browser-password-123!"
    for email, role in [
        ("admin@synthetic.test", "admin"),
        ("student@synthetic.test", "student"),
        ("parent@synthetic.test", "parent"),
    ]:
        cli(
            "provision",
            "--email",
            email,
            "--role",
            role,
            "--reason",
            "SYNTHETIC browser fixture",
            "--password",
            password,
        )
    for email in ["admin@synthetic.test", "parent@synthetic.test"]:
        cli(
            "authorize",
            "--actor-email",
            email,
            "--student-email",
            "student@synthetic.test",
            "--reason",
            "SYNTHETIC authorized relationship",
        )
    cli(
        "import-mindpal",
        EXPORT,
        "--mapping-prompt",
        args.prompt,
        "--actor-email",
        "admin@synthetic.test",
        "--reason",
        "Supplied private configuration; SYNTHETIC browser records only",
    )
    conn = sqlite3.connect(env["DATABASE_PATH"])
    sid = conn.execute("SELECT id FROM users WHERE role='student'").fetchone()[0]
    conn.close()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    log = open(t + "/server.log", "w")
    server = subprocess.Popen(
        base + ["run", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=log,
    )
    try:
        for i in range(40):
            try:
                urllib.request.urlopen(url, timeout=1)
                break
            except OSError:
                time.sleep(0.15)
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
            )

            def sign_in(page, email, admin=False):
                page.goto(url + ("/admin/login" if admin else "/login"))
                page.locator("input[name=email]").fill(email)
                page.locator("input[name=password]").fill(password)
                page.locator("form button").filter(has_text="Sign in").first.click()
                page.wait_for_load_state("networkidle")

            student = browser.new_page(viewport={"width": 1280, "height": 900})
            sign_in(student, "student@synthetic.test")
            student.goto(url + f"/students/{sid}/intake")
            for label in [
                "Student Responses",
                "Academic Information",
                "Activities and Interests",
                "Strengths",
            ]:
                student.locator('textarea[name="' + label + '"]').fill(
                    "SYNTHETIC " + label + " input"
                )
            student.get_by_role("button", name="Save draft", exact=True).click()
            student.wait_for_load_state("networkidle")
            expect(student.locator('textarea[name="Student Responses"]')).to_have_value(
                "SYNTHETIC Student Responses input"
            )
            student.get_by_role("button", name="Submit for review", exact=True).click()
            student.wait_for_load_state("networkidle")
            expect(student.get_by_text("1 of 2 submissions used.", exact=False)).to_be_visible()
            student.screenshot(path=t + "/intake-desktop.png", full_page=True)
            parent = browser.new_page(
                viewport={"width": 390, "height": 844}, reduced_motion="reduce"
            )
            sign_in(parent, "parent@synthetic.test")
            parent.goto(url + f"/students/{sid}/intake")
            assert parent.locator('textarea[name="Student Responses"]').count() == 0
            parent.locator('textarea[name="Parent Responses"]').fill(
                "SYNTHETIC private parent perspective"
            )
            parent.get_by_role("button", name="Submit for review", exact=True).click()
            parent.wait_for_load_state("networkidle")
            assert parent.evaluate("document.documentElement.scrollWidth <= innerWidth")
            parent.screenshot(path=t + "/intake-mobile.png", full_page=True)
            admin = browser.new_page()
            sign_in(admin, "admin@synthetic.test", True)
            admin.goto(url + f"/admin/students/{sid}")
            expect(
                admin.get_by_text("SYNTHETIC private parent perspective", exact=True).first
            ).to_be_visible()
            expect(
                admin.get_by_text("SYNTHETIC Student Responses input", exact=True).first
            ).to_be_visible()
            assert "LiveSwitch Career Decision Engine" in admin.content()
            # A labelled admin form reviews actual profile input, never an unsubmitted revision.
            conn = sqlite3.connect(env["DATABASE_PATH"])
            import json

            conf = json.loads(conn.execute("SELECT body FROM settings").fetchone()[0])
            conf["stage_rules"]["1"] = {
                "approvers": ["admin"],
                "requires_submission": True,
                "required_draft_fields": ["Student Responses"],
                "description": "SYNTHETIC profile completion criterion",
            }
            conn.execute("UPDATE settings SET body=?", (json.dumps(conf),))
            conn.commit()
            conn.close()
            admin.reload()
            admin.get_by_label("Completion review reason", exact=True).fill(
                "SYNTHETIC exact submitted profile review"
            )
            admin.get_by_role("button", name="Approve completion", exact=True).click()
            admin.wait_for_load_state("networkidle")
            stage_two = student.goto(url + "/student/stages/2")
            assert stage_two.status == 200
            student.goto(url + f"/students/{sid}/intake")
            assert student.get_by_role("button", name="Save draft", exact=True).count() == 0
            assert parent.request.get(url + "/api/admin/mapping-specification").status == 403
            parent.goto(url + f"/parent/students/{sid}")
            assert "selected persona" not in parent.content().lower()
            browser.close()
            print(
                "PASS: actual export and full mapping prompt import, desktop saved draft/submit, mobile parent-only input, admin visibility, private specification denial, reduced-motion and mobile overflow checks."
            )
    finally:
        server.terminate()
        server.wait(timeout=10)
        log.close()
