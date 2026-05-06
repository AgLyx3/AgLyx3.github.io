"""Service module exports."""

from .activation import apply_decay, get_activation_snapshot, update_activation
from .db import init_db
from .llm import generate_chat_answer
from .retrieval import hybrid_retrieve, load_graph
from .safety import RateLimiter, enforce_request_size, sanitize_text
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
    "apply_decay",
    "init_db",
    "enforce_request_size",
    "generate_chat_answer",
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
    "update_activation",
]
