"""Hybrid retrieval over the persisted topic/experience graph."""

from collections import defaultdict
from dataclasses import dataclass
from math import fsum
import re
from typing import Iterable

from app.models import Citation, ExperienceNode, ProfileMemoryRecord, RelevanceEdge, TopicNode
from app.services.db import get_conn


@dataclass(frozen=True)
class RetrievalItem:
    base_score: float
    citation: Citation
    topic_ids: list[str]


@dataclass(frozen=True)
class ScoredExperience:
    experience: ExperienceNode
    base_score: float
    topic_ids: list[str]


@dataclass(frozen=True)
class ProfileRetrievalResult:
    context_blocks: list[str]
    top_score: float
    matches: list[ProfileMemoryRecord]


@dataclass(frozen=True)
class CombinedMemoryRetrievalResult:
    profile: ProfileRetrievalResult
    experience: RetrievalResult


@dataclass(frozen=True)
class RetrievalResult:
    active_topics: list[str]
    citations: list[Citation]
    context_blocks: list[str]
    top_score: float
    second_score: float
    topics: list  # list[TopicNode] — passed to followups to avoid a second DB round-trip
    edges: list   # list[RelevanceEdge]


_STOP_WORDS = frozenset([
    "a", "an", "the", "and", "or", "for", "in", "is", "was", "are",
    "have", "has", "had", "be", "been", "being", "to", "from", "of",
    "on", "by", "at", "as", "with", "it", "its", "we", "i", "s", "t",
    "what", "how", "who", "where", "when", "why", "which",
    "did", "do", "does", "can", "could", "would", "should", "will",
    "you", "your", "her", "his", "their", "our", "my",
    "tell", "me", "about", "some", "any", "this", "that",
    "kind", "type", "like", "just", "very", "also", "work",
])

_SYNONYMS: dict[str, str] = {
    "pm": "product manager",
    "ml": "machine learning",
    "eng": "engineering",
    "nlp": "natural language processing",
}

_PROFILE_KEY_SYNONYMS: dict[str, frozenset[str]] = {
    "current_role": frozenset({"current", "role", "job", "title", "work", "works", "working", "company"}),
    "education": frozenset({"education", "degree", "studied", "study", "major", "college", "colby", "university", "graduate", "graduated"}),
    "interests": frozenset({"interest", "interests", "hobby", "hobbies", "outside", "personal", "free", "spare"}),
}

_BROAD_TOPIC_PATTERNS = (
    re.compile(r"\bwhat kind of\b"),
    re.compile(r"\bwhat types of\b"),
    re.compile(r"\bwhat experience do you have\b"),
    re.compile(r"\bwhat did you do\b"),
    re.compile(r"\bwhat have you built\b"),
    re.compile(r"\btell me about your\b"),
)

_GENERAL_WORK_QUERY_PATTERNS = (
    re.compile(r"\btell me about (her|yixin)(?:\s+li)?\b"),
    re.compile(r"\bwhat does (she|yixin)(?:\s+li)? do\b"),
    re.compile(r"\bwhat(?:'s| is)\s+(?:yixin's|her)\s+(?:role|job)\b"),
    re.compile(r"\bwhat (?:does |did )?(she|yixin)(?:\s+li)? work on\b"),
    re.compile(r"\bwhat (?:has |did )?(she|yixin)(?:\s+li)? build\b"),
    re.compile(r"\bwhat projects?(?: has)? (?:she|yixin)(?:\s+li)?(?: worked on| done)?\b"),
    re.compile(r"\bwhat projects?\b"),
    re.compile(r"\bwhat kind of work\b"),
)


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"\W+", text.lower()) if token]


def _meaningful_tokens(tokens: Iterable[str]) -> frozenset[str]:
    return frozenset(t for t in tokens if t not in _STOP_WORDS and len(t) > 1)


def _expand_query(text: str) -> str:
    """Append full forms of abbreviations without removing the original token."""
    additions = [_SYNONYMS[t] for t in _tokenize(text) if t in _SYNONYMS]
    return (text + " " + " ".join(additions)).strip() if additions else text


