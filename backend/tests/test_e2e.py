"""End-to-end tests using FastAPI TestClient.

These tests spin up the full application stack (routing, middleware, services,
SQLite) and exercise it over HTTP, so they catch wiring bugs that unit tests miss.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def app_client():
    """Spin up the full app against a temporary database."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "e2e_test.db"
    env_overrides = {
        "DATABASE_URL": f"sqlite:///{db_path}",
        "ANALYTICS_WRITE_ENABLED": "true",
        "ADMIN_API_KEY": "test-admin-key",
    }
    with patch.dict(os.environ, env_overrides):
        # Import app after env is patched so init_db() uses the test DB.
        import importlib
        import app.main as main_module
        importlib.reload(main_module)

        from fastapi.testclient import TestClient
        with TestClient(main_module.app) as client:
            yield client

    tmpdir.cleanup()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health(app_client):
    resp = app_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------

def test_chat_returns_sse_stream_for_fallback(app_client):
    """When retrieval scores are too low the fallback response is streamed."""
    resp = app_client.post(
        "/chat",
        json={"message": "xyzzy gobbledegook nonsense", "session_id": "e2e-fallback"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    assert "event: token" in body
    assert "event: final" in body
    assert '"session_state"' in body


def test_chat_rejects_oversized_message(app_client):
    resp = app_client.post(
        "/chat",
        json={"message": "x" * 7000, "session_id": "e2e-oversize"},
    )
    assert resp.status_code == 413


def test_chat_rejects_oversized_body(app_client):
    """Body size check should fire even without Content-Length header."""
    big_payload = json.dumps({"message": "hi", "session_id": "e2e-body-size", "history": [{"role": "user", "content": "x" * 4000}] * 10})
    resp = app_client.post(
        "/chat",
        content=big_payload,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 413


def test_chat_session_state_in_final_event(app_client):
    resp = app_client.post(
        "/chat",
        json={"message": "Tell me about accessibility", "session_id": "e2e-session-state"},
    )
    assert resp.status_code == 200
    final_line = [l for l in resp.text.splitlines() if l.startswith("data:") and '"session_state"' in l]
    assert final_line, "final SSE event not found in stream"
    data = json.loads(final_line[0].removeprefix("data:").strip())
    assert data["session_state"]["session_id"] == "e2e-session-state"


def test_chat_enforces_message_count_limit(app_client):
    """15 messages succeed; the 16th is rejected with 429."""
    session_id = "e2e-msg-limit"
    # Bypass the per-IP chat rate limiter so we can send 15 rapid requests.
    with patch("app.api.chat.chat_rate_limiter") as mock_limiter:
        mock_limiter.check.return_value = None
        for i in range(15):
            resp = app_client.post(
                "/chat",
                json={"message": f"message {i}", "session_id": session_id},
            )
            assert resp.status_code == 200, f"message {i} failed: {resp.text}"

        resp = app_client.post("/chat", json={"message": "over limit", "session_id": session_id})
        assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Rate limiter (global)
# ---------------------------------------------------------------------------

def test_rate_limiter_returns_429_after_burst(app_client):
    """The global limiter should reject after limit_per_minute hits from same IP."""
    # TestClient uses 127.0.0.1 as the client host. Patch the limiter to a
    # tight limit so we don't have to send 60 real requests.
    from app.services.safety import RateLimiter
    tight = RateLimiter(limit_per_minute=3)

    with patch("app.main.limiter", tight):
        for i in range(3):
            resp = app_client.get("/health")
            assert resp.status_code == 200
        resp = app_client.get("/health")
        assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def test_linkedin_action_tracked(app_client):
    # Seed a session first via chat so ensure_session passes.
    app_client.post("/chat", json={"message": "hi", "session_id": "e2e-action"})

    resp = app_client.post(
        "/actions/linkedin",
        json={"session_id": "e2e-action", "message_count_before_action": 1},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["action_type"] == "linkedin"
    assert body["tracked"] is True


def test_resume_action_tracked(app_client):
    app_client.post("/chat", json={"message": "hi", "session_id": "e2e-resume"})
    resp = app_client.post(
        "/actions/resume",
        json={"session_id": "e2e-resume", "message_count_before_action": 1},
    )
    assert resp.status_code == 200
    assert resp.json()["action_type"] == "download_resume"


def test_schedule_action_tracked(app_client):
    app_client.post("/chat", json={"message": "hi", "session_id": "e2e-schedule"})
    resp = app_client.post(
        "/actions/schedule",
        json={"session_id": "e2e-schedule", "message_count_before_action": 1},
    )
    assert resp.status_code == 200
    assert resp.json()["action_type"] == "schedule_time"


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------

def test_contact_message_recorded(app_client):
    app_client.post("/chat", json={"message": "hi", "session_id": "e2e-contact"})
    resp = app_client.post(
        "/contact",
        json={
            "session_id": "e2e-contact",
            "message_body": "I would love to connect!",
            "included_chat_history": False,
            "message_count_before_send": 1,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["delivery_status"] == "recorded"
    assert body["message_id"] > 0


def test_contact_no_duplicate_analytics(app_client):
    """Each contact submission should produce exactly one analytics event."""
    from app.services.analytics import log_analytics_event as real_log

    calls: list = []

    def counting_log(event):
        calls.append(event.event_name)
        return real_log(event)

    app_client.post("/chat", json={"message": "hi", "session_id": "e2e-contact-dedup"})
    with patch("app.api.actions.log_analytics_event", side_effect=counting_log):
        app_client.post(
            "/contact",
            json={
                "session_id": "e2e-contact-dedup",
                "message_body": "Hello",
                "message_count_before_send": 1,
            },
        )

    contact_events = [e for e in calls if e == "message_sent_to_yixin"]
    assert len(contact_events) == 1, f"Expected 1 event, got {len(contact_events)}"


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def test_graph_returns_seeded_data(app_client):
    resp = app_client.get("/graph")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["topics"]) > 0
    assert len(body["experiences"]) > 0
    assert len(body["edges"]) > 0


# ---------------------------------------------------------------------------
# Admin endpoints (topic_ops / analytics ingest)
# ---------------------------------------------------------------------------

def test_topic_ops_requires_admin_key(app_client):
    resp = app_client.get("/topics/notifications")
    assert resp.status_code == 403


def test_topic_ops_accessible_with_admin_key(app_client):
    resp = app_client.get(
        "/topics/notifications",
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert resp.status_code == 200


def test_analytics_ingest_requires_admin_key(app_client):
    resp = app_client.post(
        "/events",
        json={
            "session_id": "e2e-anon",
            "event_name": "chat_message_sent",
            "payload": {"message_index_in_session": 1, "message_length": 5, "message_origin": "manual"},
        },
    )
    assert resp.status_code == 403


def test_analytics_ingest_accepted_with_admin_key(app_client):
    resp = app_client.post(
        "/events",
        headers={"X-Admin-Key": "test-admin-key"},
        json={
            "session_id": "e2e-admin",
            "event_name": "chat_message_sent",
            "payload": {"message_index_in_session": 1, "message_length": 5, "message_origin": "manual"},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["accepted"] is True
