"""The three workers and the orchestrator's planning call (D-11, D-12).

Every agent call goes through `run_agent`: one session, one hook, one observability row. After each worker the crew
enforces the governed facts in code, so the result is the same whether the model used its tools or not:

- Enricher: the directory is the source of truth; a record overwrites whatever the model wrote; no record and no
  complete profile means `company_identified=False`.
- Qualifier: the form's role, the pilot stage, the gaps and the enriched company are facts; the model supplies the
  relationship (buyer / vendor / student / advisor), an inferred role when the form left it blank, and the reasons.
  The score is G0 `evaluation` on rubric `g2_lead_fit_v1`.
- Drafter: consent was checked before the call (orchestrator rule); after the call `brand_policy` and
  `claims_registry` run on the draft and their findings travel with it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from triage.llm import CallResult, ModelCallError, Session
from triage.models import CriterionNote, Draft, DraftOutcome, Enrichment, Lead, LeadProfile, OrchestratorPlan, Qualification, Role, SizeBand
from triage.prompts import DRAFTER, ENRICHER, ORCHESTRATOR, QUALIFIER, AgentSpec
from triage.safety import BlockedAttempt, make_block_hook

if TYPE_CHECKING:
    from triage.crew import Crew


class OverCap(RuntimeError):
    """The run's observability total is at or over the cap; no more model calls (D-10)."""


@dataclass
class AgentCall:
    result: CallResult
    cost_usd: float


async def run_agent(crew: Crew, spec: AgentSpec, lead: Lead, user_text: str) -> AgentCall:
    total = crew.layer.run_total(crew.run_id)
    cap = crew.layer.cap_usd()
    if total.cost_usd >= cap:
        raise OverCap(f"run {crew.run_id} has spent ${total.cost_usd:.4f} of the ${cap:.2f} cap")

    def on_block(attempt: BlockedAttempt) -> None:
        crew.layer.log_call(run_id=crew.run_id, agent=spec.name, step=f"{lead.id}:{spec.name}:blocked", status="error",
                            note=f"BLOCKED send attempt: {attempt.tool_name} — {attempt.reason}")
        crew.blocked.append(attempt)

    hook = make_block_hook(crew.safety_log, agent=spec.name, allowed_tools=spec.tools, on_block=on_block)
    session = Session(lead_id=lead.id, hook=hook, handlers=crew.handlers)
    try:
        r = await crew.caller.call(spec, user_text, session)
    except ModelCallError as e:
        crew.layer.log_call(run_id=crew.run_id, agent=spec.name, step=f"{lead.id}:{spec.name}", model=spec.model, status="error", note=str(e)[:300])
        raise
    cost = crew.layer.cost_usd(r.model, r.billed_input_tokens, r.output_tokens)
    note = f"sdk_cost_usd={r.sdk_cost_usd} tools={r.tool_calls} blocked={r.blocked} caller={crew.caller.name}"
    out = crew.layer.log_call(run_id=crew.run_id, agent=spec.name, step=f"{lead.id}:{spec.name}", model=r.model,
                              input_tokens=r.billed_input_tokens, output_tokens=r.output_tokens, cost_usd=cost,
                              duration_ms=r.duration_ms, note=note)
    if out.ok and out.over_cap:
        crew.over_cap = True
    return AgentCall(result=r, cost_usd=cost)


def _lead_text(lead: Lead, extra: dict[str, Any] | None = None) -> str:
    doc = {"contact_id": lead.id, "created_at": lead.created_at, "properties": lead.properties.model_dump(exclude_none=True)}
    if extra:
        doc.update(extra)
    return json.dumps(doc, ensure_ascii=False, indent=2)


# -- orchestrator plan ------------------------------------------------------------


async def plan(crew: Crew, lead: Lead) -> tuple[OrchestratorPlan, AgentCall]:
    call = await run_agent(crew, ORCHESTRATOR, lead, _lead_text(lead, {"task": "Decide which specialists to call for this new contact."}))
    try:
        p = OrchestratorPlan.model_validate(call.result.parsed)
    except ValidationError as e:
        raise ModelCallError(f"orchestrator: plan does not match the schema: {e}") from e
    return p, call


# -- enricher -----------------------------------------------------------------------


async def enrich(crew: Crew, lead: Lead) -> tuple[Enrichment, AgentCall]:
    call = await run_agent(crew, ENRICHER, lead, _lead_text(lead, {"task": "Fill the company fields from the directory."}))
    try:
        model_view = Enrichment.model_validate(call.result.parsed)
    except ValidationError as e:
        raise ModelCallError(f"enricher: answer does not match the schema: {e}") from e
    return enforce_enrichment(crew, lead, model_view), call


def enforce_enrichment(crew: Crew, lead: Lead, model_view: Enrichment) -> Enrichment:
    """The directory decides (D-6). The model's fields survive only where the directory and the contact are silent."""
    p = lead.properties
    record, how = crew.directory.lookup(p.company)
    if record is None and model_view.company and not crew.directory.is_placeholder(model_view.company):
        record, how = crew.directory.lookup(model_view.company)  # the model tried an alias
    if record is not None:
        return Enrichment(company_identified=True, company=record.name, industry=record.industry, size_band=record.size_band,
                          employees=record.employees, kind=record.kind, role_title=p.jobtitle,
                          sources=[f"directory:{record.name} ({how} match on '{p.company}')"], note=model_view.note)
    if p.has_full_company_profile:
        return Enrichment(company_identified=True, company=p.company, industry=p.industry, size_band=size_band_for(p.numberofemployees),
                          employees=p.numberofemployees, kind="company", role_title=p.jobtitle,
                          sources=["contact: company, industry, numberofemployees, website already on the record"], note=model_view.note)
    return Enrichment(company_identified=False, company=None, industry=None, size_band=None, employees=None, kind="unknown",
                      role_title=p.jobtitle, sources=[f"directory: no record for '{p.company or ''}' ({how})"],
                      note=model_view.note or "company could not be identified from the contact or the directory")


