---
id: segment/extract_units
version: 1
variables:
  - chunk_start
  - chunk_text
output_model: ExtractUnitsOut
---
Split the chunk below into atomic units. One unit = one claim, one story beat,
one belief, one lesson, one media mention, or one question.

Rules:
- Split compound sentences when they contain more than one checkable claim.
- Keep a personal story beat together as one unit, even across several
  sentences, unless it contains a factual claim, which is split out.
- Keep every word. Do not paraphrase. Every unit's text must be an exact
  substring of the chunk.

Offsets are relative to the chunk: position 0 is the chunk's first character
(the chunk starts at document offset $chunk_start). Count every character,
including spaces and newlines. The end offset is exclusive.

Example 1 (compound claim splits):
Chunk: "Divorce rates hit 50% in the 80s and that's why my parents split"
Units:
[{"text": "Divorce rates hit 50% in the 80s", "start": 0, "end": 32},
 {"text": "that's why my parents split", "start": 37, "end": 64}]

Example 2 (story beat stays together):
Chunk: "We drove all night. Dad sang off-key the whole way. I still hum it."
Units:
[{"text": "We drove all night. Dad sang off-key the whole way. I still hum it.",
  "start": 0, "end": 67}]

Now split this chunk. Return {"units": [{"text": ..., "start": ..., "end": ...}]}.

Chunk:
$chunk_text
