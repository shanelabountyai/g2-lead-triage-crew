"""The trigger: a FastAPI endpoint for HubSpot's `contact.creation` webhook (D-3, D-18).

HubSpot posts a JSON array of events; each carries `objectId` (the contact id), `subscriptionType`, `portalId`,
`occurredAt`, `eventId`. The app fetches the contact through the HubSpot interface (the fake in local replay, the
real client when a token is set) and runs the crew. It acknowledges at once (200, status `queued`) and triages in a
background task, so HubSpot's timeout never triggers a retry; an event already seen (same `eventId`, or same contact and
subscription type) is answered 200 `duplicate_event` and not rerun (D-22). `?wait=true` (local replay) triages inline
and answers with the outcome. With `HUBSPOT_CLIENT_SECRET` set the
v3 signature is verified. Unsigned mode is allowed only in fixture/fake mode (fake HubSpot and the recorded model): with a
real HubSpot client or a live model key and no secret the app refuses to start, and a request that reaches a live crew
without a secret is 401 (D-21).
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import os
import time
from collections.abc import Callable
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Request, Response
from fastapi.responses import JSONResponse

from triage.crew import Crew

SIGNATURE_HEADER = "X-HubSpot-Signature-v3"
TIMESTAMP_HEADER = "X-HubSpot-Request-Timestamp"
MAX_SKEW_MS = 5 * 60 * 1000


def sign_v3(secret: str, method: str, uri: str, body: bytes, timestamp_ms: int) -> str:
    """HubSpot v3: base64(HMAC-SHA256(secret, method + uri + body + timestamp))."""
    msg = f"{method.upper()}{uri}".encode() + body + str(timestamp_ms).encode()
    return base64.b64encode(hmac.new(secret.encode(), msg, hashlib.sha256).digest()).decode()


def verify_v3(secret: str, request_method: str, request_uri: str, body: bytes, timestamp: str | None, signature: str | None, now_ms: int | None = None) -> tuple[bool, str]:
    if not timestamp or not signature:
        return False, "missing signature or timestamp header"
    try:
        ts = int(timestamp)
    except ValueError:
        return False, "timestamp is not an integer"
    now = now_ms if now_ms is not None else int(time.time() * 1000)
    if abs(now - ts) > MAX_SKEW_MS:
        return False, "timestamp outside the 5-minute window"
    expected = sign_v3(secret, request_method, request_uri, body, ts)
    if not hmac.compare_digest(expected, signature):
        return False, "signature mismatch"
    return True, "ok"


class UnsignedLiveConfig(RuntimeError):
    """A real HubSpot client or a live model key is configured but no HUBSPOT_CLIENT_SECRET: refuse to start (D-21)."""


def crew_is_live(crew: Crew) -> bool:
    """Live = anything that reaches outside the process: the real HubSpot client or a live model caller."""
    return crew.hubspot.name == "real" or crew.caller.name != "recorded"


def env_is_live() -> bool:
    return bool(os.environ.get("HUBSPOT_PRIVATE_APP_TOKEN") or os.environ.get("ANTHROPIC_API_KEY"))


def create_app(crew: Crew | Callable[[], Crew], *, client_secret: str | None = None, public_url: str | None = None,
               live: bool | None = None) -> FastAPI:
    """`crew` may be a factory: it is then built on the first request, in the server's own thread and loop, because
    the layer's SQLite connection (G0 storage, not thread-safe by design) must live where the requests run.

    `live` says whether the crew will reach a real HubSpot or a live model; by default it is read from the crew (when
    given one) or the environment. Live without a secret fails closed (D-21)."""
    secret = client_secret if client_secret is not None else os.environ.get("HUBSPOT_CLIENT_SECRET")
    if live is None:
        live = crew_is_live(crew) if isinstance(crew, Crew) else env_is_live()
    if live and not secret:
        raise UnsignedLiveConfig("a real HubSpot client or a live model key is configured but HUBSPOT_CLIENT_SECRET is not set; "
                                 "refusing to serve unsigned webhooks (unsigned mode is for fixture/fake mode only, D-21)")
    app = FastAPI(title="Lead Triage Crew (G2·C) webhook", version="0.1.0")
    app.state.crew = crew if isinstance(crew, Crew) else None
    app.state.events = {}  # idempotency store (D-22): event key -> outcome record; in memory, lost on restart
    app.state.lock = asyncio.Lock()
    factory = None if isinstance(crew, Crew) else crew

    def get_crew() -> Crew:
        if app.state.crew is None:
            app.state.crew = factory()  # type: ignore[misc]
        return app.state.crew

    @app.get("/health")
    async def health() -> dict[str, Any]:
        crew = get_crew()
        h = crew.layer.health()
        cost, calls = crew.run_cost()
        return {"status": h.status, "layer": {"db_path": h.db_path, "rubrics": h.rubrics, "contracts": h.contracts}, "run_id": crew.run_id,
                "hubspot": crew.hubspot.name, "caller": crew.caller.name, "measured": crew.caller.measured, "run_cost_usd": cost, "layer_calls": calls,
                "signature_check": bool(secret), "leads_processed": len(crew.results), "blocked_attempts": len(crew.blocked),
                "events_seen": len({id(v) for v in app.state.events.values()})}

    @app.post("/hubspot/webhook")
    async def webhook(request: Request, response: Response, background: BackgroundTasks) -> Any:
        crew = get_crew()
        body = await request.body()
        if secret:
            uri = (public_url.rstrip("/") + request.url.path) if public_url else str(request.url)
            ok, why = verify_v3(secret, request.method, uri, body, request.headers.get(TIMESTAMP_HEADER), request.headers.get(SIGNATURE_HEADER))
            if not ok:
                return JSONResponse({"error": f"signature: {why}"}, status_code=401)
            response.headers["X-Triage-Signature"] = "verified"
        elif crew_is_live(crew):  # belt and braces: the built crew is live although startup was told it was not
            return JSONResponse({"error": "signature: HUBSPOT_CLIENT_SECRET is not set and the crew is live; unsigned requests are refused (D-21)"},
                                status_code=401)
        else:
            response.headers["X-Triage-Signature"] = "skipped (fixture/fake mode, no HUBSPOT_CLIENT_SECRET)"
        try:
            events = await request.json()
        except ValueError:
            return JSONResponse({"error": "body is not JSON"}, status_code=400)
        if isinstance(events, dict):
            events = [events]
        if not isinstance(events, list):
            return JSONResponse({"error": "body must be an array of events"}, status_code=400)
        wait = request.query_params.get("wait", "").lower() in ("1", "true", "yes")
        processed: list[dict[str, Any]] = []
        queued: list[tuple[str, dict[str, Any]]] = []
        for ev in events:
            if not isinstance(ev, dict):
                continue
            sub = str(ev.get("subscriptionType") or "")
            oid = str(ev.get("objectId") or "")
            if sub != "contact.creation":
                processed.append({"objectId": oid, "subscriptionType": sub, "status": "ignored"})
                continue
            keys = event_keys(ev)
            seen = next((app.state.events[k] for k in keys if k in app.state.events), None)
            if seen is not None:  # a HubSpot retry (same eventId) or a second event for the same contact: no rerun, no new note
                processed.append({"objectId": oid, "eventId": ev.get("eventId"), "status": "duplicate_event", "first": dict(seen)})
                continue
            record: dict[str, Any] = {"objectId": oid, "eventId": ev.get("eventId"), "status": "queued"}
            for k in keys:  # claimed before processing starts, so a retry that lands mid-run is a duplicate too
                app.state.events[k] = record
            queued.append((oid, record))
            if wait:
                processed.append(await process(crew, oid, record))
            else:
                processed.append(dict(record))
        if not wait:
            for oid, record in queued:  # runs after the response is sent
                background.add_task(process, crew, oid, record)
        return {"run_id": crew.run_id, "processed": processed}

    async def process(crew: Crew, oid: str, record: dict[str, Any]) -> dict[str, Any]:
        """Run one contact through the crew; the outcome is written into the idempotency record."""
        async with app.state.lock:  # one lead at a time: the crew and its SQLite layer are not built for concurrent leads
            record["status"] = "running"
            contact = crew.hubspot.get_contact(oid)
            if contact is None:
                record.update(status="unknown_contact")
                return dict(record)
            if crew.over_cap:
                record.update(status="over_cap")
                return dict(record)
            try:
                r = await crew.run_lead(contact.as_lead())
            except Exception as e:  # the crew already logged; the webhook must answer HubSpot
                record.update(status="error", error=type(e).__name__, detail=str(e)[:200])
                return dict(record)
            record.update(status="triaged", band=r.band, score=r.score, note_id=r.note_id, draft_note_id=r.draft_note_id,
                          workers_called=[d.worker for d in r.decisions if d.called], blocked_attempts=r.blocked_attempts)
            return dict(record)

    return app


def event_keys(ev: dict[str, Any]) -> list[str]:
    """Idempotency keys for one event (D-22): HubSpot's `eventId` (stable across its retries) and, as a fallback that also
    catches a second event for the same contact, `<objectId>:<subscriptionType>`."""
    keys = []
    if ev.get("eventId") not in (None, ""):
        keys.append(f"event:{ev['eventId']}")
    keys.append(f"object:{ev.get('objectId')}:{ev.get('subscriptionType')}")
    return keys


def event_for(contact_id: str, portal_id: int = 0, occurred_at_ms: int | None = None) -> dict[str, Any]:
    """One HubSpot-shaped contact.creation event (what `triage replay` posts)."""
    now = occurred_at_ms if occurred_at_ms is not None else int(time.time() * 1000)
    return {"eventId": abs(hash((contact_id, now))) % 10**12, "subscriptionId": 1, "portalId": portal_id, "appId": 1, "occurredAt": now,
            "subscriptionType": "contact.creation", "attemptNumber": 0, "objectId": contact_id, "changeSource": "FORM", "changeFlag": "NEW"}
