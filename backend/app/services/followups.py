"""Deterministic follow-up generation for the portfolio chat experience."""

from __future__ import annotations

from app.models import Citation, TopicSuggestion
from app.services.retrieval import load_graph

MAX_FOLLOWUPS = 3

_DEEP_DIVE_QUESTIONS: dict[str, str] = {
    "exp_continua_overview": "What products did Yixin build as PM at Continua AI?",
    "exp_pm_delivery": "What AI agent features did Yixin ship at Continua?",
    "exp_memory_architecture": "How did Yixin measure whether the memory was actually working?",
    "exp_agentic_poll": "How did Yixin track quality and catch issues after launch?",
    "exp_agentic_split": "How did Yixin measure whether these features were working well?",
    "exp_eval_frameworks": "How did Yixin measure whether the memory was actually working?",
    "exp_issue_viewer": "What product quality problems was the issue viewer tracking?",
    "exp_customer_discovery": "What did Yixin find from the customer discovery interviews?",
    "exp_gtm": "What did Yixin do to shape the go-to-market strategy at Continua?",
    "exp_continua_eng": "What PM work did Yixin own alongside the engineering?",
    "exp_intern_user_research": "How did Yixin use user research to shape the Continua roadmap?",
    "exp_intern_onboarding": "What research informed this onboarding redesign?",
    "exp_asana_migration": "How did Yixin migrate the Continua team from Google Docs to Asana?",
    "exp_jackson_lab": "Has Yixin published any research connected to this kind of work?",
    "exp_research_overview": "What does Yixin's published research actually cover?",
    "exp_insite_lab": "What research did Yixin do with blind and low-vision participants at the INSITE Lab?",
    "exp_eye_tracking_research": "How does this research connect to Yixin's work in AI?",
    "exp_human_feature_research": "How does Yixin's research background connect to her product decisions?",
    "exp_ethics_ai_benchmarks": "What did Yixin find analyzing AI moral dilemma benchmarks?",
    "exp_ethics_ai_art": "How does Yixin's ethics work connect to her AI product experience?",
    "exp_photography": "What's the link to Yixin's photography portfolio?",
}


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


def _title_to_deep_dive_follow_up(title: str, experience_id: str = "") -> str:
    question = _DEEP_DIVE_QUESTIONS.get(experience_id)
    if question:
        return question
    cleaned = " ".join(title.strip().split()).rstrip(".")
    for prefix, gerund in _GERUND_PREFIXES.items():
        if cleaned.startswith(prefix):
            phrase = gerund + cleaned[len(prefix):].strip()
            return f"What was the hardest part of {phrase}?"
    lowered = cleaned[:1].lower() + cleaned[1:] if cleaned else cleaned
    return f"What was the hardest part of {lowered}?"


def build_follow_up_questions(
    *,
    user_message: str,
    active_topic_id: str | None,
    active_topics: list[str],
    citations: list[Citation],
    topics: list | None = None,
    limit: int = MAX_FOLLOWUPS,
) -> list[str]:
    """Return a single concrete dive-deeper question for the current thread."""

    if topics is None:
        _, topics, _, _ = load_graph()
    topic_labels = {topic.id: _normalize_topic_label(topic.label) for topic in topics}
    chosen_topic_id = active_topic_id or (active_topics[0] if active_topics else None)
    chosen_topic_label = topic_labels.get(chosen_topic_id or "", "").strip()

    prompts: list[str] = []
    if citations:
        top_citation = citations[0]
        prompts.append(
            _title_to_deep_dive_follow_up(
                top_citation.experience_title,
                top_citation.experience_id,
            )
        )
    if not prompts:
        label = chosen_topic_label.lower() if chosen_topic_label else ""
        prompts.extend(
            (
                [
                    f"What's a concrete example of Yixin's {label} work?",
                ]
                if label
                else [
                    "What's a concrete example of something Yixin has built?",
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
        if len(unique_prompts) >= 1:
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
