"""Action and contact API models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .chat import ChatMessage

ActionType = Literal["linkedin", "send_message", "download_resume", "schedule_time"]


class ActionTrackRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message_count_before_action: int = Field(default=0, ge=0, le=1000)
    target_url: str | None = Field(default=None, max_length=1024)


class ResumeDownloadRequest(ActionTrackRequest):
    resume_variant: str = Field(default="default", min_length=1, max_length=64)


class ActionTrackResponse(BaseModel):
    action_type: ActionType
    tracked: bool = True
    target_url: str | None = None
    tracked_at: str


class ContactMessageRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message_body: str = Field(min_length=1, max_length=8000)
    included_chat_history: bool = False
    conversation_history: list[ChatMessage] = Field(default_factory=list)
    message_count_before_send: int = Field(default=0, ge=0, le=1000)


class ContactMessageResponse(BaseModel):
    message_id: int
    delivery_status: str
    included_chat_history: bool
    created_at: str
