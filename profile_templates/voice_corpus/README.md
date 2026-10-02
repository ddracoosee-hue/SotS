# Voice Corpus

<!--
(copied to profile/voice_corpus/ by `sots init`).
See blueprint 29 — Voice Lab.
-->

This folder teaches SotS how **you** write. Add material any time, in any
amount: every addition sharpens the voice checks. Nothing here is graded;
it is all training data for your Voice Model.

## How to add material

Either drop files into the folder below that matches the register and run
`sots voice sync`, or run:

```
sots voice add <file|folder> --register final|draft|spoken|casual [--weight 0.5-2.0] [--note "…"]
```

## The registers

| Folder | Register | Put here |
|---|---|---|
| `final/` | final | Polished prose you sign off on (e.g. a finished chapter). Teaches how you write for readers. |
| `drafts/` | draft | Your own drafts. |
| `spoken/` | spoken | Dictation / voice-memo transcripts, word vomits. Teaches what you think and how you talk. |
| `casual/` | casual | Texts, posts, journal entries, emails. |
| `pairs/` | pair_raw / pair_final | RAW → FINAL pairs: the dictation plus the finished version of the same passage. Teaches the transformation. |
| `not_me/` | not_me | Counter-examples: text that does NOT sound like you (rejected AI drafts, etc.). |

Spoken and casual samples never drag the prose model toward the casual
register: each register is modelled separately, and `pairs/` teaches the
transformation between them.

## Trust weights

Each item in `manifest.yaml` may carry a `weight` from 0.5 to 2.0:
how much this sample should count. Recent writing already counts more than
old writing automatically; `final/` samples never drop below a 0.6 floor.
