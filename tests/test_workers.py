"""C4: the subagents — specs, tools, model callers, and the code-side enforcement after each worker."""

import json

import pytest

from triage.bands import canonical_email, decide_band, find_duplicate
from triage.crew import Crew
from triage.llm import AgentSdkCaller, ModelCallError, RecordedCaller, Session
from triage.models import Enrichment, LeadProfile, Qualification, load_leads
from triage.prompts import AGENTS, DRAFTER, ENRICHER, ORCHESTRATOR, QUALIFIER, SHARED_POINTER
from triage.safety import SafetyLog, make_block_hook
from triage.tools import CrewContext, ToolHandlers, build_tool_server
from triage.workers import enforce_enrichment, enforce_qualification, infer_role, size_band_for


def by_id(leads, lid):
    return next(x for x in leads if x.id == lid)


# -- specs: own context, limited tool list, shared rules not copied -----------------------


def test_each_agent_has_its_own_limited_tool_list_and_no_send_tool():
    assert ORCHESTRATOR.tools == ["mcp__triage__find_duplicates"]
    assert ENRICHER.tools == ["mcp__triage__lookup_company"]
    assert QUALIFIER.tools == ["mcp__triage__evaluate_fit"]
    assert DRAFTER.tools == ["mcp__triage__check_consent", "mcp__triage__check_brand", "mcp__triage__check_claims"]
    for spec in AGENTS.values():
        assert not any("send" in t.lower() or "mail" in t.lower() for t in spec.tools)
        assert spec.model in ("claude-sonnet-5-5", "claude-haiku-5-5")
        assert spec.schema["type"] == "object"


def test_prompts_carry_a_pointer_to_the_layer_not_the_rules():
    for spec in AGENTS.values():
        sp = spec.system_prompt()
        assert SHARED_POINTER in sp
        # The brand policy's never-use list is G0's; the prompts must not restate it (attach.md step 4).
        assert "excited to share" not in sp.lower() and "circle back" not in sp.lower()


def test_sdk_options_are_built_the_safe_way(layer, hubspot, directory):
    handlers = ToolHandlers(CrewContext(layer=layer, directory=directory, hubspot=hubspot, run_id="t"))
    hook = make_block_hook(SafetyLog(), agent="drafter", allowed_tools=DRAFTER.tools)
    opts = AgentSdkCaller(max_budget_usd=10.0).options(DRAFTER, Session(lead_id="hs-1001", hook=hook, handlers=handlers))
    assert opts.tools == [] and opts.allowed_tools == DRAFTER.tools and opts.permission_mode == "dontAsk"
    assert opts.strict_mcp_config and set(opts.mcp_servers) == {"triage"} and opts.mcp_servers["triage"]["type"] == "sdk"
    assert opts.output_format == {"type": "json_schema", "schema": DRAFTER.schema}
    assert opts.max_budget_usd == 10.0 and opts.max_turns == DRAFTER.max_turns and opts.model == "claude-sonnet-5-5"
    matchers = opts.hooks["PreToolUse"]
    assert len(matchers) == 1 and matchers[0].hooks == [hook] and matchers[0].on_failure == "block"


# -- the in-process tool server ------------------------------------------------------------


async def test_tool_handlers_answer_from_the_layer_the_directory_and_hubspot(layer, hubspot, directory):
    h = ToolHandlers(CrewContext(layer=layer, directory=directory, hubspot=hubspot, run_id="t"))
    out = json.loads((await h.lookup_company({"name": "SampleCo"}))["content"][0]["text"])
    assert out["found"] and out["record"]["name"] == "Sample Co" and out["how"] == "alias"
    out = json.loads((await h.evaluate_fit({"role": "pilot-lead", "relationship": "buyer", "company": "X", "pilot_stage": "planned", "gap_at_least_6": "no", "size_band": "11-50"}))["content"][0]["text"])
    assert out["ok"] and out["passed"] is False and out["total"] == 0.6667
    out = json.loads((await h.check_consent({"email": "gia.test07@example.com"}))["content"][0]["text"])
    assert out["allowed"] is False and out["reason"] == "do_not_contact"
    out = json.loads((await h.check_brand({"text": "Hope this finds you well"}))["content"][0]["text"])
    assert out["passed"] is False
    out = json.loads((await h.check_claims({"text": "88% of orgs use AI in at least one function."}))["content"][0]["text"])
    assert out["results"][0]["status"] in ("supported", "needs_source")
    out = json.loads((await h.find_duplicates({"email": "ada.test01@example.com", "firstname": "Ada", "lastname": "Testperson", "company": "Sample Co"}))["content"][0]["text"])
    assert [c["id"] for c in out["candidates"]] == ["hs-1001", "hs-1018"]
    assert all(set(c) == {"id", "created_at", "matched_on"} for c in out["candidates"])  # ids and dates only
    assert h.calls == ["lookup_company", "evaluate_fit", "check_consent", "check_brand", "check_claims", "find_duplicates"]


