---
id: classify/classify_unit
version: 1
variables:
  - unit_id
  - unit_text
  - retry_notes
output_model: ClassificationOut
---
Classify the unit below. Apply the decision table in order; the first
matching row wins.

| If… | Then… |
|---|---|
| It describes what happened to the author/their family/friends | `PERSONAL_EXPERIENCE`, `NOT_CHECKABLE` unless `embedded_claims` is non-empty (then `PARTIAL`) |
| It states an opinion, value, or "I believe/feel" | `PERSONAL_BELIEF`, `NOT_CHECKABLE` |
| It tells the reader what to do or what to learn | `LESSON_ADVICE`. If it rests on a factual premise ("studies show…"), the premise goes into `embedded_claims` and checkability is `PARTIAL` |
| It contains a number, percentage, or rate about the world | `FACTUAL_CLAIM` / `STATISTIC` |
| It names a lawsuit, trial, ruling, or legal outcome | `FACTUAL_CLAIM` / `LEGAL_CASE` |
| It describes a viral post, influencer, online controversy, or "a TikTok where…" | `FACTUAL_CLAIM` / `SOCIAL_MEDIA_CASE` |
| It cites research, science, or psychology findings | `FACTUAL_CLAIM` / `ACADEMIC_FINDING` |
| It names or retells a book, film, show, song, game, or podcast | `MEDIA_REFERENCE` with `media_kind` |
| It says "X said…" | `FACTUAL_CLAIM` / `QUOTE_ATTRIBUTION` |
| Metaphor, transition, or a hook with no claim | `NARRATIVE_DEVICE`, `NOT_CHECKABLE` |

A pure question with no claim is `QUESTION_REFLECTION`, `NOT_CHECKABLE`.

Output constraints (a violation fails validation and forces a retry):
- `claim_kind` is set if and only if the type is `FACTUAL_CLAIM`.
- `media_kind` is set if and only if the type is `MEDIA_REFERENCE`.
- `NOT_CHECKABLE` means no `normalized_claim` and empty `embedded_claims`.
- A `MEDIA_REFERENCE` is never `NOT_CHECKABLE`.

Worked examples (one per content type):

1. "When I was nine, my father lost his job and we moved in with my
grandmother." → {"content_type": "personal_experience", "claim_kind": null,
"media_kind": null, "checkability": "not_checkable", "entities": ["father",
"grandmother"], "normalized_claim": null, "embedded_claims": [],
"confidence": 0.95}

2. "I believe grace precedes effort." → {"content_type": "personal_belief",
"claim_kind": null, "media_kind": null, "checkability": "not_checkable",
"entities": [], "normalized_claim": null, "embedded_claims": [],
"confidence": 0.9}

3. "Put your phone in another room before you sit down to write." →
{"content_type": "lesson_advice", "claim_kind": null, "media_kind": null,
"checkability": "not_checkable", "entities": [], "normalized_claim": null,
"embedded_claims": [], "confidence": 0.9}

4. "Divorce rates hit 50% in the 80s." → {"content_type": "factual_claim",
"claim_kind": "statistic", "media_kind": null, "checkability": "checkable",
"entities": [], "normalized_claim": "The divorce rate reached 50 percent in
the 1980s.", "embedded_claims": [], "confidence": 0.9}

5. "In Everything Everywhere All at Once, Evelyn fights the everything
bagel." → {"content_type": "media_reference", "claim_kind": null,
"media_kind": "film", "checkability": "checkable", "entities":
["Evelyn"], "normalized_claim": "The film Everything Everywhere All at Once
features Evelyn fighting the everything bagel.", "embedded_claims": [],
"confidence": 0.92}

6. "What if the algorithm is farming our attention?" →
{"content_type": "question_reflection", "claim_kind": null,
"media_kind": null, "checkability": "not_checkable", "entities":
["algorithm"], "normalized_claim": null, "embedded_claims": [],
"confidence": 0.95}

7. "But the story was only beginning." →
{"content_type": "narrative_device", "claim_kind": null, "media_kind": null,
"checkability": "not_checkable", "entities": [],
"normalized_claim": null, "embedded_claims": [], "confidence": 0.95}

Unit $unit_id:
$unit_text

$retry_notes
