"""Analytics and lightweight session models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

AnalyticsEventName = Literal[
    "topic_prefill_clicked",
    "chat_first_message_sent",
    "chat_message_sent",
    "chat_depth_reached",
    "cta_footer_clicked",
    "message_sent_to_yixin",
    "resume_download_started",
    "linkedin_profile_opened",
    "schedule_time_opened",
    "visitor_ask_back_answered",
    "chat_ask_back_sent",
]

MessageOrigin = Literal["topic_prefill", "manual", "suggestion_question", "suggestion_topic"]


class AnalyticsEventCreate(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    event_name: AnalyticsEventName
    payload: dict[str, Any] = Field(default_factory=dict)


class AnalyticsEventRecord(BaseModel):
    event_id: int
    session_id: str
    event_name: AnalyticsEventName
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class AnalyticsIngestResponse(BaseModel):
    accepted: bool = True
    event: AnalyticsEventRecord


class SessionSnapshot(BaseModel):
    session_id: str
    started_at: str
    last_seen_at: str
    message_count: int = Field(ge=0)
    total_token_count: int = Field(default=0, ge=0)
    input_token_count: int = Field(default=0, ge=0)
    output_token_count: int = Field(default=0, ge=0)
    first_message_at: str | None = None
    depth_5_reached_at: str | None = None
    cta_mentioned: bool = False
    cta_rejected: bool = False
    active_topic_id: str | None = None
    last_ask_back_round: int = Field(default=0, ge=0)
    ask_back_pending: bool = False
    visitor_profile: str | None = None


class SessionEnsureRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    active_topic_id: str | None = Field(default=None, max_length=128)


class SessionTouchRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    active_topic_id: str | None = Field(default=None, max_length=128)
    cta_mentioned: bool | None = None
    cta_rejected: bool | None = None


class SessionMessageRecordRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message_text: str = Field(min_length=1, max_length=8000)
    message_origin: MessageOrigin = "manual"
    active_topic_id: str | None = Field(default=None, max_length=128)
    estimated_input_tokens: int = Field(default=0, ge=0)


class SessionMessageRecordResult(BaseModel):
    session: SessionSnapshot
    message_index_in_session: int = Field(ge=1)
    first_message_recorded: bool = False
    depth_5_reached: bool = False


class _EventPayloadRequirements(BaseModel):
    required_fields: tuple[str, ...]


EVENT_PAYLOAD_REQUIREMENTS: dict[AnalyticsEventName, _EventPayloadRequirements] = {
    "topic_prefill_clicked": _EventPayloadRequirements(
        required_fields=("topic_id", "topic_label", "prefill_text")
    ),
    "chat_first_message_sent": _EventPayloadRequirements(
        required_fields=("message_text", "message_length", "message_origin")
    ),
    "chat_message_sent": _EventPayloadRequirements(
        required_fields=("message_index_in_session", "message_length", "message_origin")
    ),
    "chat_depth_reached": _EventPayloadRequirements(required_fields=("message_count",)),
    "cta_footer_clicked": _EventPayloadRequirements(
        required_fields=("action_type", "message_count_before_action")
    ),
    "message_sent_to_yixin": _EventPayloadRequirements(
        required_fields=(
            "included_chat_history",
            "message_length",
            "message_count_before_send",
        )
    ),
    "resume_download_started": _EventPayloadRequirements(
        required_fields=("resume_variant", "message_count_before_action")
    ),
    "linkedin_profile_opened": _EventPayloadRequirements(
        required_fields=("message_count_before_action",)
    ),
    "schedule_time_opened": _EventPayloadRequirements(
        required_fields=("message_count_before_action",)
    ),
}


class AnalyticsEventValidation(BaseModel):
    event_name: AnalyticsEventName
    payload: dict[str, Any]

    @model_validator(mode="after")
    def check_required_fields(self) -> "AnalyticsEventValidation":
        required = EVENT_PAYLOAD_REQUIREMENTS[self.event_name].required_fields
        missing = [field for field in required if field not in self.payload]
        if missing:
            raise ValueError(f"Missing payload fields for {self.event_name}: {', '.join(missing)}")
        return self