def size_band_for(employees: int | None) -> SizeBand | None:
    if employees is None:
        return None
    for limit, band in ((10, "1-10"), (50, "11-50"), (200, "51-200"), (1000, "201-1000"), (5000, "1001-5000")):
        if employees <= limit:
            return band  # type: ignore[return-value]
    return "5000+"


def profile_from_contact(lead: Lead) -> Enrichment:
    """What the Qualifier sees when the Enricher was skipped (D-19): the contact's own complete profile."""
    p = lead.properties
    return Enrichment(company_identified=True, company=p.company, industry=p.industry, size_band=size_band_for(p.numberofemployees),
                      employees=p.numberofemployees, kind="company", role_title=p.jobtitle,
                      sources=["contact: company profile complete on the record; Enricher skipped"])


# -- qualifier -----------------------------------------------------------------------

ROLES: tuple[Role, ...] = ("executive-sponsor", "pilot-lead", "team-member", "outside-advisor")


def infer_role(jobtitle: str | None) -> Role:
    t = (jobtitle or "").lower()
    if any(w in t for w in ("chief", "cmo", "ceo", "coo", "cto", "vp", "vice president", "head of", "director", "founder", "president", "owner")):
        return "executive-sponsor"
    if any(w in t for w in ("manager", "lead", "pmo", "program", "project")):
        return "pilot-lead"
    return "team-member"


async def qualify(crew: Crew, lead: Lead, enrichment: Enrichment) -> tuple[Qualification, AgentCall]:
    call = await run_agent(crew, QUALIFIER, lead, _lead_text(lead, {"enrichment": enrichment.model_dump(mode="json"),
                                                                     "task": "Return the normalized profile for the fit rubric."}))
    try:
        model_view = LeadProfile.model_validate(call.result.parsed)
    except ValidationError as e:
        raise ModelCallError(f"qualifier: answer does not match the schema: {e}") from e
    return enforce_qualification(crew, lead, enrichment, model_view), call


def enforce_qualification(crew: Crew, lead: Lead, enrichment: Enrichment, model_view: LeadProfile) -> Qualification:
    p = lead.properties
    role: Role | None = p.li_tool_role if p.li_tool_role in ROLES else (model_view.role or infer_role(p.jobtitle))  # type: ignore[assignment]
    profile = LeadProfile(
        role=role,
        relationship=model_view.relationship,
        pilot_stage=p.li_tool_pilot_stage,
        company=enrichment.company if enrichment.company_identified else None,
        size_band=enrichment.size_band,
        gap_at_least_6=p.max_gap >= 6,
        reasons=list(model_view.reasons)[:6],
    )
    item = {"role": profile.role, "relationship": profile.relationship, "company": profile.company, "pilot_stage": profile.pilot_stage,
            "gap_at_least_6": "yes" if profile.gap_at_least_6 else "no", "size_band": profile.size_band}
    out = crew.layer.evaluate(item, run_id=crew.run_id, judge=crew.judge)
    if not out.ok:
        raise RuntimeError(f"evaluation refused: {out.error.code} {out.error.message}")
    return Qualification(
        score=int(round(out.total * 100)), passed=out.passed, judge=str(out.judge), evaluation_id=out.evaluation_id,
        criteria=[CriterionNote(criterion=s.criterion, score=s.score, weight=s.weight, required=s.required, note=s.note) for s in out.scores],
        profile=profile,
    )


# -- drafter --------------------------------------------------------------------------


async def draft(crew: Crew, lead: Lead, enrichment: Enrichment, qualification: Qualification) -> tuple[DraftOutcome, AgentCall]:
    p = lead.properties
    gaps = {"people": p.li_tool_people_gap or 0, "process": p.li_tool_process_gap or 0, "technology": p.li_tool_technology_gap or 0}
    biggest = max(gaps, key=gaps.get)  # type: ignore[arg-type]
    user_text = _lead_text(lead, {
        "enrichment": enrichment.model_dump(mode="json"),
        "qualification": {"score": qualification.score, "reasons": qualification.profile.reasons},
        "diagnostic": {"stage": p.li_tool_pilot_stage, "biggest_gap": biggest, "gaps": gaps},
        "task": "Write the follow-up draft. It is saved as a note and never sent.",
    })
    call = await run_agent(crew, DRAFTER, lead, user_text)
    try:
        d = Draft.model_validate(call.result.parsed)
    except ValidationError as e:
        raise ModelCallError(f"drafter: answer does not match the schema: {e}") from e
    return enforce_draft(crew, d), call


def enforce_draft(crew: Crew, d: Draft) -> DraftOutcome:
    if not d.subject.strip() or not d.body.strip():
        return DraftOutcome(created=False, reason=f"drafter returned no draft: {d.rationale or 'no rationale'}", draft=d)
    brand = crew.layer.check_brand(f"{d.subject}\n\n{d.body}", channel="email")
    violations = [f"{v.rule_id}: '{v.excerpt}' — {v.fix}" for v in brand.violations] if brand.ok else [f"brand_policy refused: {brand.error.message}"]
    claims = crew.layer.check_claims(text=d.body)
    flagged = []
    if claims.ok:
        for r in claims.results:
            if r.status != "supported":
                flagged.append(f"{r.status}: '{r.claim}' — {r.note}")
    return DraftOutcome(created=True, reason="good fit, consented on email", draft=d, brand_passed=bool(brand.ok and brand.passed),
                        brand_violations=violations, claims=flagged)
