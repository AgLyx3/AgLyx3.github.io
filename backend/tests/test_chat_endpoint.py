"""Tests for the /chat API endpoint."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.chat import chat_endpoint
from app.config import get_settings
from app.models import ChatRequest, SessionSnapshot
from app.models.analytics import SessionMessageRecordResult
from app.services.retrieval import (
    CombinedMemoryRetrievalResult,
    ProfileRetrievalResult,
    RetrievalResult,
)


def _request():
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/chat",
        "headers": [],
        "client": ("127.0.0.1", 12345),
    })


def _snapshot(session_id: str = "test-session") -> SessionSnapshot:
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


async def _read_body(response) -> str:
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else str(chunk))
    return "".join(chunks)


def test_small_talk_streamed_when_retrieval_scores_too_low():
    snapshot = _snapshot("fallback-session")
    message_result = SessionMessageRecordResult(
        session=snapshot,
        message_index_in_session=1,
        first_message_recorded=True,
        depth_5_reached=False,
    )
    low_score_result = CombinedMemoryRetrievalResult(
        profile=ProfileRetrievalResult(context_blocks=[], top_score=0.0, matches=[]),
        experience=RetrievalResult(
            active_topics=[], citations=[], context_blocks=[],
            top_score=0.05, second_score=0.0, topics=[], edges=[],
        ),
    )

    with patch("app.api.chat.record_user_message", return_value=message_result), \
         patch("app.api.chat.touch_session", return_value=snapshot), \
         patch("app.api.chat.combined_memory_retrieve", return_value=low_score_result), \
         patch("app.api.chat.log_analytics_event"), \
         patch("app.api.chat.log_memory_gap"), \
         patch("app.api.chat.record_assistant_response_tokens", return_value=snapshot), \
         patch("app.api.chat.generate_small_talk_answer", return_value="Hey, ask me about Yixin's work."):
        response = asyncio.run(chat_endpoint(
            ChatRequest(message="xyzzy gobbledegook nonsense", session_id="fallback-session"),
            _request(),
            get_settings(),
        ))

    assert response.status_code == 200
    body = asyncio.run(_read_body(response))
    assert "Hey" in body
    assert '"route":"memory"' in body
    assert '"response_mode":"small_talk"' in body
    assert '"session_state"' in body


def test_oversized_message_rejected_with_413():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(chat_endpoint(
            ChatRequest(message="x" * 7000, session_id="token-limit-session"),
            _request(),
            get_settings(),
        ))
    assert exc_info.value.status_code == 413


def test_general_early_query_appends_topic_hint():
    snapshot = _snapshot("hint-session")
    message_result = SessionMessageRecordResult(
        session=snapshot,
        message_index_in_session=2,
        first_message_recorded=False,
        depth_5_reached=False,
    )
    retrieval_result = CombinedMemoryRetrievalResult(
        profile=ProfileRetrievalResult(
            context_blocks=["current role: Product Manager at Continua AI"],
            top_score=0.5,
            matches=[],
        ),
        experience=RetrievalResult(
            active_topics=["pm"],
            citations=[],
            context_blocks=[],
            top_score=0.0,
            second_score=0.0,
            topics=[],
            edges=[],
        ),
    )

    with patch("app.api.chat.record_user_message", return_value=message_result), \
         patch("app.api.chat.touch_session", return_value=snapshot), \
         patch("app.api.chat.combined_memory_retrieve", return_value=retrieval_result), \
         patch("app.api.chat.log_analytics_event"), \
         patch("app.api.chat.record_assistant_response_tokens", return_value=snapshot), \
         patch("app.api.chat.generate_chat_answer", return_value="Yixin is a product manager at Continua AI."):
        response = asyncio.run(chat_endpoint(
            ChatRequest(message="tell me about her", session_id="hint-session"),
            _request(),
            get_settings(),
        ))

    body = asyncio.run(_read_body(response))
    assert '"token": "Topics "' in body
    assert '"token": "top "' in body
    assert '"token": "right."' in body or '"token": "right "' in body
    assert '"token": "background "' in body
    assert '"token": "bubbles "' in body or '"token": "bubble "' in body
