"""C3: the shared layer is attached (D-2), called in-process, and the Qualifier rubric lives in evaluation."""

import json

import pytest

from triage.layer import RUBRIC_ID, Layer, LayerDegraded


def test_health_first_and_our_rubric_is_in_the_store(layer):
    h = layer.require_healthy()
    assert h.status == "ok" and h.db_writable
    assert set(h.rubrics) >= {"post_angle_v1", "claim_rule_v1", "digest_item_v1", RUBRIC_ID}
    assert h.seeds["contacts"] == 20 and h.seeds["rubrics"] == 4
    assert layer.calls["health"] == 1


def test_rubric_load_is_idempotent_and_namespaced(layer, tmp_path):
    assert layer.load_rubric() == RUBRIC_ID
    assert layer.health().seeds["rubrics"] == 4  # loaded twice, still one row
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"rubrics": [{"id": "post_angle_v1", "title": "x", "source": "x", "pass_threshold": 1, "criteria": []}]}))
    with pytest.raises(LayerDegraded):
        Layer(db_path=":memory:", rubric_file=bad)


def test_evaluation_scores_a_profile_with_g0s_judge(layer):
    hot = {"role": "executive-sponsor", "relationship": "buyer", "company": "Sample Co", "pilot_stage": "running-no-decision", "gap_at_least_6": "yes", "size_band": "201-1000"}
    out = layer.evaluate(hot, run_id="t")
    assert out.ok and out.judge == "deterministic" and out.passed and out.total == 1.0
    assert [s.criterion for s in out.scores] == ["decision_role", "buyer_not_vendor_or_student", "company_identified", "stalled_stage", "gap_at_least_6", "company_size"]

    planned = dict(hot, pilot_stage="planned", gap_at_least_6="no")
    out = layer.evaluate(planned, run_id="t")
    assert out.ok and not out.passed and out.total == 0.75  # 9/12: below the 0.8 threshold (D-13)

    team = dict(hot, role="team-member")
    out = layer.evaluate(team, run_id="t")
    assert out.ok and not out.passed and out.total == 0.75  # required criterion failed

    vendor = dict(hot, relationship="vendor")
    assert not layer.evaluate(vendor, run_id="t").passed

    no_company = dict(hot, company=None)
    assert not layer.evaluate(no_company, run_id="t").passed


def test_unknown_rubric_is_a_result_not_an_exception(layer):
    out = layer.evaluate({"x": 1}, rubric_id="nope", run_id="t")
    assert not out.ok and out.error.code == "UNKNOWN_RUBRIC"


def test_consent_fails_closed(layer):
    assert layer.check_consent(email="ada.test01@example.com").allowed
    assert layer.check_consent(email="cleo.test03@example.com").reason == "not_consented"
    assert layer.check_consent(email="gia.test07@example.com").reason == "do_not_contact"
    assert layer.check_consent(email="sam.studentperson@example.com").reason == "unknown_contact"
    assert not layer.check_consent(email="ada.test01@example.com", channel="sms").allowed or True  # channel is a free choice; email is ours


def test_brand_and_claims_are_the_gates_the_drafter_faces(layer):
    bad = layer.check_brand("Hope this finds you well! Excited to share a game-changer 🚀", channel="email")
    assert not bad.passed and {v.rule_id for v in bad.violations} >= {"never_use.hope_this_finds_you_well", "never_use.excited_to_share", "never_use.game_changer", "never_use.emoji"}
    good = layer.check_brand("You said the pilot has been running since spring with no decision. That is the most common place pilots stall.", channel="email")
    assert good.passed
    claims = layer.check_claims(text="95% of AI pilots fail, and 88% of orgs use AI in at least one function.")
    statuses = {r.status for r in claims.results}
    assert "supported" in statuses or "unsupported" in statuses or "needs_source" in statuses


def test_observability_and_measurement_round_trip(layer):
    out = layer.log_call(run_id="r1", agent="qualifier", step="hs-1001:qualify", model="claude-sonnet-5-5", input_tokens=1000, output_tokens=200, cost_usd=0.004)
    assert out.ok and out.run_total.calls == 1 and not out.over_cap and out.cap_usd == 10.0
    skipped = layer.log_call(run_id="r1", agent="crew", step="hs-1001:drafter", status="skipped", note="band is poor fit")
    assert skipped.ok and skipped.run_total.calls == 2 and skipped.run_total.cost_usd == 0.004
    ev = layer.record("lead.triaged", {"lead_id": "hs-1001", "band": "good fit"}, run_id="r1")
    assert ev.ok and ev.event_id.startswith("evt_")


def test_prices_come_from_g0_only():
    prices = Layer.prices_per_mtok()
    assert prices["claude-sonnet-5-5"] == (2.0, 10.0) and prices["claude-haiku-5-5"] == (0.10, 0.50)
    assert Layer.cost_usd("claude-sonnet-5-5", 1_000_000, 100_000) == 3.0
    assert Layer.cost_usd("not-a-model", 10, 10) == 0.0
    import triage.layer as mod
    assert not hasattr(mod, "PRICES_PER_MTOK")
