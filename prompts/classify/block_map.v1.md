---
id: classify/block_map
version: 1
variables:
  - chapter_id
  - unit_text
  - blocks
output_model: BlockMapOut
---
Map the unmarked dictation below ($chapter_id) to its block and, when the
text clearly answers one, its dictation prompt. Use ONLY the blocks below.

$blocks

Rules:
- block: the 1-6 block number whose purpose the text serves.
- prompt_id: the prompt id (chNN.Bn.Pm) when the text clearly answers that
  prompt, else null. Never invent ids; use only ids listed above.
- confidence: 0.0-1.0 for the mapping (low when the text could fit two blocks).

Unit text:
$unit_text
