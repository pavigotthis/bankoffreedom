-- Private imported instructions are kept in the access-controlled database, not static assets.
CREATE TABLE mapping_imports(id INTEGER PRIMARY KEY, config_version INTEGER NOT NULL, source_sha256 TEXT NOT NULL, source_json TEXT NOT NULL, source_prompt TEXT, normalized_json TEXT NOT NULL, actor_id INTEGER NOT NULL REFERENCES users(id), reason TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE intake_entries(id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES users(id), actor_id INTEGER NOT NULL REFERENCES users(id), role TEXT NOT NULL CHECK(role IN ('student','parent')), config_version INTEGER NOT NULL, draft TEXT NOT NULL DEFAULT '{}', submitted TEXT, version INTEGER NOT NULL DEFAULT 0, submitted_version INTEGER NOT NULL DEFAULT 0, submissions INTEGER NOT NULL DEFAULT 0 CHECK(submissions BETWEEN 0 AND 2), updated TEXT NOT NULL, UNIQUE(student_id,actor_id));
CREATE TABLE intake_versions(entry_id INTEGER NOT NULL REFERENCES intake_entries(id), version INTEGER NOT NULL, config_version INTEGER NOT NULL, body TEXT NOT NULL, created TEXT NOT NULL, PRIMARY KEY(entry_id,version));
CREATE TABLE intake_requests(entry_id INTEGER NOT NULL REFERENCES intake_entries(id), request_key TEXT NOT NULL, fingerprint TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(entry_id,request_key));
CREATE TABLE intake_evidence(entry_id INTEGER NOT NULL REFERENCES intake_entries(id), field TEXT NOT NULL, evidence_id INTEGER NOT NULL REFERENCES evidence(id), PRIMARY KEY(entry_id,field));

ALTER TABLE runs ADD COLUMN specification_sha256 TEXT;
