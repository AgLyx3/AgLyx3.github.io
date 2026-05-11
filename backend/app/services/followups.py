"""Deterministic follow-up generation for the portfolio chat experience."""

from __future__ import annotations

from app.models import Citation, TopicSuggestion
from app.services.retrieval import load_graph

MAX_FOLLOWUPS = 3

_EXPERIENCE_QUESTIONS: dict[str, list[str]] = {
    "exp_continua_overview": [
        "What kind of AI features did Yixin actually build there?",
        "What does Yixin's engineering work at Continua look like?",
        "How did Yixin approach customer research to figure out what to build?",
    ],
    "exp_pm_delivery": [
        "What are some of the AI features Yixin shipped?",
        "How did Yixin approach evaluation for these AI systems?",
        "What was Yixin's go-to-market work like alongside this?",
    ],
    "exp_memory_architecture": [
        "What other AI features did Yixin build alongside the memory system?",
        "How did Yixin measure whether the memory was actually working?",
        "What does Yixin's broader engineering work look like?",
    ],
    "exp_agentic_poll": [
        "What other agentic features did Yixin work on?",
        "How did Yixin track quality and catch issues after launch?",
        "What does Yixin's broader PM work look like beyond individual features?",
    ],
    "exp_agentic_split": [
        "What other conversational features did Yixin design?",
        "What engineering work did Yixin do to bring these features to life?",
        "How did Yixin measure whether these features were working well?",
    ],
    "exp_eval_frameworks": [
        "What did Yixin build that needed all this evaluation?",
        "How did Yixin use these results to improve the product?",
        "Has Yixin done research on human-AI interaction that connects to this?",
    ],
    "exp_issue_viewer": [
        "What product quality problems was the issue viewer tracking?",
        "What other tooling did Yixin build at Continua?",
        "How does this fit into Yixin's broader engineering experience?",
    ],
    "exp_customer_discovery": [
        "What did Yixin build after narrowing the ICP?",
        "Has Yixin done user research in other settings too?",
        "What go-to-market work did Yixin do at Continua?",
    ],
    "exp_gtm": [
        "What product work was happening alongside the GTM push?",
        "What customer research informed the GTM direction?",
        "Has Yixin done startup or market work in other contexts?",
    ],
    "exp_continua_eng": [
        "What PM work did Yixin own alongside the engineering?",
        "Has Yixin built AI tools in other contexts?",
        "What research background does Yixin bring to her technical work?",
    ],
    "exp_intern_user_research": [
        "What did Yixin build based on what she found?",
        "Has Yixin run user research in academic settings too?",
        "What other PM work did Yixin take on at Continua?",
    ],
    "exp_intern_onboarding": [
        "What research informed this onboarding redesign?",
        "How does this connect to Yixin's broader engineering work?",
        "What other PM work did Yixin own at the time?",
    ],
    "exp_asana_migration": [
        "What other process improvements did Yixin drive at Continua?",
        "How does this connect to Yixin's broader PM work?",
        "What startup experience does Yixin have beyond Continua?",
    ],
    "exp_jackson_lab": [
        "What other AI or ML work has Yixin done?",
        "Has Yixin published any research connected to this kind of work?",
        "What startup or product work did Yixin do around this time?",
    ],
    "exp_inclusim": [
        "How did InclusiM go from idea to a funded startup?",
        "What did Yixin actually build for InclusiM?",
        "How does founding a startup connect to what Yixin does now?",
    ],
    "exp_research_overview": [
        "What does Yixin's published research actually cover?",
        "How has Yixin applied research methods in her product work?",
        "What other technical areas has Yixin worked in?",
    ],
    "exp_insite_lab": [
        "What did Yixin find from working with blind and low-vision participants?",
        "What other user study experience does Yixin have?",
        "How does Yixin's HCI background show up in her AI product work?",
    ],
    "exp_eye_tracking_research": [
        "What other research has Yixin published?",
        "What other kinds of user studies has Yixin run?",
        "How does this research connect to Yixin's work in AI?",
    ],
    "exp_human_feature_research": [
        "Where else has Yixin applied ML in her work?",
        "What other research has Yixin published?",
        "How does Yixin's research background connect to her product decisions?",
    ],
    "exp_ethics_ai_benchmarks": [
        "What other AI ethics topics has Yixin written about?",
        "How does Yixin's ethics perspective show up in her product work?",
        "What other research has Yixin done?",
    ],
    "exp_ethics_ai_art": [
        "What other AI ethics topics has Yixin written about?",
        "How does Yixin's ethics work connect to her AI product experience?",
        "What other research has Yixin done?",
    ],
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


def _title_to_follow_up(title: str, index: int, experience_id: str = "") -> str:
    questions = _EXPERIENCE_QUESTIONS.get(experience_id, [])
    if index < len(questions):
        return questions[index]
    cleaned = " ".join(title.strip().split()).rstrip(".")
    for prefix, gerund in _GERUND_PREFIXES.items():
        if cleaned.startswith(prefix):
            phrase = gerund + cleaned[len(prefix):].strip()
            if index == 0:
                return f"What was the hardest part of {phrase}?"
            if index == 1:
                return f"What made Yixin want to work on {phrase}?"
            return f"What came out of {phrase}?"
    lowered = cleaned[:1].lower() + cleaned[1:] if cleaned else cleaned
    if index == 0:
        return f"What's the story behind {lowered}?"
    if index == 1:
        return f"What problem was {lowered} trying to solve?"
    return f"What did {lowered} lead to?"


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
        prompts.append(_title_to_follow_up(citation.experience_title, index, citation.experience_id))
    if not prompts:
        label = chosen_topic_label.lower() if chosen_topic_label else ""
        prompts.extend(
            (
                [
                    f"What has Yixin built in {label}?",
                    f"What's a good example of Yixin's {label} work?",
                    f"What does Yixin find interesting about {label}?",
                ]
                if label
                else [
                    "What's something impressive Yixin has built?",
                    "What kind of problems does Yixin like to solve?",
                    "What's Yixin's background in AI and ML?",
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
