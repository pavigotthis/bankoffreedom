# 3DU Product Requirements Document
Career discovery and mentorship platform for students in Classes 9–12

## 1. Purpose and decision context

3DU helps students understand themselves, explore career possibilities and learn from professionals. It brings interests, demonstrated strengths, academic information, family perspectives, career exposure and practical constraints into a coherent guidance experience. The platform helps a student make a better-informed next move without prescribing a final career.

### Problem to solve

Students need an understandable path from self-discovery to exploration and reflection. Parents need an appropriate shared view. Mentors need clearly scoped participation. Administrators need traceable evidence, usable review tools and controlled publication. Missing information must remain visible rather than being replaced with plausible answers.

### Product goals

- Guide students through nine ordered stages while keeping progress and next actions visible.
- Preserve student and parent perspectives separately and share only the approved six-map report.
- Provide an inspectable four-step mapping workflow, human review and version-specific publication.
- Limit mentors to actual involvement and administrators to authorized records.
- Provide persistent accounts, reliable saved work and accessible browser-based use.

### Design principles

Listen before labelling. Explore before deciding. Meet reality before committing. Present personas as provisional summaries rather than diagnoses or permanent identities. Use respectful language, clear status indicators and one visible next action. Routine student and operator tasks should be understandable without developer knowledge.

### How to read requirement status

| Label | Meaning |
| --- | --- |
| Confirmed (C) | A specified product requirement. |
| Proposed (P) | A concrete experience or workflow proposal that needs product-owner agreement. |
| TBD / decision (D) | A missing specification, policy or rule that must be resolved before dependent functionality is enabled. |
| Engineering choice (E) | A reversible technical detail; it does not establish product policy. |
| Prototype context | Illustrative content; it does not prove implemented behavior or validated findings. |

Status applies to the relevant paragraph or table row. Proposed functionality is not a substitute for an approved assessment, completion rule, mapping enumeration or policy. This document is a product review draft; unresolved decisions are listed in Section 9.


## 2. Users, access and scope

### Role contract

| Role | Allowed confirmed job | Restricted information/action |
| --- | --- | --- |
| Student | Own drafts/submissions, permitted stage review, shared progress, published report, support | No map editing/regeneration, admin/mentor approval, publication, unrelated records or private workflow material |
| Linked parent | Authorized linked student’s identical shared progress and published six-map version, support | No raw assessment answers, private notes, student draft editing, report approval or unrelated students |
| Involved mentor | Relevant session records and explicitly approved work scope; completion approvals where allowed; initial report review | No map editing/regeneration/publication; no unassigned students or unspecified fields |
| Admin | Authorized student inspection, evidence correction, mapping inspection, draft editing, requests, reruns, completion capability and version review/publication | No bypass of the initial two-approval gate; no access outside authorized scope |

### Permission matrix

| Capability | Student | Parent | Mentor | Admin |
| --- | --- | --- | --- | --- |
| View shared progress | Own | Linked student, same view | Only approved involvement scope | Authorized students |
| Save stage work | Own and unlocked | No | Session work within approved scope only | Correction method requires defined policy; not impersonated submission |
| Submit student work | Own and unlocked | No | No impersonation | No impersonation |
| Approve completion | No | No | Approved stage/student/evidence scope | Approved criteria and authority; exact interpretation remains D |
| Inspect raw evidence | Own-field visibility requires approved portal design | No | Explicit necessary field scope only | Authorized records |
| Edit evidence/maps | No | No | No maps; own permitted notes only | Yes, reasons, versions and invalidation |
| Run mapping | No | No | No | Yes, only current eligible input/specification |
| Initial report approval | No | No | Involved mentor, after admin, exact version | Exact version and shared-wording review |
| Later report approval | No | No | Not required | Exact revised version |
| Publish | No | No | No | Atomic eligibility check and audit |
| Manage assignments/accounts | No self-link/privilege | No self-link | No self-assignment | P: designated admin capability; approved authorization/verification process required |

### Relationship requirements

C: student-parent authorization and mentor-student involvement are explicit records, not inferred from an email string or request parameter. C: server checks cover every relevant read/write, including direct URLs and APIs. C: privileged roles are not public signup choices. C: revocation affects access immediately; previously recorded approvals cannot bypass a required current involved reviewer.

P: relationship management uses a browser form restricted to admins with a separately granted management capability, without adding a new public role. Show student, actor, relationship type, permitted scope, verification/reference status, who authorized it, reason and history. Do not collect identity-document values or invent a guardian-verification method. The verification method and who may grant this management capability are D.

P: a designated operator can find unassigned development records through an explicitly approved management view. Ordinary assigned admins do not automatically gain all student access. This proposed capability must not be inferred from a general admin badge.

### Scope boundaries

| Area | Confirmed scope | Proposed expansion | Decision or dependency |
| --- | --- | --- | --- |
| Public website | Explanation, audiences, how it works, start and support | Clear registration/readiness notice and separate admin entry | Approved messaging and launch mode |
| Identity | Signup/login/logout/recovery; four roles; privileged provisioning | Operator-facing account/assignment forms | Linking verification, identity provider and session policy |
| Student journey | Nine stages and stateful sequential access | Complete typed forms and source-backed content at each stage | Fields, instruments, content and completion rules |
| Parents | Linked student’s same progress and published report | Clear link-status explanation | Approved secure linking procedure; no extra questionnaire |
| Mentors | Relevant records, sessions, completion scope, exact initial review | Work queue and version-specific report review checklist | Approved field scopes and session procedures |
| Admin | Evidence, four steps, drafts, corrections, reasons, reruns, approvals, publication | Review queue, normal forms, safe assignment/configuration interfaces | Scope of account administration and assignment management |
| Mapping | Exact four steps and six report outputs | Readable tables, diff previews and blocker lists | Detailed mapping specification and selected provider |
| Operations | Persistent storage, instructions and testing | Browser-first operator runbook and readiness dashboard | Hosting, backups, security and policy approvals |

### Explicitly out of scope

No numerical career-fit scores, alignment calculations, career-cluster rankings, automated mentor matching, required Mindpal connection, embedded Mindpal run URL, invented mentor qualifications, fabricated testimonials/user counts/outcomes, invented pricing, prescribed career decisions or unsupported validated-assessment claims. A parent questionnaire is not added. Payment, subscriptions, analytics, scheduling integrations and automated recommendations are not silently included.

## 3. Core workflows and functional requirements

### Confirmed sequencing

| Order | Exact stage | Access |
| --- | --- | --- |
| 1 | Create Profile | Available at start |
| 2 | Take Assessments | Stage 1 complete |
| 3 | Discover Interests & Strengths | Stages 1–2 complete |
| 4 | Explore Career Paths | Stages 1–3 complete |
| 5 | Find Relevant Mentors | Stages 1–4 complete |
| 6 | Attend Sessions | Stages 1–5 complete |
| 7 | Complete Activities | Stages 1–6 complete |
| 8 | Get to know yourself | Stages 1–7 complete; publication separately gated |
| 9 | Track Progress | Always accessible |

C locked message: “This stage will open once you complete the previous stage.” Link to the next available action. Opening, Next, saving or submitting never silently completes work. Completed work remains reviewable. Access checks apply to server/API/direct URLs, not only navigation.

### Proposed lifecycle model

