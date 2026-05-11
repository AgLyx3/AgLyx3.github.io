"""Application configuration for the backend service."""

from dataclasses import dataclass
import os
from typing import List, Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional for local DX
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


@dataclass(frozen=True)
class Settings:
    """Runtime settings with safe defaults for local development."""

    app_name: str = "Portfolio Graph Memory API"
    app_version: str = "0.1.0"
    cors_allow_origins: Optional[List[str]] = None
    cors_allow_credentials: bool = True
    cors_allow_methods: Optional[List[str]] = None
    cors_allow_headers: Optional[List[str]] = None
    admin_api_key: str = ""

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
    retrieval_strong_top_score: float = 0.35
    profile_retrieval_top_k: int = 3
    profile_retrieval_min_top_score: float = 0.15
    memory_context_max_blocks: int = 6
    activation_min_top_score: float = 0.5
    activation_min_citation_score: float = 0.35
    rate_limit_per_minute: int = 60
    chat_rate_limit_per_minute: int = 6
    max_request_size_bytes: int = 32_768
    max_messages_per_session: int = 30
    max_total_tokens_per_session: int = 20_000
    max_input_tokens_per_message: int = 1_500
    max_output_tokens_per_response: int = 400
    activation_increment_alpha: float = 1.0
    analytics_write_enabled: bool = True
    linkedin_url: str = "https://www.linkedin.com/in/yixin-li-796994280/"
    schedule_url: str = ""
    resume_url: str = "assets/resume.pdf"
    resend_api_key: str = ""
    contact_from_email: str = "onboarding@resend.dev"
    contact_to_email: str = "yixinli.a@gmail.com"


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
        retrieval_strong_top_score=float(os.getenv("RETRIEVAL_STRONG_TOP_SCORE", "0.35")),
        profile_retrieval_top_k=int(os.getenv("PROFILE_RETRIEVAL_TOP_K", "3")),
        profile_retrieval_min_top_score=float(
            os.getenv("PROFILE_RETRIEVAL_MIN_TOP_SCORE", "0.15")
        ),
        memory_context_max_blocks=int(os.getenv("MEMORY_CONTEXT_MAX_BLOCKS", "6")),
        activation_min_top_score=float(os.getenv("ACTIVATION_MIN_TOP_SCORE", "0.5")),
        activation_min_citation_score=float(os.getenv("ACTIVATION_MIN_CITATION_SCORE", "0.35")),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        chat_rate_limit_per_minute=int(os.getenv("CHAT_RATE_LIMIT_PER_MINUTE", "6")),
        max_request_size_bytes=int(os.getenv("MAX_REQUEST_SIZE_BYTES", "32768")),
        max_messages_per_session=int(os.getenv("MAX_MESSAGES_PER_SESSION", "30")),
        max_total_tokens_per_session=int(os.getenv("MAX_TOTAL_TOKENS_PER_SESSION", "20000")),
        max_input_tokens_per_message=int(os.getenv("MAX_INPUT_TOKENS_PER_MESSAGE", "1500")),
        max_output_tokens_per_response=int(os.getenv("MAX_OUTPUT_TOKENS_PER_RESPONSE", "400")),
        activation_increment_alpha=float(os.getenv("ACTIVATION_INCREMENT_ALPHA", "1.0")),
        analytics_write_enabled=os.getenv("ANALYTICS_WRITE_ENABLED", "true").lower() == "true",
        linkedin_url=os.getenv("LINKEDIN_URL", "https://www.linkedin.com/in/yixin-li-796994280/"),
        schedule_url=os.getenv("SCHEDULE_URL", ""),
        resume_url=os.getenv("RESUME_URL", "assets/resume.pdf"),
        admin_api_key=os.getenv("ADMIN_API_KEY", ""),
        resend_api_key=os.getenv("RESEND_API_KEY", ""),
        contact_from_email=os.getenv("CONTACT_FROM_EMAIL", "onboarding@resend.dev"),
        contact_to_email=os.getenv("CONTACT_TO_EMAIL", "yixinli.a@gmail.com"),
    )
