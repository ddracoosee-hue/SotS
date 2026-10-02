-- Migration 002: record routing fallback on llm_calls (P02 T02.010, 04 §3).
-- 04 §3 requires the fallback to be recorded in the LLMCall row; v1 rows
-- default to 0 (preferred provider was used, or predates fallback tracking).

ALTER TABLE llm_calls ADD COLUMN fallback_used INTEGER NOT NULL DEFAULT 0;
