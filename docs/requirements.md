# Requirements-to-implementation checklist

Initial repository inspection: only the first-commit README existed; no application, database, authentication, tests or deployment configuration. All confirmed behaviors below were missing. The README's original project identity was preserved. No prototype capability was assumed. `source-prd.txt` retains all PRD sections including the release checklist.

**Verified local** means meaningful synthetic tests passed; it does not mean approved production configuration exists. **Blocked** means the mechanism/UI is present but a named product specification, integration or policy is missing.

| Requirement | Implementation/evidence | Status |
| --- | --- | --- |
| FR-01 signup/login/logout/recovery/role routing | Server accounts/sessions; safe student/parent signup; CLI privileged provisioning; single-use recovery; role portals. `test_auth_permissions.py`, browser smoke. | Verified local; real recovery email blocked on delivery provider. |
| FR-02 real persistence | SQLite migrations; persistent accounts, sessions, work, evidence, runs/reports; new application/browser instance restores saved work. | Verified local. |
| FR-03 nine ordered stages, sequential 1–8, always-open 9 | Domain constants, server `unlocked`, explicit shared progress schema, student navigation. `test_stages.py`. | Verified local; real completion criteria unset. |
| FR-04 open/save/submit/completion distinct | Reads never change completion; separate save/submit API and explicit completion approval endpoint; Next is navigation. | Verified local. |
| FR-05 server role/stage/direct-request enforcement | Assigned-admin/linked-parent/involved-mentor relationships checked on every relevant route; CSRF; negative tests. | Verified local. |
| FR-06 resume and completed-stage review | Persistent drafts/revisions; view-only completed work; admin source corrections are explicit and invalidate mappings. | Verified local. |
| FR-07 exact locked message/next action | HTML locked page and JSON error with next action. | Verified local/browser. |
| FR-08 configurable instruments/scoring/activity criteria | Empty config, explicit unavailable assessment state, dynamic approved fields; no scores/invented instruments. | Mechanism verified; real instruments/criteria blocked. |
| FR-09 admin completion, relevant involved mentor completion | Completion permission distinct from report approval, configured authority/evidence, current revision, mentor stage and field scope. | Mechanism verified with synthetic rules; real authority/criteria relationship unresolved. |
| US-01 save/resume | New account/work survives logout and independent app/browser login. | Verified local/browser. |
| US-02 available/locked | Nine statuses, sequential access, exact blocked route/next link. | Verified local/browser. |
| US-03 parent shared progress/report only | Same progress/report schemas as student, links enforced, no student stages/raw notes/internal fields exposed. | Verified local; real linking procedure blocked. |
| US-04 involved mentor exact initial approval, no editing | Admin-first same-version approval, relationship scope, no admin step/map/edit API access. | Verified local. |
| US-05 inspect four steps | Versioned run/snapshot/attempts, input/summary/output/evidence/confidence/gaps/status/errors; admin schemas and workspace. | Inspection/validation verified; real AI generation blocked. |
| US-06 source correction invalidates dependencies | Append-only evidence, stale steps/unpublished reports, current input fingerprint check, required reruns. | Verified local. |
| US-07 exact pending message without leak | Public pending response has only `status`/specified `message`; public published schema strictly restricted. | Verified local/browser. |
| US-08 revise without losing publication | New edited version; no inherited approval; subsequent admin-only gate; old publications immutable. | Verified local. |
| US-09 support email/phone placeholder | Persistent footer on public and all authenticated portals; correct mailto; no telephone link. | Verified local/browser. |

## PRD release checklist

| Release check | Evidence and limits |
| --- | --- |
| Signup/login/logout/recovery/routing | Automated and real-browser local flows pass. Recovery spool/token consumption pass; actual emailed delivery unrun/unimplemented. |
| Sequential locks/direct requests/completion/Track Progress | Negative API tests and browser Next/locked/progress checks pass; synthetic approved completion rules tested. No real completion rule is asserted. |
| Refresh/cross-device persistence | Database restart/new app/new client and browser reload/logout/login restore drafts. |
| Parent/mentor/admin boundaries | Unlinked/uninvolved/unassigned read/write denials, field restrictions, provision/revoke controls and audit pass. Approved real linking/field scope remains missing. |
| Upstream edits/failing runs/publication retention | Snapshot fingerprints, stale downstream attempts/drafts and failed/blocked/invalid runs checked; prior publication survives. |
| Initial two approvals; later admin approval | Exact-version admin-first mentor gate, no absent-mentor bypass, wording confirmation, no approval inheritance, duplicate/concurrent publication checked. |
| Same shared six maps/progress, private internals | Student/parent equality plus explicit response-field and private-fixture non-leak tests pass. Six schema outputs and eighteen-stage structure tested with labelled synthetic enums. |
| Responsive/keyboard/reduced motion/support | Actual Chromium desktop/mobile inspections of homepage/four portals, skip focus, media preference, no horizontal overflow/JS errors, email and non-callable phone pass. Full accessibility audit/device matrix are undefined/unrun. |
| Working code/schema/setup/config/verification | Source, two SQL migrations, secret-free variable template, pinned dependencies, CLI instructions, requirements checklist and verification report supplied. No deployment configured. |

Assessments, live recommendation/content inventory, true mapper generation and production minor-data operation cannot pass release acceptance until the materials in `decisions.md` are supplied. This checklist does not claim those blocked features complete.
