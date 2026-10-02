-- Migration 003: supplements reference index (P04 T04.015).
-- One row per file under supplements/ with its extracted text + sha256,
-- used by the supplements fetcher (P07).

CREATE TABLE IF NOT EXISTS supplement_docs (
    path TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL,
    text TEXT NOT NULL,
    indexed_at TEXT NOT NULL
);
