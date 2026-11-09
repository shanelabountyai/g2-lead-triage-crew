"""C6: the webhook trigger (D-3, D-18), the replay script and the CLI."""

import json
import time

import httpx
import pytest

from triage import cli
from triage.crew import Crew
from triage.llm import RecordedCaller
from triage.models import load_leads
from triage.webhook import SIGNATURE_HEADER, TIMESTAMP_HEADER, create_app, event_for, sign_v3, verify_v3


@pytest.fixture
def crew(layer):
    return Crew.for_fixtures(layer=layer, run_id="g2c-web")


async def _client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")


async def test_contact_creation_event_runs_the_crew_and_writes_the_note(crew):
    app = create_app(crew, client_secret=None)
    async with await _client(app) as c:
        r = await c.post("/hubspot/webhook", json=[event_for("hs-1001"), event_for("hs-1004")])
        assert r.status_code == 200 and r.headers["X-Triage-Signature"].startswith("skipped")
        body = r.json()
        assert body["run_id"] == "g2c-web"
        assert body["processed"][0]["band"] == "good fit" and body["processed"][0]["draft_note_id"] is not None
        assert body["processed"][1]["band"] == "poor fit" and body["processed"][1]["draft_note_id"] is None
        assert [n.kind for n in crew.hubspot.list_notes("hs-1001")] == ["draft", "triage"]
        h = (await c.get("/health")).json()
        assert h["status"] == "ok" and h["leads_processed"] == 2 and h["signature_check"] is False and h["hubspot"] == "fake"


async def test_other_events_and_unknown_contacts_are_acknowledged_not_processed(crew):
    app = create_app(crew, client_secret=None)
    async with await _client(app) as c:
        r = await c.post("/hubspot/webhook", json=[{"subscriptionType": "deal.propertyChange", "objectId": 5}, event_for("hs-9999"), {"not": "an event"}])
        assert r.status_code == 200
        assert [p["status"] for p in r.json()["processed"]] == ["ignored", "unknown_contact", "ignored"]
        assert crew.hubspot.notes == []
        assert (await c.post("/hubspot/webhook", content=b"nope", headers={"content-type": "application/json"})).status_code == 400
        assert (await c.post("/hubspot/webhook", json="x")).status_code == 400


async def test_signature_is_verified_when_a_secret_is_set(crew):
    secret = "test-client-secret-not-real"
    app = create_app(crew, client_secret=secret, public_url="https://triage.example.com")
    body = json.dumps([event_for("hs-1002")]).encode()
    ts = int(time.time() * 1000)
    sig = sign_v3(secret, "POST", "https://triage.example.com/hubspot/webhook", body, ts)
    async with await _client(app) as c:
        bad = await c.post("/hubspot/webhook", content=body, headers={"content-type": "application/json", TIMESTAMP_HEADER: str(ts), SIGNATURE_HEADER: "bogus"})
        assert bad.status_code == 401 and "mismatch" in bad.json()["error"]
        none = await c.post("/hubspot/webhook", content=body, headers={"content-type": "application/json"})
        assert none.status_code == 401
        good = await c.post("/hubspot/webhook", content=body, headers={"content-type": "application/json", TIMESTAMP_HEADER: str(ts), SIGNATURE_HEADER: sig})
        assert good.status_code == 200 and good.headers["X-Triage-Signature"] == "verified"
        assert good.json()["processed"][0]["band"] == "good fit"
    assert verify_v3(secret, "POST", "u", b"", str(ts - 10 * 60 * 1000), sig, now_ms=ts) == (False, "timestamp outside the 5-minute window")
    assert verify_v3(secret, "POST", "u", b"", "x", sig)[1] == "timestamp is not an integer"


def test_replay_posts_every_fixture_lead_in_batches(monkeypatch, capsys):
    from starlette.testclient import TestClient

    from triage.layer import Layer

    # a factory: the crew (and its SQLite connection) is built inside the test server's thread on the first request
    app = create_app(lambda: Crew.for_fixtures(layer=Layer(":memory:"), run_id="g2c-replay"), client_secret=None)
    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: TestClient(app))  # the replay script's client, pointed at the app in-process
    rc = cli.cmd_replay(type("A", (), {"url": "http://testserver", "batch": 7, "timeout": 5.0, "ids": []})())
    assert rc == 0
    out = capsys.readouterr().out
    assert out.count("POST http://testserver/hubspot/webhook") == 3  # 7 + 7 + 6
    assert '"band": "duplicate"' in out
    crew = app.state.crew
    assert len(crew.results) == 20 and len(crew.hubspot.notes) == 26


def test_cli_run_writes_run_log_notes_and_eval_report(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["run", "--out", str(tmp_path / "out"), "--report", str(tmp_path / "eval.md")])
    assert rc == 0
    out = capsys.readouterr().out
    assert "band accuracy 20/20" in out and "not measured live" in out
    runs = list((tmp_path / "out").iterdir())
    assert len(runs) == 1
    log = json.loads((runs[0] / "run-log.json").read_text())
    assert log["measured"] is False and len(log["results"]) == 20 and log["blocked_attempts"] == []
    report = (tmp_path / "eval.md").read_text()
    assert "20 / 20 correct" in report and "Not measured live" in report and "| hs-1018 | duplicate | duplicate |" in report
    assert "DRAFT — not sent" in (runs[0] / "notes.md").read_text()
    rc = cli.main(["eval", "--run-log", str(runs[0] / "run-log.json")])
    assert rc == 0 and "band accuracy 20/20" in capsys.readouterr().out