| State | Meaning | Student action | Authorized review action |
| --- | --- | --- | --- |
| Locked | A preceding required stage is incomplete | Go to next available stage; Track Progress | Inspect when authorized; cannot silently bypass sequencing |
| Available / not started | Accessible stage has no saved work | Open and enter approved fields | No false completion |
| Draft | Saved, unsubmitted current work | Resume, edit, save, submit if valid | Inspect authorized records; not an approved submission |
| Submitted / awaiting review | Exact submitted revision awaits applicable review | View submitted copy; proposed withdrawal/edit rule requires owner approval | Review exact revision against criterion |
| Changes requested | P: reviewer identifies actionable unmet criteria | Read safe feedback and amend permitted work | Preserve prior review; reassess new revision |
| Complete | Applicable approved completion rule satisfied | Review; continue when sequencing permits | Audited correction/reopening only under approved dependency policy |
| Setup unavailable | Required instrument/content/criterion not configured | Clear availability message and support | Responsible setup owner resolves; no normal approval button masquerading as available |

Locked access is separate from saved/submitted/completion state. These state names are a proposed implementation-facing model; final wording and whether submitted work can be withdrawn are D.

### Proposed submission/review contract

Saving stores a persistent draft and confirms the saved time. Submitting creates an immutable reviewable revision with a visible summary. A reviewer sees that exact revision and the approved completion checklist. New changes after submission must either create a new submission or use the owner-approved withdrawal mechanism; old approvals never transfer. Students see understandable reviewer feedback, not private notes or internal evidence registers. Concurrent edits produce an explicit reload/compare choice rather than overwriting.

### Stage rule approval gate

C: completion criteria remain configurable because the source did not supply them. D: admin “may approve at any time” versus evidence-specific authority must be resolved explicitly. P: a stage cannot be enabled for real students until its field/content schema, completion criterion, approver scope, return-for-changes behavior and dependencies are approved as a versioned stage contract. Each submission references that contract version. Configuration changes do not retroactively erase completions without a reviewed migration decision.

P: the setup form asks the owner for the rule in plain language and validates the corresponding implementation config. It must not suggest that filling a reason field alone supplies missing criteria. A completion decision and a review reason are different: the rule specifies what is sufficient; the reason explains why the specific reviewed submission satisfies it.

Each proposal below supplies a concrete experience while keeping unsupplied assessment, activity and mapper content absent. Proposed fields are product choices, not existing confirmed requirements. No stage rule below becomes active through this document alone.

### Stage 1 — Create Profile

Confirmed purpose: create/resume a student profile; capture approved relevant background and discovery inputs, with persistent drafts and separate submission/completion.

Proposed screen: short grouped form with an introduction, progress/save state, field-level errors, Save draft and Submit for review. Present only fields approved for this stage; avoid a single generic developer-notes box.

| Proposed field group | Candidate fields for owner review | Proposed requiredness | Boundary |
| --- | --- | --- | --- |
| Student context | Display name and current class (9–12) | Owner decision | No invented identity/guardian verification; avoid requiring full legal identity merely to explore |
| Academic context | Relevant subjects and self-described academic context | Owner decision | Do not derive assessment scores or collect school records without approved process |
| Exploration interests | Interests, activities tried, questions about careers | Proposed optional/free response | Preserve original statement and missing answers; no forced labels |
| Student goal | What the student hopes to explore next | Proposed optional | Not a promise of a final career decision |
| Practical context | Approved fields for location/lifestyle/constraints | Defer sensitive scope pending policy | Do not require precise home address, family income or identity documents through an improvised form |
| Parent involvement | Link-status display only | As authorized | Not a parent questionnaire; linking is separate verified authorization |

Proposed review criterion for discussion only: required approved fields are present, the student has submitted, and an authorized admin reviews the profile. Whether completeness alone or substantive evidence is required remains D. A submitted free-text note alone is not an approved completion rule.

Proposed reviewer actions: Approve completion, Request changes, Save review note and Cancel. Show current rule checklist, submitted values, review history and a human-language reason input. Software supplies revision/version IDs. On success show “Profile approved. Take Assessments is now available” only if all relevant rules genuinely pass. If no rule exists, display “Profile completion rule needs setup” with an authorized setup link instead of a misleading normal approval button.

Acceptance proposal: drafts survive refresh/login; incomplete approved required fields prevent submission with field-specific messages; returned work has actionable safe feedback; exact-current-revision approval is enforced; no assessment or report approval is implied.

### Stage 2 — Take Assessments

C: no invented validated questions, instruments, scoring rules or career-fit scores. D: instruments, content, licenses, age suitability, versions, response types, scoring interpretation and completion criteria must be supplied.

P experience: an approved assessment catalog explains purpose, source, expected response format and known limitations; supports resume and consent-dependent availability; renders actual approved questions in accessible controls. Show completion/review status rather than a fabricated numerical career-fit result. Ordinary users never see schema JSON. Missing content produces “Assessments are not available yet. Your saved profile is safe.” Detailed missing instrument/version information goes to the setup owner.

P review: show which approved instruments and versions have valid submitted responses and which exact criteria remain unmet. A scoring implementation is enabled only when supplied rules can be reproduced and tested. A manual completion mark cannot falsely certify an assessment was taken. Assessment stages cannot be replaced by invented generic notes for live use.

### Stage 3 — Discover Interests & Strengths

C: support exploration of interests/strengths; no invented fit/rank calculations. P experience: show source-backed, plainly worded reflection prompts/content and approved summaries of the student’s own inputs. Distinguish a student statement, a reviewer interpretation and an assessment result. Allow the student to identify uncertainties or disagree with a working summary through an approved feedback mechanism. Do not imply scientific validation from a visual label.

D: approved prompt/content inventory, what is displayed from assessments, whether a reflection submission is required, reviewer authority and sufficient evidence. Proposed completion: a defined reflection artifact is submitted and reviewed against an approved checklist, not “opened the page”.

### Stage 4 — Explore Career Paths

P experience: searchable/browsable approved career information with descriptions of work, learning pathways, practical considerations, source and reviewed date. Student bookmarks or reflections are proposals, not a recommender/ranking system. Any displayed education requirements must be source-backed and context-specific; do not invent employment outcomes, salaries or fit claims.

D: initial content inventory, editorial ownership, filters, field schema and required exploration/reflection evidence. P completion requires the owner-defined exploration activity and submitted reflection if approved; browsing/Next alone never completes. Never make paid-service purchase an unapproved gate.

### Stage 5 — Find Relevant Mentors

C: no automated matching; only real authorized mentor data and explicit involvement. P experience: approved mentor directory or admin-assisted request form, using truthful permitted profile information and availability state. A student request is not an assignment or access grant. An authorized operator performs the approved suitability/assignment process; the student sees pending/confirmed status.

D: mentor identity/qualification verification, public profile fields, eligibility, capacity, assignment process, contact boundaries and stage completion. No fabricated affiliations, credentials or implied appointments. Admins see why no mentor is available; initial report review remains pending if no involved mentor can approve.

### Stage 6 — Attend Sessions

C: relevant mentor session records and completion capability. P experience: approved session details/status, preparation information, permitted student reflection and attendance/interview review state. Scheduling, rescheduling, meeting links and reminders are separate proposals requiring integration and safeguarding decisions; do not claim a functioning calendar/video integration without one.

D: session format, how attendance/interview evidence is verified, allowed mentor fields, safe communication process, cancellation handling and completion criteria. Mapping requires the approved mentor-interview requirement; a booking or session-page visit is not evidence it occurred. Private mentor notes remain private; shared feedback needs an explicit scope.

### Stage 7 — Complete Activities

P experience: source-approved activity catalog with clear purpose, instructions, acceptable evidence and feedback. Support drafts and approved evidence-upload/text mechanisms. Attachment support is only enabled after approved file types, storage, permissions, scanning and retention rules are supplied. Avoid inventing the activities themselves.

