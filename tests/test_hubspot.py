"""C3: HubSpot behind an interface (D-8). The fake is what the crew runs on; the real client is shape-tested only."""

import json

import httpx
import pytest

from triage import hubspot as hs
from triage.hubspot import FakeHubSpot, HubSpotClient, RealHubSpot, client_from_env
from triage.models import Lead, LeadProperties
from triage.safety import SafetyViolation


def test_interface_has_no_send_and_no_deal_method():
    names = {n for n in dir(HubSpotClient) if not n.startswith("_")}
    assert names == {"get_contact", "find_contacts", "create_note", "list_notes"}
    for cls in (FakeHubSpot, RealHubSpot):
        public = [n for n in dir(cls) if not n.startswith("_")]
        assert not any("send" in n.lower() or "deal" in n.lower() or "mail" in n.lower() for n in public), (cls, public)


def test_fake_round_trips_contacts_and_notes(hubspot):
    c = hubspot.get_contact("hs-1001")
    assert c is not None and c.email == "ada.test01@example.com"
    assert c.as_lead().properties.li_tool_role == "executive-sponsor"
    assert hubspot.get_contact("hs-9999") is None
    n = hubspot.create_note("hs-1001", "Score 92 — good fit", kind="triage")
    d = hubspot.create_note("hs-1001", "DRAFT — not sent\nSubject: x", kind="draft")
    assert [x.id for x in hubspot.list_notes("hs-1001")] == [n.id, d.id]
    assert hubspot.list_notes("hs-1002") == []


def test_fake_finds_by_email_and_by_name_and_company_oldest_first(hubspot):
    assert [c.id for c in hubspot.find_contacts(email="ADA.test01@example.com")] == ["hs-1001"]
    ids = [c.id for c in hubspot.find_contacts(firstname="Tam", lastname="Testperson", company="Example Corp")]
    assert ids == ["hs-1019", "hs-1020"]
    assert hubspot.find_contacts(email="nobody@example.com") == []


def test_fake_refuses_a_note_on_a_non_synthetic_contact():
    fake = FakeHubSpot()
    fake.add_contact(Lead(id="x1", created_at="2026-11-06T00:00:00Z", properties=LeadProperties(email="real.person@company.com")))
    with pytest.raises(SafetyViolation):
        fake.create_note("x1", "hello")
    with pytest.raises(SafetyViolation):
        fake.create_note("missing", "hello")
    assert fake.notes == []


def test_client_from_env_is_the_fake_without_a_token():
    assert isinstance(client_from_env(), FakeHubSpot)


def test_real_client_refuses_to_start_without_a_token():
    with pytest.raises(RuntimeError):
        RealHubSpot()


class Recorder:
    """A mock transport: records requests, answers from a script, never touches the network."""

    def __init__(self, contacts: dict[str, dict]):
        self.requests: list[httpx.Request] = []
        self.contacts = contacts

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.method == "GET" and path.startswith("/crm/v3/objects/contacts/"):
            cid = path.rsplit("/", 1)[-1]
            if cid not in self.contacts:
                return httpx.Response(404, json={"status": "error"})
            return httpx.Response(200, json={"id": cid, "properties": self.contacts[cid]})
        if request.method == "POST" and path == "/crm/v3/objects/contacts/search":
            return httpx.Response(200, json={"results": [{"id": k, "properties": v} for k, v in self.contacts.items()]})
        if request.method == "POST" and path == "/crm/v3/objects/notes":
            return httpx.Response(201, json={"id": "7001", "createdAt": "2026-11-06T00:00:00Z"})
        return httpx.Response(500, json={"unexpected": path})


def test_real_client_builds_the_v3_requests_and_guards_the_write():
    rec = Recorder({"501": {"email": "ada.test01@example.com", "firstname": "Ada", "createdate": "2026-11-02T09:00:00Z", "numberofemployees": "640", "li_tool_people_gap": "7"}})
    client = RealHubSpot(token="test-token-not-real", transport=httpx.MockTransport(rec.handler))
    c = client.get_contact("501")
    assert c is not None and c.properties["numberofemployees"] == 640 and c.properties["li_tool_people_gap"] == 7
    assert rec.requests[0].headers["authorization"] == "Bearer test-token-not-real"
    assert "li_tool_role" in rec.requests[0].url.params["properties"]

    found = client.find_contacts(email="ada.test01@example.com")
    body = json.loads(rec.requests[1].content)
    assert body["filterGroups"][0]["filters"] == [{"propertyName": "email", "operator": "EQ", "value": "ada.test01@example.com"}]
    assert found[0].id == "501"

    note = client.create_note("501", "Score 92 — good fit")
    body = json.loads(rec.requests[-1].content)
    assert rec.requests[-1].url.path == "/crm/v3/objects/notes"
    assert body["properties"]["hs_note_body"] == "Score 92 — good fit"
    assert body["associations"][0]["types"][0]["associationTypeId"] == hs.RealHubSpot.NOTE_TO_CONTACT_ASSOCIATION_TYPE_ID
    assert note.id == "7001"
    assert client.get_contact("404") is None
    client.close()


def test_real_client_never_writes_a_note_to_a_real_address():
    rec = Recorder({"777": {"email": "real.person@company.com", "createdate": "2026-11-02T09:00:00Z"}})
    client = RealHubSpot(token="test-token-not-real", transport=httpx.MockTransport(rec.handler))
    with pytest.raises(SafetyViolation):
        client.create_note("777", "hello")
    assert all(r.url.path != "/crm/v3/objects/notes" for r in rec.requests)  # the write never left
    client.close()
