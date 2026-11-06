"""The two notes the crew writes (D-4). Plain text; HubSpot renders note bodies as-is."""

from __future__ import annotations

from triage.models import DraftOutcome, Lead, TriageResult

DRAFT_HEADER = "DRAFT — not sent"


def triage_note(lead: Lead, r: TriageResult) -> str:
    lines = [f"Lead Triage Crew (G2·C) — run {r.run_id}", f"Band: {r.band}" + (f" · Score: {r.score}/100" if r.score is not None else "")]
    if r.qualification:
        lines[-1] += f" (rubric g2_lead_fit_v1, judge {r.qualification.judge}, evaluation {r.qualification.evaluation_id})"
    if r.duplicate_of:
        lines.append(f"Duplicate of contact {r.duplicate_of}: no workers were run; triage the original.")
    lines.append("Reasons:")
    lines.extend(f"- {x}" for x in r.reasons)
    lines.append("Workers:")
    for d in r.decisions:
        lines.append(f"- {d.worker}: {'called' if d.called else 'SKIPPED'} — {d.reason}")
    if r.enrichment:
        e = r.enrichment
        if e.company_identified:
            lines.append(f"Enrichment: {e.company} · {e.industry} · {e.size_band} ({e.employees} employees) · kind {e.kind} · source: {'; '.join(e.sources)}")
        else:
            lines.append(f"Enrichment: company not identified · {'; '.join(e.sources)}")
    if r.qualification:
        lines.append("Rubric:")
        for c in r.qualification.criteria:
            lines.append(f"- {c.criterion}: {c.score:.0%} (w{c.weight:g}{', required' if c.required else ''}) — {c.note}")
    if r.draft is None:
        lines.append("Draft: not attempted")
    elif r.draft.created:
        lines.append(f"Draft: saved as a separate note headed '{DRAFT_HEADER}' · brand policy {'passed' if r.draft.brand_passed else 'FAILED (violations listed on the draft)'}")
    else:
        lines.append(f"Draft: skipped — {r.draft.reason}")
    cost = f"${r.cost_usd:.4f}" if r.measured else "not measured live (recorded fake)"
    lines.append(f"Cost: {cost} · tokens in {r.input_tokens} / out {r.output_tokens} · blocked tool attempts: {r.blocked_attempts}")
    return "\n".join(lines)


def draft_note(lead: Lead, d: DraftOutcome) -> str:
    assert d.draft is not None
    lines = [DRAFT_HEADER, f"Follow-up email for {lead.properties.full_name or lead.email} — saved by the Lead Triage Crew; nothing has been sent.", "",
             f"Subject: {d.draft.subject}", "", d.draft.body, ""]
    if d.draft.rationale:
        lines += [f"Rationale: {d.draft.rationale}", ""]
    lines.append("Brand policy (G0 brand.policy v1): " + ("passed" if d.brand_passed else "FAILED"))
    lines.extend(f"- {v}" for v in d.brand_violations)
    lines.append("Claims registry (G0 claims.registry v1): " + ("every number supported" if not d.claims else "needs attention"))
    lines.extend(f"- {c}" for c in d.claims)
    return "\n".join(lines)