D: activity inventory, evidence criteria, required versus optional work, review authority and retry/feedback rules. An uploaded file or clicked button does not demonstrate completion unless the approved criterion says so. Student evidence and reviewer decision remain distinct.

### Stage 8 — Get to know yourself

C: unlock follows Stage 7; report publication is a separate gate. Before publication show exactly: “Your mentor and the 3DU team are reviewing your insights. Your results will appear here once approved.” Share only the same reviewed six-map version seen by linked parents.

P presentation: six understandable sections with concise explanations, provisional wording and clear published-version/date indicators. Formatting must not expose private confidence, assumptions under review, intermediate classifier rules or evidence registers. Student questions/feedback on a report are a proposal requiring an approved workflow; they do not grant editing or rerunning maps.

D: whether Stage 8 itself has a completion criterion, what approved follow-up reflection occurs, and how this affects progress. Viewing/publishing a report must not silently define an unsupplied Stage 8 completion rule.

### Stage 9 — Track Progress

C: always accessible; student and linked parent receive the same authorized shared content. P: show stage name/status, safe saved/submitted/review indicators, the next available student action, report review/published state and support. Parent navigation must not expose the student’s raw stage forms. Completion percentages/timestamps are proposed presentation fields; do not imply assessment/career accuracy. Parent/student share the same data content even when role-specific controls differ.

### Functional requirements – Required Stage Behaviour

| ID | Requirement | Acceptance check |
| --- | --- | --- |
| FR-01 | Signup/login/logout/recovery/role routing | Applicable acceptance: AUTH and ADM tests |
| FR-02 | Real persistent accounts/data | Applicable acceptance: persistence/resume tests |
| FR-03 | Nine statuses; sequential 1–8; always-open 9 | Applicable acceptance: stage direct-route tests |
| FR-04 | Open/save/submit/completion separate; Next not completion | Applicable acceptance: state-transition tests |
| FR-05 | Backend role/stage/direct-URL restrictions | Applicable acceptance: permission matrix tests |
| FR-06 | Draft resume; completed-stage review without silent downstream change | Applicable acceptance: draft/correction tests |
| FR-07 | Exact locked message and next action | Applicable acceptance: UI/API/message tests |
| FR-08 | Unspecified assessments/scoring/activities configurable; no invented validation | Applicable acceptance: unavailable-content/spec tests |
| FR-09 | Admin completion capability; involved mentor scope; relationship to criteria unresolved | Applicable acceptance: configured-authority tests and D-04 decision |

## 4. Mapping workflow and output requirements

### Confirmed input coverage

Student/parent responses; educator/mentor notes; academic information; activities/interests; separate student/parent career preferences; strengths, work values, work style; lifestyle preferences; financial/geographical constraints; previous interaction notes. These are supported evidence types, not blanket authorization to collect every field. Collection purpose, sensitivity, consent and requiredness must be approved per field.

### Proposed field catalog contract

Each activated field declares identifier, label, purpose, data type/allowed values, requiredness, collection stage/process, source/stakeholder, reader/writer scopes, whether shared in public progress/report, validation rule, specification version and policy dependencies. Sensitive field activation is blocked when its policy dependency is unresolved. Scientific questions/scoring rules are imported from approved sources, not authored by engineering.

### Minimum internal evidence structure

| Element | Confirmed meaning / proposed refinement |
| --- | --- |
| Evidence ID/version | E identifier; immutable attributable versions |
| Original statement | C retained verbatim; transformations do not overwrite it |
| Stakeholder | C distinguish student, parent, educator and mentor |
| Source | C preserve source; P reference origin submission/session/document and author |
| Evidence/input type | C coverage above; classifier distinguishes fact/preference/behavior/quotation/constraint/expectation/assumption/contradiction/missing evidence |
| Career dimension | C classifier dimension; exact taxonomy/import format D |
| Sentiment/confidence | C internal metadata; taxonomy/calibration D; never a career-fit result |
| Contradiction status | C identify conflict; detailed taxonomy/resolution process D |
| Correction lineage | C original plus reason/actor/time; E implementation identifier |
| Visibility classification | P formal private/shared field scope; D policy and exact field permissions |
| Missingness | C absent remains absent; P explicit reason only when genuinely known, never guessed |

### Snapshot/run contract

C: every run references a saved versioned snapshot of its source inputs. P: snapshot also references exact stage submission/criterion versions and the evidence records relied on for readiness. Later editing does not mutate a historical snapshot. Source corrections create a new eligible snapshot and invalidate dependent unpublished outputs. A currentness check covers content and specification versions, not just a timestamp or page refresh.

### Record separation

Accounts, relationships, student draft, submitted revision, completion decision, evidence/correction, input snapshot, readiness review, workflow run, individual attempt/output, generated draft, admin-edited draft, report review/approval, publication and audit event are distinct logical records/states. Implementations may choose storage details, but collapsing them must not erase lineage, transfer approvals or overwrite published content.

### Readiness

C: mapping follows required assessments, mentor interview and activities. D: exact sufficient evidence, completion rules and reviewing authority. P: a readiness checklist shows each approved prerequisite, evidence/version and unmet dependency. “No mentor available” keeps initial approval pending; it is not a reason to fabricate an interview or bypass review. Required missing parent evidence, where the detailed specification requires it, must remain a visible limitation rather than an invented response.

### Step 1 — Evidence Classifier

C: preserve original statement; record stakeholder, source, evidence type, career dimension, sentiment, confidence and contradiction status; distinguish facts, preferences, behavior, quotations, constraints, expectations, assumptions, contradictions and missing evidence. Produce structured JSON internally and a readable evidence register. Never convert an assumption into a fact.

P acceptance: each statement can be traced to the snapshot; unknown source references are rejected; inconsistent attribution is flagged; evidence types are visible in readable columns; the admin can correct interpretation while preserving the original. Classifier output confidence is an uncertainty cue, not scientific certainty. Detailed taxonomies/provider prompts require supplied specification and validation.

### Step 2 — Persona Identifier

C: only exact student/parent options from the missing detailed mapping specification. Retain selected hypothesis, alternatives, supporting evidence, needs, barriers, confidence, gaps and assumptions needing validation. Insufficient evidence produces an explicit limitation; do not force a label or stereotype.

P acceptance: option membership is validated against an approved version; parent/student attribution remains separate; no demographic label is treated as sufficient evidence; the reviewer can see why a hypothesis is supported through evidence references and a concise transformation summary. Hidden reasoning is not collected.

### Step 3 — Empathy and Need Mapper

C: separate student/parent maps using supplied categories with internal evidence/source/confidence/validation status. Preserve distinctions among warmth, engagement, discovery quality, convenience, parent transparency and student privacy. These distinctions are not a license to invent the missing category enumeration.

P acceptance: required categories match exact approved spec; source references are valid; gaps are explicit; conflict between parent transparency and student privacy is flagged for appropriate human review, not resolved by exposing private student data.

### Step 4 — User-Journey Mapper

C: separate student/parent analytical maps with exact eighteen stages and required fields from the detailed specification. Include its specified moments of truth, risks, conflicts, human intervention and automation opportunities. The eighteen analytical stages never control/replace the nine navigation stages.

P acceptance: exactly eighteen approved stages in approved order, all specified fields or honest missingness, validated sources and actor-specific experience. Do not invent a “synthetic production journey” to make output complete.

### Exact missing specification delivery

