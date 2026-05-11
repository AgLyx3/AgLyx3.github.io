"""Core domain models for topics, experiences, profile memories, and graph edges."""

from pydantic import BaseModel, Field


class TopicNode(BaseModel):
    id: str
    type: str = "topic"
    label: str
    description: str
    base_weight: float = 0.0
    activation: float = 0.0


class ExperienceNode(BaseModel):
    id: str
    type: str = "experience"
    title: str
    experience_date: str = ""
    raw_context: str = ""
    base_weight: float = 0.0
    activation: float = 0.0


class RelevanceEdge(BaseModel):
    source_experience_id: str = Field(description="Experience node id")
    target_topic_id: str = Field(description="Topic node id")
    relevance: float = Field(ge=0.0, le=1.0)


class ProfileMemoryRecord(BaseModel):
    memory_id: str
    key: str
    value: str
    created_at: str
