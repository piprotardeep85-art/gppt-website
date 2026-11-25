PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user','admin')),
    language TEXT NOT NULL DEFAULT 'en' CHECK(language IN ('en','gu')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    guest_id TEXT,
    job_title TEXT NOT NULL DEFAULT '',
    company_name TEXT NOT NULL DEFAULT '',
    website_url TEXT NOT NULL DEFAULT '',
    recruiter_email TEXT NOT NULL DEFAULT '',
    salary TEXT NOT NULL DEFAULT '',
    job_text TEXT NOT NULL,
    score INTEGER NOT NULL,
    label TEXT NOT NULL,
    confidence TEXT NOT NULL,
    red_flags_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    guest_id TEXT,
    company_name TEXT NOT NULL,
    job_link TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL,
    screenshot_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scans_user_date ON scans(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scans_guest_date ON scans(guest_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at DESC);
