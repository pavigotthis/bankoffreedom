-- Preserve earlier generic profile notes without interpreting them as structured answers.
CREATE TABLE profile_legacy_notes(student_id INTEGER PRIMARY KEY REFERENCES users(id), note TEXT NOT NULL, captured TEXT NOT NULL);
INSERT INTO profile_legacy_notes(student_id,note,captured)
SELECT student_id,json_extract(draft,'$.reflection'),CURRENT_TIMESTAMP FROM stages WHERE stage=1 AND json_valid(draft) AND json_type(draft,'$.reflection')='text' AND length(json_extract(draft,'$.reflection'))>0;
