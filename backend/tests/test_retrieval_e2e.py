"""End-to-end retrieval tests. Run after DB is seeded.

General cases: (query, must_include_ids, must_exclude_ids)
- must_include: ALL of these must appear in top-3 citations
- must_exclude: NONE of these may appear in top-3 citations

Prefill cases: the 10 bubble-prefill questions that visitors actually click.
Each prefill must (a) pass the retrieval threshold so experience_passes=True
in the chat endpoint and (b) return at least one topically relevant experience.
"""

import pytest
from app.services.retrieval import hybrid_retrieve

# retrieval_min_top_score=0.22, retrieval_strong_top_score=0.35, retrieval_min_score_gap=0.04
_MIN_SCORE = 0.22
_STRONG_SCORE = 0.35
_MIN_GAP = 0.04


# ---------------------------------------------------------------------------
# Cases — NEEDS REVISION: expected IDs are placeholders, verify against live
# ---------------------------------------------------------------------------

RETRIEVAL_CASES = [
    # Memory
    ("tell me about the memory system you built",
     ["exp_memory_architecture"], []),
    ("what kind of work did you do on personalization",
     ["exp_memory_architecture"], []),
    ("what's your experience with retrieval system",
     ["exp_memory_architecture"], []),

    # Eval
    ("what benchmarks did you run",
     ["exp_eval_frameworks"], []),
    ("how did you measure latency in the LLM system",
     ["exp_eval_frameworks"], []),
    ("what kind of eval experience do you have",
     ["exp_eval_frameworks"], []),

    # Agentic features
    ("what kind of agentic features did you build",
     ["exp_agentic_poll", "exp_agentic_split", "exp_memory_architecture"], []),

    # Issue viewer
    ("tell me about your experience with building internal tool",
     ["exp_issue_viewer"], []),
    ("what did you do to improve internal process",
     ["exp_issue_viewer"], []),

    # PM / discovery
    ("what did you do as a PM in the company",
     ["exp_pm_delivery"], []),
    ("what customer facing work did you do",
     ["exp_customer_discovery"], []),

    # Startup
    ("what kind of startup experience did you have",
     ["exp_inclusim"], []),

    # Research / publications
    ("what kind of research did you do",
     ["exp_research_overview"], []),
    ("tell me about accessibility research",
     ["exp_insite_lab"], []),

    # Ethics
    ("what do you do about AI ethics",
     ["exp_ethics_ai_benchmarks"], []),

    # Engineering
    ("what have you built as an engineer",
     ["exp_continua_eng"], []),  # TODO: decide expected

    # Graceful degradation — should score low, not hallucinate
    ("what is your favorite color",
     [], []),
]


@pytest.mark.parametrize("query,must_include,must_exclude", RETRIEVAL_CASES)
def test_retrieval(query, must_include, must_exclude):
    result = hybrid_retrieve(query, limit=3)
    returned_ids = {c.experience_id for c in result.citations}

    for exp_id in must_include:
        assert exp_id in returned_ids, (
            f"Query '{query}'\n  expected '{exp_id}' in top 3\n  got {returned_ids}"
        )
    for exp_id in must_exclude:
        assert exp_id not in returned_ids, (
            f"Query '{query}'\n  expected '{exp_id}' excluded from top 3\n  got {returned_ids}"
        )

    if not must_include and not must_exclude and "favorite color" in query:
        assert result.top_score < 0.15, (
            f"Degradation query '{query}' scored too high: {result.top_score}"
        )


# ---------------------------------------------------------------------------
# Prefill cases — the 10 bubble questions visitors actually click
# Each prefill must pass the retrieval gate AND return topically relevant IDs.
# (query, topic_id, at_least_one_of_ids, must_not_ids)
# ---------------------------------------------------------------------------

PREFILL_CASES = [
    # ai-agents: must surface actual agent work, not ethics experiences
    (
        "What kind of AI agent work did Yixin do?",
        "ai-agents",
        ["exp_agentic_poll", "exp_agentic_split", "exp_memory_architecture"],
        ["exp_ethics_ai_benchmarks", "exp_ethics_ai_art"],
    ),
    (
        "What kind of memory systems did Yixin work on?",
        "memory",
        ["exp_memory_architecture", "exp_eval_frameworks"],
        [],
    ),
    (
        "How did Yixin approach evaluation and benchmarking?",
        "eval",
        ["exp_eval_frameworks"],
        [],
    ),
    (
        "What startup experience does Yixin have?",
        "startup",
        ["exp_inclusim", "exp_continua_overview"],
        [],
    ),
    (
        "What engineering projects has Yixin worked on?",
        "eng",
        ["exp_continua_eng", "exp_jackson_lab", "exp_inclusim"],
        [],
    ),
    (
        "What is Yixin's product management experience?",
        "pm",
        ["exp_pm_delivery", "exp_continua_overview", "exp_agentic_poll", "exp_agentic_split", "exp_intern_user_research"],
        [],
    ),
    (
        "What research has Yixin done academically?",
        "research",
        ["exp_research_overview", "exp_insite_lab", "exp_eye_tracking_research", "exp_human_feature_research"],
        [],
    ),
    (
        "What accessibility work has Yixin done?",
        "access",
        ["exp_inclusim", "exp_insite_lab"],
        [],
    ),
    (
        "What creative work has Yixin done in photography?",
        "photo",
        ["exp_photography"],
        [],
    ),
    (
        "What are Yixin's views on AI ethics?",
        "ethics",
        ["exp_ethics_ai_art", "exp_ethics_ai_benchmarks"],
        [],
    ),
]


@pytest.mark.parametrize("query,topic_id,at_least_one_of,must_not", PREFILL_CASES)
def test_prefill_retrieval(query, topic_id, at_least_one_of, must_not):
    result = hybrid_retrieve(query, limit=3)
    returned_ids = {c.experience_id for c in result.citations}
    score_gap = result.top_score - result.second_score

    # Must pass the same gate as the chat endpoint
    experience_passes = result.top_score >= _MIN_SCORE and (
        result.top_score >= _STRONG_SCORE or score_gap >= _MIN_GAP
    )
    assert experience_passes, (
        f"[{topic_id}] '{query}'\n"
        f"  retrieval gate failed: top={result.top_score:.3f} gap={score_gap:.3f}\n"
        f"  returned {returned_ids}"
    )

    assert any(exp_id in returned_ids for exp_id in at_least_one_of), (
        f"[{topic_id}] '{query}'\n"
        f"  none of {at_least_one_of} found in top-3\n"
        f"  got {returned_ids}"
    )

    for exp_id in must_not:
        assert exp_id not in returned_ids, (
            f"[{topic_id}] '{query}'\n"
            f"  wrong experience '{exp_id}' appeared in top-3\n"
            f"  got {returned_ids}"
        )
