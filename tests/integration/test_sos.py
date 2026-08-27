"""
Integration tests per project_brief.md Section 12: invalid POST /api/sos ->
400, valid -> 201 + incident created + fetchable.

Unlike the unit tests, these hit a *live* running stack over HTTP
(`make up` in another terminal, then `make test-integration`) rather than
importing the FastAPI app in-process - that way they exercise the real
Postgres/PostGIS + Celery worker path end to end, not just the API layer.
"""
import os
import uuid
import time

import pytest
import requests

BASE_URL = os.environ.get("FLOODRESCUE_API_URL", "http://localhost:8000")


def _server_available():
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
        return True
    except requests.exceptions.ConnectionError:
        return False


pytestmark = pytest.mark.skipif(
    not _server_available(),
    reason=f"no live API at {BASE_URL} - run `make up` first, then `make test-integration`",
)


def _valid_sos():
    return {
        "source": "app",
        "user_hash": uuid.uuid4().hex + uuid.uuid4().hex,  # 64 hex chars
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "coords": {"lat": 12.9715987, "lon": 77.5945627},
        "accuracy_m": 15.0,
        "comm_type": "gps",
        "consent_flag": True,
    }


def test_missing_consent_returns_400():
    body = dict(_valid_sos(), consent_flag=False)
    resp = requests.post(f"{BASE_URL}/api/sos", json=body)
    assert resp.status_code == 400


def test_missing_location_returns_400():
    body = _valid_sos()
    del body["coords"]
    resp = requests.post(f"{BASE_URL}/api/sos", json=body)
    assert resp.status_code == 400


def test_valid_sos_creates_and_returns_incident():
    resp = requests.post(f"{BASE_URL}/api/sos", json=_valid_sos())
    assert resp.status_code == 201
    incident_id = resp.json()["incident_id"]
    assert incident_id

    get_resp = requests.get(f"{BASE_URL}/api/incidents/{incident_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["incident_id"] == incident_id