| Required source item | What must be supplied | Readiness consequence |
| --- | --- | --- |
| Student persona enum | Exact options, definitions, selection/exclusion and insufficiency rules | Step 2 blocked without it |
| Parent persona enum | Exact options and separate evidence rules | Parent Step 2 blocked without it |
| Empathy categories | Exact names/order/required fields and student/parent applicability | Step 3 blocked without it |
| Eighteen journey stages | Exact analytical names/order; not portal labels | Step 4 blocked without it |
| Journey field schema | Required fields, missingness rules and moments-of-truth/risk/intervention requirements | Step 4 blocked when incomplete |
| Classification taxonomy | Dimension/sentiment/confidence/contradiction rules and schema | No claimed validated classifier without source |
| Transformation/public rendering rules | Private versus shared field contract, traceability and review rubric | No public leakage or unsupported rendering assumptions |
| Specification governance | Source/version, owner, acceptance and change history | No unversioned silently changing mappings |

### Provider execution and failure

C: private provider credentials/prompts remain server-side; missing provider/specification produces explicit unavailable status, not a fabricated report. Validate structured outputs; provider failure, invalid response and retries are visible. Failed/partial/stale outputs cannot publish and do not damage existing publications.

P: each attempt records input references, spec/provider/config version, status, timing, validation error category and safe error summary. Retry displays affected downstream records and uses idempotent/conflict-safe execution. Retry limits, timeout thresholds, operational ownership and provider selection are D. Logs must not casually copy raw student statements or secrets into public diagnostics.

## 5. Review, publication and permission rules

### Initial report publication

Required work completed → current versioned four-step mapping run → admin review and approval → involved-mentor approval of that same report version → publication to student and authorized linked parent.

Both approvals are required before the first report is published. Admin completion capability does not replace mentor report approval. Admin cannot self-provision a mentor identity merely to bypass the independent requirement. If no involved mentor can approve, show pending; no automatic exception is defined.

### Subsequent revision — confirmed

Only admin revises maps. A revised draft needs admin approval of that exact new version before publication. Fresh mentor approval is not required. Retain all earlier published versions/history. Creating a new draft does not remove the last published shared report. Approvals for unchanged historical content remain historical records; they never become approvals of a new version.

### Exactly six shared outputs

1. Student persona.
2. Parent persona.
3. Student empathy and need map.
4. Parent empathy and need map.
5. Student journey map.
6. Parent journey map.

C: student and linked parent see the identical approved content version, view-only. Shared text is reviewed for respectful wording suitable to both. Do not expose drafts, partial outputs, prompts, classifier rules, evidence registers, private reasoning, confidence calculations, assumptions under review or private admin/mentor notes.

### Proposed publication checklist

Check current authorized publisher; required work/readiness; snapshot currentness; exact mapping spec; four valid current steps; six validated public outputs; no stale dependencies; admin shared-wording review and exact approval; initial involved-mentor approval where applicable; no later published-version regression. The transition and eligibility check are atomic. Repeated clicks yield the same publication result, not duplicate records. A student/parent can never invoke publication through a browser request.

P: preview shows what both audiences will see, without internal evidence. History labels Draft, Needs review, Approved, Awaiting mentor and Published in language suitable to the operator; final labels are owner reviewed. Report downloads/export are proposals, not implied requirements; approved export/privacy rules and accessible document formatting are prerequisites.

### Confirmed invariants

- Upstream changes identify and mark dependent outputs as requiring review.
- Affected downstream steps must be rerun before presenting results as current.
- Edited approvals do not carry forward to changed content.
- Draft saving/editing/generation never overwrites the published version.
- Actor, timestamp, exact version, action and relevant reason are recorded.
- Failed runs preserve earlier published reports and history.

### Proposed dependency contract

| Change | Proposed impact | Operator explanation |
| --- | --- | --- |
| Source evidence/submission correction | New snapshot; dependent mapping outputs and unpublished drafts stale | Show before/after, affected run/draft versions, required reruns/reviews |
| Step 1 output | Steps 1–4 and dependent draft need review/rerun | Classification change can affect every map |
| Step 2 output | Steps 2–4 and dependent draft need review/rerun | Persona interpretation changes downstream maps |
| Step 3 output | Steps 3–4 and dependent draft need review/rerun | Empathy change affects journey synthesis |
| Step 4 output | Step 4 and dependent draft need review | Earlier validated outputs may be reused if current |
| Public wording edit | New report content version; no inherited approvals | Re-review exact shared wording; initial mentor approval still required before first publication |
| Mapping spec/provider-rule change | Determine affected steps through approved dependency rules; new spec/run versions | Do not silently recompute or certify old work |
| Stage rule change | Owner-approved migration handling for submissions/completions | No retroactive state rewrite through a generic config save |
| Relationship revocation | Immediate access removal; current approval eligibility checked | No approval bypass by a revoked/uninvolved actor |

P: reuse valid upstream outputs only when snapshot/specification dependencies match and lineage is preserved. Final dependency graph and reopening/migration policies are D.

### Completed-work corrections

C: reviewing completed work does not silently alter downstream state. P: a correction request previews consequences and asks for an explicit authorized action/reason. Original submissions remain inspectable; student-facing safe feedback distinguishes a correction request from a data-loss event. Whether a completion is revoked, temporarily held or remains completed pending correction is D. Never invent a downstream reset policy.

## 6. Portals, data, security and quality requirements

### Browser-first principles — proposed

Daily work is performed with labelled inputs, clear buttons and readable statuses. IDs, revisions, CSRF values, JSON schemas and execution payloads are handled by software. Advanced diagnostics may offer read-only structured data to specifically authorized technical staff. Editing JSON is never necessary to save a profile, assign a student, review completion, approve a report or publish. A configuration failure must not be presented as an error in the student’s work.

### Screen inventory

| Screen / route concept | Status | Primary action | Required states |
| --- | --- | --- | --- |
| Public homepage / | C | Begin or sign in; support; Admin Login | Clear explanation; honest availability; no unsupported claims |
| Signup /signup | C | Create eligible student/parent account | Validation, existing account, gated collection, success |
| Login /login | C | Authenticate and route by role | Wrong credentials, expiry, account recovery |
| Recovery /recover and reset | C | Request/consume supported reset flow | Generic request response, expiry, used token, delivery limitations |
| Admin Login /admin/login | C | Authenticate admin only | Password visibility, recovery, non-admin denial, expiry |
| Admin dashboard /admin/dashboard | C | Open authorized student/workflow | Assigned list, empty assignments, permission denial |
| Student stage screens | C navigation; P detailed forms | Draft, submit, review or next available action | Draft, pending review, complete, locked, source/setup unavailable |
| Track Progress | C | See shared progress/report | Always available; pending report; published report |
| Parent portal | C | Shared progress/report | No link, authorized link, pending/published |
| Mentor portal | C | Relevant session/review action | No involvement/scope, assigned work, pending report review |
| Submission review queue | P | Select exact pending submission | Empty, filters, stale item, review in progress, missing criterion |
| Assignment management | P | Authorized audited link/assignment | Missing account, scope validation, verification pending, revoked |
| Product setup/readiness | P | Resolve precise setup dependency | Missing spec, invalid/incomplete draft, approved active version |
| Mapping inspector | C; P readable presentation | Inspect/run eligible steps | Pending, valid, stale, invalid, failed, blocked, retry |
| Report review/editor | C; P form experience | Save revised draft, review exact version | Diff, approval status, stale/unpublished, conflict |
| Publication confirmation/history | C; P checklist presentation | Publish eligible reviewed version | Eligibility failures, prior versions, repeated request |

### Navigation

