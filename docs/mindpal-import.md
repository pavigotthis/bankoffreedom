# Supplied mapping-only workflow

The user supplied the MindPal JSON export and its original full mapping prompt, then explicitly confirmed **only Evidence Classifier, Persona Identifier, Empathy and Need Mapper, and User-Journey Mapper**. Only these four nodes run. Imported text is private configuration interpreted under the PRD, not instructions to remove the frontend or execute the entire exported engine.

The two files together supply eight student/five parent personas, ten evidence types, seventeen empathy categories, warmth definitions, eighteen exact analytical stages and sixteen stage fields plus six markers. The JSON alone omits stage names and abbreviates some categories; the original prompt resolves them. It explicitly allows blank input, so those inputs remain missing rather than enforcing the JSON's earlier required flags. Stage completion and readiness are separate mentor-defined criteria.

Numerical career fitting, alignment scores, ranking, automated mentor matching, router thresholds and exported educator-gate branches remain excluded. Analytical stage names such as “Career-cluster shortlisting” and “Parent–student alignment discussion” mean qualitative exploration and discussion, not those algorithms. The separately supplied research career model is reference only and is not used by these four steps. Source role descriptions such as “psychometrician” do not prove scientific validation.

## Update the existing installation

Back up the private `instance` folder. From the repository directory, pull code and apply migrations without resetting records:

```bash
git pull --ff-only origin main
.venv/bin/python -m flask --app three_du:create_app init-db
```

Upload both source files to a private host folder outside `static`. Import with an existing provisioned admin and the same database binding as the web application:

```bash
.venv/bin/python -m flask --app three_du:create_app import-mindpal "/absolute/private/path/mapping-export.json" --mapping-prompt "/absolute/private/path/mapping-prompt.txt" --actor-email YOUR_ADMIN_EMAIL --reason "Import supplied mapping-only definitions"
```

Replace `YOUR_ADMIN_EMAIL` with the admin login email. The command privately stores both original sources, source fingerprints, selected four instructions, normalized fields, actor/reason/time and configuration version. Existing stage/readiness rules and publications are preserved. Unpublished dependent work is invalidated. An identical repeated import is a no-op. Importing JSON alone remains supported as a partial configuration, but cannot supply the eighteen stages.

Do not commit the raw export, full private prompt or database to a public repository. The protected admin workspace displays the imported instructions, source fingerprint, excluded branches and attempts. Runs retain their exact source fingerprint; admin inspection can retrieve historical instructions. Student/parent responses never expose those instructions.

## Persistent student and parent intake

Student Stage 1 links to `/students/STUDENT_ID/intake`. Linked parents get the same URL, but the server serves only that parent's own fields and entry. The export's labelled text fields are used. The full prompt allows blank inputs; scientific questions or response scales are not invented.

Saving preserves a draft. Initial submit saves attributable evidence; one later resubmission updates the same entry and locks further author editing. Repeated identical request keys are idempotent; changed content with an already used key is rejected. Concurrent resubmissions permit only one accepted revision. Draft saves do not replace the submitted version or consume the resubmission. Validation errors retain the current browser text. Entry/history/source metadata record author, student, specification version and timestamps.

Admin sees labelled submitted values, author email, initial/latest metadata and stable entry ID in the assigned student workspace. Each source preserves student/parent attribution and correction lineage. Changing input invalidates unpublished mapping and requires a new snapshot. Student drafts/initial submission mirror Stage 1 work without completing it. After initial submission, unsent revision drafts do not replace the admin-review version. The legacy notes API is blocked for imported profile forms, preventing revision-limit bypass. Admin completion uses an ordinary reason field, the current submitted revision and active mentor-defined criteria. No intake action completes a stage or publishes a report. Completed student work remains read-only pending an authorized correction; parent revision allowance remains separate from the student's stage completion.

Educator and mentor notes are authorized internal evidence; do not accept an impersonated staff record from student/parent forms. Scoring-only Mentor Database is excluded. Sensitive live collection remains blocked pending approved policies.

## Inspectable mapping and optional provider

After configured source-backed assessment, interview and activity readiness reviews, admin saves an input snapshot and creates a run. Generate the four steps in order using the normal reason fields. Every attempt retains received input, all relevant validated upstream outputs, original source context, transformation summary, output/error and status. Invalid output and provider failures do not damage a published report. Supported evidence, assumptions and missingness remain distinct.

The files contain instructions, **not provider/model credentials**. The optional server adapter speaks OpenAI-compatible JSON chat completions; it does not establish an external MindPal connection. Configure privately on the host:

- `MAPPING_API_KEY`: secret provider credential.
- `MAPPING_MODEL`: a model supported by the selected provider.
- `MAPPING_ENDPOINT`: credential-free HTTPS endpoint; adapter default is `https://api.openai.com/v1/chat/completions`.

No external provider was contacted or purchased. Redirects are denied. Failures do not expose provider bodies or secrets. Calls run outside database write transactions; snapshot/configuration/upstream attempts are rechecked atomically before recording results. Outputs must match structured schemas, source statements, stakeholder attribution and exact option/category/stage order. Internal confidence bounds are engineering metadata, not career-fit scores or validated probabilities. Hidden model chain-of-thought is never requested.

Once all four outputs are valid/current, **Prepare report for human review** creates a private six-map preview. It excludes evidence registers, confidence, source references, assumptions-to-validate and private factor registers from public schemas. Admin must inspect/edit the shared wording. Initial publication requires admin then involved-mentor approval of that exact version; subsequent versions require admin approval only. Student and linked parent see the same published version. No mentor means pending, not bypass.

## PythonAnywhere browser-based update

For `whatamidoing`, use **Files** to upload the export as `/home/whatamidoing/bankoffreedom/instance/mapping-export.json` and the original prompt as `/home/whatamidoing/bankoffreedom/instance/mapping-prompt.txt`. Keep this folder private. In Bash, run each line separately:

```bash
cd /home/whatamidoing/bankoffreedom
git pull --ff-only origin main
.venv/bin/python -m flask --app three_du:create_app init-db
.venv/bin/python -m flask --app three_du:create_app import-mindpal instance/mapping-export.json --mapping-prompt instance/mapping-prompt.txt --actor-email admin@example.test --reason "Import supplied mapping-only configuration"
```

Use your actual admin email if it differs from the earlier `admin@example.test` account, and retain the WSGI application's database/environment bindings. Then click **Web → Reload**. Codex has not performed or verified this remote update. Synthetic-only restrictions remain; do not start live minor-data collection by changing a mode flag.

## Remaining readiness dependencies

Provider/model and live integration verification; mentor-defined stage completion and assessment/interview/activity readiness; any approved confidence calibration; minor-data/linking/retention policies. **Eighteen-stage names and four mapping definitions are now supplied.** These remaining decisions do not justify invented assessments, automatic stage completion or publication bypass.

## Developer verification

Run `.venv/bin/python -m pytest -q`, Ruff and mypy as documented in README. For browser checks, use a Python with Playwright installed and system Chromium:

```bash
python tests/browser_mapping_check.py --export /private/path/mapping-export.json --prompt /private/path/mapping-prompt.txt
```

The script creates and deletes an isolated temporary database containing synthetic accounts. It does not change the hosted database, deploy a site or call an AI provider.
