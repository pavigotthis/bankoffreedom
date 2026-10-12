# Update the existing PythonAnywhere site

This update uses the existing Flask/Python 3.12 installation and persistent database. No MindPal connection or new paid package is required. Do not create another web app, reset the database or reprovision accounts that already exist.

## Upload the private configuration

PythonAnywhere → Files → `/home/whatamidoing/bankoffreedom/instance/` → upload `3DU-Standalone-Mapping.json` with that exact filename. Keep it outside static folders and public repositories.

## Apply the update

Open the existing Bash console. Run each line individually:

```bash
cd /home/whatamidoing/bankoffreedom
git pull --ff-only origin main
.venv/bin/python -m flask --app three_du:create_app backup-db
.venv/bin/python -m flask --app three_du:create_app init-db
.venv/bin/python -m flask --app three_du:create_app grant-mapping-setup --actor-email admin@example.test --authorized-by admin@example.test --reason "Authorize team mapping setup"
.venv/bin/python -m flask --app three_du:create_app import-3du-mapping instance/3DU-Standalone-Mapping.json --actor-email admin@example.test --reason "Activate approved standalone 3DU specification"
```

Use the actual provisioned admin email in both email options if it differs. Trusted host-console provisioning records the administrator authorized to configure mapping; it does not add educator permissions or authorize live collection. The import is an explicit owner-approved bootstrap action. Future browser changes follow draft → validate → record owner approval → activate at `/admin/setup/mapping`.

The CLI and WSGI application must use the same DATABASE_PATH and environment bindings. For the original installation, the default database is `instance/3du.sqlite3`. If WSGI specifies another path, configure the same path before these commands. Stop on errors; do not delete databases, force Git resets or replace secrets to work around them. `git pull --ff-only` preserves local changes and may refuse when conflicting changes exist.

Backup uses SQLite's consistent backup API, includes committed WAL data and saves private mode-0600 files under the database's `backups` folder. Retain backups privately. `init-db` applies migration 004 without reseeding accounts/stages or replacing publications. Repeating the exact import leaves the configuration unchanged.

## Reload and inspect

PythonAnywhere → Web → existing `whatamidoing.pythonanywhere.com` app → green Reload button. Open `https://whatamidoing.pythonanywhere.com/`, then `/admin/login`. Existing passwords/accounts are retained. Team setup appears on the dashboard; ordinary admins cannot configure mapping without the separate capability.

Students and linked parents can save incomplete drafts; all mandatory role-owned fields are checked at submission. Submitted work appears in the assigned admin record. Initial plus one later resubmission remains the same entry. Involved mentors have their own mandatory Mentor Notes and optional Previous Interaction Notes form. Educator access remains blocked pending an approved scope.

The report editor uses labelled fields, exact-version reasons and explicit shared-wording review. Six shared outputs remain view-only; public journey outputs are concise summaries, never full internal stage arrays. Original historical publications are retained privately; the standalone public response omits historic journey arrays.

## Known blockers and verification boundary

The code update does not supply assessments, stage sufficiency criteria, assessment/interview/activity mapping readiness, educator authorization or the unresolved rule for whether both educator and mentor notes are always required. Mapping readiness visibly blocks these dependencies; configuration import cannot waive them. Provider/model credentials are still needed for real generation. No AI provider was called in verification.

A generated journey-summary placeholder must be edited and reviewed before approval. Initial publication requires assigned admin then involved mentor approval of the same version; subsequent versions require admin approval only. Missing mentor never triggers a bypass.

Live minor-data policies remain unresolved; the site remains a labelled synthetic demonstration. A publicly reachable site is not approval to collect live student data. Real email recovery remains unconfigured unless the operator has separately implemented delivery; the existing development recovery spool is not operational email.

Codex has prepared and tested this update, but cannot operate the user's logged-in PythonAnywhere dashboard. Remote deployment/reload and post-deployment checks must be performed by the account owner. The external site request from this execution environment was blocked by its network proxy (403); no remote site behavior was verified.

## Account-name update

Migration 005 adds a persistent optional stored name for existing accounts and requires a name for all new student/parent signups. Existing names remain unknown until the owner supplies one; no email-derived name is fabricated. Existing students/parents use the account navigation's Add your name / Your name link (`/account/name`). Name changes are self-service, CSRF-protected, audited and cannot change roles, relationships or another account. Assigned admin dashboards and submitted-input author labels show names alongside emails.

To install this incremental update, pull the new code, run `backup-db`, run `init-db`, then reload the existing PythonAnywhere app. No mapping reimport or account reprovisioning is necessary.
