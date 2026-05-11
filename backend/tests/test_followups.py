"""Tests for follow-up question and adjacent topic generation."""

from __future__ import annotations

from app.models.chat import Citation
from app.services.followups import build_adjacent_topics, build_follow_up_questions

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
    assert len(questions) <= 3


def test_follow_up_questions_derived_from_citation_title(test_db):
    questions = build_follow_up_questions(
        user_message="What eval work did Yixin do?",
        active_topic_id="topic_eval",
        active_topics=["topic_eval"],
        citations=[_CITATION],
    )
    assert any("LoCoMo and EverMemBenchmark" in q for q in questions)


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
    )
    assert len(topics) <= 3
