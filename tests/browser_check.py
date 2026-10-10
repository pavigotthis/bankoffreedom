"""Real Chromium smoke checks. Run with Python that has Playwright installed.
Creates an isolated temporary SQLite database; all accounts/data are synthetic.
"""

import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "SYNTHETIC-browser-password-123!"


def main():
    with tempfile.TemporaryDirectory(prefix="3du-browser-") as temp:
        env = dict(
            os.environ,
            DATABASE_PATH=temp + "/browser.sqlite3",
            RECOVERY_DIR=temp + "/recovery",
            SYNTHETIC_ONLY="1",
        )
        base = [str(ROOT / ".venv/bin/python"), "-m", "flask", "--app", "three_du:create_app"]

        def cli(*args):
            r = subprocess.run(base + list(args), env=env, cwd=ROOT, capture_output=True, text=True)
            assert r.returncode == 0, r.stderr + r.stdout

        cli("init-db")
        for email, role in [
            ("admin@synthetic.test", "admin"),
            ("parent@synthetic.test", "parent"),
            ("mentor@synthetic.test", "mentor"),
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
                PASSWORD,
            )
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        log = open(temp + "/server.log", "w")
        server = subprocess.Popen(
            base + ["run", "--host", "127.0.0.1", "--port", str(port)],
            env=env,
            cwd=ROOT,
            stdout=log,
            stderr=log,
        )
        try:
            for _ in range(100):
                try:
                    with urllib.request.urlopen(url + "/health", timeout=1) as r:
                        if r.status == 200:
                            break
                except OSError:
                    time.sleep(0.1)
            else:
                raise AssertionError("Server failed to start")
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    executable_path=os.getenv("CHROMIUM_PATH", "/usr/bin/chromium"),
                    headless=True,
                    args=["--no-sandbox"],
                )
                context = browser.new_context(
                    viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
                )
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(url)
                expect(
                    page.get_by_role(
                        "heading", name="Start with who you are. Explore what’s possible."
                    )
                ).to_be_visible()
                page.keyboard.press("Tab")
                expect(page.get_by_role("link", name="Skip to content")).to_be_focused()
                assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.locator("h1").click()
                page.screenshot(path="/tmp/3du-home-desktop.png", full_page=True)
                page.goto(url + "/signup")
                page.get_by_label("Email address").fill("student@synthetic.test")
                page.get_by_label("Password (at least 12 characters)").fill(PASSWORD)
                page.get_by_label("I will use fictional development data only.").check()
                page.get_by_role("button", name="Create development account").click()
                page.wait_for_url("**/student/stages/1")
                page.get_by_label("Your saved development notes").fill("SYNTHETIC browser draft")
                page.get_by_role("button", name="Save draft", exact=True).click()
                expect(page.get_by_text("Draft · revision 1")).to_be_visible()
                page.reload()
                expect(page.get_by_label("Your saved development notes")).to_have_value(
                    "SYNTHETIC browser draft"
                )
                page.get_by_role("button", name="Submit for review").click()
                expect(page.get_by_text("Submitted · revision 2")).to_be_visible()
                page.get_by_role("link", name="Next stage", exact=True).click()
                expect(
                    page.get_by_text("This stage will open once you complete the previous stage.")
                ).to_be_visible()
                page.get_by_role("link", name="Go to your next available action").click()
                page.wait_for_url("**/student/stages/1")
                for role in ["admin", "parent", "mentor"]:
                    cli(
                        "authorize",
                        "--actor-email",
                        role + "@synthetic.test",
                        "--student-email",
                        "student@synthetic.test",
                        "--reason",
                        "SYNTHETIC browser relationship",
                    )
                page.set_viewport_size({"width": 390, "height": 844})
                page.goto(url + "/student/stages/9")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                expect(
                    page.get_by_text(
                        "Your mentor and the 3DU team are reviewing your insights. Your results will appear here once approved."
                    )
                ).to_be_visible()
                page.screenshot(path="/tmp/3du-progress-mobile.png", full_page=True)
                page.get_by_role("button", name="Sign out").click()

                def sign_in(email):
                    page.goto(url + ("/admin/login" if email.startswith("admin@") else "/login"))
                    page.get_by_label("Email address").fill(email)
                    if email.startswith("admin@"):
                        page.get_by_role("button", name="Show password", exact=True).click()
                        expect(page.get_by_label("Password", exact=True)).to_have_attribute(
                            "type", "text"
                        )
                        page.get_by_role("button", name="Hide password", exact=True).click()
                        expect(page.get_by_label("Password", exact=True)).to_have_attribute(
                            "type", "password"
                        )
                    page.get_by_label("Password", exact=True).fill(PASSWORD)
                    page.get_by_role("button", name="Sign in", exact=True).click()

                sign_in("student@synthetic.test")
                page.wait_for_url("**/student/stages/1")
                expect(page.get_by_label("Your saved development notes")).to_have_value(
                    "SYNTHETIC browser draft"
                )
                page.get_by_role("button", name="Sign out").click()
                for role in ["parent", "mentor", "admin"]:
                    sign_in(role + "@synthetic.test")
                    page.get_by_role(
                        "link",
                        name={
                            "parent": "View shared progress",
                            "mentor": "Open workspace",
                            "admin": "Open workspace",
                        }[role],
                        exact=True,
                    ).click()
                    expect(page.get_by_role("link", name="Email support")).to_have_attribute(
                        "href", "mailto:prashasawan@gmail.com"
                    )
                    assert not page.locator('a[href^="tel:"]').count()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
                        role + " mobile overflow"
                    )
                    page.set_viewport_size({"width": 1440, "height": 1000})
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    if role == "admin":
                        expect(
                            page.get_by_role("heading", name="Generation is blocked")
                        ).to_be_visible()
                        page.locator("#evidence").fill(
                            json.dumps(
                                {
                                    "stakeholder": "student",
                                    "source": "SYNTHETIC browser fixture",
                                    "type": "assumption",
                                    "statement": "SYNTHETIC statement",
                                    "reason": "SYNTHETIC test",
                                }
                            )
                        )
                        page.get_by_role("button", name="Save attributed evidence").click()
                        expect(page.get_by_text("SYNTHETIC statement", exact=True)).to_be_visible()
                        page.locator("#snapshot").fill(json.dumps({"reason": "SYNTHETIC snapshot"}))
                        page.get_by_role("button", name="Save snapshot", exact=True).click()
                        expect(page.get_by_text("Snapshot 1", exact=False).first).to_be_visible()
                        page.locator("#run").fill(json.dumps({"reason": "SYNTHETIC blocked run"}))
                        page.get_by_role("button", name="Create versioned run").click()
                        expect(
                            page.locator(".form-status").filter(has_text="blocked:").first
                        ).to_be_visible()
                        page.reload()
                        expect(page.get_by_text("Run 1 · blocked", exact=False)).to_be_visible()
                        page.screenshot(path="/tmp/3du-admin-desktop.png", full_page=True)
                    page.get_by_role("button", name="Sign out").click()
                    page.set_viewport_size({"width": 390, "height": 844})
                page.goto(url + "/")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.screenshot(path="/tmp/3du-home-mobile.png", full_page=True)
                assert not errors, errors
                browser.close()
                print(
                    "PASS: desktop/mobile homepage and four portals; keyboard focus; reduced motion; signup/login/logout; draft save/submit/resume; locked Next; parent/mentor restriction states; dedicated admin login/password toggle/dashboard; admin evidence/snapshot/blocked run; support; no horizontal overflow or JavaScript errors."
                )
        finally:
            server.terminate()
            server.wait(timeout=10)
            log.close()


if __name__ == "__main__":
    main()
