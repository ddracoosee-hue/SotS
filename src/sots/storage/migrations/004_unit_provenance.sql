-- Migration 004: author-declared provenance on units (P04A T04A.034, 25 §7).
-- author_provenance is live_source | belief | experience | opinion (R-PROV-01);
-- source_ref names the live source; serial tags multi-chapter threads.

ALTER TABLE units ADD COLUMN author_provenance TEXT;
ALTER TABLE units ADD COLUMN source_ref TEXT;
ALTER TABLE units ADD COLUMN serial TEXT;
