-- Migration 005: foundation pieces on agent cards (P04A T04A.022).
-- JSON list[str]; old rows default to [] (no foundation context loaded).

ALTER TABLE agent_cards ADD COLUMN foundation_pieces TEXT NOT NULL DEFAULT '[]';