def _overlap_score(query_tokens: Iterable[str], candidate_text: str) -> float:
    """Precision-style: overlap / doc_token_count. Used for BM25 title match."""
    text_tokens = _tokenize(candidate_text)
    if not text_tokens:
        return 0.0
    overlap = sum(1 for token in set(query_tokens) if token in set(text_tokens))
    return overlap / max(1, len(set(text_tokens)))


def _recall_score(query_tokens: Iterable[str], candidate_text: str) -> float:
    """Recall-style: meaningful_overlap / meaningful_query_count. Used for semantic match."""
    q_meaningful = _meaningful_tokens(query_tokens)
    if not q_meaningful:
        return 0.0
    text_tokens = set(_tokenize(candidate_text))
    return sum(1 for t in q_meaningful if t in text_tokens) / len(q_meaningful)


def _profile_key_boost(query_tokens: Iterable[str], key: str) -> float:
    tokens = set(_meaningful_tokens(query_tokens))
    if not tokens:
        return 0.0
    boost = 0.0
    normalized_key = key.lower().strip()
    for candidate_key, related_tokens in _PROFILE_KEY_SYNONYMS.items():
        if normalized_key != candidate_key:
            continue
        overlap = tokens & related_tokens
        if overlap:
            boost = max(boost, 0.08 + 0.04 * len(overlap))
    return boost


def _is_broad_topic_query(query: str) -> bool:
    normalized = " ".join(query.lower().split())
    return any(pattern.search(normalized) for pattern in _BROAD_TOPIC_PATTERNS)


def is_general_work_query(query: str) -> bool:
    normalized = " ".join(query.lower().split())
    return any(pattern.search(normalized) for pattern in _GENERAL_WORK_QUERY_PATTERNS)


