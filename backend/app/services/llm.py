"""LLM response generation via OpenAI-compatible Chat Completions API."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from app.config import Settings
from app.models import Citation, CTAMention, TopicSuggestion

MEMORY_FALLBACK_RESPONSE = (
    "I am not sure about this based on my memory about Yixin. Wanna ask something different?"
)

SYSTEM_PROMPT_SECTIONS = (
    "You are the portfolio chat assistant for Yixin Li.",
    "Always talk about Yixin in the third person. Never speak as Yixin in first person.",
    "Answer only from the provided memory context and routing metadata.",
    "Keep the response concise and natural, usually 2 to 5 sentences.",
    "Ground every answer in Yixin's actual experiences when context is available.",
    (
        "If the memory is weak, ambiguous, or missing, respond with exactly this sentence and nothing else: "
        f"\"{MEMORY_FALLBACK_RESPONSE}\""
    ),
    "Do not invent facts, dates, organizations, or outcomes that are not in the provided context.",
    "Answer the user's question directly before offering any continuation prompt.",
    "Do not include bullet lists unless the user explicitly asks for a list.",
    "If a CTA hook is present, incorporate it at most once as a short final sentence. Otherwise do not mention CTAs.",
)


def _api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for LLM chat generation")
    return api_key


def portfolio_chat_system_prompt() -> str:
    return "\n".join(f"{index + 1}. {section}" for index, section in enumerate(SYSTEM_PROMPT_SECTIONS))


def build_portfolio_chat_user_prompt(
    *,
    user_message: str,
    context_blocks: list[str],
    citations: list[Citation] | None = None,
    active_topic_id: str | None = None,
    prefill_origin: str | None = None,
    message_index: int | None = None,
    follow_up_questions: list[str] | None = None,
    adjacent_topics: list[TopicSuggestion] | None = None,
    cta_mention: CTAMention | None = None,
) -> str:
    """Build the user prompt as a single JSON payload for maintainability."""

    prompt_payload: dict[str, Any] = {
        "visitor_question": user_message,
        "session": {
            "active_topic_id": active_topic_id,
            "prefill_origin": prefill_origin,
            "message_index": message_index,
        },
        "memory_context": context_blocks,
        "citations": [
            {
                "experience_id": citation.experience_id,
                "experience_title": citation.experience_title,
                "snippet": citation.snippet,
                "score": citation.score,
            }
            for citation in (citations or [])
        ],
        "follow_up_budget": {
            "max_adjacent_questions": 3,
            "max_adjacent_topics": 3,
            "suggested_adjacent_questions": follow_up_questions or [],
            "suggested_adjacent_topics": [
                {"topic_id": topic.topic_id, "label": topic.label} for topic in (adjacent_topics or [])
            ],
        },
        "cta_hook": (
            {
                "action_type": cta_mention.action_type,
                "label": cta_mention.label,
                "message": cta_mention.message,
            }
            if cta_mention
            else None
        ),
        "output_rules": {
            "voice": "third_person",
            "target_length": "2-5 sentences",
            "fallback_if_memory_weak": MEMORY_FALLBACK_RESPONSE,
        },
    }
    return json.dumps(prompt_payload, ensure_ascii=True, indent=2)


def _post_chat_completion(*, settings: Settings, payload: dict[str, Any]) -> str:
    req = request.Request(
        f"{settings.chat_api_base.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=settings.chat_timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        parsed = json.loads(raw)
        return str(parsed["choices"][0]["message"]["content"]).strip()
    except (TimeoutError, error.URLError, error.HTTPError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"LLM chat generation failed: {exc}") from exc


def generate_chat_answer(
    *,
    settings: Settings,
    user_message: str,
    context_blocks: list[str],
    citations: list[Citation] | None = None,
    active_topic_id: str | None = None,
    prefill_origin: str | None = None,
    message_index: int | None = None,
    follow_up_questions: list[str] | None = None,
    adjacent_topics: list[TopicSuggestion] | None = None,
    cta_mention: CTAMention | None = None,
    max_output_tokens: int | None = None,
) -> str:
    if not context_blocks:
        return MEMORY_FALLBACK_RESPONSE

    payload = {
        "model": settings.chat_model,
        "messages": [
            {"role": "system", "content": portfolio_chat_system_prompt()},
            {
                "role": "user",
                "content": build_portfolio_chat_user_prompt(
                    user_message=user_message,
                    context_blocks=context_blocks,
                    citations=citations,
                    active_topic_id=active_topic_id,
                    prefill_origin=prefill_origin,
                    message_index=message_index,
                    follow_up_questions=follow_up_questions,
                    adjacent_topics=adjacent_topics,
                    cta_mention=cta_mention,
                ),
            },
        ],
        "temperature": 0.2,
    }
    if max_output_tokens is not None:
        payload["max_tokens"] = max_output_tokens
    return _post_chat_completion(settings=settings, payload=payload)


def assign_memory_topics_with_llm(
    *,
    settings: Settings,
    title: str,
    details: str,
    topics: list[dict[str, str]],
) -> list[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for LLM topic assignment")
    if not topics:
        return []

    payload = {
        "model": settings.topic_labeler_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You assign memory entries to existing topic IDs. "
                    "Return strict JSON: {\"topic_ids\":[\"topic_id_a\",\"topic_id_b\"]}. "
                    "Return 1-3 topic_ids from provided candidates only."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "memory": {"title": title, "details": details},
                        "candidate_topics": topics,
                    }
                ),
            },
        ],
        "temperature": 0.1,
    }
    req = request.Request(
        f"{settings.topic_labeler_api_base.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=settings.topic_labeler_timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        parsed = json.loads(raw)
        content = parsed["choices"][0]["message"]["content"]
        obj = json.loads(content)
        selected = [str(t).strip() for t in obj.get("topic_ids", []) if str(t).strip()]
        allowed = {topic["id"] for topic in topics}
        return [topic_id for topic_id in selected if topic_id in allowed][:3]
    except (TimeoutError, error.URLError, error.HTTPError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"LLM topic assignment failed: {exc}") from exc