C: nine stage labels are exact, with Track Progress always available. C: support persists in authenticated portals. C: public footer exposes clearly labelled Admin Login. P: admin main navigation is Dashboard, Students, Review queue, Mapping, Reports, History and Setup, filtered by permissions. P: daily review screens separate operational tasks from setup/diagnostics.

### Public website acceptance

Explain who 3DU serves, how discovery/mentorship/reflection work, student entry, parent/mentor participation and support. Use readable, respectful language. No invented social proof or assured outcomes. Keep personal journey records behind authorization. Proposal: identify whether the site is a fictional demonstration, restricted pilot or approved service before collecting any input.

### Authentication and admin access

C: accounts/data persist in real storage; localStorage is not identity or a shared database. Admin Login has email/password, show/hide password, recovery access and server-side role verification; success routes to /admin/dashboard. Anonymous admin page access requires login; signed-in students/parents/mentors are denied. Every admin API requires the relevant role and record scope. Logout and expiry invalidate session use. Privileged provisioning is secure, documented and not exposed as public role selection.

P: authentication forms preserve safe non-password input when validation fails; failures use readable messages without revealing whether a recovery address exists. Show the logged-in account email and role in the account menu so operators do not mistake another admin’s assignments for a defect. Do not display sensitive identity data in public headers.

D: approved session lifetime, email verification, identity provider, recovery delivery channel, operator provisioning verification and account suspension procedures. Live recovery must have an actually working authorized delivery mechanism; a spool-only flow cannot be called live email recovery.

### First-admin bootstrap and hosting

C: provide a secure setup command with prompted credentials; no hardcoded password or client-side secret. P: a deployment checklist confirms retained storage, migrations, HTTPS, first-admin access, student assignment, recovery status and required content/rules before calling the site ready. Bootstrap can require a trusted console; ordinary daily operations should not. Restricted bootstrap authorization remains distinct from public registration.

P: document the selected host’s service limits, HTTPS address, renewal and maintenance procedure, and persistence checks. A free hosting option is not an unlimited availability commitment. Public reachability does not authorize live minor-data collection.

### Admin portal operating requirements — proposed

### Dashboard and student discovery

C: dedicated protected dashboard connects to authorized student records/progress, parent links, mentor involvement, completion approvals, evidence, four-step mapping, draft editing, reruns, approvals, publication and history.

P: show signed-in operator identity, students awaiting authorized review, assigned-student search, missing-setup alerts and tasks awaiting mentor approval. Filters operate only on authorized records. Search results never reveal unrelated student existence. Clearly distinguish “no assigned students”, “no students registered”, “no pending submissions” and “no matching records”. A proposed assignment-management link is shown only to the owner-approved management capability.

### Review queue

P: queue items show student, stage, submitted time, applicable criterion version, current review state and permitted reviewer. The operator opens one submission and sees readable values and checklist. Do not require ID copying, revision editing or console commands. Claim/assignment locks and multi-reviewer handling require an approved operating model; regardless, optimistic concurrency must prevent stale review.

P: Request changes includes specific feedback suitable for the student; private operator notes use a visibly distinct input and are never sent by accident. Unsupported delivery channels remain unconfigured. The owner must decide whether in-app feedback alone is sufficient; no implicit email/SMS sending.

### Completion review form

| UI element | Proposed behavior |
| --- | --- |
| Submitted work | Human-readable labelled values; expandable approved attachments; source/version visible to operator without manual entry |
| Checklist | Approved stage-specific evidence requirements, marked met/unmet/needs clarification based on source-backed review |
| Review reason | Ordinary labelled text area explaining this decision; not JSON and not a replacement for criteria |
| Approve completion | Enabled only when configured authority/evidence/current revision permit; server independently validates |
| Request changes | Requires actionable shareable feedback; preserves old submission/review history |
| Missing criterion | “Setup required” and an authorized setup action; no silent default rule |
| Conflict | “This submission changed while you were reviewing it. Reload and review the new version.” |
| Success | Shows completed stage and next genuinely available action; does not approve/publish a report |

### Evidence editing and requests

C: preserve original statements/source attribution and separate stakeholders; correct evidence with a reason and history. P: evidence register uses labelled columns and source/correction diff. Admin editing cannot silently overwrite the student’s original submission. Requests state the missing information and why it is needed; safe collection/recipient/delivery method must be approved. No improvised parent questionnaire is introduced.

### Mapping workspace

C: inspect every step’s input, extracted evidence, transformation summary, output, confidence/gaps, downstream payload and validation/execution state. P: tabs and readable tables show these without forcing raw JSON editing. Advanced structured view is read-only. Run/rerun controls preview affected downstream artifacts and show unavailable prerequisites before execution. No hidden chain-of-thought is requested or displayed.

### Report editor and publication

C: only admin edits maps; editing creates a new content version and invalidates inherited approvals. P: a six-section editor shows proposed public wording alongside approved-version comparison, protected evidence links and warnings about private material. Wordings that will be shared with both student/parent are visibly labelled. Exact-version approve/reject/publication actions bind automatically to the reviewed content.

P: publication confirmation shows all eligibility checks, current admin approval, initial involved-mentor approval where required, current run/snapshot/spec versions and safe audience preview. A reason is an ordinary text field. Publish is disabled when ineligible and server-side atomic checks still reject bypass attempts. Repeat requests never duplicate publication.

### Product setup workspace

P: authorized setup forms separately cover approved fields/content references, stage rules, reviewer scopes, readiness criteria, mapper spec version, provider/delivery status and policy-release gates. Require draft → validate → owner approve → activate, with actor/time/version/reason. Proposed production configuration approval is separate from report approval. No owner, rule, validated instrument or policy is invented by form defaults. Configuration changes show affected records and require reviewed migration/invalidation actions.

### Parent portal

C: show only authorized linked student’s same Track Progress and published six-map report, view-only, with support. No raw answers, private notes, drafts, internal workflow outputs or unrelated students. No extra parent workflow/questionnaire is introduced.

P: if linking is pending/unavailable, explain the status and approved support action without exposing whether an arbitrary student exists. Display which authorized student is being viewed when multiple links are allowed; whether multiple links are supported is D. Never infer a link merely because an entered email matches an account.

Parent evidence remains a supported internal input type, separate from student evidence. D: its approved collection process, attribution/verification and consent. Until decided, preserve missing parent evidence as missing; do not infer a parent persona from a student’s account of a parent as if it were an original parent response.

### Mentor portal

C: actual involvement determines access, not role alone. P: show assigned/involved student cards, permitted sessions/tasks and a queue for exact initial report review. Unknown field scope remains restricted. A completion checklist references permitted evidence; if necessary evidence is outside scope, route the task to an authorized reviewer instead of exposing it.

C: mentors cannot edit/regenerate maps. Initial report review shows exactly the admin-approved public version, not a later edited draft. P: Accept/Request clarification are ordinary forms with review reasons; whether mentor rejection returns a draft for admin correction is an owner-approved workflow proposal. Any corrected version requires new exact-version approvals. Session records are attributable to their author; visibility of other mentors’ notes is D, restricted until approved.

P: every enabled assessment, career article, mentor profile, activity, reflection prompt, mapping taxonomy and support message has a source/owner/version and review state. Unapproved content is not used in a live student experience. Superseded content is retained for historical lineage where permitted by policy. Age suitability, localization, accessibility and content-update procedures are D.

C: persistent “Contact for support”; mailto:prashasawan@gmail.com. Phone is labelled “number not supplied / unavailable” and not callable until a real number is authorized. No fabricated support availability or response-time promise.

P: meaningful in-app notifications can indicate submitted, changes requested, approved and published states without leaking private notes. Email/SMS/push delivery and contact-sharing are proposals requiring approved channels, consent, templates and provider configuration. Recording an internal request does not count as successfully delivering a message.

