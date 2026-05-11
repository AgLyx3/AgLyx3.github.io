"""Tests for contact message creation."""

from __future__ import annotations

from unittest.mock import patch

from app.models.actions import ContactMessageRequest
from app.services.contact import create_contact_message


def test_contact_message_persists_with_correct_params():
    captured: dict = {}

    class FakeCursor:
        def fetchone(self):
            return {"message_id": 42}

    class FakeConn:
        def execute(self, query, params=()):
            captured["params"] = params
            return FakeCursor()

        def commit(self):
            captured["committed"] = True

    class FakeConnManager:
        def __enter__(self):
            return FakeConn()

        def __exit__(self, *_):
            return False

    from app.config import Settings
    no_resend_settings = Settings(resend_api_key="")

    with patch("app.services.contact.ensure_session"), \
         patch("app.services.contact.get_conn", return_value=FakeConnManager()):
        response = create_contact_message(
            ContactMessageRequest(
                session_id="contact-session",
                message_body="hello there",
                included_chat_history=True,
                conversation_history=[],
                message_count_before_send=3,
            ),
            settings=no_resend_settings,
        )

    assert response.message_id == 42
    assert captured["params"][2] is False
    assert captured.get("committed") is True
