# Kickoff — Lead Triage Crew (Build Log G2, Agentic AI track)

Paste the block below into Claude Code started in `~/Projects/agentic-track/g2-lead-triage-crew`, on Fable (`/model`).

```
You are starting a new build: Lead Triage Crew (Build Log G2, Agentic AI track,
graphic row "Scope"). The spec is docs/prd.md. Read it fully before doing anything.
Also read ../README.md for the track order and the shared-layer (G0) contract rule.

The project is built twice, in this order:
- G2·B (n8n first): n8n: HubSpot new-contact trigger -> orchestrator AI Agent node with Enricher, Qualifier and Drafter as AI Agent Tool nodes; HubSpot note write-back; no send node anywhere.
  Deliver it as importable workflow JSON in n8n/, with a README on how to import it
  into the owner's self-hosted n8n.
- G2·C (code second): Python 3.12 + Claude Agent SDK + FastAPI webhook: orchestrator plus three subagents with limited tool lists; a hook that blocks any send/email-out tool call and logs the attempt.
  Start G2·C only after G2·B passes its acceptance criteria.

Test data: ~20 synthetic HubSpot leads, hand-labeled with the expected band (good fit, poor fit, student, vendor, duplicate, missing company info). Labels are the eval set.

Safety invariants (land with tests BEFORE any code path can reach a live system):
Draft only: nothing is ever sent. HubSpot writes go only to notes on synthetic test contacts. No deal-stage edits.

Shared layer (G0): the PRD lists the shared capabilities this project calls
(claims.registry, brand.policy, audience.consent, measurement, evaluation,
observability). If ../shared/ does not exist yet, build local stubs with the same
input and output shape, in one clearly named module, so they can be swapped for G0
later. Never copy rules into an agent's prompt that belong in the shared layer.

Open decisions in the PRD: Trigger (webhook vs poll), where the draft lives (note vs native draft), Qualifier buyer definition, Enricher web lookup allowed or synthetic only.
Take the PRD's recommendation for each unless I say otherwise, and record each as a
D- entry in docs/DECISIONS.md before writing code.

Working rules:
- Confirm current Claude model IDs and prices from Anthropic's docs before using them.
  Confirm current n8n node names and options from n8n's docs; record what you found.
- Log tokens and cost per run from the first live call. Hard cap: $10 of live model
  calls for the whole build unless I raise it.
- Keep NEXT.md current, matching the other build-log repos: what is done, what is
  next, and exact hand steps for the owner.
- Commit at the end of every task with a clear message. Never commit secrets; keys
  live in a gitignored .env.
- Work on a branch named `kickoff`. No merges to main, no deploys, no live external
  writes, and no account changes without my explicit go.

Step 1, plan first: write docs/BACKLOG.md breaking G2·B then G2·C into tasks
you can finish and test in one sitting, each with acceptance criteria taken from the
PRD. List owner hand steps separately. Then stop and show me the backlog and
DECISIONS.md before building.
```
