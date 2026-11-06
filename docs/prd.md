# G2 Lead Triage Crew — PRD v0.1

Nov 3, 2026 · @Shane LaBounty

## Summary

Agentic AI track, build-log G2. A new HubSpot lead triggers an orchestrator agent, which decides which specialists to call: an Enricher, a Qualifier and a Drafter. It writes its findings back to HubSpot as notes and leaves a follow-up email as a draft. It never sends anything.

The project is built twice: **G2·B in n8n first**, then **G2·C in Python with the Claude Agent SDK**.

**From the build-log card (already set):** orchestrator–worker pattern; HubSpot write-back; draft only; graphic row "Scope"; C version enforces draft-only with a blocking hook. Order is G1 → G0 (shared layer) → G2, so G2 attaches to the shared layer instead of carrying its own rules.

**Everything else here is a proposal.**

## Why it's in the portfolio

N1 Speed-to-Lead follows a fixed path. G2 shows the step up: the orchestrator chooses which specialist to call based on the lead, and acts across systems instead of just answering. The C version adds the point hiring managers care about: "draft only" is enforced by the system, not promised by a prompt.

## Scope

**In:**

- Trigger on a new HubSpot contact (webhook or polling)
- Orchestrator plus three worker agents
- HubSpot note with enrichment, score and reasoning
- Draft follow-up email saved to HubSpot, not sent
- Run log: which workers were called, tokens, cost per lead

**Out:** sending email; editing deal stages; real prospect data; QuickBooks; running live for Lab Intelligence (demo only, consistent with your automation-track decision).

## Agents

| Agent | Job | Tools | Output |
| --- | --- | --- | --- |
| Orchestrator | Read the lead, decide which workers to call and in what order, skip ones that aren't needed | The three workers as tools | Final summary + decisions taken |
| Enricher | Fill company, role, size and industry from what the lead gave plus public web lookup | Web search / fetch | Structured company fields + sources |
| Qualifier | Score fit against Lab Intelligence's ideal buyer (AI pilot sponsor) | Shared evaluation capability (from G0) | Score 0–100, band, reasons |
| Drafter | Write a short follow-up email in Lab Intelligence's voice | Shared brand and claims capabilities (from G0) | Email draft (subject + body) |

**Example of the orchestrator choosing:** a lead with a full company profile skips the Enricher; a student or vendor lead gets scored low and skips the Drafter.

## Shared-layer hooks (proposed)

- **brand.policy** and **claims.registry:** the Drafter calls these instead of carrying its own voice and claim rules.
- **audience.consent:** checked before any draft is created.
- **evaluation:** the Qualifier's rubric lives here, not in the agent.
- **observability:** every run logs worker calls and cost.

If G0 isn't built when G2 starts, stub these as simple sub-workflows with the same input and output shape so they can be swapped later.

## Test data

Your HubSpot account has no real contacts, so G2 needs synthetic leads loaded first.

*Proposal:* about 20 synthetic leads, hand-labeled with the expected band. Include good fits, poor fits, students, vendors, duplicates, and leads with missing company info. The labels become the eval set for G2·C.

## G2·B (n8n) build notes

- HubSpot trigger → orchestrator AI Agent node
- Enricher, Qualifier and Drafter as AI Agent Tool nodes the orchestrator can call
- HubSpot nodes to write a note and save the draft
- No send node anywhere in the workflow
- Runs on your self-hosted n8n

## G2·C (code) build notes

- FastAPI webhook receives the HubSpot event
- Orchestrator plus three subagents, each with its own context and a limited tool list
- A hook that blocks any send or email-out tool call and logs the attempt
- Same synthetic leads; compare band accuracy and cost per lead against G2·B

## Acceptance criteria (proposed)

1. Every synthetic lead gets a HubSpot note with score, band and reasons.
2. Good-fit leads get a saved draft; nothing is ever sent.
3. At least one test shows the orchestrator skipping a worker, with the reason logged.
4. **C only:** a forced attempt to send is blocked by the hook and logged.
5. Band accuracy against the hand labels and cost per lead are reported for both versions.

## Decisions needed (one at a time)

**1. Trigger** Options: HubSpot webhook / scheduled poll. *Recommendation: webhook.* It's real-time and closer to how a client would run it. Fall back to polling only if your self-hosted n8n isn't reachable from HubSpot.

**2. Where the draft lives** Options: HubSpot email draft / a note containing the draft text. *Recommendation: a note* for v1. It's simplest and still proves draft-only; switch to a native draft only if the HubSpot nodes support it cleanly.

**3. Build before or after G0** *Recommendation: after G0,* as the build-log order says, with stubs only if G0 slips.

## Questions for you

1. Should the Qualifier score against the Stalled-Pilot Diagnostic buyer (AI pilot sponsor), or a broader Lab Intelligence buyer?
2. Is web lookup in the Enricher OK for a public portfolio demo, or should it stay on synthetic data only?
3. Want the LinkedIn write-up planned now, or after the build?
