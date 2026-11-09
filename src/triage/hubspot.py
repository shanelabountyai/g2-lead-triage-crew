"""HubSpot behind an interface (D-8).

`HubSpotClient` is the whole surface the crew may touch: read a contact, find contacts, write a note, list notes.
There is no send method and no deal method, so "nothing is sent" and "no deal-stage edits" hold by construction.
Every write goes through `safety.assert_synthetic` first: notes land only on `@example.com` test contacts.

`FakeHubSpot` is in memory and is what every test and the fixture run use. `RealHubSpot` talks to the v3 API with a
private-app token from `HUBSPOT_PRIVATE_APP_TOKEN`; it is implemented and request-shape tested with a mock transport,
and it is never exercised live in this build (no token; the kickoff forbids live HubSpot calls). The hand steps that
use it are in NEXT.md.
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, Field

from triage.models import Lead, LeadProperties
from triage.safety import SafetyViolation, assert_synthetic

NoteKind = Literal["triage", "draft"]

CONTACT_PROPERTIES = [
    "email", "firstname", "lastname", "company", "jobtitle", "industry", "numberofemployees", "website",
    "li_tool_name", "li_tool_role", "li_tool_pilot_stage", "li_tool_result", "li_tool_people_gap", "li_tool_process_gap",
    "li_tool_technology_gap", "li_tool_lead_grade", "message", "createdate",
]


class Contact(BaseModel):
    id: str
    created_at: str
    properties: dict[str, Any] = Field(default_factory=dict)

    @property
    def email(self) -> str:
        return str(self.properties.get("email") or "")

    def as_lead(self) -> Lead:
        return Lead(id=self.id, created_at=self.created_at, properties=LeadProperties.model_validate(self.properties))


class Note(BaseModel):
    id: str
    contact_id: str
    body: str
    kind: NoteKind
    created_at: str


class HubSpotClient(Protocol):
    """Read contacts, write notes. Nothing else exists."""

    name: str

    def get_contact(self, contact_id: str) -> Contact | None: ...

    def find_contacts(self, *, email: str | None = None, firstname: str | None = None, lastname: str | None = None,
                      company: str | None = None) -> list[Contact]: ...

    def create_note(self, contact_id: str, body: str, kind: NoteKind = "triage") -> Note: ...

    def list_notes(self, contact_id: str) -> list[Note]: ...


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


# -- the fake --------------------------------------------------------------------------


class FakeHubSpot:
    name = "fake"

    def __init__(self) -> None:
        self.contacts: dict[str, Contact] = {}
        self.notes: list[Note] = []
        self._next_note = 1

    @classmethod
    def seeded(cls, leads: list[Lead]) -> FakeHubSpot:
        fake = cls()
        for lead in leads:
            fake.add_contact(lead)
        return fake

    def add_contact(self, lead: Lead) -> Contact:
        props = lead.properties.model_dump()
        c = Contact(id=lead.id, created_at=lead.created_at, properties=props)
        self.contacts[c.id] = c
        return c

    def get_contact(self, contact_id: str) -> Contact | None:
        return self.contacts.get(contact_id)

    def find_contacts(self, *, email: str | None = None, firstname: str | None = None, lastname: str | None = None,
                      company: str | None = None) -> list[Contact]:
        out = []
        for c in self.contacts.values():
            if email is not None and c.email.lower() != email.lower():
                continue
            if firstname is not None and _norm(c.properties.get("firstname")) != _norm(firstname):
                continue
            if lastname is not None and _norm(c.properties.get("lastname")) != _norm(lastname):
                continue
            if company is not None and _norm(c.properties.get("company")) != _norm(company):
                continue
            out.append(c)
        return sorted(out, key=lambda c: c.created_at)

    def create_note(self, contact_id: str, body: str, kind: NoteKind = "triage") -> Note:
        c = self.contacts.get(contact_id)
        if c is None:
            raise SafetyViolation(f"no contact {contact_id}; a note needs a known synthetic contact")
        assert_synthetic(c.email)
        note = Note(id=f"note-{self._next_note}", contact_id=contact_id, body=body, kind=kind, created_at=_now())
        self._next_note += 1
        self.notes.append(note)
        return note

    def list_notes(self, contact_id: str) -> list[Note]:
        return [n for n in self.notes if n.contact_id == contact_id]


# -- the real one (never exercised in this build) ------------------------------------------


class RealHubSpot:
    """Thin v3 client. Reads: contacts get/search. Writes: notes only, on synthetic contacts only.

    The constructor needs the token in the environment; the tests pass a mock transport and assert the request
    shapes. No test, and no part of this run, makes a network call.
    """

    name = "real"
    BASE = "https://api.hubapi.com"
    NOTE_TO_CONTACT_ASSOCIATION_TYPE_ID = 202  # HubSpot-defined: note → contact

    def __init__(self, token: str | None = None, transport: httpx.BaseTransport | None = None, timeout: float = 15.0) -> None:
        tok = token or os.environ.get("HUBSPOT_PRIVATE_APP_TOKEN")
        if not tok:
            raise RuntimeError("HUBSPOT_PRIVATE_APP_TOKEN is not set; the real HubSpot client cannot start. Use FakeHubSpot.")
        self._client = httpx.Client(base_url=self.BASE, headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                                    transport=transport, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def _contact(self, obj: dict[str, Any]) -> Contact:
        props = dict(obj.get("properties") or {})
        for k in ("numberofemployees", "li_tool_people_gap", "li_tool_process_gap", "li_tool_technology_gap"):
            if props.get(k) not in (None, ""):
                try:
                    props[k] = int(props[k])
                except (TypeError, ValueError):
                    props[k] = None
            else:
                props[k] = None
        for k in list(props):
            if props[k] == "":
                props[k] = None
        return Contact(id=str(obj["id"]), created_at=str(props.get("createdate") or obj.get("createdAt") or _now()), properties=props)

    def get_contact(self, contact_id: str) -> Contact | None:
        r = self._client.get(f"/crm/v3/objects/contacts/{contact_id}", params={"properties": ",".join(CONTACT_PROPERTIES)})
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return self._contact(r.json())

    def find_contacts(self, *, email: str | None = None, firstname: str | None = None, lastname: str | None = None,
                      company: str | None = None) -> list[Contact]:
        filters = [{"propertyName": k, "operator": "EQ", "value": v} for k, v in
                   (("email", email), ("firstname", firstname), ("lastname", lastname), ("company", company)) if v]
        if not filters:
            return []
        r = self._client.post("/crm/v3/objects/contacts/search", json={"filterGroups": [{"filters": filters}], "properties": CONTACT_PROPERTIES,
                                                                       "sorts": [{"propertyName": "createdate", "direction": "ASCENDING"}], "limit": 20})
        r.raise_for_status()
        return [self._contact(o) for o in r.json().get("results", [])]

    def create_note(self, contact_id: str, body: str, kind: NoteKind = "triage") -> Note:
        c = self.get_contact(contact_id)
        if c is None:
            raise SafetyViolation(f"no contact {contact_id}; a note needs a known synthetic contact")
        assert_synthetic(c.email)  # the write guard: synthetic test contacts only (D-7)
        payload = {
            "properties": {"hs_note_body": body, "hs_timestamp": _now()},
            "associations": [{"to": {"id": contact_id}, "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": self.NOTE_TO_CONTACT_ASSOCIATION_TYPE_ID}]}],
        }
        r = self._client.post("/crm/v3/objects/notes", json=payload)
        r.raise_for_status()
        obj = r.json()
        return Note(id=str(obj["id"]), contact_id=contact_id, body=body, kind=kind, created_at=str(obj.get("createdAt") or _now()))

    def list_notes(self, contact_id: str) -> list[Note]:
        r = self._client.get(f"/crm/v4/objects/contacts/{contact_id}/associations/notes")
        r.raise_for_status()
        ids = [str(x["toObjectId"]) for x in r.json().get("results", [])]
        if not ids:
            return []
        r = self._client.post("/crm/v3/objects/notes/batch/read", json={"inputs": [{"id": i} for i in ids], "properties": ["hs_note_body", "hs_timestamp"]})
        r.raise_for_status()
        out = []
        for o in r.json().get("results", []):
            body = str(o.get("properties", {}).get("hs_note_body") or "")
            out.append(Note(id=str(o["id"]), contact_id=contact_id, body=body, kind="draft" if body.startswith("DRAFT") else "triage",
                            created_at=str(o.get("properties", {}).get("hs_timestamp") or o.get("createdAt") or _now())))
        return out


def client_from_env() -> HubSpotClient:
    """Real only when a token is present; the fake otherwise. The crew never guesses."""
    if os.environ.get("HUBSPOT_PRIVATE_APP_TOKEN"):
        return RealHubSpot()
    return FakeHubSpot()
