"""Tests for analytics event logging."""

from __future__ import annotations

import pytest

from app.models import AnalyticsEventCreate
from app.services.analytics import log_analytics_event


def test_valid_event_is_persisted(test_db):
    event = log_analytics_event(AnalyticsEventCreate(
        session_id="analytics-test",
        event_name="chat_message_sent",
        payload={
            "message_index_in_session": 1,
            "message_length": 18,
            "message_origin": "manual",
        },
    ))
    assert event.event_id > 0
    assert event.event_name == "chat_message_sent"


def test_event_with_missing_required_payload_raises(test_db):
    with pytest.raises(ValueError):
        log_analytics_event(AnalyticsEventCreate(
            session_id="analytics-test",
            event_name="chat_depth_reached",
            payload={},
        ))
