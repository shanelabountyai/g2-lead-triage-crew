"""Model calls (D-10, D-11, D-16).

`AgentSdkCaller` runs one agent in one Claude Agent SDK session (`claude_agent_sdk.query`): its own system prompt,
its own context, `tools=[]` (no built-ins), `allowed_tools` = the agent's list, the in-process `triage` MCP server,
the D-7 PreToolUse hook, structured output. The answer arrives parsed in `ResultMessage.structured_output`, usage
in `ResultMessage.usage`.

`RecordedCaller` answers from `fixtures/recorded-responses.json` and makes no network call. A recorded entry may carry
`tool_attempts`; the caller pushes each through the same hook the SDK would, and runs the allowed ones against the
same handlers, so the fixture path exercises the tools and the hook end to end. `RecordingCaller` wraps a real
caller and saves what it got, so the first live run (`triage run --fixtures --record`) replaces the hand-made file.
"""

from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from triage.models import FIXTURES_DIR
from triage.prompts import AgentSpec
from triage.tools import ToolHandlers

RECORDED_FILE = FIXTURES_DIR / "recorded-responses.json"

Hook = Callable[[dict[str, Any], str | None, Any], Awaitable[dict[str, Any]]]


class ModelCallError(RuntimeError):
    """The model did not return usable JSON for the agent's schema."""


@dataclass
class Session:
    """What one agent call needs besides the prompt: the lead it is about, the hook and the tool handlers."""

    lead_id: str
    hook: Hook
    handlers: ToolHandlers


@dataclass
class CallResult:
    agent: str
    model: str
    parsed: dict[str, Any]
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    sdk_cost_usd: float | None = None
    stop_reason: str | None = None
    duration_ms: int | None = None
    tool_calls: list[str] = field(default_factory=list)
    tool_attempts: list[dict[str, Any]] = field(default_factory=list)
    blocked: int = 0
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def billed_input_tokens(self) -> int:
        """Fresh input plus cache writes and reads, counted at the input price: an upper bound on purpose."""
        return self.input_tokens + self.cache_creation_tokens + self.cache_read_tokens


class ModelCaller(Protocol):
    name: str
    measured: bool  # True when the usage numbers are real

    async def call(self, spec: AgentSpec, user_text: str, session: Session) -> CallResult: ...


# ---------------------------------------------------------------- the real thing


class AgentSdkCaller:
    name = "claude-agent-sdk"
    measured = True

    def __init__(self, max_budget_usd: float = 10.0) -> None:
        self.max_budget_usd = max_budget_usd

    def options(self, spec: AgentSpec, session: Session) -> Any:
        from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

        from triage.tools import build_tool_server

        return ClaudeAgentOptions(
            model=spec.model,
            system_prompt=spec.system_prompt(),
            tools=[],
            allowed_tools=list(spec.tools),
            mcp_servers={"triage": build_tool_server(session.handlers)},
            strict_mcp_config=True,
            permission_mode="dontAsk",
            setting_sources=[],
            max_turns=spec.max_turns,
            effort=spec.effort,  # type: ignore[arg-type]
            output_format={"type": "json_schema", "schema": spec.schema},
            max_budget_usd=self.max_budget_usd,
            hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[session.hook], on_failure="block")]},
        )

    async def call(self, spec: AgentSpec, user_text: str, session: Session) -> CallResult:
        from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock, query

        options = self.options(spec, session)
        started = time.monotonic()
        result: ResultMessage | None = None
        text_parts: list[str] = []
        tool_calls: list[str] = []
        tool_attempts: list[dict[str, Any]] = []
        model_seen = spec.model
        async for message in query(prompt=user_text, options=options):
            if isinstance(message, AssistantMessage):
                model_seen = message.model or model_seen
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
                    elif isinstance(block, ToolUseBlock):
                        tool_calls.append(block.name)
                        tool_attempts.append({"name": block.name, "input": dict(block.input or {})})
            elif isinstance(message, ResultMessage):
                result = message
        duration_ms = int((time.monotonic() - started) * 1000)
        if result is None:
            raise ModelCallError(f"{spec.name}: the SDK returned no result message")
        if result.is_error:
            raise ModelCallError(f"{spec.name}: SDK error {result.subtype} status={result.api_error_status} {result.errors or ''}")
        parsed = result.structured_output
        if not isinstance(parsed, dict):
            parsed = parse_json((text_parts[-1] if text_parts else "") or (result.result or ""), spec.name)
        usage = result.usage or {}
        return CallResult(
            agent=spec.name, model=model_seen, parsed=parsed,
            input_tokens=int(usage.get("input_tokens", 0)), output_tokens=int(usage.get("output_tokens", 0)),
            cache_read_tokens=int(usage.get("cache_read_input_tokens", 0)), cache_creation_tokens=int(usage.get("cache_creation_input_tokens", 0)),
            sdk_cost_usd=result.total_cost_usd, stop_reason=result.stop_reason, duration_ms=duration_ms, tool_calls=tool_calls,
            tool_attempts=tool_attempts, blocked=len(result.permission_denials or []),
            raw={"usage": usage, "model_usage": result.model_usage, "num_turns": result.num_turns, "session_id": result.session_id},
        )