C: no live minor-data collection under invented terms. D: consent, guardian verification, privacy notice, retention, deletion, export, incident process, safety escalation, who can view sensitive evidence and operational owners. Do not assert a jurisdiction-specific age rule or legal compliance without approved advice/policy.

P: a formal release gate separates fictional demo, restricted approved pilot and real service. Each gate lists approved policies, allowed data, accessible accounts/content, integration status and responsible sign-off. Fictional fixtures are labelled and separated from real records. Changing a mode flag alone cannot authorize production collection.

P: field minimization and purpose are reviewed before activation. Sensitive financial/location/family information is collected only when approved and necessary; refusing optional information must have a defined, respectful consequence. Parent transparency never means indiscriminate access to private student evidence. Requests for deletion/export are modelled only after scope, authorization and history/retention treatment are approved.

P: upload/contact/session safeguarding controls must be specified before enabling those capabilities. Malware scanning, attachment permissions, inappropriate-content handling, mentor conduct and incident pathways remain explicit dependencies, not invented operational policies.

### Confirmed minimum behavior

Server-enforced role/record/field/stage access; persistent secure accounts; no browser-held provider secrets; protected drafts/internal outputs; reliable state across sessions; versioned migrations; conflict-safe edits; duplicate-safe approvals; atomic publication; clear failure/empty/denied states; responsive keyboard-accessible layouts, labelled forms, visible focus and reduced-motion support.

### Proposed nonfunctional acceptance plan

| Area | Proposed acceptance method | Target/owner needing approval |
| --- | --- | --- |
| Accessibility | Keyboard-only end-to-end tests, labelled errors, focus recovery, screen-reader review, contrast and reduced motion | Conformance standard/level, audit threshold and owner D |
| Compatibility | Test agreed desktop/mobile browsers and breakpoints on actual devices | Supported browser/device matrix D |
| Availability/performance | Measure agreed journeys and error rates using approved non-sensitive telemetry | Service targets, traffic/load assumptions and monitoring owner D |
| Backup/recovery | Restore into separate environment and check accounts/work/publication/history consistency | Frequency, retention, recovery targets and owner D |
| Security | Threat model, negative authorization tests, credential/session/recovery checks and independent review scope | Security standard, frequency and owner D |
| Hosting | HTTPS, retained database, migration/runbook, deployment rollback, renewal/service limits | Provider/plan, budget authorization and operational owner D |
| Integrations | Real provider/delivery contract tests including failure and credential rotation | Selected services, credentials, retry policy and owner D |

Do not replace unknown targets with arbitrary numeric success benchmarks. Engineering can measure observed behavior; product/operations must approve required thresholds.

| Trigger | Proposed user-visible behavior | Authorized operator detail |
| --- | --- | --- |
| Locked stage | Exact confirmed locked message plus next available action | Which preceding completion is unmet |
| Saved draft | “Your draft is saved” with safe saved state | Persisted revision; no auto-completion |
| Submission accepted | “Submitted for review” and safe next action | Exact submission/criterion version |
| Completion rule absent | “This stage is waiting for setup; your work is saved” | Specific missing criterion/authority and responsible setup action |
| Invalid field | Error beside the field with correction guidance; preserve safe inputs | Validation rule; no raw stack trace |
| Review reason absent | Labelled reason-field validation | Not “invalid JSON” |
| Stale review | Explain changed submission and require new review | Current/reviewed versions and diff |
| No admin assignments | Explain assignment scope; authorized assignment/help action | Distinguish account missing, role wrong and link absent without broad disclosure |
| Parent not linked | Approved link/support status; no student existence leak | Verification/process record for authorized operator |
| Mentor scope absent | No raw records; explain pending permitted scope | Exact approved involvement/field scope |
| Mapping spec/provider missing | Clear waiting state; no fabricated report | Exact missing enum/spec/credential destination, excluding secret values |
| Invalid/provider-failed run | Shared published report remains intact | Attempt, safe failure reason, validated retry controls |
| Initial mentor unavailable | Pending review; no bypass | Eligible current involvement and same-version approvals |
| Before first publication | Exact confirmed pending message | Private readiness/review states stay internal |
| Expired login | Sign in again; avoid falsely claiming unsaved work was saved | Session revocation/expiry checks; preserve unsaved UI text where feasible |
| Access denied | Understandable denial/support or role portal action | Auditable safe permission event; no private record details |
| Network save failure | Keep entered work visible and offer retry; no false saved badge | No duplicate submit/publication on retry |

Final wording beyond the two confirmed messages requires product review. Diagnostic terms must not overwhelm student/parent flows.

## 7. User stories and release acceptance

### User stories

| Story | User value | Testable evidence |
| --- | --- | --- |
| US-01 | Student saves/resumes | Same draft after refresh/logout and authorized later login |
| US-02 | Student knows available/locked stages | Nine correct statuses; locked URL safe return action |
| US-03 | Parent sees only shared authorized progress/report | Equality of authorized public content; raw/unrelated reads denied |
| US-04 | Involved mentor reviews exact initial report | Role/involvement/version enforced; editing/regeneration denied |
| US-05 | Admin understands mapping | Each step’s source, summary, output, gaps/confidence and downstream status inspectable |
| US-06 | Source correction invalidates dependent outputs | Currentness checks and stale-publication rejection |
| US-07 | Pending results are explained without leaks | Exact pending message; no draft/internal payload exposed |
| US-08 | Revision preserves published version | New draft/version/approval; historical publications retained |
| US-09 | Support is easy to find | Persistent correct mailto and non-callable phone placeholder |

### Admin authentication acceptance

| ID | Status | Contract |
| --- | --- | --- |
| ADM-C01 | C | Dedicated /admin/login with email/password, visibility control and recovery |
| ADM-C02 | C | Public footer Admin Login link |
| ADM-C03 | C | Persistent authentication; server checks admin role before access |
| ADM-C04 | C | Success redirects to /admin/dashboard |
| ADM-C05 | C | Admin pages/APIs reject unauthenticated/non-admin access appropriately |
| ADM-C06 | C | Secure documented first-admin provisioning; no hardcoded/client credentials or privileged signup |
| ADM-C07 | C | Logout and expiry handling |
| ADM-C08 | C | Dashboard access to records/progress/relationships/completion/evidence/mapping/drafts/reruns/approval/publication/history |
| ADM-C09 | C | Preserve initial two exact-version approvals and later admin-only approval |

### Proposed usability acceptance

| ID | Status | Proposed acceptance contract |
| --- | --- | --- |
| UX-P01 | P | Ordinary operational actions never require JSON, IDs or console commands |
| UX-P02 | P | Each enabled stage has an approved typed form/content/completion contract |
| UX-P03 | P | Admin review queue opens exact submissions with readable checklists and safe feedback |
| UX-P04 | P | Missing configuration is distinguishable from student errors; approve controls accurately represent eligibility |
| UX-P05 | P | Authorized assignment management is a browser form with verification/scope/audit checks |
| UX-P06 | P | Account menu identifies signed-in email/role to reduce assignment confusion |
| UX-P07 | P | Shared wording editor/diff/eligibility checklist handles exact version binding automatically |
| UX-P08 | P | Product setup uses labelled versioned forms, with owner approval before activation |
| UX-P09 | P | Readable evidence/mapping inspector; optional restricted read-only structured diagnostics |
| UX-P10 | P | Hosting/bootstrap runbook separate from daily end-user use; no unapproved paid purchase |
| UX-P11 | P | Submitted/reviewed/completed and report-published states are visibly distinct |
| UX-P12 | P | Preserve safe draft inputs on validation/network/conflict errors; do not claim unsaved work is saved |

