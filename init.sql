-- init.sql: schema + seed data for workspace.db
-- Usage: sqlite3 instance/workspace.db < init.sql
--
-- Test accounts (password = username + "123"):
--   Group A: lena / lena123, tom / tom123
--   Group B: anna / anna123, peter / peter123
-- Hashes use the Werkzeug format (pbkdf2:sha256:600000$salt$hash),
-- verifiable with werkzeug.security.check_password_hash().

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

DROP TABLE IF EXISTS datasets;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS groups;

CREATE TABLE groups (
    group_id   INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE
);

CREATE TABLE users (
    user_id       INTEGER PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    group_id      INTEGER NOT NULL REFERENCES groups(group_id)
);

CREATE TABLE datasets (
    dataset_id    INTEGER PRIMARY KEY,
    group_id      INTEGER NOT NULL REFERENCES groups(group_id),
    owner_id      INTEGER NOT NULL REFERENCES users(user_id),
    name          TEXT NOT NULL,
    original_name TEXT NOT NULL,          -- original CSV file name
    stored_name   TEXT NOT NULL UNIQUE,   -- uuid.csv in instance/storage/
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO groups (group_id, name) VALUES
    (1, 'Group A'),
    (2, 'Group B');

INSERT INTO users (user_id, username, password_hash, group_id) VALUES
    (1, 'lena',  'pbkdf2:sha256:600000$f88c7872e3ff37a5$81c227a04dd50541caad8dabb25cea21df8a640f4450ec500dde5ce30f03161d', 1),
    (2, 'tom',   'pbkdf2:sha256:600000$e95e59ba051ddbf1$6c733b4093df4bf8c95c57fa20114139d3252c67a2bd953c6a0ffce45b1cca47', 1),
    (3, 'anna',  'pbkdf2:sha256:600000$e8832a92208c80f2$d839d27316d12838df794e4edc58a9a5fd75a429605393e8177235fdb53cb9be', 2),
    (4, 'peter', 'pbkdf2:sha256:600000$2e1603fb1d10ec03$e023eba1c5218335ac5a47fc3e1b1c69a3c767a28d07432e9615c6261ad4b9d6', 2);

-- The stored_name files must exist in instance/storage/:
--   sample_data/soil_samples.csv -> instance/storage/3f2a9c1e-7b4d-4e8a-9c21-5d6e7f8a9b01.csv
--   sample_data/air_quality.csv  -> instance/storage/b7e6d5c4-3a2b-4c1d-9e8f-0a1b2c3d4e03.csv
INSERT INTO datasets (dataset_id, group_id, owner_id, name, original_name, stored_name) VALUES
    (1, 1, 1, 'Soil samples (North/East/South sites)', 'soil_samples.csv', '3f2a9c1e-7b4d-4e8a-9c21-5d6e7f8a9b01.csv'),
    (2, 2, 3, 'Campus air quality readings',           'air_quality.csv',  'b7e6d5c4-3a2b-4c1d-9e8f-0a1b2c3d4e03.csv');

COMMIT;