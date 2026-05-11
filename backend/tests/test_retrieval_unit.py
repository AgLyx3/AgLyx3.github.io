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
