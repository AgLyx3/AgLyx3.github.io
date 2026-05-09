"""End-to-end retrieval tests. Run after DB is seeded.

Each case: (query, must_include_ids, must_exclude_ids)
- must_include: ALL of these must appear in top-3 citations
- must_exclude: NONE of these may appear in top-3 citations

Revise expected IDs once you've reviewed retrieval behavior manually.
"""

import pytest
from app.services.retrieval import hybrid_retrieve


# ---------------------------------------------------------------------------
# Cases — NEEDS REVISION: expected IDs are placeholders, verify against live
# ---------------------------------------------------------------------------

RETRIEVAL_CASES = [
    # Memory
    ("tell me about the memory system you built",
     ["exp_memory_architecture"], []),
    ("how did you build per-user personalization",
     ["exp_memory_architecture"], []),
    ("what is the privacy gate in the memory system",
     ["exp_memory_architecture"], []),

    # Eval
    ("what benchmarks did you run",
     ["exp_eval_frameworks"], []),
    ("how did you measure latency in the LLM system",
     ["exp_eval_frameworks"], []),
    ("tell me about LoCoMo and EverMemBench",
     ["exp_eval_frameworks"], []),

    # Agentic features
    ("tell me about the polling feature",
     ["exp_agentic_poll"], []),
    ("how did you design the expense splitting feature",
     ["exp_agentic_split"], []),

    # Issue viewer
    ("tell me about the issue viewer",
     ["exp_issue_viewer"], []),

    # PM / discovery
    ("how do you write PRDs",
     ["exp_pm_delivery"], []),
    ("tell me about customer discovery",
     ["exp_customer_discovery"], []),

    # Startup
    ("tell me about InclusiM",
     ["exp_inclusim"], []),
    ("did you raise funding",
     ["exp_inclusim"], []),

    # Research / publications
    ("do you have any publications",
     [], []),  # TODO: decide expected after testing
    ("tell me about accessibility research",
     [], []),  # TODO: decide expected — exp_insite_lab or exp_inclusim

    # Ethics
    ("what do you think about AI ethics",
     ["exp_ethics_ai_benchmarks"], []),

    # Engineering
    ("what have you built as an engineer",
     [], []),  # TODO: decide expected

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
