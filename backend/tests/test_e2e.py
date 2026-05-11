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

from app.models.chat import Citation


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
        json={"message": "hi", "session_id": "e2e-session-state"},
    )
    assert resp.status_code == 200
    final_line = [l for l in resp.text.splitlines() if l.startswith("data:") and '"session_state"' in l]
    assert final_line, "final SSE event not found in stream"
    data = json.loads(final_line[0].removeprefix("data:").strip())
    assert data["session_state"]["session_id"] == "e2e-session-state"
    assert data["route"] == "small_talk"


def test_chat_enforces_message_count_limit(app_client):
    """Messages up to limit succeed; the one over is rejected with 429."""
    from app.config import get_settings
    limit = get_settings().max_messages_per_session
    session_id = "e2e-msg-limit"
    with patch("app.api.chat.chat_rate_limiter") as mock_limiter:
        mock_limiter.check.return_value = None
        for i in range(limit):
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
    with patch("app.services.contact._send_via_resend"):
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
    assert body["delivery_status"] in {"recorded", "sent"}
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


def test_graph_activation_changes_only_for_experience_queries(app_client):
    from app.services.retrieval import CombinedMemoryRetrievalResult, ProfileRetrievalResult, RetrievalResult

    graph_before = app_client.get("/graph")
    assert graph_before.status_code == 200
    body_before = graph_before.json()
    edge = body_before["edges"][0]
    experience_id = edge["source_experience_id"]
    topic_id = edge["target_topic_id"]
    experience = next(exp for exp in body_before["experiences"] if exp["id"] == experience_id)
    exp_before = next(exp["activation"] for exp in body_before["experiences"] if exp["id"] == experience_id)
    topic_before = next(topic["activation"] for topic in body_before["topics"] if topic["id"] == topic_id)

    exp_result = RetrievalResult(
        active_topics=[topic_id],
        citations=[
            Citation(
                experience_id=experience_id,
                experience_title=experience["title"],
                snippet=experience["raw_context"],
                score=0.8,
            )
        ],
        context_blocks=[f"{experience['title']}: {experience['raw_context']}"],
        top_score=0.8,
        second_score=0.1,
        topics=[],
        edges=[],
    )
    memory_result = CombinedMemoryRetrievalResult(
        profile=ProfileRetrievalResult(context_blocks=[], top_score=0.0, matches=[]),
        experience=exp_result,
    )

    with patch("app.api.chat.combined_memory_retrieve", return_value=memory_result), \
         patch("app.api.chat.generate_chat_answer", return_value="Grounded experience answer."), \
         patch("app.api.chat.chat_rate_limiter") as mock_limiter:
        mock_limiter.check.return_value = None
        resp = app_client.post(
            "/chat",
            json={"message": "what ML projects has she done?", "session_id": "e2e-activation-exp"},
        )
    assert resp.status_code == 200

    graph_after_experience = app_client.get("/graph")
    assert graph_after_experience.status_code == 200
    body_after_experience = graph_after_experience.json()
    exp_after = next(exp["activation"] for exp in body_after_experience["experiences"] if exp["id"] == experience_id)
    topic_after = next(topic["activation"] for topic in body_after_experience["topics"] if topic["id"] == topic_id)
    assert exp_after > exp_before
    assert topic_after > topic_before

    graph_before_profile = app_client.get("/graph").json()
    exp_before_profile = next(exp["activation"] for exp in graph_before_profile["experiences"] if exp["id"] == experience_id)
    topic_before_profile = next(topic["activation"] for topic in graph_before_profile["topics"] if topic["id"] == topic_id)
    profile_result = CombinedMemoryRetrievalResult(
        profile=ProfileRetrievalResult(
            context_blocks=["education: Colby College, Computer Science"],
            top_score=0.7,
            matches=[],
        ),
        experience=RetrievalResult(
            active_topics=[],
            citations=[],
            context_blocks=[],
            top_score=0.01,
            second_score=0.0,
            topics=[],
            edges=[],
        ),
    )
    with patch("app.api.chat.combined_memory_retrieve", return_value=profile_result), \
         patch("app.api.chat.generate_chat_answer", return_value="Grounded profile answer."), \
         patch("app.api.chat.chat_rate_limiter") as mock_limiter2:
        mock_limiter2.check.return_value = None
        resp = app_client.post(
            "/chat",
            json={"message": "what degree did she get?", "session_id": "e2e-activation-profile"},
        )
    assert resp.status_code == 200

    graph_after_profile = app_client.get("/graph").json()
    exp_after_profile = next(exp["activation"] for exp in graph_after_profile["experiences"] if exp["id"] == experience_id)
    topic_after_profile = next(topic["activation"] for topic in graph_after_profile["topics"] if topic["id"] == topic_id)
    assert exp_after_profile == exp_before_profile
    assert topic_after_profile == topic_before_profile


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
