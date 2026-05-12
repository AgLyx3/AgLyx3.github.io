"""Service module exports."""

from .activation import apply_decay, get_activation_snapshot, update_activation
from .analytics import log_analytics_event
from .contact import create_contact_message
from .cta_rules import detect_cta_rejection, should_offer_cta
from .db import init_db
from .followups import build_adjacent_topics, build_follow_up_questions
from .llm import MEMORY_FALLBACK_RESPONSE, SMALL_TALK_RESPONSE, generate_chat_answer, generate_small_talk_answer, topic_exploration_hint
from .query_router import ChatRoute, is_visitor_statement, route_query
from .retrieval import (
    CombinedMemoryRetrievalResult,
    ProfileRetrievalResult,
    combined_memory_retrieve,
    hybrid_retrieve,
    is_general_work_query,
    load_graph,
    profile_retrieve,
)
from .safety import RateLimiter, enforce_request_size, estimate_tokens, sanitize_text, truncate_text_to_token_limit
from .session import clear_ask_back_pending, ensure_session, record_ask_back, record_assistant_response_tokens, record_user_message, snooze_ask_back, touch_session, update_visitor_profile
from .topic_ops import (
    create_topic_memory,
    ingest_memory,
    list_memory_gaps,
    list_topic_notifications,
    list_topics_pending_memory,
    log_memory_gap,
)

__all__ = [
    "RateLimiter",
    "MEMORY_FALLBACK_RESPONSE",
    "SMALL_TALK_RESPONSE",
    "CombinedMemoryRetrievalResult",
    "ProfileRetrievalResult",
    "ChatRoute",
    "route_query",
    "combined_memory_retrieve",
    "profile_retrieve",
    "is_general_work_query",
    "apply_decay",
    "build_adjacent_topics",
    "build_follow_up_questions",
    "create_contact_message",
    "detect_cta_rejection",
    "clear_ask_back_pending",
    "ensure_session",
    "record_ask_back",
    "snooze_ask_back",
    "is_visitor_statement",
    "update_visitor_profile",
    "init_db",
    "enforce_request_size",
    "estimate_tokens",
    "generate_chat_answer",
    "generate_small_talk_answer",
    "topic_exploration_hint",
    "get_activation_snapshot",
    "hybrid_retrieve",
    "ingest_memory",
    "load_graph",
    "sanitize_text",
    "create_topic_memory",
    "list_topic_notifications",
    "list_topics_pending_memory",
    "list_memory_gaps",
    "log_memory_gap",
    "log_analytics_event",
    "record_assistant_response_tokens",
    "record_user_message",
    "should_offer_cta",
    "touch_session",
    "truncate_text_to_token_limit",
    "update_activation",
]
