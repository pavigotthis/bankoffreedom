# Operate 3DU locally

Use fictional development data only. GitHub stores the code; to use the website interactively, run it on your own computer. No public website is deployed.

## 1. Download and start

Install Git and Python **3.12 or later**, then open a terminal.

```sh
git clone https://github.com/pavigotthis/bankoffreedom.git
cd bankoffreedom
```

Create and activate a virtual environment:

macOS/Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, skip activation and substitute `.\.venv\Scripts\python.exe` for `python` in the commands below. Do not change your machine's security policy just to activate a virtual environment.

With the environment active:

```sh
python -m pip install --no-deps -r requirements.lock
python -m pip check
python -m flask --app three_du:create_app init-db
python -m flask --app three_du:create_app run --host 127.0.0.1 --port 5000
```

Leave that terminal running. On **your own computer**, open a browser and enter `127.0.0.1:5000`. If port 5000 is already used, start with `--port 5001` and use that port instead.

## 2. Try the student experience

1. Choose **Begin exploring** / **Create account**.
2. Enter a fictional email and a password of at least 12 characters, select **Student**, and confirm fictional development use.
3. In **Create Profile**, enter fictional notes and choose **Save draft**.
4. Refresh the page: your saved draft remains.
5. Choose **Submit for review**. Status becomes submitted; this does not complete the stage.
6. Choose **Next stage**: it remains locked until valid completion approval. The return action leads back to your current work.
7. Choose **Track Progress** at any time. Before publication, the specified review-pending message appears.
8. Sign out and sign back in to verify resume behavior.

Default completion and mapping specifications are empty. The application will not invent rules to unlock stages or generate results.

## 3. Create the administrator account

Open a **second terminal** in the repository and activate the same virtual environment. Keep the server running in the first terminal.

```sh
python -m flask --app three_du:create_app provision --email admin@example.test --role admin --reason 'Authorized synthetic development administrator'
```

Enter and confirm a new password when prompted. There are no default passwords. To assign the fictional student you registered:

```sh
python -m flask --app three_du:create_app authorize --actor-email admin@example.test --student-email student@example.test --reason 'Assign synthetic student record'
```

Replace `student@example.test` with the exact fictional student account you created. In a separate browser profile/private window, sign in as `admin@example.test`. Open the assigned student workspace.

The admin can inspect saved work, record attributed evidence/corrections, save snapshots, record internal information requests and inspect runs/history. **Specification** holds approved completion/readiness rules and exact mapper enums. Missing configuration produces explicit blocked states. Use `README.md` for field schemas and the complete workflow.

Do not create real assessments, persona categories or journey enums to make those blocks disappear. Synthetic enums/rules exist only in isolated automated tests; they are not production requirements.

## 4. Try the parent portal

1. In another browser profile, sign up with a fictional **Parent** account.
2. In the operator terminal, authorize its synthetic link:

```sh
python -m flask --app three_du:create_app authorize --actor-email parent@example.test --student-email student@example.test --reason 'Authorize synthetic parent relationship'
```

Use your actual fictional account emails. Refresh the parent's workspace and choose **View shared progress**. Parents see the same shared progress/published report as the student, without raw work or internal records. This operator command is not a real guardian-verification procedure.

## 5. Try the mentor portal

```sh
python -m flask --app three_du:create_app provision --email mentor@example.test --role mentor --reason 'Authorized synthetic mentor'
python -m flask --app three_du:create_app authorize --actor-email mentor@example.test --student-email student@example.test --reason 'Record synthetic mentor involvement'
```

Sign in as that mentor. Involvement alone grants no raw draft-field access. Approved work scopes require explicit stage/field authorization; see `README.md`. Mentors can record their own relevant sessions and review an eligible admin-approved initial report, but cannot edit/regenerate maps.

## 6. Understand completion and reports

The real workflow becomes operational when the approved missing materials in `decisions.md` are supplied:

1. Configure stage-specific completion evidence and approver authority.
2. Review the exact work revision and approve completion; preceding-stage requirements still control navigation.
3. Supply exact mapper enums/fields and approved readiness criteria.
4. Save an immutable evidence/work snapshot and record source-backed assessment, mentor-interview and activity readiness confirmations.
5. Run and validate the four ordered mapping steps. No AI provider is currently configured; the provider action records a blocked attempt. Explicit operator-authored synthetic outputs can exercise validation independently.
6. Save six public maps as a separate draft version.
7. Admin reviews shared wording and approves the exact version.
8. An involved mentor approves that **same initial version**.
9. Admin publishes the eligible version. Student and linked parent then see identical, view-only maps.
10. Later edits create new drafts and require new admin approval; earlier publication stays intact. Fresh mentor approval is not required for later revisions.

Missing mentor approval never has an automatic bypass. Saving/submitting/completing a stage and publishing a report are different actions.

## 7. Run the verified synthetic checks

With the virtual environment active:

```sh
python -m pytest -q
python -m ruff check three_du tests
python -m mypy three_du
```

The automated suite uses temporary databases with clearly labelled synthetic content to exercise the full sequencing, access, versioning and initial/subsequent publication flow. It does not populate your normal application database. Real-browser checks are optional and require Playwright plus Chromium; see `README.md`.

## 8. Stop, resume and recover

- Stop the server with **Ctrl+C** in its terminal. Start it again using the same Flask run command.
- Work persists in `instance/3du.sqlite3`. Do not delete it to restart the website.
- To update code later, stop the server, run `git pull`, reinstall `requirements.lock`, run `init-db`, then restart. Preserve local code changes before pulling.
- **Recover account** prepares a private local recovery file under `instance/recovery/`. An authorized local operator can open the appropriate fictional account's `path` on the same local website. The token expires after 30 minutes and is single-use. No recovery email is sent.
- Support email uses `mailto:prashasawan@gmail.com`; the phone is an unavailable placeholder.

This is locally working development software. Live minor-data collection, real assessment/mapping generation, email delivery and production deployment require the missing approved specifications, policies and integrations.
