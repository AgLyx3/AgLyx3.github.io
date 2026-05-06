"""Graph API request/response models."""

from pydantic import BaseModel

from .core import ExperienceNode, ProfileMemoryRecord, RelevanceEdge, TopicNode


class GraphResponse(BaseModel):
    profile_memories: list[ProfileMemoryRecord]
    topics: list[TopicNode]
    experiences: list[ExperienceNode]
    edges: list[RelevanceEdge]
