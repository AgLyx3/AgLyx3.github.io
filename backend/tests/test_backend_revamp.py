from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
import asyncio
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from app.api.chat import chat_endpoint
from app.config import get_settings
from app.models import (
    AnalyticsEventCreate,
    ChatRequest,
    SessionMessageRecordRequest,
    SessionSnapshot,
)
from app.models.actions import ContactMessageRequest
from app.models.chat import Citation
from app.models.analytics import SessionMessageRecordResult
from app.services.analytics import log_analytics_event
from app.services.contact import create_contact_message
from app.services.cta_rules import detect_cta_rejection, should_offer_cta
from app.services.db import init_db
from app.services.followups import build_adjacent_topics, build_follow_up_questions
from app.services.retrieval import RetrievalResult
from app.services.session import record_user_message


class BackendRevampTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls._db_path = Path(cls._tmpdir.name) / "test.db"
        cls._original_database_url = os.environ.get("DATABASE_URL")
        cls._original_analytics_write_enabled = os.environ.get("ANALYTICS_WRITE_ENABLED")
        os.environ["DATABASE_URL"] = f"sqlite:///{cls._db_path}"
        os.environ["ANALYTICS_WRITE_ENABLED"] = "true"
        init_db()

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = cls._original_database_url
        if cls._original_analytics_write_enabled is None:
            os.environ.pop("ANALYTICS_WRITE_ENABLED", None)
        else:
            os.environ["ANALYTICS_WRITE_ENABLED"] = cls._original_analytics_write_enabled
        cls._tmpdir.cleanup()

    def test_record_user_message_tracks_first_and_depth(self) -> None:
        session_id = "session-depth-check"
        first = record_user_message(
            SessionMessageRecordRequest(
                session_id=session_id,
                message_text="hello",
                message_origin="manual",
                estimated_input_tokens=2,
            )
        )
        self.assertTrue(first.first_message_recorded)
        self.assertFalse(first.depth_5_reached)
        self.assertEqual(first.message_index_in_session, 1)

        final = None
        for index in range(2, 6):
            final = record_user_message(
                SessionMessageRecordRequest(
                    session_id=session_id,
                    message_text=f"message {index}",
                    message_origin="manual",
                    estimated_input_tokens=2,
                )
            )
        assert final is not None
        self.assertEqual(final.message_index_in_session, 5)
        self.assertTrue(final.depth_5_reached)
        self.assertEqual(final.session.message_count, 5)

    def test_record_user_message_enforces_session_message_limit(self) -> None:
        session_id = "session-message-limit"
        for index in range(15):
            result = record_user_message(
                SessionMessageRecordRequest(
                    session_id=session_id,
                    message_text=f"message {index}",
                    message_origin="manual",
                    estimated_input_tokens=2,
                )
            )
        self.assertEqual(result.session.message_count, 15)
        with self.assertRaises(HTTPException) as exc:
            record_user_message(
                SessionMessageRecordRequest(
                    session_id=session_id,
                    message_text="message 16",
                    message_origin="manual",
                    estimated_input_tokens=2,
                )
            )
        self.assertEqual(exc.exception.status_code, 429)

    def test_analytics_event_validation_and_persistence(self) -> None:
        event = log_analytics_event(
            AnalyticsEventCreate(
                session_id="analytics-session",
                event_name="chat_message_sent",
                payload={
                    "message_index_in_session": 1,
                    "message_length": 18,
                    "message_origin": "manual",
                },
            )
        )
        self.assertGreater(event.event_id, 0)
        self.assertEqual(event.event_name, "chat_message_sent")

        with self.assertRaises(ValueError):
            log_analytics_event(
                AnalyticsEventCreate(
                    session_id="analytics-session",
                    event_name="chat_depth_reached",
                    payload={},
                )
            )

    def test_cta_rules_are_one_time_and_rejection_aware(self) -> None:
        mention = should_offer_cta(
            user_message="How can I contact Yixin about this?",
            message_index=2,
            cta_already_mentioned=False,
            cta_rejected=False,
        )
        self.assertIsNotNone(mention)
        self.assertEqual(mention.action_type, "send_message")
        self.assertTrue(detect_cta_rejection("No thanks, do not mention it again."))
        self.assertIsNone(
            should_offer_cta(
                user_message="Can I connect?",
                message_index=6,
                cta_already_mentioned=True,
                cta_rejected=False,
            )
        )

    def test_followups_are_limited(self) -> None:
        citations = [
            Citation(
                experience_id="exp_locomo_benchmarking",
                experience_title="Ran LoCoMo and EverMemBenchmark across matched configurations",
                snippet="Executed long-memory benchmarks with carefully aligned prompts.",
                score=0.91,
            )
        ]
        questions = build_follow_up_questions(
            user_message="What eval work did Yixin do?",
            active_topic_id="topic_eval",
            active_topics=["topic_eval", "topic_memory_architecture"],
            citations=citations,
        )
        topics = build_adjacent_topics(
            active_topic_id="topic_eval",
            active_topics=["topic_eval"],
            citations=citations,
        )
        self.assertLessEqual(len(questions), 3)
        self.assertLessEqual(len(topics), 3)
        self.assertTrue(any("LoCoMo and EverMemBenchmark" in question for question in questions))
        self.assertFalse(any("What experience does Yixin have with eval?" == question for question in questions))

    def test_chat_endpoint_uses_exact_fallback_message(self) -> None:
        snapshot = SessionSnapshot(
            session_id="chat-fallback-session",
            started_at="2026-01-01T00:00:00+00:00",
            last_seen_at="2026-01-01T00:00:00+00:00",
            message_count=1,
            first_message_at="2026-01-01T00:00:00+00:00",
            depth_5_reached_at=None,
            cta_mentioned=False,
            cta_rejected=False,
            active_topic_id=None,
        )
        message_result = SessionMessageRecordResult(
            session=snapshot,
            message_index_in_session=1,
            first_message_recorded=True,
            depth_5_reached=False,
        )
        retrieval_result = RetrievalResult(
            active_topics=[],
            citations=[],
            context_blocks=[],
            top_score=0.05,
            second_score=0.0,
            topics=[],
            edges=[],
        )

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/chat",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }
        request = Request(scope)

        with patch("app.api.chat.record_user_message", return_value=message_result), patch(
            "app.api.chat.touch_session", return_value=snapshot
        ), patch("app.api.chat.hybrid_retrieve", return_value=retrieval_result), patch(
            "app.api.chat.log_analytics_event"
        ), patch("app.api.chat.log_memory_gap"), patch(
            "app.api.chat.record_assistant_response_tokens", return_value=snapshot
        ):
            response = asyncio.run(
                chat_endpoint(
                    ChatRequest(
                        message="What did Yixin do in school?",
                        session_id="chat-fallback-session",
                    ),
                    request,
                    get_settings(),
                )
            )
            self.assertEqual(response.status_code, 200)
            body = asyncio.run(self._read_streaming_body(response))
            for token in ("I ", "am ", "not ", "sure ", "Yixin. ", "different?"):
                self.assertIn(token, body)
            self.assertIn('"session_state"', body)

    def test_chat_endpoint_rejects_messages_over_token_limit(self) -> None:
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/chat",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }
        request = Request(scope)

        with self.assertRaises(HTTPException) as exc:
            asyncio.run(
                chat_endpoint(
                    ChatRequest(message="x" * 7000, session_id="token-limit-session"),
                    request,
                    get_settings(),
                )
            )
        self.assertEqual(exc.exception.status_code, 413)

    def test_contact_message_writes_boolean_for_chat_history_flag(self) -> None:
        captured: dict[str, object] = {}

        class FakeCursor:
            def fetchone(self):
                return {"message_id": 42}

        class FakeConn:
            def execute(self, query, params=()):
                captured["query"] = query
                captured["params"] = params
                return FakeCursor()

            def commit(self):
                captured["committed"] = True

        class FakeConnManager:
            def __enter__(self):
                return FakeConn()

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch("app.services.contact.ensure_session"), patch(
            "app.services.contact.get_conn", return_value=FakeConnManager()
        ):
            response = create_contact_message(
                ContactMessageRequest(
                    session_id="contact-session",
                    message_body="hello there",
                    included_chat_history=True,
                    conversation_history=[],
                    message_count_before_send=3,
                )
            )

        self.assertEqual(response.message_id, 42)
        self.assertIn("params", captured)
        self.assertIs(captured["params"][2], False)
        self.assertTrue(captured.get("committed", False))

    async def _read_streaming_body(self, response) -> str:
        chunks: list[str] = []
        async for chunk in response.body_iterator:
            chunks.append(chunk.decode() if isinstance(chunk, bytes) else str(chunk))
        return "".join(chunks)


if __name__ == "__main__":
    unittest.main()
