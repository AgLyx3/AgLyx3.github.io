"""Chat API models."""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

_IMAGE_URL_RE = re.compile(
    r"^https?://\S+\.(?:png|jpe?g|gif|webp|svg|bmp|avif)(?:\?\S*)?$",
    re.IGNORECASE,
)


def _is_non_text_history_content(content: str) -> bool:
    text = content.strip()
    if not text:
        return True
    lowered = text.casefold()
    if lowered.startswith("<image"):
        return True
    if lowered.startswith("!["):
        return True
    if lowered.startswith("[image #"):
        return True
    if lowered.startswith("data:image/"):
        return True
    if _IMAGE_URL_RE.match(text):
        return True
    return False


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: Optional[str] = Field(default=None, max_length=128)
    history: list[ChatMessage] = Field(default_factory=list)
    active_topic_id: Optional[str] = Field(default=None, max_length=128)
    prefill_origin: Optional[
        Literal["topic_prefill", "manual", "suggestion_question", "suggestion_topic"]
    ] = None
    message_index: Optional[int] = Field(default=None, ge=1, le=1000)
    cta_already_mentioned: bool = False
    cta_rejected: bool = False
    viewport_width: Optional[int] = Field(default=None, ge=1, le=10000)

    @model_validator(mode="after")
    def normalize_history(self) -> "ChatRequest":
        text_history = [
            ChatMessage(role=msg.role, content=msg.content.strip())
            for msg in self.history
            if not _is_non_text_history_content(msg.content)
        ]
        self.history = text_history[-8:]
        return self


class Citation(BaseModel):
    experience_id: str
    experience_title: str
    snippet: str
    score: float
    key_concepts: list[str] = Field(default_factory=list)


class MediaItem(BaseModel):
    id: int
    url: str
    media_type: str
    caption: str | None = None


class TopicSuggestion(BaseModel):
    topic_id: str
    label: str


class CTAMention(BaseModel):
    action_type: Literal["linkedin", "send_message", "download_resume", "schedule_time"]
    label: str
    message: str
    href: str | None = Field(default=None, max_length=512)


class ChatSessionState(BaseModel):
    session_id: Optional[str] = None
    active_topic_id: Optional[str] = None
    prefill_origin: Optional[
        Literal["topic_prefill", "manual", "suggestion_question", "suggestion_topic"]
    ] = None
    message_index: Optional[int] = Field(default=None, ge=1, le=1000)
    cta_already_mentioned: bool = False
    cta_rejected: bool = False
    first_message_recorded: bool = False
    depth_5_reached: bool = False


class ChatFinalMetadata(BaseModel):
    active_topics: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list, max_length=3)
    adjacent_topics: list[TopicSuggestion] = Field(default_factory=list, max_length=3)
    cta_mention: Optional[CTAMention] = None
    session_state: Optional[ChatSessionState] = None
    route: Optional[Literal["small_talk", "memory"]] = None
    memory_sources: list[Literal["profile", "experience"]] = Field(default_factory=list)
    response_mode: Optional[Literal["small_talk", "profile", "experience", "blended"]] = None
    media: Optional[MediaItem] = None
    highlight_terms: list[str] = Field(default_factory=list)
