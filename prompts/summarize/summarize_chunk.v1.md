---
id: summarize/summarize_chunk
version: 1
variables:
  - level
  - text
output_model: ChunkSummaryOut
---
Summarize the text below in at most 200 words. Keep every named person,
place, number, and claim; drop repetitions and filler. Write plain prose,
no bullet lists, no preamble.

This is a level-$level summary: level 0 summarizes one raw chunk of the
manuscript; higher levels summarize groups of child summaries into one.

Text:
$text

Return {"text": "..."} with the summary alone.
