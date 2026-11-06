"""The trigger: a FastAPI endpoint for HubSpot's `contact.creation` webhook (D-3, D-18).

HubSpot posts a JSON array of events; each carries `objectId` (the contact id), `subscriptionType`, `portalId`,
`occurredAt`, `eventId`. The app fetches the contact through the HubSpot interface (the fake in local replay, the
real client when a token is set), runs the crew, and answers with what it did. With `HUBSPOT_CLIENT_SECRET` set the
v3 signature is verified; without it (local replay) the check is skipped and said so in the response headers.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request, Response
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


def create_app(crew: Crew | Callable[[], Crew], *, client_secret: str | None = None, public_url: str | None = None) -> FastAPI:
    """`crew` may be a factory: it is then built on the first request, in the server's own thread and loop, because
    the layer's SQLite connection (G0 storage, not thread-safe by design) must live where the requests run."""
    app = FastAPI(title="Lead Triage Crew (G2·C) webhook", version="0.1.0")
    secret = client_secret if client_secret is not None else os.environ.get("HUBSPOT_CLIENT_SECRET")
    app.state.crew = crew if isinstance(crew, Crew) else None
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
                "signature_check": bool(secret), "leads_processed": len(crew.results), "blocked_attempts": len(crew.blocked)}

    @app.post("/hubspot/webhook")
    async def webhook(request: Request, response: Response) -> Any:
        crew = get_crew()
        body = await request.body()
        if secret:
            uri = (public_url.rstrip("/") + request.url.path) if public_url else str(request.url)
            ok, why = verify_v3(secret, request.method, uri, body, request.headers.get(TIMESTAMP_HEADER), request.headers.get(SIGNATURE_HEADER))
            if not ok:
                return JSONResponse({"error": f"signature: {why}"}, status_code=401)
            response.headers["X-Triage-Signature"] = "verified"
        else:
            response.headers["X-Triage-Signature"] = "skipped (no HUBSPOT_CLIENT_SECRET)"
        try:
            events = await request.json()
        except ValueError:
            return JSONResponse({"error": "body is not JSON"}, status_code=400)
        if isinstance(events, dict):
            events = [events]
        if not isinstance(events, list):
            return JSONResponse({"error": "body must be an array of events"}, status_code=400)
        processed: list[dict[str, Any]] = []
        for ev in events:
            if not isinstance(ev, dict):
                continue
            sub = str(ev.get("subscriptionType") or "")
            oid = str(ev.get("objectId") or "")
            if sub != "contact.creation":
                processed.append({"objectId": oid, "subscriptionType": sub, "status": "ignored"})
                continue
            contact = crew.hubspot.get_contact(oid)
            if contact is None:
                processed.append({"objectId": oid, "status": "unknown_contact"})
                continue
            if crew.over_cap:
                processed.append({"objectId": oid, "status": "over_cap"})
                continue
            try:
                r = await crew.run_lead(contact.as_lead())
            except Exception as e:  # the crew already logged; the webhook must answer HubSpot
                processed.append({"objectId": oid, "status": "error", "error": type(e).__name__, "detail": str(e)[:200]})
                continue
            processed.append({"objectId": oid, "status": "triaged", "band": r.band, "score": r.score, "note_id": r.note_id,
                              "draft_note_id": r.draft_note_id, "workers_called": [d.worker for d in r.decisions if d.called],
                              "blocked_attempts": r.blocked_attempts})
        return {"run_id": crew.run_id, "processed": processed}

    return app


def event_for(contact_id: str, portal_id: int = 0, occurred_at_ms: int | None = None) -> dict[str, Any]:
    """One HubSpot-shaped contact.creation event (what `triage replay` posts)."""
    now = occurred_at_ms if occurred_at_ms is not None else int(time.time() * 1000)
    return {"eventId": abs(hash((contact_id, now))) % 10**12, "subscriptionId": 1, "portalId": portal_id, "appId": 1, "occurredAt": now,
            "subscriptionType": "contact.creation", "attemptNumber": 0, "objectId": contact_id, "changeSource": "FORM", "changeFlag": "NEW"}
