"""C5: the crew end to end on the fixtures — PRD acceptance criteria 1–5 (D-12..D-17)."""

import json

import pytest

from triage.crew import Crew
from triage.llm import RecordedCaller
from triage.models import load_leads
from triage.notes import DRAFT_HEADER
from triage.workers import OverCap


@pytest.fixture
async def ran(layer):
    leads = load_leads()
    crew = Crew.for_fixtures(layer=layer, run_id="g2c-test", leads=leads)
    results = await crew.run_all(leads)
    return crew, leads, results


# -- AC 1: every lead gets a note with score, band and reasons -------------------------------


async def test_ac1_every_lead_gets_a_triage_note_with_band_score_and_reasons(ran):
    crew, leads, results = ran
    assert len(results) == 20
    for lead, r in zip(leads, results):
        notes = crew.hubspot.list_notes(lead.id)
        triage = [n for n in notes if n.kind == "triage"]
        assert len(triage) == 1 and r.note_id == triage[0].id
        body = triage[0].body
        assert f"Band: {r.band}" in body and "Reasons:" in body and r.reasons, lead.id
        if r.band in ("good fit", "poor fit", "student", "vendor"):
            assert r.score is not None and f"Score: {r.score}/100" in body and "Rubric:" in body
        else:
            assert r.score is None


# -- AC 2: good-fit leads get a saved draft; nothing is ever sent -------------------------------


async def test_ac2_consented_good_fits_get_a_draft_note_and_nothing_is_sent(ran):
    crew, leads, results = ran
    drafted = {r.lead_id for r in results if r.draft and r.draft.created}
    assert drafted == {"hs-1001", "hs-1002", "hs-1006", "hs-1008", "hs-1013", "hs-1019"}
    for lid in drafted:
        drafts = [n for n in crew.hubspot.list_notes(lid) if n.kind == "draft"]
        assert len(drafts) == 1 and drafts[0].body.startswith(DRAFT_HEADER) and "Subject:" in drafts[0].body
        assert "Brand policy (G0 brand.policy v1): passed" in drafts[0].body
    # good fits without consent: band stays good fit, the note says why there is no draft (D-15)
    by = {r.lead_id: r for r in results}
    assert by["hs-1003"].band == "good fit" and by["hs-1003"].draft.created is False and "not_consented" in by["hs-1003"].draft.reason
    assert by["hs-1007"].band == "good fit" and "do_not_contact" in by["hs-1007"].draft.reason
    assert not [n for n in crew.hubspot.list_notes("hs-1003") if n.kind == "draft"]
    # the only writes anywhere are notes on synthetic contacts
    assert len(crew.hubspot.notes) == 26 and all(crew.hubspot.get_contact(n.contact_id).email.endswith("@example.com") for n in crew.hubspot.notes)
    assert crew.blocked == [] and all(r.blocked_attempts == 0 for r in results)


# -- AC 3: the orchestrator skips a worker, reason logged ------------------------------------------


async def test_ac3_skips_are_logged_with_their_reason(ran):
    crew, leads, results = ran
    by = {r.lead_id: r for r in results}

    def skipped(lid, worker):
        d = next(x for x in by[lid].decisions if x.worker == worker)
        assert not d.called
        rows = crew.layer.db.conn.execute("SELECT note FROM run_log WHERE run_id=? AND agent='crew' AND step=? AND status='skipped'", ("g2c-test", f"{lid}:{worker}")).fetchall()
        assert rows and rows[0]["note"] == d.reason
        assert f"- {worker}: SKIPPED — {d.reason}" in crew.hubspot.list_notes(lid)[-1].body
        return d.reason

    assert "company profile complete" in skipped("hs-1013", "enricher")          # D-19
    assert "could not be identified" in skipped("hs-1010", "qualifier")           # unresolved company
    assert skipped("hs-1010", "drafter") == "no qualification"
    assert skipped("hs-1004", "drafter") == "band is poor fit; no follow-up"
    assert skipped("hs-1014", "drafter") == "band is student; no follow-up"
    assert "consent: not_consented" == skipped("hs-1003", "drafter")
    assert "duplicate of contact hs-1001" in skipped("hs-1018", "enricher")
    called = {r.lead_id: [d.worker for d in r.decisions if d.called] for r in results}
    assert called["hs-1013"] == ["qualifier", "drafter"] and called["hs-1018"] == [] and called["hs-1010"] == ["enricher"]


