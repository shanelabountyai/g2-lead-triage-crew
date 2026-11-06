"""C2: the safety invariants (D-7). These tests existed before any code path could reach an external system."""

import json

import pytest

from triage import safety
from triage.safety import BlockedAttempt, SafetyLog, SafetyViolation, assert_synthetic, classify_tool_call, make_block_hook


def pre_tool_use(tool_name: str, tool_input: dict | None = None, tool_use_id: str = "toolu_01") -> dict:
    return {"hook_event_name": "PreToolUse", "session_id": "sess", "tool_name": tool_name, "tool_input": tool_input or {}, "tool_use_id": tool_use_id}


# -- AC 4: a forced send attempt is blocked by the hook and logged -----------------------


async def test_forced_send_is_denied_and_logged():
    log = SafetyLog()
    seen: list[BlockedAttempt] = []
    hook = make_block_hook(log, agent="drafter", on_block=seen.append)
    out = await hook(pre_tool_use("mcp__hubspot__send_email", {"to": "ada.test01@example.com", "subject": "x", "body": "y"}), "toolu_99", None)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "BLOCKED" in out["hookSpecificOutput"]["permissionDecisionReason"]
    assert len(log) == 1 and seen[0].tool_name == "mcp__hubspot__send_email" and seen[0].agent == "drafter"
    assert seen[0].tool_use_id == "toolu_99"
    assert seen[0].input_keys == ["body", "subject", "to"]  # keys only, never the body


@pytest.mark.parametrize("tool_name", [
    "send_email", "sendEmail", "gmail_send", "mcp__gmail__send_message", "smtp_relay", "mcp__hubspot__single_send",
    "sendgrid_mail", "deliver_message", "publish_post", "mcp__gmail__reply", "mcp__gmail__forward", "Send",
])
async def test_every_send_shaped_tool_name_is_denied(tool_name):
    log = SafetyLog()
    hook = make_block_hook(log, agent="t")
    out = await hook(pre_tool_use(tool_name), None, None)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny", tool_name
    assert len(log) == 1


async def test_innocent_name_with_send_endpoint_in_input_is_denied():
    hook = make_block_hook(SafetyLog(), agent="t")
    out = await hook(pre_tool_use("http_request", {"url": "https://api.hubapi.com/marketing/v3/transactional/single-email/send", "method": "POST"}), None, None)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


async def test_innocent_name_with_recipient_and_body_is_denied():
    hook = make_block_hook(SafetyLog(), agent="t")
    out = await hook(pre_tool_use("create_message", {"to": "x@example.com", "body": "hi"}), None, None)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


async def test_deal_stage_edit_is_denied():
    hook = make_block_hook(SafetyLog(), agent="t")
    out = await hook(pre_tool_use("update_object", {"objectType": "deals", "properties": {"dealstage": "closedwon"}}), None, None)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    out = await hook(pre_tool_use("mcp__hubspot__update_deal_stage", {}), None, None)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize("tool_name", ["mcp__triage__check_consent", "mcp__triage__lookup_company", "mcp__triage__evaluate_fit",
                                       "mcp__triage__check_brand", "mcp__triage__check_claims", "mcp__triage__find_duplicates"])
async def test_the_crew_tools_pass_through(tool_name):
    log = SafetyLog()
    hook = make_block_hook(log, agent="t")
    assert await hook(pre_tool_use(tool_name, {"contact_id": "hs-1", "body": "note text"}), None, None) == {}
    assert len(log) == 0


async def test_tool_outside_the_agents_list_is_denied():
    log = SafetyLog()
    hook = make_block_hook(log, agent="enricher", allowed_tools=["mcp__triage__lookup_company"])
    assert await hook(pre_tool_use("mcp__triage__lookup_company", {"name": "Sample Co"}), None, None) == {}
    out = await hook(pre_tool_use("mcp__triage__check_consent", {"email": "a@example.com"}), None, None)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "not in the enricher's tool list" in log.attempts[0].reason


async def test_other_hook_events_get_no_opinion():
    hook = make_block_hook(SafetyLog(), agent="t")
    assert await hook({"hook_event_name": "PostToolUse", "tool_name": "send_email"}, None, None) == {}


async def test_module_level_hook_uses_the_default_log():
    before = len(safety.DEFAULT_SAFETY_LOG)
    out = await safety.block_send_hook(pre_tool_use("send_email"), None, None)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert len(safety.DEFAULT_SAFETY_LOG) == before + 1


def test_safety_log_writes_jsonl_without_the_body(tmp_path):
    log = SafetyLog(path=tmp_path / "blocked.jsonl")
    log.record(BlockedAttempt(at="2026-11-06T00:00:00Z", agent="t", tool_name="send_email", reason="r", input_keys=["body", "to"]))
    rows = [json.loads(line) for line in (tmp_path / "blocked.jsonl").read_text().splitlines()]
    assert rows[0]["tool_name"] == "send_email" and rows[0]["input_keys"] == ["body", "to"]
    assert "hi" not in (tmp_path / "blocked.jsonl").read_text()


# -- synthetic contacts only -------------------------------------------------------------


def test_assert_synthetic_accepts_example_com_only():
    assert assert_synthetic("Ada.Test01@Example.com") == "ada.test01@example.com"
    for bad in ("real.person@company.com", "someone@example.org", "@example.com", "", None, "x@notexample.com"):
        with pytest.raises(SafetyViolation):
            assert_synthetic(bad)


def test_classify_is_pure():
    assert classify_tool_call("write_note", {"contact_id": "1", "body": "x"}) is None
    assert classify_tool_call("send_note", {}) is not None
