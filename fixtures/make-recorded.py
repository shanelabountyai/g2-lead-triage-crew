"""Generate fixtures/recorded-responses.json: one hand-made answer per agent per lead (D-16).

This is NOT a recording of a live model. It is what a sensible model would plausibly answer, derived from the lead's
own fields (title, role, company, message) and the synthetic directory with plain heuristics. It never reads the
labels in leads.json, so the fixture-mode eval (`triage eval`) measures the governed pipeline, not a lookup of the
answer key. `triage run --fixtures --record` with ANTHROPIC_API_KEY overwrites this file with real responses.

Run: uv run python fixtures/make-recorded.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from triage.directory import Directory  # noqa: E402
from triage.models import load_leads  # noqa: E402
from triage.prompts import DRAFTER, ENRICHER, ORCHESTRATOR, QUALIFIER, TOOL  # noqa: E402
from triage.workers import infer_role  # noqa: E402

STUDENT_WORDS = ("student", "thesis", "class project", "mba candidate", "intern", "dissertation", "coursework", "researching for my")
VENDOR_WORDS = ("we help", "our platform", "partner with", "let me show you", "demo", "referrals", "account executive", "founder", "our product", "our solution")
STAGE_WORDS = {
    "running-no-decision": "a pilot that has been running with no decision on what happens next",
    "finished-not-rolled-out": "a pilot that finished and never rolled out",
    "rolled-out-low-use": "a rollout that few people use",
    "shut-down": "a pilot that was shut down",
    "planned": "a pilot that has not started",
}
GAP_WORDS = {"people": "ownership and adoption", "process": "success criteria and what happens when the pilot ends", "technology": "data access and how the tool fits the systems people already use"}


def orchestrator(lead, directory):
    p = lead.properties
    full = p.has_full_company_profile
    blank = directory.is_placeholder(p.company)
    return {
        "response": {
            "call_enricher": not full,
            "enricher_reason": ("contact already carries company, industry, number of employees and website" if full
                                else ("no company given; the Enricher will try the title and message" if blank else f"company '{p.company}' needs industry, size and kind from the directory")),
            "call_qualifier": not blank,
            "qualifier_reason": ("no company to score" if blank else f"{p.li_tool_role or 'role not given'} at {p.company}; pilot stage {p.li_tool_pilot_stage}, grade {p.li_tool_lead_grade}"),
            "summary": f"{p.firstname} {p.lastname}, {p.jobtitle or 'no title'}, {p.company or 'no company'}: {p.li_tool_role or 'no role'}, stage {p.li_tool_pilot_stage}.",
        },
        "tool_attempts": [{"name": TOOL["find_duplicates"], "input": {"email": p.email, "firstname": p.firstname or "", "lastname": p.lastname or "", "company": p.company or ""}}],
    }


def enricher(lead, directory):
    p = lead.properties
    record, how = directory.lookup(p.company)
    if record is None:
        resp = {"company_identified": False, "company": None, "industry": None, "size_band": None, "employees": None, "kind": "unknown",
                "role_title": p.jobtitle, "sources": [f"directory: no record for '{p.company or ''}'"], "note": "no usable company on the contact"}
    else:
        resp = {"company_identified": True, "company": record.name, "industry": record.industry, "size_band": record.size_band, "employees": record.employees,
                "kind": record.kind, "role_title": p.jobtitle, "sources": [f"directory:{record.name}"], "note": f"{how} match on '{p.company}'"}
    return {"response": resp, "tool_attempts": [{"name": TOOL["lookup_company"], "input": {"name": p.company or ""}}]}


def relationship_for(lead, directory):
    p = lead.properties
    text = " ".join([(p.jobtitle or ""), (p.message or "")]).lower()
    record, _ = directory.lookup(p.company)
    kind = record.kind if record else "unknown"
    if kind == "education" or any(w in text for w in STUDENT_WORDS):
        return "student", "student or researcher: the title or message says so" + (" and the organization is a school" if kind == "education" else "")
    if kind == "vendor" or any(w in text for w in VENDOR_WORDS):
        return "vendor", "sells to this audience: " + ("the company is a vendor in the directory" if kind == "vendor" else "the message pitches a product or partnership")
    if p.li_tool_role == "outside-advisor" or "advisor" in text:
        return "advisor", "an outside advisor acting for a client, not the buyer"
    return "buyer", "a leader at an operating company"


def qualifier(lead, directory):
    p = lead.properties
    role = p.li_tool_role or infer_role(p.jobtitle)
    rel, why = relationship_for(lead, directory)
    record, _ = directory.lookup(p.company)
    reasons = [
        f"Role: {role}" + ("" if p.li_tool_role else f" (inferred from title '{p.jobtitle}'; the form left role blank)"),
        f"Relationship: {rel} — {why}",
        f"Pilot stage: {p.li_tool_pilot_stage}; biggest gap {p.max_gap}/9",
        (f"Company: {record.name}, {record.industry}, {record.size_band}" if record else "Company: not identified"),
    ]
    resp = {"role": role, "relationship": rel, "pilot_stage": p.li_tool_pilot_stage, "company": record.name if record else None,
            "size_band": record.size_band if record else None, "gap_at_least_6": p.max_gap >= 6, "reasons": reasons}
    item = {k: ("yes" if v is True else "no" if v is False else v) for k, v in resp.items() if k != "reasons"}
    return {"response": resp, "tool_attempts": [{"name": TOOL["evaluate_fit"], "input": {k: (v or "") for k, v in item.items()}}]}


def drafter(lead, directory):
    p = lead.properties
    gaps = {"people": p.li_tool_people_gap or 0, "process": p.li_tool_process_gap or 0, "technology": p.li_tool_technology_gap or 0}
    biggest = max(gaps, key=gaps.get)
    stage = STAGE_WORDS.get(p.li_tool_pilot_stage or "", "a pilot")
    body = (
        f"Hi {p.firstname},\n\n"
        f"Your diagnostic describes {stage}, with the biggest gap in {GAP_WORDS[biggest]}. "
        f"I ran into the same pattern more than once with a large marketing team: the model was fine, the decision about what happens next was nobody's job.\n\n"
        f"If it would help, I'll walk through what I'd fix first in your situation on a short call. No deck, no pitch. "
        f"Reply with a day that works and I'll send a time.\n\n"
        f"Shane"
    )
    subject = {"people": "Who owns the next decision", "process": "Stop criteria for the pilot", "technology": "Where the pilot meets your systems"}[biggest]
    resp = {"subject": subject, "body": body, "rationale": f"Leads with the stage and the {biggest} gap from the diagnostic; one concrete next step; no numbers."}
    return {"response": resp, "tool_attempts": [{"name": TOOL["check_consent"], "input": {"email": p.email, "channel": "email"}},
                                                {"name": TOOL["check_brand"], "input": {"text": body, "channel": "email"}}]}


def main() -> None:
    directory = Directory()
    out = {
        "_about": "Hand-made answers in each agent's output schema, generated by fixtures/make-recorded.py from the lead fields "
                  "and the synthetic directory with plain heuristics (D-16). NOT a recording of a live model: no live G2·C call "
                  "has been made. It never reads the labels. Usage is zero, so cost per lead is 'not measured live'. "
                  "`triage run --fixtures --record` with ANTHROPIC_API_KEY overwrites this file with real responses.",
        "recorded_live": False,
        "recorded_at": None,
        "responses": {},
    }
    for lead in load_leads():
        for spec, fn in ((ORCHESTRATOR, orchestrator), (ENRICHER, enricher), (QUALIFIER, qualifier), (DRAFTER, drafter)):
            entry = fn(lead, directory)
            out["responses"][f"{spec.name}:{lead.id}"] = {
                "model": spec.model, "response": entry["response"], "stop_reason": "hand-made", "sdk_cost_usd": None,
                "usage": {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
                "tool_attempts": entry["tool_attempts"],
            }
    path = HERE / "recorded-responses.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(out['responses'])} entries)")


if __name__ == "__main__":
    main()
