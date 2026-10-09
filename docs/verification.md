# Verification report

Verified on 2026-10-09 using Python 3.12.14, Flask 3.1.2, SQLite and system Chromium 151.0.7922.173. All test accounts, statements, completion rules and mapper enumerations were explicitly synthetic; the normal development database has no seeded student/parent/mentor/admin records or mapper enums.

## Passed

- **46 pytest cases** completed: authentication/role routing, rejection of privileged signup, malformed credentials, local recovery expiry/single use/session revocation, CSRF and cookie/security headers, persistent drafts across a new app/client/login, unauthorized parent/mentor/admin/direct-request denials, mentor stage versus field scope, restricted completion review, exact sequential locks, always-open Track Progress, open/save/submit/Next separation, completed-stage review, conflicting save/review rejection, configurable completion authority, out-of-order admin completion without navigation bypass, stage 8 versus publication separation, default mapper blocking, exact-version initial admin-then-mentor approval, absent/uninvolved/revoked mentor blocking, human wording confirmation, subsequent admin-only approval, new-version/no-inherited-approval edits, prior published history preservation, student/parent shared response equality and restricted field shapes, input snapshot invalidation, downstream reruns, invalid assumption-to-fact rejection, provider failure/blocked attempts, failed-run publication preservation, configuration concurrency/enumeration validation, source-backed readiness, duplicate approvals and concurrent atomic publication, all template compilation and repeatable migrations.
- **Real Chromium browser checks** on desktop (1440×1000) and mobile (390×844): public homepage and all four portals, keyboard skip-link focus, reduced-motion preference, signup/login/logout, save/submit/reload/later-login restoration, Next lock and return action, Track Progress and exact pending message, authorized parent/mentor restricted views, admin evidence creation/snapshot/blocked run, persistent support mailto and non-callable phone placeholder. No horizontal overflow or JavaScript page errors were observed. Screenshots inspected at `/tmp/3du-home-desktop.png`, `/tmp/3du-home-mobile.png`, `/tmp/3du-progress-mobile.png`, `/tmp/3du-admin-desktop.png`.
- Ruff lint and formatting checks passed for all Python source/tests.
- Mypy `check_untyped_defs` passed for three application modules. This is useful inferred-body checking and provider protocol validation, not full strict type annotation coverage.
- Python source compilation, all Jinja template compilation, rendered portal tests and JavaScript syntax check passed. The interpreted/server-rendered stack has no separate frontend bundle.
- Frozen dependency reinstall was repeatable; `pip check` found no broken requirements.
- SQL migrations applied twice without deleting accounts/work or duplicating schema versions.
- Final local server restarted with current source; functional HTTP requests returned 200 for database-backed `/health` and the homepage with expected content/support action.
- Git whitespace check passed. Application/database/recovery/generated caches are excluded from tracking; no credentials are in source/configuration.

## Blocked, unimplemented or not claimed

- Actual AI execution and real mapping outputs: provider/private prompts and exact detailed mapping specification absent. The server provider interface visibly records unavailable execution, not invented results. Human-authored synthetic outputs validate the independent workflow/publication mechanisms.
- Validated assessments/scoring, real stage/activity/readiness criteria and career/mentor content: source material/decisions missing. Empty configurable interfaces are present, not certified instruments or matching algorithms.
- Actual recovery email delivery: no service/sending identity/credentials selected. The local spool/reset flow was tested; no email was sent.
- Real guardian linking/verification, approved mentor field-access policy and live minor-data operation: policies/approved procedures missing. Operator-only synthetic linking and restrictions were tested. Disabling synthetic mode blocks data collection rather than activating live use.
- Full WCAG conformance, exhaustive keyboard/screen-reader testing, multiple browser/device compatibility, load testing, production security assessment, backup/disaster recovery and availability targets: thresholds/owners/infrastructure are unspecified; no certification is claimed.
- Public deployment, paid-service purchase, outbound messaging, live data collection and production analytics: not performed.
- Fresh-task restoration/publication of the cloud environment: not verified. Reusable install/start instructions are saved as a draft; draft persistence does not publish or deploy. Git publication status is recorded in the repository history; publication of the code does not deploy the application.

The package-managed Playwright Chromium download was denied by egress policy. This did not block testing: the preinstalled `/usr/bin/chromium` was used successfully without changing network policy or disabling verification.