def load_graph() -> tuple[list[ProfileMemoryRecord], list[TopicNode], list[ExperienceNode], list[RelevanceEdge]]:
    with get_conn() as conn:
        profile_rows = conn.execute(
            """
            SELECT memory_id, key, value, created_at
            FROM profile_memories
            ORDER BY created_at, memory_id
            """
        ).fetchall()
        topic_rows = conn.execute(
            "SELECT id, label, description, activation FROM topics ORDER BY label"
        ).fetchall()
        experience_rows = conn.execute(
            """
            SELECT id, title, raw_context, experience_date, activation
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
            key=row["key"],
            value=row["value"],
            created_at=row["created_at"],
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
            experience_date=row["experience_date"],
            raw_context=row["raw_context"],
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
    meaningful = _meaningful_tokens(query_tokens)
    joined = " ".join(query_tokens)
    scored = {}
    for topic in topics:
        candidate = f"{topic.id} {topic.label} {topic.description}"
        score = _overlap_score(meaningful, candidate) if meaningful else 0.0
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


def _topic_ids_for_experience(experience_id: str, edges: list[RelevanceEdge]) -> list[str]:
    return [
        edge.target_topic_id
        for edge in edges
        if edge.source_experience_id == experience_id and edge.relevance >= 0.35
    ]


def _score_experiences(
    *,
    query_tokens: list[str],
    query_topic_weights: dict[str, float],
    topics: list[TopicNode],
    experiences: list[ExperienceNode],
    edges: list[RelevanceEdge],
) -> list[ScoredExperience]:
    ranked: list[ScoredExperience] = []
    q_meaningful = _meaningful_tokens(query_tokens)

    for exp in experiences:
        # bm25: meaningful-token precision on title; semantic: recall on raw_context
        bm25 = _overlap_score(q_meaningful, exp.title)
        semantic = _recall_score(query_tokens, exp.raw_context)
        hybrid = 0.6 * bm25 + 0.4 * semantic
        topic_boost = sum(
            query_topic_weights.get(topic.id, 0.0) * _experience_topic_weight(exp.id, topic.id, edges)
            for topic in topics
        )
        final_score = hybrid + 0.35 * topic_boost
        ranked.append(
            ScoredExperience(
                experience=exp,
                base_score=final_score,
                topic_ids=_topic_ids_for_experience(exp.id, edges),
            )
        )

    ranked.sort(key=lambda row: row.base_score, reverse=True)
    return ranked


def _infer_dominant_topic(
    *,
    query_tokens: list[str],
    topics: list[TopicNode],
    experiences: list[ExperienceNode],
    edges: list[RelevanceEdge],
) -> tuple[str | None, bool]:
    query_topic_weights = _topic_distribution(query_tokens, topics)
    ranked_query_topics = sorted(query_topic_weights.items(), key=lambda row: row[1], reverse=True)
    if ranked_query_topics and ranked_query_topics[0][1] > 0:
        top_topic, top_weight = ranked_query_topics[0]
        second_weight = ranked_query_topics[1][1] if len(ranked_query_topics) > 1 else 0.0
        if second_weight == 0 or top_weight >= second_weight * 1.1:
            return top_topic, True

    meaningful = _meaningful_tokens(query_tokens)
    topic_scores: defaultdict[str, float] = defaultdict(float)

    for exp in experiences:
        bm25 = _overlap_score(meaningful, exp.title)
        semantic = _recall_score(query_tokens, exp.raw_context)
        hybrid = 0.6 * bm25 + 0.4 * semantic
        if hybrid <= 0:
            continue
        for edge in edges:
            if edge.source_experience_id == exp.id and edge.relevance > 0:
                topic_scores[edge.target_topic_id] += hybrid * edge.relevance

    if not topic_scores:
        return None, False

    ranked_topics = sorted(topic_scores.items(), key=lambda row: row[1], reverse=True)
    top_topic, top_score = ranked_topics[0]
    second_score = ranked_topics[1][1] if len(ranked_topics) > 1 else 0.0
    if top_score <= 0:
        return None, False
    if second_score and top_score < second_score * 1.1:
        return None, False
    return top_topic, False


def _title_similarity(left: str, right: str) -> float:
    left_tokens = _meaningful_tokens(_tokenize(left))
    right_tokens = _meaningful_tokens(_tokenize(right))
    if not left_tokens or not right_tokens:
        return 0.0
    union = left_tokens | right_tokens
    if not union:
        return 0.0
    return len(left_tokens & right_tokens) / len(union)


def _select_broad_topic_results(
    *,
    dominant_topic_id: str,
    ranked: list[ScoredExperience],
    edges: list[RelevanceEdge],
    limit: int,
    query_named_topic: bool,
) -> list[ScoredExperience]:
    candidates = [
        row
        for row in ranked
        if _experience_topic_weight(row.experience.id, dominant_topic_id, edges) > 0
        and (
            _experience_topic_weight(row.experience.id, dominant_topic_id, edges) >= 0.6
            or row.base_score > 0
        )
    ]
    candidates.sort(
        key=lambda row: (
            _experience_topic_weight(row.experience.id, dominant_topic_id, edges),
            row.experience.activation,
            row.base_score,
        ),
        reverse=True,
    )

    selected: list[ScoredExperience] = []
    remaining = list(candidates)
    while remaining and len(selected) < limit:
        best_idx = 0
        best_score = float("-inf")
        for idx, candidate in enumerate(remaining):
            dominant_edge = _experience_topic_weight(candidate.experience.id, dominant_topic_id, edges)
            activation_bonus = candidate.experience.activation / 10.0
            redundancy_penalty = 0.0
            diversity_bonus = 0.0
            if selected:
                max_similarity = max(
                    _title_similarity(candidate.experience.title, prior.experience.title)
                    for prior in selected
                )
                redundancy_penalty = 0.08 * max_similarity
                diversity_bonus = 0.04 * (1.0 - max_similarity)
            if query_named_topic:
                broad_score = (
                    0.72 * dominant_edge
                    + 0.03 * candidate.base_score
                    + 0.25 * activation_bonus
                    + diversity_bonus
                    - redundancy_penalty
                )
            else:
                broad_score = (
                    0.55 * dominant_edge
                    + 0.20 * candidate.base_score
                    + 0.25 * activation_bonus
                    + diversity_bonus
                    - redundancy_penalty
                )
            if broad_score > best_score:
                best_score = broad_score
                best_idx = idx
        selected.append(remaining.pop(best_idx))

    return selected


def _select_general_work_results(
    *,
    ranked: list[ScoredExperience],
    limit: int,
) -> list[ScoredExperience]:
    prioritized = sorted(
        ranked,
        key=lambda row: (
            row.experience.activation,
            row.base_score,
        ),
        reverse=True,
    )
    return prioritized[:limit]


def _hybrid_retrieve_from_graph(
    *,
    query: str,
    topics: list[TopicNode],
    experiences: list[ExperienceNode],
    edges: list[RelevanceEdge],
    limit: int = 3,
) -> RetrievalResult:
    expanded_query = _expand_query(query)
    query_tokens = _tokenize(expanded_query)
    topic_weights = _topic_distribution(query_tokens, topics)
    ranked = _score_experiences(
        query_tokens=query_tokens,
        query_topic_weights=topic_weights,
        topics=topics,
        experiences=experiences,
        edges=edges,
    )

    selected_experiences = ranked[:limit]
    if is_general_work_query(query):
        selected_experiences = _select_general_work_results(ranked=ranked, limit=limit)
    elif _is_broad_topic_query(query):
        dominant_topic_id, query_named_topic = _infer_dominant_topic(
            query_tokens=query_tokens,
            topics=topics,
            experiences=experiences,
            edges=edges,
        )
        if dominant_topic_id is not None:
            topic_selected = _select_broad_topic_results(
                dominant_topic_id=dominant_topic_id,
                ranked=ranked,
                edges=edges,
                limit=limit,
                query_named_topic=query_named_topic,
            )
            if len(topic_selected) == limit:
                selected_experiences = topic_selected

    selected = [
        RetrievalItem(
            base_score=row.base_score,
            citation=Citation(
                experience_id=row.experience.id,
                experience_title=row.experience.title,
                snippet=row.experience.raw_context,
                score=round(row.base_score, 4),
            ),
            topic_ids=row.topic_ids,
        )
        for row in selected_experiences
    ]
    top_score = selected[0].base_score if selected else 0.0
    second_score = selected[1].base_score if len(selected) > 1 else 0.0
    citations = [item.citation for item in selected]
    active_topics = sorted({topic_id for item in selected for topic_id in item.topic_ids})
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


def hybrid_retrieve(
    query: str,
    limit: int = 3,
    *,
    topics: list[TopicNode] | None = None,
    experiences: list[ExperienceNode] | None = None,
    edges: list[RelevanceEdge] | None = None,
) -> RetrievalResult:
    if topics is None or experiences is None or edges is None:
        _, topics, experiences, edges = load_graph()
    return _hybrid_retrieve_from_graph(
        query=query,
        topics=topics,
        experiences=experiences,
        edges=edges,
        limit=limit,
    )


def profile_retrieve(
    query: str,
    limit: int = 3,
    *,
    profile_memories: list[ProfileMemoryRecord] | None = None,
) -> ProfileRetrievalResult:
    """Rank profile memories for the current query."""
    if profile_memories is None:
        profile_memories, _, _, _ = load_graph()

    expanded_query = _expand_query(query)
    query_tokens = _tokenize(expanded_query)
    is_general_work_match = is_general_work_query(query)
    ranked: list[tuple[float, ProfileMemoryRecord]] = []

    for memory in profile_memories:
        candidate_text = f"{memory.key.replace('_', ' ')} {memory.value}"
        score = _recall_score(query_tokens, candidate_text) + _profile_key_boost(query_tokens, memory.key)
        normalized_key = memory.key.lower().strip()
        if is_general_work_match and normalized_key in {"current_role", "currentrole"}:
            score += 0.35
        ranked.append((score, memory))

    ranked.sort(key=lambda row: row[0], reverse=True)
    selected = ranked[:limit]
    return ProfileRetrievalResult(
        context_blocks=[
            f"{memory.key.replace('_', ' ')}: {memory.value}"
            for score, memory in selected
            if score > 0
        ],
        top_score=selected[0][0] if selected else 0.0,
        matches=[memory for score, memory in selected if score > 0],
    )


def combined_memory_retrieve(
    query: str,
    *,
    profile_limit: int = 3,
    experience_limit: int = 3,
) -> CombinedMemoryRetrievalResult:
    profile_memories, topics, experiences, edges = load_graph()
    return CombinedMemoryRetrievalResult(
        profile=profile_retrieve(query, limit=profile_limit, profile_memories=profile_memories),
        experience=_hybrid_retrieve_from_graph(
            query=query,
            topics=topics,
            experiences=experiences,
            edges=edges,
            limit=experience_limit,
        ),
    )
