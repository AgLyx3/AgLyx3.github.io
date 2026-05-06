"""Core domain models for topics, experiences, profile memories, and graph edges."""

from pydantic import BaseModel, Field


class ProfileMemoryField(BaseModel):
    key: str
    value: str


class StructuredMemoryView(BaseModel):
    context: str = ""
    action: str = ""
    result: str = ""


class TopicNode(BaseModel):
    id: str
    type: str = "topic"
    label: str
    description: str
    activation: float = 0.0


class ExperienceNode(BaseModel):
    id: str
    type: str = "experience"
    title: str
    summary: str
    experience_date: str = ""
    raw_context: str = ""
    structured_json: StructuredMemoryView = Field(default_factory=StructuredMemoryView)
    activation: float = 0.0


class RelevanceEdge(BaseModel):
    source_experience_id: str = Field(description="Experience node id")
    target_topic_id: str = Field(description="Topic node id")
    relevance: float = Field(ge=0.0, le=1.0)


class ProfileMemoryRecord(BaseModel):
    memory_id: str
    title: str
    raw_context: str
    structured_fields: list[ProfileMemoryField]
    source: str
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: str
    updated_at: str
