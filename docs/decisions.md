# Decision boundaries and continuation

## Source of truth

The supplied attachment was named **3DU PRD.docx**, rather than the prompt's **3DU PRD(1).docx**. Its entire text was read before code changes and retained in `source-prd.txt`. No other specification, video or prototype screen was supplied. References inside the document were treated as references, not as material already read or additional authorization.

Confirmed requirements include the exact nine navigation stages, sequential unlocking, always-open Track Progress, save/submit/completion separation, role/relationship enforcement, distinct portals, attributed separate stakeholder evidence, four inspectable steps, six shared outputs, initial admin-then-involved-mentor approval of the same version, subsequent admin approval, immutable published history, and the specified support email/phone placeholder.

Prototype context informs the purpose/presentation only. It establishes neither validated assessments nor implemented research, verified mentor qualifications, real outcomes or usage. None of those claims were added.

## Reversible engineering choices (not product-owner decisions)

- Flask/Python 3.12, SQLite WAL with foreign keys, server-rendered Jinja, local CSS/JavaScript and versioned SQL migrations. No cloud service is necessary for synthetic local use. SQLite is suitable for this local single-instance workflow; production scaling/hosting remains open.
- Opaque random server-side session cookies, hashed session/recovery tokens, scrypt password hashes, SameSite=Lax/HttpOnly cookies, CSRF on every mutation, security headers, login/recovery rate limits, eight-hour sessions and thirty-minute recovery tokens. These lifetimes are engineering defaults, not approved product session policy. HTTPS requires secure cookies; production authentication/security review remains open.
- Recoveries use a private local delivery spool. A real delivery provider has not been selected. No message is sent.
- Every new draft has an immutable content version; edits create new records. Stage revision and step attempt checks reject conflicting updates. Approval uniqueness and atomic `BEGIN IMMEDIATE` publication protect duplicate/concurrent requests. Historical approvals remain inspectable but do not transfer to new content.
- Admin assignment is explicit rather than granting every admin access to every student. Privileged accounts and relationships can only be provisioned by trusted CLI operators. Product-approved linking/assignment procedures remain open.
- Completion scope and mentor field scope are separate; scope defaults expose no raw fields. A scope must name approved draft fields explicitly. Legacy stage-only scope does not grant raw data access.
- Unknown assessment/activity content uses a clearly labelled fictional draft workspace. Approved configurable draft-field names can be displayed; this is not a validated assessment instrument or recommendation algorithm.
- Human completion criteria specify approver roles, submission requirement and required draft fields. No rule is enabled initially. Admin can approve outside navigation order only if the supplied criterion permits; portal locks still require every preceding completion.
- Readiness uses configured required stage completions plus separate source-backed admin confirmations of assessments, mentor interview and activities, bound to exact snapshot and configuration versions. This is a configurable human review mechanism, not invented assessment or activity criteria. It rejects missing/assumed proof.
- Evidence corrections are append-only. Source changes conservatively invalidate every mapping step for that student; step changes invalidate that step and downstream steps. The conservative dependency rule is documented and reversible, not a claim about unspecified granular product dependencies. Published historical content is retained as the last approved published version.
- Step outputs are structured JSON; internal confidence uses a 0–1 engineering validation range, not a calibrated probability or career-fit score. Original statement/source checks, known-evidence references, exact configured enumerations and JSON schemas prevent malformed outputs. No hidden model reasoning is requested or exposed.
- Operator-authored synthetic steps and shared drafts are supported. No AI generation is fabricated: the provider contract is unconfigured and returns a recorded blocked attempt. Initial manual report drafts are explicitly `admin-edited`; the `generated` state is reserved for a future configured generator.
- Public map responses allow only summaries and labelled text items. Human shared-wording approval is explicit. Public response schemas prevent structural leakage; reviewers still must check that text does not include private evidence or inappropriate wording.
- The application is gated to synthetic development. Switching `SYNTHETIC_ONLY` off blocks collection; there is no production activation switch. Synthetic fixtures only populate isolated test databases, never the normal application database.
- Calm green/cream presentation, system fonts, responsive grids, focus outlines, skip navigation, labelled controls, explicit status/error text and reduced-motion CSS. This does not establish conformance to an unspecified accessibility standard.

## Missing specifications and precise unblockers

| Missing decision/material | What is blocked | What to supply |
| --- | --- | --- |
| Detailed mapping specification | Real persona/empathy/journey generation | Exact **student persona options**, **parent persona options**, **empathy/need categories**, the ordered **eighteen analytical journey stage names**, **required stage fields**, and specified moments-of-truth/risk/conflict/intervention/automation requirements. No nine-stage substitute is allowed. |
| Assessment instruments/scoring | Live assessment questions and scores | Validated source instruments, licensed/approved questions, versions, scoring rules and evidence requirements. |
| Stage-specific completion rules | Normal completion/unlocking | Exact evidence criteria and which admin/mentor roles can approve each stage; define how approval authority relates to criteria and whether an admin may independently complete particular work. Approval does not override report gates. |
| Mapping readiness | Real generation eligibility | Exact assessment, mentor-interview and activity criteria plus their required completion/evidence rules. Source-backed review mechanism is implemented but no real rule is loaded. |
| Mentor field access | Additional raw work visibility | Approved per-stage field names and necessary session/record scope. Default involvement allows no raw draft fields. |
| Student-parent linking, involvement/provisioning procedure | Self-service real relationships and privileged roles | Authorized identity/guardian verification, assignment/provisioning workflow and responsible operator. An email/student ID alone never establishes access. |
| Minor-data policies | All live data collection/use | Approved consent/guardian verification, privacy, retention, deletion, export, incident policy and responsible owners. No invented policy text exists. |
| AI provider/private prompts | AI execution | Selected provider, secure server-side credentials, complete private specification/prompts, integration/validation rules. No provider key is currently required/requested because no provider is chosen. |
| Recovery delivery provider | Real emailed recovery | Selected service, authorized sending identity and secure credentials. Local recovery is verified; outbound delivery is unimplemented. |
| Content inventory | Real career exploration/activity/mentor content | Approved materials and real, authorized mentor profile data. No automated matching, ranking, affiliations or fictional credentials were added. |
| Phone support | Operational phone action | Real authorized support number, or confirmation of email-only support. Current number is a non-callable placeholder. |
| Release/operations | Production readiness | Product/technical/final approval owners, hosting, backup/recovery/security standards, device/browser and accessibility thresholds, operational support owners and rollout approval. |
| Measurement | Live analytics and success evaluation | Approved data collection/event definitions, owners, windows, baselines and targets. No analytics/targets/pricing are invented. |

Missing decisions do not block local authentication, persistence, authorization, draft state, inspection, human review structures, versioning, publication safety or synthetic testing. They do block a claim that assessment/mapping generation and production operations are complete. No external services were purchased, no emails/messages sent, no public deployment made, and no real minor-data collection was activated.
