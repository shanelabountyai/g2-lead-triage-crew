"""C1: the fixtures are the eval set (D-9) and the Enricher's whole world (D-6)."""

from collections import Counter

from triage.models import BANDS, STALLED_STAGES, load_companies, load_leads


def test_twenty_leads_cover_every_band():
    leads = load_leads()
    assert len(leads) == 20
    counts = Counter(lead.label.band for lead in leads)
    assert set(counts) == set(BANDS) - {"not qualified"}  # D-23: a runtime band (Qualifier skipped by the plan), not a label
    assert counts["good fit"] == 8 and counts["poor fit"] == 4
    assert all(counts[b] == 2 for b in ("student", "vendor", "duplicate", "missing company info"))


def test_every_email_is_example_com_and_every_name_is_obviously_fake():
    for lead in load_leads():
        assert lead.email.lower().endswith("@example.com"), lead.id
        assert (lead.properties.lastname or "").endswith("person"), lead.id


def test_ids_unique_and_duplicates_come_after_their_originals():
    leads = load_leads()
    ids = [lead.id for lead in leads]
    assert len(ids) == len(set(ids))
    by_id = {lead.id: lead for lead in leads}
    assert by_id["hs-1018"].created_at > by_id["hs-1001"].created_at
    assert by_id["hs-1020"].created_at > by_id["hs-1019"].created_at


def test_lead_grade_matches_the_diagnostic_rule():
    """hot = all three conditions, warm = two, cool otherwise (li-lead-gen-tools gradeLead, D-5)."""
    for lead in load_leads():
        p = lead.properties
        met = sum([
            p.li_tool_role in ("executive-sponsor", "pilot-lead"),
            p.li_tool_pilot_stage in STALLED_STAGES,
            p.max_gap >= 6,
        ])
        expected = {3: "hot", 2: "warm"}.get(met, "cool")
        assert p.li_tool_lead_grade == expected, (lead.id, met)


def test_one_lead_has_a_full_company_profile_and_the_rest_do_not():
    full = [lead.id for lead in load_leads() if lead.properties.has_full_company_profile]
    assert full == ["hs-1013"]


def test_directory_is_synthetic_and_covers_every_named_company():
    companies = load_companies()
    names = {c.name for c in companies}
    assert len(names) == len(companies)
    for c in companies:
        assert c.domain.endswith((".example.com", ".example.edu", ".example.org")), c.name
    for lead in load_leads():
        company = (lead.properties.company or "").strip()
        if company and company.lower() != "self":
            assert company in names, lead.id
    assert {c.kind for c in companies} >= {"company", "education", "vendor"}
