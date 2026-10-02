# 07 — MEDIA ACCURACY (Stage 6)

**Goal:** when the author mentions or retells a book, film, TV show, song, game, podcast,
or artwork, check four things:
1. **Identity**: is it the right work, creator, and year?
2. **Retelling facts**: did the events, characters, and details happen as described?
3. **Quotes and attribution**: is the line real, and who said or wrote it?
4. **Meaning**: does the author's reading of the work's message hold up, and does it
   serve the book's point?

## 1. Identify the work (`media/identify.py`, task `media.identify`)

1. The LLM extracts `{title_guess, creator_guess, year_guess, kind}` from the unit and its
   neighbours.
2. Deterministic lookup by kind:
   - FILM/TV → `tmdb` search (title + year)
   - BOOK → `openlibrary` search (title + author)
   - MUSIC → `musicbrainz` recording/release search (title + artist)
   - Other kinds → `wikipedia` search
3. Pick the candidate with the highest title similarity (rapidfuzz `token_sort_ratio`),
   using the year and creator to break ties. It is accepted only if title similarity ≥ 85.
4. If nothing is accepted: `work.resolved = False`. The report asks the author to confirm
   the work (the TUI offers the top 3 candidates). Checking continues with
   accuracy = `unverifiable` for all points.
5. **Identity errors are findings.** A wrong year, wrong director/author, or wrong artist
   becomes a `MediaPoint` with point_type `attribution`.

## 2. Gather sources about the work
- Plot/summary: the TMDB overview, Open Library description, and Wikipedia article (Plot /
  Synopsis sections, extracted by heading).
- Meaning: Wikipedia "Themes", "Reception", and "Analysis" sections, plus up to 3 web
  results for `"<title>" themes analysis`, `"<title>" <creator> interview meaning`.
- Creator intent: interview or statement pages found by the search above. These get
  source_class JOURNALISM or PRIMARY_RECORD when the creator is directly quoted.
- All of these pass through the same fetch → excerpt check as `06 §3.4` (R-TRUTH-02).

**Copyright rule:** never fetch or store full lyrics, scripts, or book text. Store only
short excerpts (≤ 300 characters) needed as evidence. For songs, check the author's
description of the meaning, not the lyrics word by word. If the author quotes a lyric, mark
the quote point `unverifiable` unless a reputable source quotes the same line.

## 3. Check (`media/checker.py`, task `media.check`)

Input: the unit + neighbours, the resolved work, the source passages, and the book and
chapter context (so the model can judge whether the reference serves the point).

The LLM output must follow `MediaCheck` (`03 §4`), minus the ids. Instructions to the model:
- Break the author's retelling into individual `MediaPoint`s. **One point per
  checkable statement.**
- For each point: accurate / partly_accurate / inaccurate / unverifiable, with a correction
  when it is not accurate and the evidence URLs + excerpts that support the judgment.
- `author_reading`: restate what the author says the work means, in one or two sentences.
- `established_readings`: 1–4 readings from sources, each tied to evidence.
- `interpretation_status`: pick exactly one, using this ladder:
  1. The creator explicitly said otherwise → `contradicted_by_source`
  2. It matches creator intent or clear critical consensus → `supported_reading`
  3. Critics are split on it → `contested_reading`
  4. It isn't found in sources but is consistent with the plot facts → `plausible_personal_reading`
- A personal reading is **legitimate** in a reflective self-help book. The report must
  never call a `plausible_personal_reading` wrong. It suggests framing like "to me, this
  film is about…" instead of "this film is about…".
- `message_alignment` (0–1) and `use_in_book_note`: does the reference support the chapter
  message it sits next to? (This uses the chapter's key_messages from the profile.)

## 4. Deterministic checks after the LLM
- Every `MediaPoint` with accuracy `accurate` or `inaccurate` needs ≥ 1 evidence id.
  Otherwise downgrade it to `unverifiable`.
- `supported_reading` and `contradicted_by_source` need ≥ 1 evidence id in
  `established_readings`. Otherwise downgrade to `plausible_personal_reading`.
- If the work is unresolved, the status is forced to `plausible_personal_reading` and all
  points are `unverifiable`.

## 5. Report section per media reference
- Work: title, creator, year (✔ / ✘ correct as the author wrote it)
- Retelling: a table of points → accuracy → correction
- Meaning: the author's reading vs the established readings → status
- A framing suggestion when it is a personal reading
- "Does it serve the chapter?": alignment score + note
