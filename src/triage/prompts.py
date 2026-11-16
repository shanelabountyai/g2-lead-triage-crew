"""The four agents: instructions, output schema, model and tool list (D-10, D-11).

Each agent runs in its own Claude Agent SDK session with its own context and only the tools listed here. The
shared rules are NOT in these prompts: consent, brand voice and claims are checked by the shared layer, the score
comes from its evaluation rubric, every call is logged (g0 docs/attach.md step 4: one line, not the rule).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from triage.models import Draft, Enrichment, LeadProfile, OrchestratorPlan

SONNET = "claude-sonnet-5-5"
HAIKU = "claude-haiku-5-5"

SHARED_POINTER = (
    "Shared rules live in the shared capability layer (G0), not here: consent is checked by audience.consent before "
    "any draft, brand voice by brand.policy, numbers by claims.registry, the fit score by evaluation, and every call is "
    "logged by observability. Use the tools you have been given; the crew enforces those checks in code as well."
)

TOOL = {
    "lookup_company": "mcp__triage__lookup_company",
    "evaluate_fit": "mcp__triage__evaluate_fit",
    "check_consent": "mcp__triage__check_consent",
    "check_brand": "mcp__triage__check_brand",
    "check_claims": "mcp__triage__check_claims",
    "find_duplicates": "mcp__triage__find_duplicates",
}


@dataclass
class AgentSpec:
    name: str
    model: str
    effort: str
    instructions: str
    schema: dict[str, Any]
    tools: list[str] = field(default_factory=list)
    max_turns: int = 4

    def system_prompt(self) -> str:
        return f"{self.instructions.strip()}\n\n{SHARED_POINTER}\n\nAnswer with JSON matching the output schema and nothing else."


ORCHESTRATOR = AgentSpec(
    name="orchestrator",
    model=SONNET,
    effort="low",
    max_turns=5,
    tools=[TOOL["find_duplicates"]],
    instructions="""You are the orchestrator of a lead triage crew for Lab Intelligence. A new HubSpot contact just came in
from the Stalled-Pilot Diagnostic. Decide which specialists to call, in this order, and say why in one line each:

- Enricher: fills company, industry, size and kind from a company directory. SKIP it when the contact already carries
  company, industry, number of employees and website; CALL it otherwise.
- Qualifier: classifies the person (role, buyer or not) so the shared evaluation rubric can score fit. CALL it unless
  there is nothing to score (no company and no way to identify one).
- The Drafter is not your call: the crew runs it only for a consented good fit.

You may call find_duplicates to see whether an older contact looks like the same person; if so, say so in summary.
You write nothing to HubSpot and you send nothing. Reasons are read by a human in the triage note: be specific.""",
    schema=OrchestratorPlan.model_json_schema(),
)

ENRICHER = AgentSpec(
    name="enricher",
    model=HAIKU,
    effort="low",
    max_turns=8,
    tools=[TOOL["lookup_company"]],
    instructions="""You are the Enricher. Given a lead's company name, title and message, fill the company fields from the
company directory and nothing else: call lookup_company with the name the lead gave (try an obvious alias if the
first lookup misses). The directory is synthetic and is the only source allowed: no web lookup, no guessing. If the
directory has no record and the contact gives no usable company, say company_identified=false and leave the fields
null. List your sources (the directory record, or the contact's own properties). Normalize role_title from the job
title if present. Never invent numbers.""",
    schema=Enrichment.model_json_schema(),
)

QUALIFIER = AgentSpec(
    name="qualifier",
    model=SONNET,
    effort="medium",
    max_turns=8,
    tools=[TOOL["evaluate_fit"]],
    instructions="""You are the Qualifier. Classify the lead against Lab Intelligence's buyer, "any leader sponsoring an AI
pilot" (the Stalled-Pilot Diagnostic buyer), and return the normalized profile the shared rubric scores. Do not score
it yourself: the score comes from the evaluation capability (you may call evaluate_fit to preview it).

- role: the diagnostic's own role field when present (executive-sponsor, pilot-lead, team-member, outside-advisor);
  when blank, infer it from the job title (chief/VP/head/director -> executive-sponsor; manager/lead -> pilot-lead;
  else team-member).
- relationship: buyer (a leader at an operating company), vendor (sells to that audience: consultancies, platforms,
  account executives, founders pitching partnerships), student (students, interns on class projects, researchers),
  advisor (an outside advisor acting for a client). Use the directory kind and the message.
- pilot_stage, company, size_band from the enrichment and the contact; gap_at_least_6 when any diagnostic category gap is 6 or more.
- reasons: three to five short lines a human can read in the note.""",
    schema=LeadProfile.model_json_schema(),
)

DRAFTER = AgentSpec(
    name="drafter",
    model=SONNET,
    effort="medium",
    max_turns=8,
    tools=[TOOL["check_consent"], TOOL["check_brand"], TOOL["check_claims"]],
    instructions="""You are the Drafter. Write a short follow-up email from Shane LaBounty (Lab Intelligence) to a good-fit lead
who just ran the Stalled-Pilot Diagnostic. It is a DRAFT saved to a HubSpot note; it is never sent by this system.

Voice: Shane is a senior marketing-operations leader who ran large budgets and teams and now tests AI against that
world. Warm, direct, first person, contractions fine, experience first. Specific over general: name the one thing
from their diagnostic (the stage, the biggest gap) and one concrete next step (a short call). No pleasantries, no
pitch, no hype, no emoji, no numbers you were not given. Under 120 words. Subject under 8 words.

Before you answer you may call check_consent for the lead's email (if not allowed, return an empty subject and body
and say why in rationale), check_brand on your body, and check_claims on any sentence with a number.""",
    schema=Draft.model_json_schema(),
)

AGENTS: dict[str, AgentSpec] = {a.name: a for a in (ORCHESTRATOR, ENRICHER, QUALIFIER, DRAFTER)}
