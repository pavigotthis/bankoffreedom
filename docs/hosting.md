# Browser-accessible hosting

The repository now includes `wsgi.py`, a standard WSGI entry point for hosting behind HTTPS. Hosted cookies default to Secure. Importing the application never resets/initializes a database, seeds accounts or starts Flask's development server.

The hosted build remains **fictional-data testing only**. Production operation for real students is blocked on the specifications/policies listed in `decisions.md`. A GitHub repository or the Codex cloud workspace does not provide a publicly accessible running Flask application by itself.

## PythonAnywhere: browser-based setup

This is a practical hosting option for the current Flask/SQLite architecture. Hosting account access is required; no account, service purchase or live site was created by Codex. Review the provider's current plan/region limits during signup. Choose a Python version supported by this project (3.12 or later).

1. Create/sign in to your PythonAnywhere account in your browser. Keep passwords and authentication tokens out of chat.
2. Open a **Bash console on PythonAnywhere**. This console runs on the hosting server, not your computer. Clone the repository:

   ```sh
   git clone https://github.com/pavigotthis/bankoffreedom.git
   cd bankoffreedom
   python3.12 -m venv .venv
   .venv/bin/python -m pip install --no-deps -r requirements.lock
   .venv/bin/python -m pip check
   .venv/bin/python -m flask --app three_du:create_app init-db
   ```

   Use the corresponding executable if you selected another supported Python version. Do not run `flask run` for the hosted web app.

3. Open **Web → Add a new web app**. Choose **Manual configuration**, and the same Python version used for the virtual environment. Use the hostname supplied by your account.
4. Set the web app's virtualenv path to `/home/YOUR_USERNAME/bankoffreedom/.venv`. Replace `YOUR_USERNAME` with the account username. Account roots can differ by provider/region; use the actual home path shown in the console.
5. Open the web app's **WSGI configuration file**. Replace the starter/example application code with the following, using your actual repository path:

   ```python
   import sys
   project = '/home/YOUR_USERNAME/bankoffreedom'
   if project not in sys.path:
       sys.path.insert(0, project)
   from wsgi import application
   ```

6. Reload the web app. Use its **HTTPS** address shown in the Web dashboard. That address can be opened from another computer or phone. Test signup/login with fictional records, save/refresh/resume, Track Progress and the lock states. Hosted readiness has not been verified until these requests succeed on the actual host.
7. Configure any provider-specific HTTPS redirect setting. Always use HTTPS so Secure cookies work. Do not expose a separate Flask development-server port.
8. The database defaults to `/home/YOUR_USERNAME/bankoffreedom/instance/3du.sqlite3`, on the hosting account's retained filesystem. Verify the provider retains that directory across reloads and the storage quota is sufficient. Do not deploy this SQLite configuration on an ephemeral filesystem or with multiple independent copies of the database. Never add public static mappings to `instance/`, recovery files, or the project root. Serving `static/` is permitted.
9. Create administrator/mentor accounts and assignments through the provider's browser console using the `provision`/`authorize` commands in `operate.md`, substituting `.venv/bin/python` for `python`. Passwords are entered only at the prompt. There is no default admin password.
10. To update: preserve/back up database files securely, run `git pull`, reinstall the pinned requirements, run `init-db`, and reload the web app. Applying migrations does not reset data. Follow provider-specific backup instructions; production backup/recovery targets remain undefined.

If the account cannot provide a supported Python version or retained storage, stop and choose a compatible host. Do not discard the database, install an unpinned workaround, or disable TLS/package verification. Real recovery email and AI generation remain unconfigured; their blocked states are expected.

## Other hosts

Any compatible WSGI hosting service can use `wsgi:application`. Requirements: supported Python, HTTPS, retained database/recovery storage, migration execution before startup, and operator access for provisioning. This release uses one shared SQLite filesystem database; horizontal replicas with separate disks are unsupported. Production service choice and operations require a separate review. Hosting credentials are not present in this workspace, and no deployment API is connected.
