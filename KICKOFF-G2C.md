# Kickoff — Lead Triage Crew, G2·C (code first, on G0) — drafted 2026-11-05 10:55 PM CT

Owner reorder (2026-11-05): G2·C (code) built first, unattended on Fable; G2·B (n8n) is the owner's hand build afterwards. Attached to G0·C from the start (no stubs). Run prompt below; also usable pasted into Claude Code in `~/Projects/agentic-track/g2-lead-triage-crew`.

```
Nobody is watching this run: do not ask questions; take the most reasonable reading and record it in docs/DECISIONS.md. Never call Notion, Stripe or Postman. Never call the HubSpot connector or any live HubSpot API in this run. The only repo you may push to is shanelabountyai/g2-lead-triage-crew; push only the branch `kickoff`, never main. No deploys, no sends, no account changes, no secrets in commits.

You are starting Lead Triage Crew, code version (Build Log G2·C, Agentic AI track, graphic row "Scope"), in the repo shanelabountyai/g2-lead-triage-crew. Clone it (--depth 1; add_repo with push access first if refused), read docs/prd.md, KICKOFF.md, CLAUDE.md, README.md fully. Work on branch `kickoff`; commit per task; push; open ONE pull request against main when done and do NOT merge it.

G2·C attaches to the Shared Capability Layer G0·C: repo shanelabountyai/g0-shared-layer, branch `kickoff`, commit 1cb74df6c3e4a5212f681f7f7bdf594b37b53070 (PR #1, unmerged). Clone it read-only, read README.md, docs/attach.md, contracts/ and its Python package, and pin exactly that commit as a git dependency in pyproject.toml. Also read, read-only, how the first consumer attached: shanelabountyai/g1-signal-scout branch `g1c` (docs/DECISIONS.md, docs/attach.md or README's G1·C section, and the code that calls G0) so G2·C attaches the same way.

Decisions already made by the owner. Record each as a numbered D- entry in docs/DECISIONS.md before writing code (dated 2026-11-05):
- G2·C (code) is built now, unattended; G2·B (n8n) is the owner's hand build afterwards from the same synthetic leads and the same contracts. The KICKOFF's "G2·B first" order is superseded.
- Attached to G0 from the start; no local stubs. brand.policy + claims.registry gate every Drafter output; audience.consent is checked before any draft is created; the Qualifier's rubric lives in G0's evaluation capability (register the rubric there through its contract if the contract allows, otherwise keep the rubric file in this repo and call evaluation with it, and record which); observability logs every model call; measurement records each lead processed with band and cost.
- PRD decision 1, trigger: webhook. FastAPI endpoint receiving a HubSpot contact.creation event; include a local replay script that posts the synthetic leads to it.
- PRD decision 2, draft lives in a HubSpot note (not a native email draft).
- PRD question 1: the Qualifier scores against the Stalled-Pilot Diagnostic buyer (AI pilot sponsor), using the buyer definition in shanelabountyai/li-lead-gen-tools docs (read-only clone; search docs/ for the Stalled-Pilot Diagnostic PRD and its buyer/persona section) — cite the file.
- PRD question 2: Enricher uses synthetic data only; no live web lookup in this run. Enricher reads from a local synthetic company directory fixture. Record that live lookup is a later owner decision.
- Safety invariants land with tests BEFORE any code path can reach an external system: draft only, nothing is ever sent; HubSpot writes are notes on synthetic test contacts only; no deal-stage edits. A hook blocks any send/email-out tool call and logs the attempt (PRD AC 4).
- HubSpot access: a thin client behind an interface with an in-memory fake used by all tests; the real client reads a token from an env var and is never exercised in this run. Loading the synthetic leads into the owner's HubSpot and the live note write-back are owner hand steps.
- Test data: ~20 synthetic leads in fixtures/, hand-labeled with the expected band (good fit, poor fit, student, vendor, duplicate, missing company info); obviously fake names and example.com emails. The labels are the eval set.
- Live model calls only if ANTHROPIC_API_KEY is present; confirm current model IDs and prices from Anthropic's docs; log tokens and cost per lead; hard cap $10. If no key is present, run on fixtures with a recorded-response fake and say so in NEXT.md; band accuracy and cost per lead are then reported as "not measured live".

Working rules: Python 3.12, uv, src/ layout, pytest, Claude Agent SDK for the orchestrator + Enricher/Qualifier/Drafter subagents, each with its own context and a limited tool list. Acceptance criteria from the PRD: (1) every synthetic lead gets a note with score, band and reasons; (2) good-fit leads get a saved draft, nothing sent; (3) at least one test shows the orchestrator skipping a worker with the reason logged; (4) a forced send attempt is blocked by the hook and logged; (5) band accuracy vs labels and cost per lead reported. All tests must pass before the PR. README.md for a reviewer: architecture, how each G0 capability is called, how to run on fixtures, how to run live, the eval results. Keep NEXT.md current with exact owner hand steps (G2·B n8n build, HubSpot load, live run).

Order of work: 1) DECISIONS.md + docs/BACKLOG.md; commit. 2) fixtures (leads + labels + company directory); commit. 3) safety invariants + hook + tests; commit. 4) G0 attachment + HubSpot interface/fake; commit. 5) subagents, then orchestrator; commit each. 6) webhook + replay script; commit. 7) eval report, README, NEXT.md; push; open the PR. If something blocks you, write it to NEXT.md and keep going.

Final output: a PushNotification in <routine_summary> tags: PR link, test counts, AC 1–5 status, eval accuracy and cost (or "not measured"), and the owner's next hand step.
```
