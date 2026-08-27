"""Tests for Langfuse tracing.

These assert that spans are actually produced, not merely that instrumented
code still runs — a shim that silently no-ops would pass the rest of the suite.
Spans are captured with an in-memory OTel exporter, so nothing leaves the box.
"""

from __future__ import annotations

import asyncio
import itertools
from unittest.mock import patch

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from starlette.requests import Request

from app.api.chat import chat_endpoint
from app.api.voice import VoiceTurnReport, voice_turn_report
from app.config import get_settings
from app.models import ChatRequest, SessionSnapshot
from app.models.analytics import SessionMessageRecordResult
from app.services import tracing
from app.services.retrieval import (
    CombinedMemoryRetrievalResult,
    ProfileRetrievalResult,
    RetrievalResult,
)


_client_seq = itertools.count(1)


def _request():
    """Unique client IP per turn: the chat rate limiter (6/min) is process-wide
    shared state, so reusing one IP makes these tests fail the whole suite."""
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/chat",
        "headers": [],
        "client": (f"10.0.0.{next(_client_seq)}", 12345),
    })


def _snapshot(session_id: str) -> SessionSnapshot:
    return SessionSnapshot(
        session_id=session_id,
        started_at="2026-01-01T00:00:00+00:00",
        last_seen_at="2026-01-01T00:00:00+00:00",
        message_count=1,
        first_message_at="2026-01-01T00:00:00+00:00",
        depth_5_reached_at=None,
        cta_mentioned=False,
        cta_rejected=False,
        active_topic_id=None,
    )


def _retrieval_hit() -> CombinedMemoryRetrievalResult:
    return CombinedMemoryRetrievalResult(
        profile=ProfileRetrievalResult(
            context_blocks=["Yixin is a product manager."], top_score=0.8, matches=[]
        ),
        experience=RetrievalResult(
            active_topics=[], citations=[], context_blocks=["Worked on eval tooling."],
            top_score=0.7, second_score=0.2, topics=[], edges=[],
        ),
    )


@pytest.fixture(scope="module")
def _langfuse_test_client():
    """One client for the module.

    Langfuse installs a process-wide OTel tracer provider on first use, so a
    per-test client would silently never register its exporter.
    """
    from langfuse import Langfuse

    exporter = InMemorySpanExporter()
    client = Langfuse(
        public_key="pk-lf-test",
        secret_key="sk-lf-test",
        tracing_enabled=True,
        span_exporter=exporter,
    )
    return client, exporter


@pytest.fixture
def captured_spans(_langfuse_test_client):
    """Point the tracing shim at the in-memory exporter, emptied per test."""
    client, exporter = _langfuse_test_client
    exporter.clear()
    tracing._client = client
    tracing._init_attempted = True
    try:
        yield exporter
    finally:
        tracing._reset_for_tests()


async def _drain(response) -> str:
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, str) else chunk.decode())
    return "".join(chunks)


def _run_turn(payload: ChatRequest, answer: str = "Yixin is a product manager."):
    snapshot = _snapshot(payload.session_id or "trace-session")
    message_result = SessionMessageRecordResult(
        session=snapshot,
        message_index_in_session=1,
        first_message_recorded=True,
        depth_5_reached=False,
    )
    with patch("app.api.chat.record_user_message", return_value=message_result), \
         patch("app.api.chat.touch_session", return_value=snapshot), \
         patch("app.api.chat.combined_memory_retrieve", return_value=_retrieval_hit()), \
         patch("app.api.chat.log_analytics_event"), \
         patch("app.api.chat.log_memory_gap"), \
         patch("app.api.chat.update_activation"), \
         patch("app.api.chat.record_assistant_response_tokens", return_value=snapshot), \
         patch("app.api.chat.generate_chat_answer", return_value=answer):
        response = asyncio.run(chat_endpoint(payload, _request(), get_settings()))
        body = asyncio.run(_drain(response))
    return response, body


def _names(exporter) -> list[str]:
    tracing.flush()
    return [span.name for span in exporter.get_finished_spans()]


def _spans_named(exporter, name: str) -> list:
    tracing.flush()
    return [s for s in exporter.get_finished_spans() if s.name == name]


def test_chat_turn_emits_root_and_retrieval_spans(captured_spans):
    response, body = _run_turn(
        ChatRequest(message="what does Yixin do?", session_id="trace-session")
    )

    assert response.status_code == 200
    names = _names(captured_spans)
    assert "chat-turn" in names, f"no root span, got {names}"
    assert "retrieval" in names, f"no retrieval span, got {names}"


