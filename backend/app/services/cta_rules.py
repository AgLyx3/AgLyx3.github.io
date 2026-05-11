"""Deterministic CTA eligibility rules for portfolio chat."""

from __future__ import annotations

from app.models import CTAMention

CONTACT_INTENT_TERMS = (
    "contact",
    "email",
    "reach out",
    "message",
    "talk",
    "connect",
    "interview",
    "resume",
    "linkedin",
)

REJECTION_TERMS = (
    "no thanks",
    "not now",
    "no need",
    "don't",
    "do not",
    "stop",
    "nah",
)


def detect_cta_rejection(user_message: str) -> bool:
    normalized = user_message.casefold()
    return any(term in normalized for term in REJECTION_TERMS)


def should_offer_cta(
    *,
    user_message: str,
    message_index: int | None,
    cta_already_mentioned: bool,
    cta_rejected: bool,
) -> CTAMention | None:
    """Return a single in-chat CTA mention or None.

    Footer actions are always available in the UI. This rule exists only for the
    one-time in-chat mention defined in the PRD.
    """

    if cta_already_mentioned or cta_rejected:
        return None

    normalized = user_message.casefold()
    explicit_contact_intent = any(term in normalized for term in CONTACT_INTENT_TERMS)

    if explicit_contact_intent:
        return CTAMention(
            action_type="send_message",
            label="Send message",
            message="If this sounds relevant, the visitor can send Yixin a message directly from the portfolio.",
            href="#send-message",
        )
    if (message_index or 0) >= 5:
        return CTAMention(
            action_type="send_message",
            label="Send message",
            message="If the visitor wants to continue the conversation, they can send Yixin a direct message from the portfolio.",
            href="#send-message",
        )
    return None
