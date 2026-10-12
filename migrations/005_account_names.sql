-- Existing accounts retain unknown names until their owner supplies one.
ALTER TABLE users ADD COLUMN name TEXT CHECK(name IS NULL OR (length(name) BETWEEN 1 AND 120));
