"""Chat API models."""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=128)
    history: list[ChatMessage] = Field(default_factory=list)


class Citation(BaseModel):
    experience_id: str
    experience_title: str
    snippet: str
    score: float


class ChatFinalMetadata(BaseModel):
    active_topics: list[str]
    citations: list[Citation]
