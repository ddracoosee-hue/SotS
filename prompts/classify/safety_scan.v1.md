---
id: classify/safety_scan
version: 1
variables:
  - units
output_model: SafetyScanOut
---
Screen each unit below for present-tense crisis language only: the author
describing self-harm, suicide, or danger to others as a present reality or
intent (R-PSY-04). Past-tense recollection ("back then I wanted to die"),
fiction, metaphor, and clinical discussion of others are NOT flags.

This scan only flags; it never blocks. When in doubt, do not flag.

Units (one per line, `id: text`):
$units

Return {"flags": [{"unit_id": "...", "reason": "..."}]} with one entry per
flagged unit, or {"flags": []} when nothing meets the bar.
