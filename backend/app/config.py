"""Application configuration for the backend service."""

from dataclasses import dataclass
import os
from typing import List


@dataclass(frozen=True)
class Settings:
    """Runtime settings with safe defaults for local development."""

    app_name: str = "Portfolio Graph Memory API"
    app_version: str = "0.1.0"
    cors_allow_origins: List[str] = None
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = None
    cors_allow_headers: List[str] = None

    candidate_min_distinct_sessions: int = 5
    candidate_time_window_days: int = 7
    candidate_max_confidence_to_existing_topic: float = 0.45
    candidate_auto_approve_topics: bool = True
    topic_labeler_model: str = "gpt-4o-mini"
    topic_labeler_api_base: str = "https://api.openai.com/v1"
    topic_labeler_timeout_seconds: int = 20
    chat_model: str = "gpt-4o-mini"
    chat_api_base: str = "https://api.openai.com/v1"
    chat_timeout_seconds: int = 30
    database_url: str = "sqlite:///backend/data/app.db"
    retrieval_top_k: int = 3
    retrieval_min_top_score: float = 0.22
    retrieval_min_score_gap: float = 0.04
    activation_min_top_score: float = 0.5
    activation_min_citation_score: float = 0.35
    rate_limit_per_minute: int = 60
    max_request_size_bytes: int = 32_768
    activation_increment_alpha: float = 1.0


def _parse_csv(value: str | None, fallback: List[str]) -> List[str]:
    if not value:
        return fallback
    return [part.strip() for part in value.split(",") if part.strip()]


def get_settings() -> Settings:
    """Return settings object used by the app."""
    return Settings(
        cors_allow_origins=_parse_csv(os.getenv("CORS_ALLOW_ORIGINS"), ["*"]),
        cors_allow_methods=_parse_csv(os.getenv("CORS_ALLOW_METHODS"), ["*"]),
        cors_allow_headers=_parse_csv(os.getenv("CORS_ALLOW_HEADERS"), ["*"]),
        cors_allow_credentials=os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
        candidate_min_distinct_sessions=int(os.getenv("CANDIDATE_MIN_DISTINCT_SESSIONS", "5")),
        candidate_time_window_days=int(os.getenv("CANDIDATE_TIME_WINDOW_DAYS", "7")),
        candidate_max_confidence_to_existing_topic=float(
            os.getenv("CANDIDATE_MAX_CONFIDENCE_TO_EXISTING_TOPIC", "0.45")
        ),
        candidate_auto_approve_topics=os.getenv("CANDIDATE_AUTO_APPROVE_TOPICS", "true").lower()
        == "true",
        topic_labeler_model=os.getenv("TOPIC_LABELER_MODEL", "gpt-4o-mini"),
        topic_labeler_api_base=os.getenv("TOPIC_LABELER_API_BASE", "https://api.openai.com/v1"),
        topic_labeler_timeout_seconds=int(os.getenv("TOPIC_LABELER_TIMEOUT_SECONDS", "20")),
        chat_model=os.getenv("CHAT_MODEL", "gpt-4o-mini"),
        chat_api_base=os.getenv("CHAT_API_BASE", "https://api.openai.com/v1"),
        chat_timeout_seconds=int(os.getenv("CHAT_TIMEOUT_SECONDS", "30")),
        database_url=os.getenv("DATABASE_URL", "sqlite:///backend/data/app.db"),
        retrieval_top_k=int(os.getenv("RETRIEVAL_TOP_K", "3")),
        retrieval_min_top_score=float(os.getenv("RETRIEVAL_MIN_TOP_SCORE", "0.22")),
        retrieval_min_score_gap=float(os.getenv("RETRIEVAL_MIN_SCORE_GAP", "0.04")),
        activation_min_top_score=float(os.getenv("ACTIVATION_MIN_TOP_SCORE", "0.5")),
        activation_min_citation_score=float(os.getenv("ACTIVATION_MIN_CITATION_SCORE", "0.35")),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        max_request_size_bytes=int(os.getenv("MAX_REQUEST_SIZE_BYTES", "32768")),
        activation_increment_alpha=float(os.getenv("ACTIVATION_INCREMENT_ALPHA", "1.0")),
    )