These are acceptance requirements for the agreed release, not a claim they currently pass. Scenario content must use isolated labelled synthetic fixtures until live use is approved.

| Test ID | Scenario | Expected outcome |
| --- | --- | --- |
| AUTH-01 | Eligible fictional student/parent signup | Persistent account; correct portal; no privileged role granting |
| AUTH-02 | Crafted signup/profile request asks for admin/mentor | Server refuses; no privilege change |
| AUTH-03 | Valid/invalid login and role routing | Authorized identity only; wrong credentials handled safely |
| AUTH-04 | Recovery nonexistent/existing account | Same safe request response; delivery actually matches configured mode |
| AUTH-05 | Expired/reused reset token; successful reset | Reject invalid use; successful reset preserves role and revokes sessions |
| ADM-01 | Admin credentials at dedicated login | Dashboard redirect and authorized scope |
| ADM-02 | Anonymous/expired admin page/API | Login requirement/401; no private response |
| ADM-03 | Student/parent/mentor directly requests admin page/API | Server denies, regardless of hidden navigation |
| ADM-04 | First-admin bootstrap; duplicated account email | Prompted secret hash; no default credential; no silent role overwrite |
| ADM-05 | Assigned/unassigned admin records | Only authorized student scope; clear correct empty-state meaning |
| STG-01 | Stage 1/Track Progress at start; Stage 2 direct URL | Available/always available; locked message and next action for Stage 2 |
| STG-02 | Open, Next, save and submit | No implicit completion or unapproved downstream unlock |
| STG-03 | Save, refresh, logout and later login | Authorized persistent draft restored |
| STG-04 | Missing criterion and otherwise submitted profile | Clear setup-needed status; no fabricated completion or misleading enabled action |
| STG-05 | Valid exact submission/current approved checklist | Allowed reviewer completes; genuinely next stage unlocks |
| STG-06 | Submitted revision changes while reviewer works | Stale review rejected; safe compare/reload prompt |
| STG-07 | Involved mentor lacks required evidence field scope | No leakage or invalid approval; authorized review route |
| STG-08 | Review completed work/correction | Original preserved; approved dependency consequences explicit |
| STG-09 | Admin approves later-stage work outside order under approved rule | Earlier missing completions still gate student navigation |
| REL-01 | Crafted email/student ID link attempt | Does not grant parent or mentor access |
| REL-02 | Authorized assignment/revocation | Audited scope update; immediate access effect |
| PAR-01 | Parent tries raw answers/private notes/another student | Denied; shared report/progress equality remains |
| MEN-01 | Uninvolved mentor; forged student ID; map edit/rerun | Denied server-side |
| MAP-01 | Missing persona/categories/eighteen-stage spec/provider | Honest limitation/blocked generation; no invented values |
| MAP-02 | Snapshot change after run; unknown evidence reference | Output stale/invalid; ineligible publication |
| MAP-03 | Classifier turns an assumption into a fact | Invalid output rejected/flagged; source retained |
| MAP-04 | Insufficient evidence for persona | Explicit limitation and gaps, no forced label |
| MAP-05 | Nine navigation labels substituted for analytical stages | Schema/spec rejection |
| MAP-06 | Step rerun/failure/invalid response | Visible attempt/error; correct downstream invalidation; old publication preserved |
| REP-01 | Initial draft with no/admin-only/wrong-version mentor approvals | Publication rejected |
| REP-02 | Initial exact admin then involved mentor approval | Atomic permitted publication; six validated shared outputs |
| REP-03 | No involved mentor can approve | Pending; no admin bypass |
| REP-04 | Approved draft edited | New version with no inherited approval; previous publication preserved |
| REP-05 | Later revised version with exact admin approval | Publish without fresh mentor approval; retain history |
| REP-06 | Simultaneous/repeated approval/publication requests | Conflict/duplicate-safe, at most one transition per version |
| REP-07 | Stale/partial/failed draft presented as current | Rejected; no public internal/partial output |
| VIS-01 | Student/parent APIs and report UI | Explicit safe schema; identical published version/progress content |
| UX-01 | Daily admin profile review by nontechnical operator | No JSON, revision editing or terminal; checklist and labelled reason sufficient to operate approved rule |
| UX-02 | Field/reason validation failure | Readable contextual errors, entered safe text retained |
| UX-03 | Keyboard/mobile/reduced-motion journey | Core flows usable, clear focus/labels; approved conformance thresholds checked |
| OPS-01 | Hosted reload/restart and database restore | Persistent accounts/work/reports; no accidental reseeding/reset |
| OPS-02 | Support action/phone placeholder | Exact mailto; no invented callable phone |
| SAFE-01 | Policies absent or mode flag toggled | No authorization to start live minor-data collection |

### Proposed delivery increments

| Increment | Purpose | Entry dependencies | Exit evidence |
| --- | --- | --- | --- |
| A — experience/rule agreement | Resolve what the app should do, before further feature coding | Owner review of this draft and missing stage/spec materials | Approved stage contracts, UI scope, decision register and acceptance plan |
| B — daily-admin usability | Replace JSON/console dependence in approved operations | Approved UX-P scope and assignment-management authority | Browser review/assignment/checklist/draft workflows; negative permission tests |
| C — real student stages/content | Build approved forms, instruments and content | Approved fields, assessments, career/activity inventory and completion rules | Each stage’s functional and source-validity tests; no generic-notes substitution |
| D — full mapping/report experience | Source-valid generation, readable inspection and publication | Complete exact mapping spec, readiness criteria, provider integration if used | Structured validation, human review, version/invalidation and six-map publication tests |
| E — approved pilot/live release | Operationally safe hosted use | Policies, guardian process, owners, infrastructure/integrations and final approval | Release checklist, backups/recovery/security/accessibility evidence and explicit sign-off |

Delivery increments are proposals; no dates, prices or launch targets are established. Independent work may proceed without treating missing decisions as answered. No static mockup alone counts as functional acceptance.

### Required release checklist

The release checklist covers: authentication/recovery/routing; sequencing/direct requests/completion/always-open progress; cross-session persistence; parent/mentor/admin scope/audit; upstream invalidation and failed-run preservation; exact-version initial two approvals/later admin approval; identical shared maps/progress without internal leakage; responsive keyboard/reduced-motion/support; code/schema/setup/verification deliverables.

Proposed readiness checks: all enabled stages have approved content/criteria; daily admin operations are nontechnical forms; unavailable setup is clearly explained; secure linking/provisioning procedures are usable by authorized operators; real delivery/provider integrations work where promised; backup/restore and hosted maintenance are demonstrated; minor-data policies and release approval exist; acceptance distinguishes passed, failed, skipped, blocked and unrun checks.

### Definition of done

For an approved feature: source requirement and decision are traceable; typed UI and backend behavior are implemented; permissions, normal/negative/empty/error/concurrency paths pass relevant tests; persisted state survives appropriate restart/login; wording and accessibility are reviewed to approved standards; dependencies genuinely configured; setup/support instructions are usable; no false completion/publication claim exists. A placeholder, hidden button, zero-test run or mocked provider response does not satisfy this definition.

### Delivery requirements

Deliver working code, versioned migrations/data models, role/relationship/field enforcement, all agreed screens/forms, real account provisioning/recovery flow, stage contracts/content integration, snapshot/workflow/report/approval/publication lineage, appropriate tests and verification report, variable template without secrets, hosted deployment/maintenance/restore instructions, nontechnical operator guide and missing-decision register. Synthetic fixtures are clearly labelled and isolated.

