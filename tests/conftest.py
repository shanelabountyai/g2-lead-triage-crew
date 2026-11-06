import os

import pytest

from triage.directory import Directory
from triage.hubspot import FakeHubSpot
from triage.layer import Layer
from triage.models import load_leads


@pytest.fixture(autouse=True)
def _no_keys(monkeypatch):
    """No test may reach a model or HubSpot. Keys are scrubbed even if the environment has them."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("HUBSPOT_PRIVATE_APP_TOKEN", raising=False)
    monkeypatch.delenv("HUBSPOT_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("TRIAGE_RUN_LOG_DIR", raising=False)
    monkeypatch.setenv("G0_DB_PATH", ":memory:")
    assert "ANTHROPIC_API_KEY" not in os.environ


@pytest.fixture
def layer():
    lay = Layer(db_path=":memory:")
    yield lay
    lay.close()


@pytest.fixture
def leads():
    return load_leads()


@pytest.fixture
def hubspot(leads):
    return FakeHubSpot.seeded(leads)


@pytest.fixture
def directory():
    return Directory()