def test_tool_server_builds_with_the_six_tools(layer, hubspot, directory):
    server = build_tool_server(ToolHandlers(CrewContext(layer=layer, directory=directory, hubspot=hubspot, run_id="t")))
    assert server["type"] == "sdk" and server["name"] == "triage"


# -- the recorded caller ----------------------------------------------------------------------


async def test_recorded_caller_replays_tool_attempts_through_the_hook_and_handlers(layer, hubspot, directory):
    caller = RecordedCaller()
    assert caller.measured is False and "NOT a recording" in caller.about
    handlers = ToolHandlers(CrewContext(layer=layer, directory=directory, hubspot=hubspot, run_id="t"))
    log = SafetyLog()
    hook = make_block_hook(log, agent="enricher", allowed_tools=ENRICHER.tools)
    r = await caller.call(ENRICHER, "x", Session(lead_id="hs-1001", hook=hook, handlers=handlers))
    assert r.parsed["company_identified"] is True and r.tool_calls == ["mcp__triage__lookup_company"] and r.blocked == 0
    assert handlers.calls == ["lookup_company"] and r.input_tokens == 0
    with pytest.raises(ModelCallError):
        await caller.call(ENRICHER, "x", Session(lead_id="hs-0000", hook=hook, handlers=handlers))


async def test_recorded_caller_blocks_a_tool_outside_the_agents_list(layer, hubspot, directory, tmp_path):
    doc = {"recorded_live": False, "responses": {"enricher:hs-1001": {"model": "claude-haiku-5-5", "response": {"company_identified": False},
                                                                      "tool_attempts": [{"name": "mcp__triage__check_consent", "input": {"email": "a@example.com"}}]}}}
    p = tmp_path / "rec.json"
    p.write_text(json.dumps(doc))
    handlers = ToolHandlers(CrewContext(layer=layer, directory=directory, hubspot=hubspot, run_id="t"))
    log = SafetyLog()
    r = await RecordedCaller(p).call(ENRICHER, "x", Session(lead_id="hs-1001", hook=make_block_hook(log, agent="enricher", allowed_tools=ENRICHER.tools), handlers=handlers))
    assert r.blocked == 1 and handlers.calls == [] and len(log) == 1


# -- enforcement after each worker ----------------------------------------------------------------


def test_enricher_directory_overrides_an_invented_field(layer, leads):
    crew = Crew.for_fixtures(layer=layer, run_id="t")
    lead = by_id(leads, "hs-1001")
    invented = Enrichment(company_identified=True, company="Sample Co", industry="Aerospace", size_band="1-10", employees=3, kind="vendor")
    e = enforce_enrichment(crew, lead, invented)
    assert e.industry == "Consumer packaged goods" and e.size_band == "201-1000" and e.employees == 640 and e.kind == "company"
    assert e.sources[0].startswith("directory:Sample Co")


def test_enricher_unresolved_company_is_not_identified_whatever_the_model_said(layer, leads):
    crew = Crew.for_fixtures(layer=layer, run_id="t")
    lead = by_id(leads, "hs-1011")  # company "self"
    confident = Enrichment(company_identified=True, company="Kai Industries", industry="Software", size_band="51-200", employees=100, kind="company")
    e = enforce_enrichment(crew, lead, confident)
    assert e.company_identified is False and e.company is None
    lead = by_id(leads, "hs-1013")  # complete profile on the contact, no directory lookup needed
    e = enforce_enrichment(crew, lead, Enrichment(company_identified=False))
    assert e.company_identified and e.company == "Testdata Ltd" and e.size_band == "1001-5000"


