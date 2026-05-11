"""Tests for CTA offer and rejection rules."""

from __future__ import annotations

from app.services.cta_rules import detect_cta_rejection, should_offer_cta


def test_cta_offered_on_contact_intent():
    mention = should_offer_cta(
        user_message="How can I contact Yixin about this?",
        message_index=2,
        cta_already_mentioned=False,
        cta_rejected=False,
    )
    assert mention is not None
    assert mention.action_type == "send_message"
    assert mention.href == "#send-message"


def test_cta_not_repeated_if_already_mentioned():
    assert should_offer_cta(
        user_message="Can I connect?",
        message_index=6,
        cta_already_mentioned=True,
        cta_rejected=False,
    ) is None


def test_cta_not_offered_if_rejected():
    assert should_offer_cta(
        user_message="How can I reach Yixin?",
        message_index=4,
        cta_already_mentioned=False,
        cta_rejected=True,
    ) is None


def test_rejection_phrase_is_detected():
    assert detect_cta_rejection("No thanks, do not mention it again.") is True


def test_non_rejection_phrase_is_not_detected():
    assert detect_cta_rejection("Tell me more about her research.") is False
