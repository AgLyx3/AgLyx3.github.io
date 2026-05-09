"""Deterministic follow-up generation for the portfolio chat experience."""

from __future__ import annotations

from app.models import Citation, TopicSuggestion
from app.services.retrieval import load_graph

MAX_FOLLOWUPS = 3


def _normalize_topic_label(label: str) -> str:
    return " ".join(label.strip().split())


_GERUND_PREFIXES = {
    "Built ": "building ",
    "Ran ": "running ",
    "Designed ": "designing ",
    "Interviewed ": "interviewing ",
    "Wrote ": "writing ",
    "Won ": "winning ",
    "Worked ": "working ",
}


def _title_to_follow_up(title: str, index: int) -> str:
    cleaned = " ".join(title.strip().split()).rstrip(".")
    for prefix, gerund in _GERUND_PREFIXES.items():
        if cleaned.startswith(prefix):
            phrase = gerund + cleaned[len(prefix) :].strip()
            if index == 0:
                return f"What did Yixin learn from {phrase}?"
            if index == 1:
                return f"How did Yixin approach {phrase}?"
            return f"How did {phrase} connect to Yixin's broader work?"
    lowered = cleaned[:1].lower() + cleaned[1:] if cleaned else cleaned
    if index == 0:
        return f"Can you tell me more about {lowered}?"
    if index == 1:
        return f"What did Yixin learn from {lowered}?"
    return f"How does {lowered} connect to Yixin's broader work?"


def build_follow_up_questions(
    *,
    user_message: str,
    active_topic_id: str | None,
    active_topics: list[str],
    citations: list[Citation],
    topics: list | None = None,
    limit: int = MAX_FOLLOWUPS,
) -> list[str]:
    """Return up to three concise adjacent questions."""

    if topics is None:
        _, topics, _, _ = load_graph()
    topic_labels = {topic.id: _normalize_topic_label(topic.label) for topic in topics}
    chosen_topic_id = active_topic_id or (active_topics[0] if active_topics else None)
    chosen_topic_label = topic_labels.get(chosen_topic_id or "", "").strip()

    prompts: list[str] = []
    for index, citation in enumerate(citations[:limit]):
        prompts.append(_title_to_follow_up(citation.experience_title, index))
    if not prompts:
        label = chosen_topic_label.lower() if chosen_topic_label else ""
        prompts.extend(
            (
                [
                    f"What experience does Yixin have with {label}?",
                    f"How did Yixin apply {label} in practice?",
                    f"What did Yixin learn from working on {label}?",
                ]
                if label
                else [
                    "What kind of work has Yixin done recently?",
                    "Which topic should I explore next?",
                    "What is a strong example of Yixin's experience?",
                ]
            )
        )

    normalized_message = user_message.casefold().strip()
    unique_prompts: list[str] = []
    seen = {normalized_message}
    for prompt in prompts:
        normalized = prompt.casefold().strip()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_prompts.append(prompt)
        if len(unique_prompts) >= limit:
            break
    return unique_prompts


def build_adjacent_topics(
    *,
    active_topic_id: str | None,
    active_topics: list[str],
    citations: list[Citation],
    topics: list | None = None,
    edges: list | None = None,
    limit: int = MAX_FOLLOWUPS,
) -> list[TopicSuggestion]:
    """Return up to three adjacent topics based on cited experiences."""

    if topics is None or edges is None:
        _, topics, _, edges = load_graph()
    topic_by_id = {topic.id: topic for topic in topics}
    selected_topics = [topic_id for topic_id in [active_topic_id, *active_topics] if topic_id]
    excluded = set(selected_topics)

    weighted: dict[str, float] = {}
    citation_scores = {citation.experience_id: citation.score for citation in citations}
    for edge in edges:
        if edge.source_experience_id not in citation_scores:
            continue
        if edge.target_topic_id in excluded:
            continue
        weighted[edge.target_topic_id] = weighted.get(edge.target_topic_id, 0.0) + (
            citation_scores[edge.source_experience_id] * edge.relevance
        )

    ranked = sorted(weighted.items(), key=lambda item: item[1], reverse=True)
    suggestions: list[TopicSuggestion] = []
    for topic_id, _score in ranked:
        topic = topic_by_id.get(topic_id)
        if not topic:
            continue
        suggestions.append(TopicSuggestion(topic_id=topic.id, label=topic.label))
        if len(suggestions) >= limit:
            break
    return suggestions
