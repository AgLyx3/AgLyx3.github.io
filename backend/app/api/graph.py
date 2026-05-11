"""Graph API endpoint exposing topic/experience graph with activation."""

from fastapi import APIRouter

from app.models import ExperienceNode, GraphResponse, TopicNode
from app.services import get_activation_snapshot, load_graph

router = APIRouter(tags=["graph"])


@router.get("/graph", response_model=GraphResponse)
def get_graph() -> GraphResponse:
    profile_memories, db_topics, db_experiences, db_edges = load_graph()
    topic_activation, experience_activation = get_activation_snapshot()

    topics = [
        TopicNode(
            id=topic.id,
            label=topic.label,
            description=topic.description,
            activation=round(topic_activation.get(topic.id, topic.activation), 4),
        )
        for topic in db_topics
    ]
    experiences = [
        ExperienceNode(
            id=exp.id,
            title=exp.title,
            experience_date=exp.experience_date,
            raw_context=exp.raw_context,
            activation=round(experience_activation.get(exp.id, exp.activation), 4),
        )
        for exp in db_experiences
    ]
    return GraphResponse(
        profile_memories=profile_memories,
        topics=topics,
        experiences=experiences,
        edges=db_edges,
    )
