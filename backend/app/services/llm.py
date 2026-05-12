"""LLM response generation via OpenAI-compatible Chat Completions API."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from app.config import Settings
from app.models import Citation, CTAMention, TopicSuggestion

MEMORY_FALLBACK_RESPONSE = (
    "I don't have enough real context to answer that confidently, and I'm not going to make something up. Try a different angle, or use the footer to send Yixin a direct message or email her."
)

SMALL_TALK_RESPONSE = (
    "Hey! I'm Yixin's portfolio assistant. Ask me about her work in AI/ML, "
    "product management, research, or accessibility — happy to dig in."
)

SYSTEM_PROMPT_SECTIONS = (
    "You are the portfolio chat assistant for Yixin Li.",
    "Always talk about Yixin in the third person. Never speak as Yixin in first person.",
    "Answer only from the provided memory context and routing metadata.",
    "Keep answers short — usually 2 to 5 sentences. Sound like a knowledgeable friend talking about a colleague: casual, warm, and direct. Not a formal bio.",
    "Do not brag or oversell. Present what Yixin did factually and let the work speak for itself. Avoid superlatives, hype, or framing her as exceptional unless the context explicitly supports it.",
    "Use profile context for stable background facts and experience context for concrete project or work claims.",
    (
        "If the memory is weak, ambiguous, or missing, respond with exactly this sentence and nothing else "
        "(keep the dry, self-aware tone — no apology, no hedging): "
        f"\"{MEMORY_FALLBACK_RESPONSE}\""
    ),
    "Do not invent facts, dates, organizations, or outcomes that are not in the provided context.",
    "Answer the user's question directly. Do not end every response with the same closing invitation — most answers should just end. Only occasionally, when it genuinely fits, add a short closer.",
    "Do not include bullet lists unless the user explicitly asks for a list.",
    "If the visitor asks something you cannot answer from the available context, briefly acknowledge it and suggest either asking a related question you can answer or using the footer to send Yixin a direct message or email her.",
    "If a CTA hook is present, incorporate it at most once as a short final sentence. Otherwise do not mention CTAs.",
    (
        "If ask_visitor_question is true in the input, your output must be exactly two paragraphs. "
        "Paragraph 1: answer the user's question normally. "
        "Paragraph 2: one single-sentence question to the visitor. "
        "There must be one blank line between the two paragraphs. "
        "The question should be about the visitor — their own work, what they're building, or what brought them here. "
        "Not a question about Yixin. One sentence, keep it natural and contextual. "
        "Examples: 'Are you working on something similar?', 'What kind of AI work are you exploring these days?', "
        "'What brought you to check out the portfolio?'"
    ),
    (
        "If visitor_context is present in the input, the visitor just shared something about themselves in response "
        "to a question you asked. Acknowledge what they shared in one warm sentence, then naturally bridge to "
        "Yixin's most relevant experience from the provided context. Keep it direct. "
        "Do not end with a question — let the visitor continue at their own pace. "
        "Do not use the fallback response in this case — always bridge, even if the connection is loose."
    ),
)


def _api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for LLM chat generation")
    return api_key


def topic_exploration_hint(*, is_mobile: bool = False) -> str:
    return "You can also steer the conversation with the bubbles in the background or the Topics button in the top right."


def portfolio_chat_system_prompt() -> str:
    return "\n".join(f"{index + 1}. {section}" for index, section in enumerate(SYSTEM_PROMPT_SECTIONS))


def build_portfolio_chat_user_prompt(
    *,
    user_message: str,
    profile_context: list[str],
    experience_context: list[str],
    citations: list[Citation] | None = None,
    active_topic_id: str | None = None,
    prefill_origin: str | None = None,
    message_index: int | None = None,
    follow_up_questions: list[str] | None = None,
    adjacent_topics: list[TopicSuggestion] | None = None,
    cta_mention: CTAMention | None = None,
    ask_visitor_question: bool = False,
    visitor_context: str | None = None,
) -> str:
    """Build the user prompt as a single JSON payload for maintainability."""

    prompt_payload: dict[str, Any] = {
        "visitor_question": user_message,
        "session": {
            "active_topic_id": active_topic_id,
            "prefill_origin": prefill_origin,
            "message_index": message_index,
        },
        "profile_context": profile_context,
        "experience_context": experience_context,
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
            "tone": "casual and conversational — like a knowledgeable friend, not a formal bio",
            "target_length": "2-5 sentences",
            "fallback_if_memory_weak": MEMORY_FALLBACK_RESPONSE,
        },
    }
    if ask_visitor_question:
        prompt_payload["ask_visitor_question"] = True
    if visitor_context is not None:
        prompt_payload["visitor_context"] = visitor_context
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


def generate_small_talk_answer(*, settings: Settings, user_message: str, is_mobile: bool = False) -> str:
    explore_hint = topic_exploration_hint()
    payload = {
        "model": settings.chat_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Yixin.exe, portfolio assistant for Yixin Li. "
                    "The visitor is making small talk or just saying hi. Reply like you're texting a friend — match their energy, keep it short (1-2 sentences). "
                    "Tone: lowercase when it feels natural, short punchy sentences, contractions, light wit. "
                    "No corporate speak, no double exclamation points, no forced slang. "
                    "If the visitor just greets (hi, hey, hello, etc.), nudge them to ask about Yixin's work — make it feel like an invitation, not a menu. "
                    "Aim for something in this vibe (don't copy, just match the register):\n"
                    "  'hey! wanna know what yixin's been building?'\n"
                    "  'solid opener — she's done a lot. pick a topic and let's go'\n"
                    "  'lol fair — i'm a bot with a narrow job description but i do it well'\n"
                    f"Somewhere naturally slip in: \"{explore_hint}\""
                ),
            },
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.8,
    }
    return _post_chat_completion(settings=settings, payload=payload)

def generate_chat_answer(
    *,
    settings: Settings,
    user_message: str,
    profile_context: list[str] | None = None,
    experience_context: list[str] | None = None,
    citations: list[Citation] | None = None,
    active_topic_id: str | None = None,
    prefill_origin: str | None = None,
    message_index: int | None = None,
    follow_up_questions: list[str] | None = None,
    adjacent_topics: list[TopicSuggestion] | None = None,
    cta_mention: CTAMention | None = None,
    max_output_tokens: int | None = None,
    ask_visitor_question: bool = False,
    visitor_context: str | None = None,
) -> str:
    profile_context = profile_context or []
    experience_context = experience_context or []
    if not profile_context and not experience_context and not visitor_context:
        return MEMORY_FALLBACK_RESPONSE

    payload = {
        "model": settings.chat_model,
        "messages": [
            {"role": "system", "content": portfolio_chat_system_prompt()},
            {
                "role": "user",
                "content": build_portfolio_chat_user_prompt(
                    user_message=user_message,
                    profile_context=profile_context,
                    experience_context=experience_context,
                    citations=citations,
                    active_topic_id=active_topic_id,
                    prefill_origin=prefill_origin,
                    message_index=message_index,
                    follow_up_questions=follow_up_questions,
                    adjacent_topics=adjacent_topics,
                    cta_mention=cta_mention,
                    ask_visitor_question=ask_visitor_question,
                    visitor_context=visitor_context,
                ),
            },
        ],
        "temperature": 0.4,
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