Before coding a proposed requirement, verify its approval status and supplied materials. Before enabling a stage, confirm its accepted content/fields/criterion/authority. Before generation, confirm exact specification/provider/readiness. Before publication, enforce the required version-specific approvals. Before live collection, obtain actual policy and release authorization. Continue independent authorized work where another dependency is missing; do not turn a blocked component into fabricated production content.

## 8. Measurement, dependencies and risks

### Success measurement

No numeric targets, baselines, event taxonomy or measurement windows are established. Data collection and measurement require approved privacy controls, definitions and owners.

| Outcome area | Definition to agree | Baseline / target |
| --- | --- | --- |
| Pipeline progression | Eligible students completing each stage within an agreed cohort and time window | TBD |
| Progress clarity | Ability to identify the next available action in an approved usability exercise | Method and threshold TBD |
| Mapping quality | Source traceability, missingness handling, contradiction handling and reviewer corrections by step | Rubric and threshold TBD |
| Publication integrity | Exact-version approvals, stale-output prevention and preservation of published versions | Monitoring and target TBD |
| Access control | Unauthorized role, relationship and record reads/writes rejected | Coverage and threshold TBD |
| Experience health | Authentication, recovery, saving, resuming and workflow reliability | Service targets TBD |

### Dependencies and blockers

- Approved stage-specific fields, content, completion criteria and reviewer authority.
- Actual validated assessment instruments, permitted use, scoring rules and limitations.
- Approved career information, mentor profiles, session procedures and activity inventory.
- Exact mapping specification: student/parent persona options, empathy categories, eighteen analytical journey stages and all required fields.
- Mapping readiness criteria for assessments, mentor interview and activities.
- Authorized provisioning, relationship verification and mentor field-level access procedures.
- Secure generation and recovery integrations where needed; working persistent hosted storage and maintenance ownership.
- Approved minor-data consent, guardian verification, retention, deletion, export, incident and privacy policies before live collection.
- Accessibility and browser expectations, support ownership and any approved measurement or launch commitments.

### Principal risks and controls

| Risk | Required control |
| --- | --- |
| Unvalidated assessment or invented career-fit output | Use supplied approved instruments only; do not fabricate scores or scientific validation. |
| Student/parent conflict or unsuitable shared wording | Separate evidence; review shared wording; publish only the approved shared version. |
| Unauthorized private-data exposure | Server-side role, relationship, stage and record checks; explicit negative tests. |
| Stale maps after evidence changes | Versioned snapshots, dependency invalidation and blocked stale publication. |
| Misleading approval controls | Show the missing criterion or authority; do not suggest that a review reason supplies a completion rule. |
| Unusable routine administration | Proposed labelled forms, review checklists and safe browser operations; technical setup separate. |
| Failed workflow or conflicting edits | Preserve publications; visible failures; version checks and atomic transitions. |
| Demonstration mistaken for live readiness | Label synthetic records, disclose unavailable integrations and block unapproved minor-data collection. |


## 9. Open decisions and references

All decisions below remain D unless explicitly approved in a subsequent owner response. Suggested responsible function is a proposal; no person is assigned by this draft.

| ID | Decision to resolve | Suggested responsible function | Affected delivery | Precise answer/material needed |
| --- | --- | --- | --- | --- |
| D-01 | Confirm decision owners/final approver | Product sponsor | All | Names, authority and how approvals are recorded |
| D-02 | Approve proposed nontechnical admin UX | Product/design | Admin experience | Accept/edit UX-P01–12 and representative screens |
| D-03 | Stage 1 actual fields and requiredness | Product/privacy | Student profile | Approved field list, purpose/validation/visibility and optional versus required |
| D-04 | Stage completion versus admin/mentor authority | Product/safeguarding | All stages | Per-stage sufficient evidence, allowed reviewers and out-of-order approval/reopening policy |
| D-05 | Submitted work changes/request-changes lifecycle | Product | Draft/review | Whether withdrawal/editing is allowed; safe feedback and resubmission contract |
| D-06 | Approved assessments/scoring | Assessment owner | Stage 2/mapping | Full instruments/licenses/versions/questions/scoring/limitations/completion |
| D-07 | Interests/strengths reflection content | Content/product | Stage 3 | Exact prompts/artifacts, use of results and completion checklist |
| D-08 | Career content and exploration evidence | Content/product | Stage 4 | Source inventory, editorial fields/filters/update policy and completion |
| D-09 | Mentor directory/request/assignment process | Mentorship/safeguarding | Stage 5 | Real profile fields/verifications/capacity/authority; no automatic matching |
| D-10 | Session/interview/booking evidence | Mentorship/product | Stage 6/readiness | Required session/interview evidence, field scope, cancellation/scheduling and review |
| D-11 | Activity inventory/evidence/review | Content/mentorship | Stage 7 | Real activities, evidence rules, required/optional distinctions and reviewer |
| D-12 | Stage 8 completion and follow-up | Product | Stage 8/progress | Whether/how it completes independently of publication; optional feedback/export |
| D-13 | Mapping readiness | Product/mapping | Generation | Required assessment/interview/activity criteria and source-backed checks |
| D-14 | Full detailed mapping specification | Mapping owner | Steps 1–4/six outputs | Exact enums/taxonomies/eighteen names/order/fields and uncertainty rules |
| D-15 | Safe student/parent public wording/schema | Product/privacy | Report sharing | Public field contract, shared wording rubric and conflict/privacy treatment |
| D-16 | Granular dependency/reopening/migration policy | Product/engineering | Edits/reruns | Approved dependency graph, config changes and completed-work consequences |
| D-17 | Assignment/account management authority | Product/security | Admin browser management | Which admins can manage which actors/records and how authority is granted |
| D-18 | Student-parent verification and parent evidence collection | Privacy/safeguarding | Parent links/evidence | Approved verification, collection, revocation and multi-student scope |
| D-19 | Mentor field-level access/notes | Privacy/mentorship | Mentor portal | Exact permitted fields and author/shared-note scope |
| D-20 | AI provider/private prompts and delivery integration | Technical/product | Generation/recovery/messages | Selected providers, secure bindings, approved source prompts and contract tests |
| D-21 | Minor consent/retention/deletion/export/incident policies | Privacy/safeguarding | Live collection/release | Approved actual policies, owners and implementation acceptance |
| D-22 | Hosted operations/security/session standards | Technical/operations | Public service | Supported hosting budget, HTTPS/storage/backup/recovery, session policy and security review |
| D-23 | Accessibility/browser/device expectations | Product/design/QA | Release verification | Approved conformance level/matrix and audit threshold |
| D-24 | Support/notifications | Operations/product | Communication | Real support number or email-only, support owner, approved channels/templates |
| D-25 | Measurement/analytics/business/launch | Product sponsor | Operational planning | Approved data/event collection, definitions, owners, baselines/targets, budget/model/cohort/date if desired |

### Approval record template

For each accepted/changed decision record: decision ID; exact approved text/source file/version; approving person and authority; date; affected requirement IDs; rationale; dependent implementation/testing changes; whether it permits fictional demo, pilot or real operation; any remaining limitations. Record explicit rejection/deferment as such. Approving this PRD does not by itself provide the missing instrument/specification files or authorize collection under unapproved policies.

### References required

The detailed mapping specification, approved assessment instruments, content inventories and policy documents must be supplied and versioned before dependent features are enabled. Referenced prototype materials are illustrative; no missing specification is assumed to have been read.

### PRD owners

Pallipalem Huns Pavitra

Diksha Omar

Nikunj Katariya

