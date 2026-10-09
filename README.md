# 3DU

A locally working, **synthetic-development-only** career discovery platform for Classes 9–12. It preserves sequential student work, private evidence, human review and exact-version publication gates. The full supplied PRD was read before implementation; see [source text](docs/source-prd.txt), [requirements checklist](docs/requirements.md), [decisions and blockers](docs/decisions.md), and [verification](docs/verification.md).

For a beginner walkthrough, see [step-by-step operation](docs/operate.md).

For an app address accessible from other computers/phones, see [browser-based hosting setup](docs/hosting.md). The hosted HTTPS entry point is `wsgi:application`; hosting account access is still required.

## Run locally

Requires Python 3.12+ and SQLite (included in Python). No paid services or external credentials are required for local development.

```sh
cd /workspace/bankoffreedom
python -m venv .venv
.venv/bin/pip install --no-deps -r requirements.lock
.venv/bin/pip check
.venv/bin/python -m flask --app three_du:create_app init-db
.venv/bin/python -m flask --app three_du:create_app run --host 127.0.0.1 --port 5000
```

The server is local only; no deployment is configured. Create a fictional student or parent account through signup. Parent accounts begin with no links. All completion and mapper criteria are intentionally unset, so a new student can draft/submit stage 1 and always use Track Progress; later stages remain locked until configured completion approval. Database migrations are versioned and repeatable; `init-db` does not reset data. Sessions, drafts, audit records and reports persist in `instance/3du.sqlite3`. Back up that directory securely during development; recovery links inside it are credentials.

`.env.example` lists configuration names without secrets. Flask does not automatically load that file: export the desired variables before starting. `DATABASE_PATH` and `RECOVERY_DIR` can be absolute paths. `SYNTHETIC_ONLY=0` **blocks** registration, provisioning and application data writes; it does not enable a production mode. HTTPS deployments would require `COOKIE_SECURE=1` and a separate production readiness review.

## Authorized provisioning and relationships

The following commands are restricted to trusted operators with filesystem/database access. They are not public signup APIs. Use synthetic accounts only. A reason is recorded. Passwords are prompted, never included in documentation or saved configuration.

```sh
.venv/bin/python -m flask --app three_du:create_app provision --email admin@example.test --role admin --reason 'Authorized synthetic development operator'
.venv/bin/python -m flask --app three_du:create_app provision --email mentor@example.test --role mentor --reason 'Authorized synthetic development mentor'
.venv/bin/python -m flask --app three_du:create_app authorize --actor-email admin@example.test --student-email student@example.test --reason 'Assign synthetic student record'
.venv/bin/python -m flask --app three_du:create_app authorize --actor-email parent@example.test --student-email student@example.test --reason 'Authorized synthetic relationship'
.venv/bin/python -m flask --app three_du:create_app authorize --actor-email mentor@example.test --student-email student@example.test --reason 'Record synthetic involvement'
```

Admin accounts see only assigned students. Parent linking remains an operator-only synthetic capability pending an approved guardian-verification process. Mentor involvement by itself grants no raw-work access. Approved completion scopes and field scopes can be set explicitly, for example `--scopes '6' --fields '{"6":["APPROVED_FIELD_NAME"]}'`; the field name must come from an approved scope, not this placeholder. Stage scope alone permits relevant completion actions if criteria allow, but does not expose arbitrary draft fields. Mentors see only their own session notes and admin-approved initial shared report content for review.

Revoke access with `revoke --actor-email ... --student-email ... --reason ...`. Revocation removes access immediately, and a revoked mentor's approval no longer satisfies initial publication. Existing accounts cannot silently change role through `provision`. There is no role-update or self-link API.

## Account recovery

Recovery uses expiring, hashed, single-use tokens and revokes all prior account sessions when completed. In local development, instructions are delivered to private files under `instance/recovery/` (0700 directory, 0600 files). An authorized local operator can inspect the appropriate fictional account's `path`, then open that path in the local browser. Tokens are not returned through public APIs. Recovery always returns the same public response for existing/nonexistent accounts. Real email delivery is **not configured**; no emails are sent.

