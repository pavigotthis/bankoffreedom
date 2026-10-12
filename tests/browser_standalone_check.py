"""Supplied configuration, synthetic browser accounts; no hosted data or provider calls."""

import argparse
import os
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--configuration", required=True)
parser.add_argument("--skip-import", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="3du-standalone-browser-") as directory:
    env = dict(
        os.environ,
        DATABASE_PATH=directory + "/test.sqlite3",
        RECOVERY_DIR=directory + "/recovery",
        SYNTHETIC_ONLY="1",
    )
    base = [str(root / ".venv/bin/python"), "-m", "flask", "--app", "three_du:create_app"]

    def cli(*arguments):
        result = subprocess.run(
            base + list(arguments), cwd=root, env=env, text=True, capture_output=True
        )
        assert result.returncode == 0, result.stdout + result.stderr

    cli("init-db")
    password = "SYNTHETIC-browser-password-123!"
    for email, role in [
        ("admin@synthetic.test", "admin"),
        ("student@synthetic.test", "student"),
        ("parent@synthetic.test", "parent"),
        ("mentor@synthetic.test", "mentor"),
    ]:
        cli(
            "provision",
            "--email",
            email,
            "--role",
            role,
            "--password",
            password,
            "--reason",
            "SYNTHETIC browser fixture",
        )
    for email in ["admin@synthetic.test", "parent@synthetic.test", "mentor@synthetic.test"]:
        cli(
            "authorize",
            "--actor-email",
            email,
            "--student-email",
            "student@synthetic.test",
            "--reason",
            "SYNTHETIC relationship",
        )
    cli(
        "grant-mapping-setup",
        "--actor-email",
        "admin@synthetic.test",
        "--authorized-by",
        "admin@synthetic.test",
        "--reason",
        "SYNTHETIC trusted setup",
    )
    if not args.skip_import:
        cli(
            "import-3du-mapping",
            args.configuration,
            "--actor-email",
            "admin@synthetic.test",
            "--reason",
            "Supplied configuration with SYNTHETIC records",
        )
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    log = open(directory + "/server.log", "w")
    server = subprocess.Popen(
        base + ["run", "--host", "127.0.0.1", "--port", str(port)],
        cwd=root,
        env=env,
        stdout=log,
        stderr=log,
    )
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(url, timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
            )
            for width in [1280, 390]:
                context = browser.new_context(
                    viewport={"width": width, "height": 850}, reduced_motion="reduce"
                )
                page = context.new_page()

                def sign_in(email, admin=False):
                    page.goto(url + ("/admin/login" if admin else "/login"))
                    page.locator("input[name=email]").fill(email)
                    page.locator("input[name=password]").fill(password)
                    page.get_by_role("button", name="Sign in", exact=True).click()
                    page.wait_for_load_state("networkidle")

                page.goto(url + "/signup")
                expect(page.get_by_label("Your name", exact=True)).to_be_visible()
                assert (
                    page.get_by_label("Your name", exact=True).get_attribute("required") is not None
                )
                sign_in("student@synthetic.test")
                page.goto(url + "/account/name")
                page.get_by_label("Your name", exact=True).fill("SYNTHETIC Browser Student")
                page.get_by_role("button", name="Save name", exact=True).click()
                expect(page.get_by_role("status")).to_contain_text("Your name has been saved")
                page.reload()
                expect(page.get_by_label("Your name", exact=True)).to_have_value(
                    "SYNTHETIC Browser Student"
                )
                page.goto(url + "/student/stages/1")
                expect(page.get_by_label("Student Responses", exact=False)).to_be_visible()
                page.get_by_role("button", name="Submit for review", exact=True).click()
                expect(page.locator(".form-status")).to_contain_text("Complete required fields")
                page.get_by_label("Student Responses", exact=False).fill("SYNTHETIC saved draft")
                page.get_by_role("button", name="Save draft", exact=True).click()
                page.wait_for_load_state("networkidle")
                expect(page.get_by_label("Student Responses", exact=False)).to_have_value(
                    "SYNTHETIC saved draft"
                )
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.goto(url + "/admin/setup/mapping")
                expect(page.get_by_role("heading", name="Let’s pause here")).to_be_visible()
                context.close()
                context = browser.new_context(
                    viewport={"width": width, "height": 850}, reduced_motion="reduce"
                )
                page = context.new_page()
                sign_in("admin@synthetic.test", True)
                page.goto(url + "/admin/setup/mapping")
                expect(
                    page.get_by_role("heading", name="Independent mapping configuration")
                ).to_be_visible()
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.keyboard.press("Tab")
                assert page.evaluate("document.activeElement.tagName") != "BODY"
                context.close()
            browser.close()
        print(
            "Desktop/mobile browser checks passed: required validation, draft persistence, access denial, setup UI, keyboard focus, reduced-motion context, no horizontal overflow."
        )
    finally:
        server.terminate()
        server.wait(timeout=10)
        log.close()
