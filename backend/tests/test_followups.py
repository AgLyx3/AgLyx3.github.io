"""Tests for follow-up question and adjacent topic generation."""

from __future__ import annotations

from app.models.chat import Citation
from app.services.followups import (
    _DEEP_DIVE_QUESTIONS,
    build_adjacent_topics,
    build_follow_up_questions,
)
from app.services.query_router import route_query

_CITATION = Citation(
    experience_id="exp_locomo_benchmarking",
    experience_title="Ran LoCoMo and EverMemBenchmark across matched configurations",
    snippet="Executed long-memory benchmarks with carefully aligned prompts.",
    score=0.91,
)


def test_follow_up_questions_capped_at_three(test_db):
    questions = build_follow_up_questions(
        user_message="What eval work did Yixin do?",
        active_topic_id="topic_eval",
        active_topics=["topic_eval", "topic_memory_architecture"],
        citations=[_CITATION],
    )
    assert len(questions) <= 1


def test_follow_up_questions_derived_from_citation_title(test_db):
    questions = build_follow_up_questions(
        user_message="What eval work did Yixin do?",
        active_topic_id="topic_eval",
        active_topics=["topic_eval"],
        citations=[_CITATION],
    )
    assert any("hardest part" in q.casefold() for q in questions)


def test_follow_up_deduplicates_against_user_message(test_db):
    duplicate_message = "What was the hardest part of running LoCoMo and EverMemBenchmark across matched configurations?"
    questions = build_follow_up_questions(
        user_message=duplicate_message,
        active_topic_id="topic_eval",
        active_topics=["topic_eval"],
        citations=[_CITATION],
    )
    assert not any(q.casefold() == duplicate_message.casefold() for q in questions)


def test_adjacent_topics_capped_at_three(test_db):
    topics = build_adjacent_topics(
        active_topic_id="topic_eval",
        active_topics=["topic_eval"],
        citations=[_CITATION],
        limit=2,
    )
    assert len(topics) <= 2


def test_eval_followup_prefers_defined_deep_dive_question(test_db):
    eval_citation = Citation(
        experience_id="exp_eval_frameworks",
        experience_title="Owned evaluation frameworks for production LLM systems at Continua",
        snippet="Focused on memory quality and latency.",
        score=0.94,
    )
    questions = build_follow_up_questions(
        user_message="How did Yixin approach evaluation and benchmarking?",
        active_topic_id="eval",
        active_topics=["eval"],
        citations=[eval_citation],
    )
    assert questions == ["How did Yixin measure whether the memory was actually working?"]


def test_all_follow_up_questions_route_to_memory():
    """Every defined follow-up question must route to memory, not small_talk."""
    bad = [
        (exp_id, q, route_query(q))
        for exp_id, q in _DEEP_DIVE_QUESTIONS.items()
        if route_query(q) != "memory"
    ]
    assert not bad, (
        "These follow-up questions routed to small_talk instead of memory:\n"
        + "\n".join(f"  {exp_id!r}: {q!r} → {route!r}" for exp_id, q, route in bad)
    )


def test_all_follow_up_questions_retrieve_above_threshold(test_db):
    """Every follow-up question must score above the retrieval threshold so it
    gets a grounded answer instead of the fallback response.

    Mirrors the experience_passes check in chat.py:
        top_score >= min_top AND (top_score >= strong_top OR gap >= min_gap)

    When you add or change a question in _DEEP_DIVE_QUESTIONS, run this test
    to confirm retrieval still passes — weak or vague phrasings will fail here.
    """
    from app.config import get_settings
    from app.services.retrieval import combined_memory_retrieve

    s = get_settings()
    bad = []
    for exp_id, q in _DEEP_DIVE_QUESTIONS.items():
        result = combined_memory_retrieve(q)
        top = result.experience.top_score
        second = result.experience.second_score
        gap = top - second
        passes = top >= s.retrieval_min_top_score and (
            top >= s.retrieval_strong_top_score or gap >= s.retrieval_min_score_gap
        )
        if not passes:
            bad.append((exp_id, q, top, gap))

    assert not bad, (
        "These follow-up questions fall below the retrieval threshold "
        f"(min_top={s.retrieval_min_top_score}, strong={s.retrieval_strong_top_score}, "
        f"min_gap={s.retrieval_min_score_gap}):\n"
        + "\n".join(
            f"  {exp_id!r}: score={top:.3f} gap={gap:.3f}  {q!r}"
            for exp_id, q, top, gap in bad
        )
    )