# -- AC 4: a forced send attempt is blocked and logged, end to end -----------------------------------


async def test_ac4_forced_send_from_a_worker_is_blocked_and_logged(layer, tmp_path):
    leads = [x for x in load_leads() if x.id == "hs-1001"]
    doc = json.loads(RecordedCaller().path.read_text())
    entry = doc["responses"]["drafter:hs-1001"]
    entry["tool_attempts"] = [
        {"name": "mcp__hubspot__send_email", "input": {"to": "ada.test01@example.com", "subject": "x", "body": "y"}},  # a send
        {"name": "mcp__triage__check_consent", "input": {"email": "ada.test01@example.com"}},                          # allowed
        {"name": "Bash", "input": {"command": "curl -X POST https://api.hubapi.com/marketing/v3/transactional/single-email/send"}},  # not in the list, and a send
    ]
    p = tmp_path / "forced.json"
    p.write_text(json.dumps(doc))
    crew = Crew.for_fixtures(layer=layer, run_id="g2c-forced", leads=leads, caller=RecordedCaller(p))
    r = await crew.run_lead(leads[0])
    assert r.blocked_attempts == 2 and len(crew.safety_log) == 2
    assert [b.tool_name for b in crew.blocked] == ["mcp__hubspot__send_email", "Bash"]
    rows = crew.layer.db.conn.execute("SELECT note FROM run_log WHERE run_id='g2c-forced' AND status='error'").fetchall()
    assert len(rows) == 2 and all(row["note"].startswith("BLOCKED send attempt") for row in rows)
    assert "blocked tool attempts: 2" in crew.hubspot.list_notes("hs-1001")[-1].body
    # the draft still exists as a note, and only as a note
    assert r.draft.created and [n.kind for n in crew.hubspot.list_notes("hs-1001")] == ["draft", "triage"]
    assert crew.handlers.calls.count("check_consent") >= 1  # the allowed call still ran


# -- AC 5: band accuracy against the labels, cost per lead -----------------------------------------


async def test_ac5_fixture_mode_band_accuracy_and_cost_are_reported_honestly(ran):
    crew, leads, results = ran
    correct = sum(r.band == lead.label.band for lead, r in zip(leads, results))
    assert correct == 20  # the recorded fake never reads the labels (D-16); this pins the governed path
    assert all(r.measured is False for r in results) and all(r.cost_usd == 0.0 for r in results)
    cost, calls = crew.run_cost()
    assert cost == 0.0 and calls > 20
    assert "not measured live" in crew.hubspot.list_notes("hs-1001")[-1].body


# -- the layer sees every call and every lead ----------------------------------------------------------


async def test_every_model_call_and_every_lead_is_in_the_layer(ran):
    crew, leads, results = ran
    db = crew.layer.db.conn
    agents = {row["agent"]: row["n"] for row in db.execute("SELECT agent, COUNT(*) AS n FROM run_log WHERE run_id='g2c-test' AND status='ok' GROUP BY agent")}
    assert agents["orchestrator"] == 18 and agents["enricher"] == 17 and agents["qualifier"] == 16 and agents["drafter"] == 6
    events = db.execute("SELECT fields FROM events WHERE event='lead.triaged' AND run_id='g2c-test'").fetchall()
    assert len(events) == 20
    for row in events:
        f = json.loads(row["fields"])
        assert set(f) >= {"lead_id", "band", "workers_called", "workers_skipped", "drafted", "cost_usd", "measured"}
        assert "@" not in json.dumps(f)  # no personal data in measurement fields
    assert db.execute("SELECT COUNT(*) FROM evaluations WHERE rubric_id='g2_lead_fit_v1'").fetchone()[0] >= 16


# -- the cap stops the run ---------------------------------------------------------------------------------


async def test_over_cap_stops_before_the_next_model_call(layer, monkeypatch):
    monkeypatch.setenv("G0_RUN_CAP_USD", "0")
    leads = load_leads()[:3]
    crew = Crew.for_fixtures(layer=layer, run_id="g2c-cap", leads=leads)
    results = await crew.run_all(leads)
    assert results == [] and crew.over_cap
    rows = crew.layer.db.conn.execute("SELECT note FROM run_log WHERE run_id='g2c-cap' AND status='skipped'").fetchall()
    assert rows and "cap" in rows[0]["note"]
    with pytest.raises(OverCap):
        await crew.run_lead(leads[0])
    assert crew.hubspot.notes == []
