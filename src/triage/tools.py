"""The crew's tools: an in-process SDK MCP server (D-11).

Six read-only tools, each backed by the shared layer, the synthetic directory or the HubSpot interface. Nothing
here writes to HubSpot (the crew does that itself, in code, after the governance checks), and nothing here sends.
The handlers are plain async functions so the tests call them directly; `build_tool_server` wraps the same handlers
for a live agent session.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from triage.directory import Directory
from triage.hubspot import HubSpotClient
from triage.layer import Layer


@dataclass
class CrewContext:
    layer: Layer
    directory: Directory
    hubspot: HubSpotClient
    run_id: str


def _text(payload: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, default=str)}]}


class ToolHandlers:
    """The six handlers, bound to one crew context."""

    def __init__(self, ctx: CrewContext) -> None:
        self.ctx = ctx
        self.calls: list[str] = []

    async def lookup_company(self, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append("lookup_company")
        company, how = self.ctx.directory.lookup(args.get("name"))
        if company is None:
            return _text({"found": False, "how": how, "name": args.get("name")})
        return _text({"found": True, "how": how, "record": company.model_dump()})

    async def evaluate_fit(self, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append("evaluate_fit")
        item = {k: args.get(k) for k in ("role", "relationship", "company", "pilot_stage", "gap_at_least_6", "size_band")}
        out = self.ctx.layer.evaluate(item, run_id=self.ctx.run_id)
        return _text(out.model_dump(mode="json"))

    async def check_consent(self, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append("check_consent")
        out = self.ctx.layer.check_consent(email=args.get("email"), channel=str(args.get("channel") or "email"))
        return _text(out.model_dump(mode="json"))

    async def check_brand(self, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append("check_brand")
        out = self.ctx.layer.check_brand(str(args.get("text") or ""), channel=str(args.get("channel") or "email"))
        return _text(out.model_dump(mode="json"))

    async def check_claims(self, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append("check_claims")
        out = self.ctx.layer.check_claims(text=str(args.get("text") or ""))
        return _text(out.model_dump(mode="json"))

    async def find_duplicates(self, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append("find_duplicates")
        hs = self.ctx.hubspot
        seen: dict[str, dict[str, Any]] = {}
        email = args.get("email")
        if email:
            for c in hs.find_contacts(email=str(email)):
                seen[c.id] = {"id": c.id, "created_at": c.created_at, "matched_on": "email"}
        if args.get("firstname") and args.get("lastname") and args.get("company"):
            for c in hs.find_contacts(firstname=str(args["firstname"]), lastname=str(args["lastname"]), company=str(args["company"])):
                seen.setdefault(c.id, {"id": c.id, "created_at": c.created_at, "matched_on": "name+company"})
        # Only ids and dates leave this tool: no names, no emails (same rule as audience.consent).
        return _text({"candidates": sorted(seen.values(), key=lambda x: x["created_at"])})


def build_tool_server(handlers: ToolHandlers):
    """Wrap the handlers as an SDK MCP server named `triage` (tools appear as mcp__triage__<name>)."""
    from claude_agent_sdk import create_sdk_mcp_server, tool

    def obj(required: list[str], **props: str) -> dict[str, Any]:
        return {"type": "object", "properties": {k: {"type": "string", "description": v} for k, v in props.items()}, "required": required, "additionalProperties": False}

    specs = [
        ("lookup_company", "Look a company up in the synthetic directory by name. Returns the record or found=false.",
         obj(["name"], name="The company name as the lead gave it.")),
        ("evaluate_fit", "Preview the shared evaluation rubric g2_lead_fit_v1 on a normalized profile.",
         obj([], role="executive-sponsor|pilot-lead|team-member|outside-advisor", relationship="buyer|vendor|student|advisor", company="Identified company name or empty",
             pilot_stage="The diagnostic's stage id", gap_at_least_6="yes|no", size_band="1-10|11-50|51-200|201-1000|1001-5000|5000+")),
        ("check_consent", "Ask the shared layer whether this contact may be reached on a channel (default email).",
         obj(["email"], email="The contact's email", channel="email|linkedin|sms|phone")),
        ("check_brand", "Check text against the shared brand policy on a channel (default email).",
         obj(["text"], text="The text to check", channel="email|linkedin|digest|post_angle|other")),
        ("check_claims", "Check every number in the text against the shared claims registry.", obj(["text"], text="The text to check")),
        ("find_duplicates", "Find older contacts that look like the same person. Returns ids and dates only.",
         obj([], email="Email to match exactly", firstname="First name", lastname="Last name", company="Company")),
    ]
    tools = []
    for name, description, schema in specs:
        fn = getattr(handlers, name)
        tools.append(tool(name, description, schema)(fn))
    return create_sdk_mcp_server("triage", "0.1.0", tools)