## Inspect the mapping workflow

Sign in as an assigned admin and open the student's workspace. JSON editing is deliberate for inspectability; validation errors retain unsaved text. All labels/forms are accessible, and the public/student/parent experience uses simpler language.

1. Enter **approved** stage rules and complete mapping enums in Specification. Blank defaults represent missing decisions. The schema is in `three_du/domain.py`; `/api/admin/schemas/steps/1` through `/4` expose the current validation schemas to admins only. No synthetic test enums are loaded into the application.
2. Review fictional student work. Completion is distinct from save/submit and requires current revision, configured approver authority, submission (if required), and configured evidence fields. Admin may review or approve out of navigation order if approved criteria permit; this does not skip preceding stage locks or report approvals.
3. Add attributed evidence; student and parent are separate stakeholders. Correct evidence using `corrected_from`; original records remain. Save an immutable input snapshot containing the current evidence and original student work.
4. Record separate source-backed readiness reviews for `assessments`, `mentor_interview`, and `activities` against approved criteria. Each references evidence IDs in the exact current snapshot/configuration. An assumption or missing-evidence record cannot prove completion. Required stage completions must also be satisfied.
5. Start a run on the latest snapshot. Missing specification/readiness creates a visible **blocked** run. AI execution remains unavailable until a provider and private specification are supplied. For synthetic development, an operator may record explicit human-authored step JSON. Every step preserves its input, summary, validated output, confidence/gaps, execution status and retry attempt. Use `expected_attempt` to avoid conflicting retries. Steps 2–4 require the previous valid output.
6. After all four steps validate, author the six-map public draft with `summary` and `items` (`label`, `text`) only. Persona `items` is empty; empathy/journey item labels match exact approved enums and order. These human-authored drafts are labelled `admin-edited`, never misrepresented as AI-generated. Evidence metadata stays in private step records.
7. Review wording suitable for both audiences; approve the exact version with `wording_reviewed: true`. The involved mentor must then approve **that same initial version**. Publication remains blocked if no mentor can approve. A subsequent revision creates a new version, requires admin approval, and does not require fresh mentor approval.

Source changes stale all dependent steps/unpublished drafts. A step rerun stales that step's old attempt and subsequent steps. You must rerun affected downstream steps and create a new draft/reapprove; stale drafts cannot regain eligibility. A correction/new configuration/new snapshot requires a new current snapshot/run as appropriate. Published reports and publication history are immutable and remain available as the last approved published version, even if a later workflow fails. Creating/editing drafts never overwrites them.

Information requests are internal records only; automated delivery and unspecified evidence collection procedures remain blocked. No parent questionnaire, automated mentor matching, career ranking, numerical fit scores, invented instruments, external Mindpal dependency or fabricated affiliations are included.

## Verify

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check three_du tests
.venv/bin/ruff format --check three_du tests
.venv/bin/mypy three_du
.venv/bin/python -m compileall -q three_du
node --check static/app.js
```

Python is interpreted; there is no separate frontend bundle/build. Source compilation, template compilation/rendering tests and JavaScript syntax validation cover build-time checks. Mypy checks untyped function bodies and the provider protocol; this is not full strict annotation coverage.

For repeatable real-browser checks, use a Python with `playwright` installed and a Chromium executable (this environment supplies both):

```sh
python tests/browser_check.py
```

It starts/stops its own isolated server/database, uses explicitly fictional fixtures, and writes screenshots to `/tmp/3du-*.png`. Override `CHROMIUM_PATH` when needed. It does not use the application's normal database, deploy or send messages. Automated test fixture enums are synthetic and confined to `tests/conftest.py`.

## Before live use

Supply the missing detailed mapping specification, approved instruments and criteria, approved linking/provisioning scopes, minor consent/guardian/privacy/retention/deletion/export/incident policies, and selected provider/delivery/hosting integrations. Operational security, backups, accessibility conformance and device coverage require defined standards and review. See the full blockers in `docs/decisions.md`. No production readiness or live-data activation is claimed.