def parse_json(text: str, agent: str) -> dict[str, Any]:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("{"):]
    try:
        out, _ = json.JSONDecoder().raw_decode(t)  # first object only; models sometimes repeat it
    except json.JSONDecodeError as e:
        raise ModelCallError(f"{agent}: response is not JSON ({e}): {t[:200]!r}") from e
    if not isinstance(out, dict):
        raise ModelCallError(f"{agent}: response JSON is not an object")
    return out


# ---------------------------------------------------------------- recorded responses (no key)


class RecordedCaller:
    """Answers each (agent, lead) from a file. `measured` is True only when the file says it was recorded live."""

    name = "recorded"
    measured = False

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or RECORDED_FILE
        doc = json.loads(self.path.read_text(encoding="utf-8"))
        self.about: str = str(doc.get("_about", ""))
        self.recorded_live: bool = bool(doc.get("recorded_live", False))
        self.responses: dict[str, dict[str, Any]] = {k: v for k, v in doc.get("responses", {}).items()}
        self.measured = self.recorded_live

    async def call(self, spec: AgentSpec, user_text: str, session: Session) -> CallResult:
        rec = self.responses.get(f"{spec.name}:{session.lead_id}")
        if rec is None:
            raise ModelCallError(f"{spec.name}: no recorded response for {session.lead_id} in {self.path.name}")
        tool_calls: list[str] = []
        blocked = 0
        # Replay the tool attempts through the same hook the SDK would call, then the same handlers.
        for i, attempt in enumerate(rec.get("tool_attempts") or []):
            name, args = str(attempt["name"]), dict(attempt.get("input") or {})
            decision = await session.hook({"hook_event_name": "PreToolUse", "session_id": f"recorded-{session.lead_id}", "tool_name": name,
                                           "tool_input": args, "tool_use_id": f"toolu_rec_{spec.name}_{i}"}, None, None)
            if decision.get("hookSpecificOutput", {}).get("permissionDecision") == "deny":
                blocked += 1
                continue
            tool_calls.append(name)
            short = name.split("__")[-1]
            handler = getattr(session.handlers, short, None)
            if handler is not None:
                await handler(args)
        usage = rec.get("usage") or {}
        return CallResult(
            agent=spec.name, model=str(rec.get("model") or spec.model), parsed=dict(rec["response"]),
            input_tokens=int(usage.get("input_tokens", 0)), output_tokens=int(usage.get("output_tokens", 0)),
            cache_read_tokens=int(usage.get("cache_read_input_tokens", 0)), cache_creation_tokens=int(usage.get("cache_creation_input_tokens", 0)),
            sdk_cost_usd=rec.get("sdk_cost_usd"), stop_reason=str(rec.get("stop_reason") or "recorded"), duration_ms=0,
            tool_calls=tool_calls, tool_attempts=list(rec.get("tool_attempts") or []), blocked=blocked, raw={"recorded_from": self.path.name},
        )


class RecordingCaller:
    """Wraps a real caller and writes every response to `path` in RecordedCaller's format."""

    name = "recording"
    measured = True

    def __init__(self, inner: ModelCaller, path: Path | None = None) -> None:
        self.inner = inner
        self.path = path or RECORDED_FILE
        self.doc: dict[str, Any] = {
            "_about": "Recorded live responses of the four G2·C agents on fixtures/leads.json, saved by "
                      "`triage run --fixtures --record`. Replayed by RecordedCaller when no ANTHROPIC_API_KEY is present.",
            "recorded_live": True,
            "recorded_at": None,
            "responses": {},
        }

    async def call(self, spec: AgentSpec, user_text: str, session: Session) -> CallResult:
        r = await self.inner.call(spec, user_text, session)
        self.doc["recorded_at"] = datetime.now(UTC).isoformat(timespec="seconds")
        self.doc["responses"][f"{spec.name}:{session.lead_id}"] = {
            "model": r.model, "response": r.parsed, "stop_reason": r.stop_reason, "sdk_cost_usd": r.sdk_cost_usd,
            "usage": {"input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
                      "cache_read_input_tokens": r.cache_read_tokens, "cache_creation_input_tokens": r.cache_creation_tokens},
            "tool_attempts": r.tool_attempts,
            "user_text_chars": len(user_text),
        }
        self.path.write_text(json.dumps(self.doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return r


def caller_from_env(record: bool = False, cap_usd: float = 10.0, recorded_path: Path | None = None) -> ModelCaller:
    import os

    if os.environ.get("ANTHROPIC_API_KEY"):
        live: ModelCaller = AgentSdkCaller(max_budget_usd=cap_usd)
        return RecordingCaller(live, recorded_path) if record else live
    return RecordedCaller(recorded_path)
