"""Models for topic notifications and memory curation operations."""

from pydantic import BaseModel, Field


class TopicNotification(BaseModel):
    event: str
    created_at: str
    topic_id: str
    topic_name: str
    candidate_id: str
    distinct_sessions: int
    mentions: int


class TopicMemoryCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    details: str = Field(min_length=10, max_length=8000)
    source: str = Field(default="manual")


class TopicMemoryRecord(BaseModel):
    memory_id: str
    topic_id: str
    title: str
    summary: str
    details: str
    source: str
    created_at: str


class TopicPendingMemory(BaseModel):
    topic_id: str
    topic_name: str
    created_at: str
    memory_count: int


class MemoryIngestRequest(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    details: str = Field(min_length=10, max_length=8000)
    source: str = Field(default="manual")
    topic_ids: list[str] | None = None


class MemoryIngestResponse(BaseModel):
    memory_id: str
    experience_id: str
    assigned_topics: list[str]
    assignment_mode: str


class MemoryGapRecord(BaseModel):
    gap_id: int
    query_text: str
    session_id: str
    top_score: float
    score_gap: float
    created_at: str
