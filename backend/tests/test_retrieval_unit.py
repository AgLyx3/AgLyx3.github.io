"""Unit tests for retrieval service internals."""

from __future__ import annotations

from unittest.mock import patch

from app.services.retrieval import combined_memory_retrieve


def test_combined_retrieve_calls_load_graph_exactly_once(test_db):
    with patch("app.services.retrieval.load_graph", return_value=([], [], [], [])) as mock:
        combined_memory_retrieve("what degree did she get?")
    mock.assert_called_once()


def test_general_work_query_returns_profile_and_experience_context(test_db):
    result = combined_memory_retrieve("what does she do")

    joined_profile = " ".join(result.profile.context_blocks).lower()
    returned_ids = {citation.experience_id for citation in result.experience.citations}

    assert "current role" in joined_profile
    assert "continua ai" in joined_profile
    assert result.experience.citations
    assert {
        "exp_continua_overview",
        "exp_eval_frameworks",
        "exp_memory_architecture",
        "exp_pm_delivery",
    } & returned_ids


def test_project_query_returns_real_experience_results(test_db):
    result = combined_memory_retrieve("what projects")

    returned_ids = {citation.experience_id for citation in result.experience.citations}

    assert result.experience.citations
    assert {
        "exp_memory_architecture",
        "exp_agentic_poll",
        "exp_pm_delivery",
    } & returned_ids


def test_tell_me_about_her_returns_profile_and_work_context(test_db):
    result = combined_memory_retrieve("tell me about her")

    joined_profile = " ".join(result.profile.context_blocks).lower()
    returned_ids = {citation.experience_id for citation in result.experience.citations}

    assert "continua ai" in joined_profile
    assert result.experience.citations
    assert {
        "exp_continua_overview",
        "exp_memory_architecture",
        "exp_pm_delivery",
    } & returned_ids


def test_every_seeded_profile_key_has_a_synonym_entry(tmp_path):
    """_profile_key_boost matches on equality, so a rename silently kills it.

    The seeds moved to Interest / Education_background while the synonym table
    still said interests / education. Nothing failed — those two rows just
    stopped earning a key boost forever. This pins the two together.

    Seeds into its own database rather than the shared one: other tests insert
    profile rows of their own, and those are not the seed's business.
    """
    import os

    from app.services.db import get_conn, init_db
    from app.services.retrieval import _PROFILE_KEY_SYNONYMS

    previous = os.environ["DATABASE_URL"]
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'seed.db'}"
    try:
        init_db()
        with get_conn() as conn:
            seeded = {row["key"].lower() for row in conn.execute("SELECT key FROM profile_memories")}
    finally:
        os.environ["DATABASE_URL"] = previous

    assert seeded, "expected seeded profile memories"
    orphans = seeded - set(_PROFILE_KEY_SYNONYMS)
    assert not orphans, f"profile keys with no synonym entry: {sorted(orphans)}"


def test_technical_stack_query_returns_the_stack_profile_block(test_db):
    result = combined_memory_retrieve("what languages and frameworks does she use")

    joined_profile = " ".join(result.profile.context_blocks).lower()

    assert "technical stack" in joined_profile
    assert "typescript" in joined_profile
