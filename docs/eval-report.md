# Eval report — G2·C

Generated 2026-11-06T18:36:33+00:00 · run `g2c-20261106-183633` · mode: fixture mode — recorded fake (recorded); usage is zero, so cost is **not measured live** · judge: `deterministic` · HubSpot: `fake`.

## Band accuracy vs the hand labels (AC 5)

**20 / 20 correct (100%)** — **fixture mode, not measured live**: the recorded fake answers from the lead fields, never the labels (D-16), so this number tests the governed pipeline (duplicates, directory, rubric, consent, band precedence), not a model.

| label \ got | good fit | poor fit | student | vendor | duplicate | missing company info |
|---|---|---|---|---|---|---|
| good fit | 8 |  |  |  |  |  |
| poor fit |  | 4 |  |  |  |  |
| student |  |  | 2 |  |  |  |
| vendor |  |  |  | 2 |  |  |
| duplicate |  |  |  |  | 2 |  |
| missing company info |  |  |  |  |  | 2 |

## Cost per lead (AC 5)

**Not measured live.** 20 leads, $0.0000 — no `ANTHROPIC_API_KEY` was present, so no model was called. The hand step in NEXT.md produces the live number.
Shared-layer calls this run: 78 observability rows (one per model call, per blocked attempt and per skip).

## Per lead

| lead | label | band | score | workers called | skipped (reason) | draft | cost | blocked |
|---|---|---|---|---|---|---|---|---|
| hs-1001 | good fit | good fit | 100 | enricher, qualifier, drafter | — | saved | n/m | 0 |
| hs-1002 | good fit | good fit | 100 | enricher, qualifier, drafter | — | saved | n/m | 0 |
| hs-1003 | good fit | good fit | 100 | enricher, qualifier | drafter (consent: not_consented) | no (consent: not_consented) | n/m | 0 |
| hs-1004 | poor fit | poor fit | 75 | enricher, qualifier | drafter (band is poor fit; no follow-up) | — | n/m | 0 |
| hs-1005 | poor fit | poor fit | 75 | enricher, qualifier | drafter (band is poor fit; no follow-up) | — | n/m | 0 |
| hs-1006 | good fit | good fit | 100 | enricher, qualifier, drafter | — | saved | n/m | 0 |
| hs-1007 | good fit | good fit | 100 | enricher, qualifier | drafter (consent: do_not_contact) | no (consent: do_not_contact) | n/m | 0 |
| hs-1008 | good fit | good fit | 83 | enricher, qualifier, drafter | — | saved | n/m | 0 |
| hs-1009 | poor fit | poor fit | 67 | enricher, qualifier | drafter (band is poor fit; no follow-up) | — | n/m | 0 |
| hs-1010 | missing company info | missing company info | — | enricher | qualifier (company could not be identified (directory: no record for '' (placeholder)); nothing to score); drafter (no qualification) | — | n/m | 0 |
| hs-1011 | missing company info | missing company info | — | enricher | qualifier (company could not be identified (directory: no record for 'self' (placeholder)); nothing to score); drafter (no qualification) | — | n/m | 0 |
| hs-1012 | poor fit | poor fit | 50 | enricher, qualifier | drafter (band is poor fit; no follow-up) | — | n/m | 0 |
| hs-1013 | good fit | good fit | 100 | qualifier, drafter | enricher (company profile complete on the contact (company, industry, size, website)) | saved | n/m | 0 |
| hs-1014 | student | student | 50 | enricher, qualifier | drafter (band is student; no follow-up) | — | n/m | 0 |
| hs-1015 | student | student | 50 | enricher, qualifier | drafter (band is student; no follow-up) | — | n/m | 0 |
| hs-1016 | vendor | vendor | 42 | enricher, qualifier | drafter (band is vendor; no follow-up) | — | n/m | 0 |
| hs-1017 | vendor | vendor | 75 | enricher, qualifier | drafter (band is vendor; no follow-up) | — | n/m | 0 |
| hs-1018 | duplicate | duplicate | — | none | enricher (duplicate of contact hs-1001 (created 2026-11-02T09:00:00Z)); qualifier (duplicate of contact hs-1001 (created 2026-11-02T09:00:00Z)); drafter (duplicate of contact hs-1001 (created 2026-11-02T09:00:00Z)) | — | n/m | 0 |
| hs-1019 | good fit | good fit | 100 | enricher, qualifier, drafter | — | saved | n/m | 0 |
| hs-1020 | duplicate | duplicate | — | none | enricher (duplicate of contact hs-1019 (created 2026-11-03T09:30:00Z)); qualifier (duplicate of contact hs-1019 (created 2026-11-03T09:30:00Z)); drafter (duplicate of contact hs-1019 (created 2026-11-03T09:30:00Z)) | — | n/m | 0 |

## Acceptance criteria

1. Every lead gets a note with score, band and reasons: **20/20** triage notes written (26 notes in all).
2. Good-fit leads get a saved draft, nothing sent: **6 drafts** saved as notes headed `DRAFT — not sent`; 2 good fits without a draft for lack of consent (D-15). No send path exists.
3. Orchestrator skipping a worker with the reason logged: **21 skips** logged as observability rows (`status=skipped`) and listed in the notes.
4. Forced send blocked by the hook and logged: `tests/test_crew.py::test_ac4_forced_send_from_a_worker_is_blocked_and_logged` and `tests/test_safety.py`; blocked attempts in this run: **0**.
5. Band accuracy and cost per lead: above.