def test_cli_hubspot_load_prints_the_payload_and_never_calls_hubspot(tmp_path, capsys):
    out = tmp_path / "batch.json"
    rc = cli.main(["hubspot-load", "--out", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert len(payload["inputs"]) == 20
    assert all(i["properties"]["email"].endswith("@example.com") for i in payload["inputs"])
    assert "message" not in payload["inputs"][0]["properties"] and payload["inputs"][0]["properties"]["li_tool_role"] == "executive-sponsor"
    text = capsys.readouterr().out
    assert "never calls HubSpot" in text and "$HUBSPOT_PRIVATE_APP_TOKEN" in text


def test_leads_are_the_webhook_contacts():
    # the fake is seeded with the fixture leads, so a replayed objectId resolves (D-18)
    crew = Crew.for_fixtures(run_id="x")
    assert {lead.id for lead in load_leads()} == set(crew.hubspot.contacts)


# -- review fix 1 (D-20): `serve` builds the client the banner reports ------------------------------


def _serve_args(**kw):
    base = {"host": "127.0.0.1", "port": 8042, "judge": "deterministic", "public_url": None, "record": False}
    base.update(kw)
    return type("A", (), base)()


def test_serve_uses_the_fake_without_a_token_and_says_so():
    app, banner = cli.serve_app(_serve_args())
    assert "HubSpot client: fake (seeded from fixtures)" in banner
    from starlette.testclient import TestClient

    with TestClient(app) as c:
        assert c.get("/health").json()["hubspot"] == "fake"
    assert app.state.crew.hubspot.name == "fake" and "hs-1001" in app.state.crew.hubspot.contacts


def test_serve_uses_the_real_client_when_a_token_is_set(monkeypatch):
    from triage.hubspot import RealHubSpot
    from triage.safety import SafetyViolation

    monkeypatch.setenv("HUBSPOT_PRIVATE_APP_TOKEN", "pat-test-not-real")
    monkeypatch.setenv("HUBSPOT_CLIENT_SECRET", "test-client-secret-not-real")  # fix 2: a real client needs a secret
    app, banner = cli.serve_app(_serve_args())
    assert "HubSpot client: real" in banner and app.state.crew is None  # the crew is built on the first request; none is made here
    built = cli._crew(_serve_args(), hubspot=cli._hubspot_for_serve())  # the constructor makes no network call
    assert isinstance(built.hubspot, RealHubSpot) and built.hubspot.name == "real"
    # the synthetic-only write guard is still in force on the real client: a non-example.com contact is refused before any POST
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        if request.method == "GET":
            return httpx.Response(200, json={"id": "77", "properties": {"email": "real.person@acme.com"}, "createdAt": "2026-11-01T00:00:00Z"})
        return httpx.Response(201, json={"id": "n1"})

    guarded = RealHubSpot(token="pat-test-not-real", transport=httpx.MockTransport(handler))
    with pytest.raises(SafetyViolation):
        guarded.create_note("77", "x")
    assert [m for m, _ in calls] == ["GET"]


# -- review fix 2 (D-21): unsigned mode only in fixture/fake mode ---------------------------------


def test_serve_refuses_to_start_unsigned_with_a_real_hubspot_token(monkeypatch, capsys):
    import uvicorn

    monkeypatch.setenv("HUBSPOT_PRIVATE_APP_TOKEN", "pat-test-not-real")
    monkeypatch.setattr(uvicorn, "run", lambda *a, **kw: pytest.fail("the server must not start"))
    assert cli.main(["serve"]) == 2
    assert "HUBSPOT_CLIENT_SECRET is not set" in capsys.readouterr().err


def test_create_app_refuses_unsigned_with_a_live_model_key(monkeypatch):
    from triage.webhook import UnsignedLiveConfig

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")  # nothing is built or called: the app refuses first
    with pytest.raises(UnsignedLiveConfig):
        create_app(lambda: pytest.fail("no crew may be built"), client_secret=None)
    with pytest.raises(UnsignedLiveConfig):
        cli.serve_app(_serve_args())


def test_create_app_refuses_a_live_crew_instance_without_a_secret(crew):
    from triage.webhook import UnsignedLiveConfig

    crew.caller.name = "claude-agent-sdk"  # stand-in for a live caller; nothing is called
    with pytest.raises(UnsignedLiveConfig):
        create_app(crew, client_secret=None)


async def test_a_live_crew_behind_an_unsigned_app_gets_401_on_every_request(layer):
    from triage.hubspot import RealHubSpot

    calls = []
    real = RealHubSpot(token="pat-test-not-real", transport=httpx.MockTransport(lambda r: calls.append(r) or httpx.Response(500)))
    live_crew = Crew(layer=layer, hubspot=real, caller=RecordedCaller(), run_id="g2c-live")
    app = create_app(lambda: live_crew, client_secret=None, live=False)  # startup told the wrong thing on purpose
    async with await _client(app) as c:
        r = await c.post("/hubspot/webhook", json=[event_for("hs-1001")])
        assert r.status_code == 401 and "unsigned requests are refused" in r.json()["error"]
    assert calls == []  # HubSpot was never reached


def test_fake_mode_banner_says_unsigned_is_fixture_only():
    _, banner = cli.serve_app(_serve_args())
    assert "signature check: off — fixture/fake mode only" in banner and "model: recorded fake" in banner
