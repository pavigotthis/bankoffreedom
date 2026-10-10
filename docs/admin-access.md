# Admin login and first account: PythonAnywhere

The admin login is `/admin/login`; successful login opens `/admin/dashboard`. The public footer contains **Admin Login**. Accounts are real persistent database accounts. Public signup never creates admin or mentor privileges. The deployment remains fictional-data development only.

## Update your existing hosted app

In PythonAnywhere, open **Consoles → your Bash console**. Run these commands one line at a time:

```sh
cd /home/whatamidoing/bankoffreedom
git pull origin main
.venv/bin/python -m flask --app three_du:create_app init-db
```

Then open **Web** and click **Reload whatamidoing.pythonanywhere.com**. Your existing WSGI file and virtualenv path stay valid. No new dependencies or destructive database reset are required. Other deployments should use their actual repository path.

## Create the first admin account

In that same Bash console:

```sh
.venv/bin/python -m flask --app three_du:create_app provision --email admin@example.test --role admin --reason 'Authorized first development administrator'
```

`admin@example.test` is a development login identifier; it is not a real email delivery address. You may substitute an operator-controlled address. Choose a password of at least 12 characters at the prompt, then enter it again to confirm. Password typing may appear blank; that is normal. Do not paste passwords into chat, source files or command arguments. No default/hardcoded password exists. The database stores a password hash. The command records its provisioning reason and refuses to silently change an existing account's role.

Open `https://whatamidoing.pythonanywhere.com/admin/login`, enter that account's email/password and choose **Sign in**. The show/hide password control does not alter credentials. A verified admin is redirected to `/admin/dashboard`; students, parents and mentors cannot enter admin pages or backend operations. Anonymous page visits redirect to admin login; unauthenticated API requests receive 401, and wrong-role requests receive 403.

## Assign a student record

The dashboard shows only students explicitly assigned to that administrator. An empty dashboard is expected before assignment. Substitute the exact fictional student email already registered on this hosted site:

```sh
.venv/bin/python -m flask --app three_du:create_app authorize --actor-email admin@example.test --student-email student@example.test --reason 'Assign fictional student to administrator'
```

Refresh the dashboard. Each assigned record shows progress, parent links/mentor involvement and access to:

- Stage work and configured completion approvals.
- Attributed evidence, append-only corrections, immutable snapshots and readiness reviews.
- All four mapping steps, execution/validation errors, output inspection and downstream reruns.
- Draft editing and exact-version wording/review approval.
- Atomic eligible report publication and approval/publication/version history.

Parent links and mentor involvement can be inspected in the dashboard/student workspace. They are managed by the trusted `authorize`/`revoke` CLI procedures described in `README.md`, not by public signup or an invented guardian-verification flow. Admin role provisioning alone never grants all student records.

## Publication and unresolved specifications

Completion approval is separate from report approval. Initial publication still requires required work/readiness, a current valid mapping run, admin approval and then an involved mentor's approval **of that same version**. No missing-mentor bypass exists. Later revisions require a new admin approval and do not require fresh mentor approval. Existing published versions survive edits and failed runs; stale drafts cannot publish.

Missing assessment content, completion/readiness decisions, exact mapper enumerations and provider configuration continue to block their dependent operations. The new login/dashboard does not invent these product decisions or make them ready.

## Logout, expiry and recovery

Use **Sign out** in the page header. It revokes the current session. Sessions expire after the existing eight-hour engineering default; admin pages redirect to login with an expiry notice, APIs reject expired identity, and interrupted admin form submissions provide a sign-in link without discarding unsaved text automatically. Successful login rotates the server session/CSRF credentials.

The admin login links to **Recover password**. Recovery uses the existing single-use, 30-minute token flow; a completed reset revokes all account sessions and preserves its admin role. Outbound email remains unconfigured. An authorized operator can inspect the appropriate private file under `instance/recovery/` through PythonAnywhere Files, then use its `path` on this HTTPS website. Recovery tokens are credentials: never publish/share the files, expose that folder as static content, or paste tokens into chat. No recovery token is returned by public API responses.
