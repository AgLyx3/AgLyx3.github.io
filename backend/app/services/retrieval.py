"""Hybrid retrieval over the persisted topic/experience graph."""

from dataclasses import dataclass
import json
from math import fsum
import re
from typing import Iterable

from app.models import (
    Citation,
    ExperienceNode,
    ProfileMemoryField,
    ProfileMemoryRecord,
    RelevanceEdge,
    StructuredMemoryView,
    TopicNode,
)
from app.services.db import get_conn


@dataclass(frozen=True)
class RetrievalItem:
    citation: Citation
    topic_ids: list[str]


@dataclass(frozen=True)
class RetrievalResult:
    active_topics: list[str]
    citations: list[Citation]
    context_blocks: list[str]
    top_score: float
    second_score: float
    topics: list  # list[TopicNode] — passed to followups to avoid a second DB round-trip
    edges: list   # list[RelevanceEdge]


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"\W+", text.lower()) if token]


def _overlap_score(query_tokens: Iterable[str], candidate_text: str) -> float:
    text_tokens = _tokenize(candidate_text)
    if not text_tokens:
        return 0.0
    overlap = sum(1 for token in set(query_tokens) if token in set(text_tokens))
    return overlap / max(1, len(set(text_tokens)))


def _load_structured_json(raw: str | None) -> StructuredMemoryView:
    if not raw:
        return StructuredMemoryView()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return StructuredMemoryView()
    return StructuredMemoryView(
        context=str(parsed.get("context", "")).strip(),
        action=str(parsed.get("action", "")).strip(),
        result=str(parsed.get("result", "")).strip(),
    )


def _load_profile_fields(raw: str | None) -> list[ProfileMemoryField]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    fields: list[ProfileMemoryField] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        value = str(item.get("value", "")).strip()
        if key and value:
            fields.append(ProfileMemoryField(key=key, value=value))
    return fields


def load_graph() -> tuple[list[ProfileMemoryRecord], list[TopicNode], list[ExperienceNode], list[RelevanceEdge]]:
    with get_conn() as conn:
        profile_rows = conn.execute(
            """
            SELECT memory_id, title, raw_context, structured_json, source, confidence, created_at, updated_at
            FROM profile_memories
            ORDER BY created_at, memory_id
            """
        ).fetchall()
        topic_rows = conn.execute(
            "SELECT id, label, description, activation FROM topics ORDER BY label"
        ).fetchall()
        experience_rows = conn.execute(
            """
            SELECT id, title, summary, experience_date, raw_context, structured_json, activation
            FROM experiences
            ORDER BY title
            """
        ).fetchall()
        edge_rows = conn.execute(
            "SELECT source_experience_id, target_topic_id, relevance FROM relevance_edges"
        ).fetchall()

    profile_memories = [
        ProfileMemoryRecord(
            memory_id=row["memory_id"],
            title=row["title"],
            raw_context=row["raw_context"],
            structured_fields=_load_profile_fields(row["structured_json"]),
            source=row["source"],
            confidence=float(row["confidence"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in profile_rows
    ]
    topics = [
        TopicNode(
            id=row["id"],
            label=row["label"],
            description=row["description"],
            activation=float(row["activation"]),
        )
        for row in topic_rows
    ]
    experiences = [
        ExperienceNode(
            id=row["id"],
            title=row["title"],
            summary=row["summary"],
            experience_date=row["experience_date"],
            raw_context=row["raw_context"],
            structured_json=_load_structured_json(row["structured_json"]),
            activation=float(row["activation"]),
        )
        for row in experience_rows
    ]
    edges = [
        RelevanceEdge(
            source_experience_id=row["source_experience_id"],
            target_topic_id=row["target_topic_id"],
            relevance=float(row["relevance"]),
        )
        for row in edge_rows
    ]
    return profile_memories, topics, experiences, edges


def _topic_distribution(query_tokens: Iterable[str], topics: list[TopicNode]) -> dict[str, float]:
    scored = {}
    joined = " ".join(query_tokens)
    for topic in topics:
        score = _overlap_score(query_tokens, f"{topic.label} {topic.description}")
        if topic.id == "topic_memory" and "memory" in joined:
            score += 0.2
        scored[topic.id] = score
    total = fsum(scored.values()) or 1.0
    return {topic_id: value / total for topic_id, value in scored.items()}


def _experience_topic_weight(experience_id: str, topic_id: str, edges: list[RelevanceEdge]) -> float:
    for edge in edges:
        if edge.source_experience_id == experience_id and edge.target_topic_id == topic_id:
            return edge.relevance
    return 0.0


def hybrid_retrieve(query: str, limit: int = 3) -> RetrievalResult:
    _, topics, experiences, edges = load_graph()
    query_tokens = _tokenize(query)
    topic_weights = _topic_distribution(query_tokens, topics)
    ranked: list[tuple[float, RetrievalItem]] = []

    for exp in experiences:
        # bm25: title+summary (concise); semantic proxy: raw_context (richer)
        bm25 = _overlap_score(query_tokens, exp.title)
        semantic = _overlap_score(query_tokens, exp.raw_context)
        hybrid = 0.6 * bm25 + 0.4 * semantic
        topic_boost = sum(
            topic_weights.get(topic.id, 0.0) * _experience_topic_weight(exp.id, topic.id, edges)
            for topic in topics
        )
        final_score = hybrid + 0.35 * topic_boost
        related_topics = [
            edge.target_topic_id
            for edge in edges
            if edge.source_experience_id == exp.id and edge.relevance >= 0.35
        ]
        ranked.append(
            (
                final_score,
                RetrievalItem(
                    citation=Citation(
                        experience_id=exp.id,
                        experience_title=exp.title,
                        snippet=exp.raw_context,
                        score=round(final_score, 4),
                    ),
                    topic_ids=related_topics,
                ),
            )
        )

    ranked.sort(key=lambda row: row[0], reverse=True)
    selected = ranked[:limit]
    top_score = selected[0][0] if selected else 0.0
    second_score = selected[1][0] if len(selected) > 1 else 0.0
    citations = [item.citation for _, item in selected]
    active_topics = sorted({topic_id for _, item in selected for topic_id in item.topic_ids})
    context_blocks = [
        f"{citation.experience_title}: {citation.snippet}" for citation in citations
    ]
    return RetrievalResult(
        active_topics=active_topics,
        citations=citations,
        context_blocks=context_blocks,
        top_score=top_score,
        second_score=second_score,
        topics=topics,
        edges=edges,
    )