def test_spans_share_one_trace_and_carry_session_id(captured_spans):
    _run_turn(ChatRequest(message="what does Yixin do?", session_id="trace-session"))

    root = _spans_named(captured_spans, "chat-turn")[-1]
    retrieval = _spans_named(captured_spans, "retrieval")[-1]
    assert root.context.trace_id == retrieval.context.trace_id, (
        "pipeline spans were split across traces"
    )

    assert root.attributes.get("session.id") == "trace-session"


def test_retrieval_span_records_scores(captured_spans):
    _run_turn(ChatRequest(message="what does Yixin do?", session_id="trace-session"))

    retrieval = _spans_named(captured_spans, "retrieval")[-1]
    output = retrieval.attributes.get("langfuse.observation.output", "")
    # The whole point of this span: know what retrieval handed the model.
    assert "experience_top_score" in output
    assert "0.7" in output


def test_voice_turn_is_named_and_tagged_separately(captured_spans):
    _run_turn(
        ChatRequest(message="what does Yixin do?", session_id="v-session", voice_mode=True)
    )
    assert "voice-turn" in _names(captured_spans)


def test_turn_id_stitches_requests_into_one_trace(captured_spans):
    """Two separate requests sharing a turn_id must land on one trace."""
    _run_turn(
        ChatRequest(message="what does Yixin do?", session_id="v-session",
                    voice_mode=True, turn_id="turn-abc")
    )
    chat_trace_id = _spans_named(captured_spans, "voice-turn")[-1].context.trace_id

    # A later, independent request (e.g. /voice/tts) seeded with the same id.
    with tracing.observe("tts", trace_id=tracing.trace_id_for("turn-abc")):
        pass

    tts_span = _spans_named(captured_spans, "tts")[-1]
    assert tts_span.context.trace_id == chat_trace_id


def test_tracing_is_a_no_op_when_unconfigured():
    """Without keys the shim must stay silent, not raise."""
    tracing._reset_for_tests()
    with patch.object(tracing, "_get_client", return_value=None):
        with tracing.observe("chat-turn", session_id="x") as span:
            span.update(output="anything")
            span.score("memory_fallback", 1)
        tracing.score_current_trace("memory_fallback", 0)
        tracing.flush()
        assert tracing.trace_id_for("seed") is None
        assert tracing.tracing_enabled() is False


def test_mask_redacts_visitor_authored_fields():
    masked = tracing._mask(
        data={
            "user_message": "I work on ML infra",
            "visitor_context": "at a startup",
            "route": "memory",
            "nested": {"transcript": "hello there", "score": 0.7},
        }
    )
    assert masked["user_message"] == "[redacted]"
    assert masked["visitor_context"] == "[redacted]"
    assert masked["nested"]["transcript"] == "[redacted]"
    # Non-visitor fields must survive or the traces are useless.
    assert masked["route"] == "memory"
    assert masked["nested"]["score"] == 0.7


def test_voice_turn_report_joins_the_chat_turn_trace(captured_spans):
    """The browser-side STT/TTS legs must land on the same trace as /chat."""
    _run_turn(
        ChatRequest(message="what does Yixin do?", session_id="v-session",
                    voice_mode=True, turn_id="turn-xyz")
    )
    chat_trace_id = _spans_named(captured_spans, "voice-turn")[-1].context.trace_id

    result = voice_turn_report(VoiceTurnReport(
        turn_id="turn-xyz",
        session_id="v-session",
        transcript="what does Yixin do",
        confidence=0.42,
        audio_duration_ms=2100,
        tts_sentences=5,
        tts_chars=320,
        tts_ms=1800,
    ))
    assert result["accepted"] is True

    stt = _spans_named(captured_spans, "stt")[-1]
    tts = _spans_named(captured_spans, "tts")[-1]
    assert stt.context.trace_id == chat_trace_id
    assert tts.context.trace_id == chat_trace_id
    # One tts span for the whole turn, not one per synthesised sentence.
    assert len(_spans_named(captured_spans, "tts")) == 1
    assert tts.attributes.get("langfuse.observation.metadata.sentences") == 5
    # Floats are serialised to strings in OTel attributes; ints are not.
    assert stt.attributes.get("langfuse.observation.metadata.confidence") == "0.42"


def test_voice_turn_report_is_inert_when_tracing_disabled():
    tracing._reset_for_tests()
    with patch.object(tracing, "_get_client", return_value=None):
        result = voice_turn_report(VoiceTurnReport(turn_id="turn-1", confidence=0.9))
    assert result["accepted"] is False
