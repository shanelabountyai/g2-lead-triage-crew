"""Safety invariants (D-7). These landed, with tests, before any code path could reach an external system.

1. Draft only: nothing is ever sent. `block_send_hook` is a Claude Agent SDK `PreToolUse` hook that denies any
   tool call that looks like a send, an email-out or a deal-stage edit, and logs the attempt (PRD AC 4). It is
   attached to every agent session; the forced-send test calls the same function.
2. HubSpot writes go only to notes on synthetic test contacts: `assert_synthetic` refuses any email that is not on
   `example.com`, and every HubSpot client calls it before a write.
3. No deal-stage edits: the HubSpot interface has no deal method (hubspot.py), and the hook denies any tool input
   that names a deal stage or a deals endpoint.

The hook is defense in depth: no send tool exists in the crew's tool lists in the first place (prompts.py).
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SYNTHETIC_DOMAIN = "@example.com"


class SafetyViolation(RuntimeError):
    """An invariant was about to be broken. Raised, never swallowed."""


def assert_synthetic(email: str | None) -> str:
    """Return the lower-cased email if it is a synthetic test address; raise otherwise (D-7, D-8)."""
    e = (email or "").strip().lower()
    if not e.endswith(SYNTHETIC_DOMAIN) or e == SYNTHETIC_DOMAIN:
        raise SafetyViolation(f"HubSpot writes go only to synthetic test contacts on {SYNTHETIC_DOMAIN}; refused a write for a contact that is not one.")
    return e


# -- what counts as a send ------------------------------------------------------------

# Tool names (case-insensitive) that mean "this leaves the building". Matched on the bare tool name and on the
# MCP-qualified form (mcp__<server>__<tool>).
SEND_NAME_PATTERNS = (
    r"(^|[_\-\.])send($|[_\-\.a-z])",   # send, send_email, sendEmail, gmail_send, single_send
    r"sendemail", r"sendmail", r"sendgrid", r"mailgun", r"smtp", r"gmail", r"outlook", r"postmark", r"ses_",
    r"single[-_]?send", r"transactional", r"deliver", r"publish", r"dispatch", r"email[_\-]?out", r"reply", r"forward",
)
# Input shapes that mean the same even when the tool name is innocent.
SEND_INPUT_URL_PATTERNS = (
    r"/marketing/v3/transactional", r"/marketing/v3/emails/.*/send", r"/single-send", r"/communication-preferences",
    r"gmail\.googleapis\.com", r"graph\.microsoft\.com/.*/sendMail", r"api\.sendgrid\.com", r"api\.mailgun\.net",
)
DEAL_PATTERNS = (r"dealstage", r"deal_stage", r"/crm/v3/objects/deals", r"hs_deal", r"pipeline_stage")

_send_name_re = re.compile("|".join(SEND_NAME_PATTERNS), re.IGNORECASE)
_send_url_re = re.compile("|".join(SEND_INPUT_URL_PATTERNS), re.IGNORECASE)
_deal_re = re.compile("|".join(DEAL_PATTERNS), re.IGNORECASE)


def _flatten(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):  # pragma: no cover
        return str(value)


def classify_tool_call(tool_name: str, tool_input: dict[str, Any] | None) -> str | None:
    """Why this call must be denied, or None when it is fine. Pure; no side effects."""
    name = tool_name or ""
    bare = name.split("__")[-1]
    if _send_name_re.search(bare) or _send_name_re.search(name):
        return f"tool '{name}' looks like a send or email-out; this crew is draft only"
    text = _flatten(tool_input or {})
    if _send_url_re.search(text):
        return f"tool '{name}' input targets a send endpoint; this crew is draft only"
    if _deal_re.search(bare) or _deal_re.search(text):
        return f"tool '{name}' would edit a deal or a deal stage; the crew never edits deals"
    inp = tool_input or {}
    if isinstance(inp, dict) and ({"to", "recipients", "recipient"} & {k.lower() for k in inp}) and ({"subject", "body", "html", "text"} & {k.lower() for k in inp}):
        return f"tool '{name}' input is shaped like an outgoing message (recipient + body); this crew is draft only"
    return None


# -- the log ---------------------------------------------------------------------------


@dataclass
class BlockedAttempt:
    at: str
    agent: str
    tool_name: str
    reason: str
    tool_use_id: str | None = None
    input_keys: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"at": self.at, "agent": self.agent, "tool_name": self.tool_name, "reason": self.reason,
                "tool_use_id": self.tool_use_id, "input_keys": self.input_keys}


class SafetyLog:
    """Append-only. In memory always; also a JSONL file under TRIAGE_RUN_LOG_DIR when set (never the input body:
    a draft that someone tried to send is still a draft, and must not leak into a log)."""

    def __init__(self, path: Path | None = None) -> None:
        d = os.environ.get("TRIAGE_RUN_LOG_DIR")
        self.path = path or (Path(d) / "blocked-attempts.jsonl" if d else None)
        self.attempts: list[BlockedAttempt] = []

    def record(self, attempt: BlockedAttempt) -> None:
        self.attempts.append(attempt)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(attempt.as_dict(), ensure_ascii=False) + "\n")

    def __len__(self) -> int:
        return len(self.attempts)


OnBlock = Callable[[BlockedAttempt], None]


# -- the hook ----------------------------------------------------------------------------


def make_block_hook(
    safety_log: SafetyLog,
    *,
    agent: str = "crew",
    allowed_tools: list[str] | None = None,
    on_block: OnBlock | None = None,
) -> Callable[[dict[str, Any], str | None, Any], Awaitable[dict[str, Any]]]:
    """Build the PreToolUse callback for one agent session.

    Denies (a) anything `classify_tool_call` flags and (b), when `allowed_tools` is given, any tool outside that
    list. Every denial is written to `safety_log` and handed to `on_block` (the crew uses it to write the
    observability row). Anything else returns {} — "no opinion" — so the SDK's own permission rules apply.
    The callback signature is the SDK's HookCallback: (input_data, tool_use_id, context) -> hook JSON output.
    """

    allowed = set(allowed_tools) if allowed_tools is not None else None

    async def hook(input_data: dict[str, Any], tool_use_id: str | None, context: Any) -> dict[str, Any]:
        if input_data.get("hook_event_name") not in (None, "PreToolUse"):
            return {}
        tool_name = str(input_data.get("tool_name") or "")
        tool_input = input_data.get("tool_input") or {}
        reason = classify_tool_call(tool_name, tool_input if isinstance(tool_input, dict) else {"value": tool_input})
        if reason is None and allowed is not None and tool_name not in allowed and tool_name != "StructuredOutput":  # SDK's own answer channel, no side effect
            reason = f"tool '{tool_name}' is not in the {agent}'s tool list ({sorted(allowed)})"
        if reason is None:
            return {}
        attempt = BlockedAttempt(
            at=datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            agent=agent, tool_name=tool_name, reason=reason, tool_use_id=tool_use_id or input_data.get("tool_use_id"),
            input_keys=sorted(tool_input.keys()) if isinstance(tool_input, dict) else [],
        )
        safety_log.record(attempt)
        if on_block is not None:
            on_block(attempt)
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"BLOCKED: {reason}. Logged.",
            },
        }

    hook.__name__ = f"block_send_hook_{agent}"
    return hook


# A module-level hook with the default log, for callers that have no crew context (and for the forced-send test).
DEFAULT_SAFETY_LOG = SafetyLog()
block_send_hook = make_block_hook(DEFAULT_SAFETY_LOG, agent="crew")