def test_qualifier_facts_come_from_the_contact_and_the_score_from_g0(layer, leads):
    crew = Crew.for_fixtures(layer=layer, run_id="t")
    lead = by_id(leads, "hs-1005")  # team-member on the form
    enrichment = enforce_enrichment(crew, lead, Enrichment(company_identified=False))
    model_view = LeadProfile(role="executive-sponsor", relationship="buyer", pilot_stage="planned", gap_at_least_6=False, reasons=["model says sponsor"])
    q = enforce_qualification(crew, lead, enrichment, model_view)
    assert q.profile.role == "team-member"  # the form's role wins over the model's
    assert q.profile.pilot_stage == "running-no-decision" and q.profile.gap_at_least_6 is True  # facts from the contact
    assert q.passed is False and q.score == 75 and q.judge == "deterministic" and q.evaluation_id.startswith("eval_")
    assert [c.criterion for c in q.criteria if c.score < 1] == ["decision_role"]


def test_role_inference_when_the_form_left_it_blank():
    assert infer_role("Chief Marketing Officer") == "executive-sponsor"
    assert infer_role("Content Ops Manager") == "pilot-lead"
    assert infer_role("Copywriter") == "team-member"
    assert infer_role(None) == "team-member"
    assert size_band_for(2300) == "1001-5000" and size_band_for(5) == "1-10" and size_band_for(9000) == "5000+" and size_band_for(None) is None


# -- bands and duplicates --------------------------------------------------------------------------


def test_band_precedence(layer, leads):
    crew = Crew.for_fixtures(layer=layer, run_id="t")
    lead = by_id(leads, "hs-1001")
    e = enforce_enrichment(crew, lead, Enrichment(company_identified=False))
    good = enforce_qualification(crew, lead, e, LeadProfile(relationship="buyer"))
    vendor = enforce_qualification(crew, lead, e, LeadProfile(relationship="vendor"))
    student = enforce_qualification(crew, lead, e, LeadProfile(relationship="student"))
    assert decide_band(duplicate_of="hs-1", enrichment=e, qualification=good) == "duplicate"
    assert decide_band(duplicate_of=None, enrichment=e, qualification=student) == "student"
    assert decide_band(duplicate_of=None, enrichment=e, qualification=vendor) == "vendor"
    assert decide_band(duplicate_of=None, enrichment=Enrichment(company_identified=False), qualification=None) == "missing company info"
    assert decide_band(duplicate_of=None, enrichment=e, qualification=good) == "good fit"
    poor = enforce_qualification(crew, lead, e, LeadProfile(relationship="advisor"))
    assert decide_band(duplicate_of=None, enrichment=e, qualification=poor) == "poor fit"


def test_find_duplicate_rule(hubspot, leads):
    assert canonical_email("Ada.Test01+again@Example.com") == "ada.test01@example.com"
    assert find_duplicate(hubspot, by_id(leads, "hs-1018")).id == "hs-1001"   # +tag email
    assert find_duplicate(hubspot, by_id(leads, "hs-1020")).id == "hs-1019"   # name + company
    assert find_duplicate(hubspot, by_id(leads, "hs-1001")) is None          # the original is not a duplicate of its copy
    assert find_duplicate(hubspot, by_id(leads, "hs-1019")) is None
    assert find_duplicate(hubspot, by_id(leads, "hs-1002")) is None


def test_find_duplicate_same_createdate_falls_back_to_id(hubspot, leads):
    """HubSpot stamps a whole batch with one createdate (seen live): the lower numeric id is the older contact."""
    from triage.hubspot import FakeHubSpot
    twin = by_id(leads, "hs-1018").model_copy(update={"id": "951", "created_at": "2026-11-09T18:43:02.409Z"})
    orig = by_id(leads, "hs-1001").model_copy(update={"id": "940", "created_at": "2026-11-09T18:43:02.409Z"})
    fake = FakeHubSpot()
    fake.add_contact(orig); fake.add_contact(twin)
    assert find_duplicate(fake, twin).id == "940"
    assert find_duplicate(fake, orig) is None
