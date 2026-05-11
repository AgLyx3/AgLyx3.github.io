"""Tests for session tracking and message limits."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.models import SessionMessageRecordRequest
from app.services.session import record_user_message


def test_first_message_flag_is_set(test_db):
    result = record_user_message(SessionMessageRecordRequest(
        session_id="session-first-msg",
        message_text="hello",
        message_origin="manual",
        estimated_input_tokens=2,
    ))
    assert result.first_message_recorded is True
    assert result.message_index_in_session == 1


def test_depth_5_flag_triggers_at_fifth_message(test_db):
    session_id = "session-depth-5"
    result = None
    for i in range(1, 6):
        result = record_user_message(SessionMessageRecordRequest(
            session_id=session_id,
            message_text=f"message {i}",
            message_origin="manual",
            estimated_input_tokens=2,
        ))
    assert result is not None
    assert result.depth_5_reached is True
    assert result.message_index_in_session == 5
    assert result.session.message_count == 5


def test_message_limit_raises_429(test_db):
    session_id = "session-limit-test"
    limit = get_settings().max_messages_per_session
    for i in range(limit):
        record_user_message(SessionMessageRecordRequest(
            session_id=session_id,
            message_text=f"message {i}",
            message_origin="manual",
            estimated_input_tokens=2,
        ))
    with pytest.raises(HTTPException) as exc_info:
        record_user_message(SessionMessageRecordRequest(
            session_id=session_id,
            message_text="one too many",
            message_origin="manual",
            estimated_input_tokens=2,
        ))
    assert exc_info.value.status_code == 429
