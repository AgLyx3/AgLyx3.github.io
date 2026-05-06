"""LLM response generation via OpenAI-compatible Chat Completions API."""

from __future__ import annotations

import json
import os
from urllib import error, request

from app.config import Settings


def generate_chat_answer(*, settings: Settings, user_message: str, context_blocks: list[str]) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for LLM chat generation")

    context_text = "\n".join(f"- {block}" for block in context_blocks) or "- No context found."
    system_prompt = (
        "You are a portfolio assistant. Answer based only on provided context. "
        "If context is insufficient, say what is missing briefly."
    )
    user_prompt = f"User question: {user_message}\n\nContext:\n{context_text}"

    payload = {
        "model": settings.chat_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
    }
    req = request.Request(
        f"{settings.chat_api_base.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
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
        "model": settings.chat_model,
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
        f"{settings.chat_api_base.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=settings.chat_timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        parsed = json.loads(raw)
        content = parsed["choices"][0]["message"]["content"]
        obj = json.loads(content)
        selected = [str(t).strip() for t in obj.get("topic_ids", []) if str(t).strip()]
        allowed = {topic["id"] for topic in topics}
        return [topic_id for topic_id in selected if topic_id in allowed][:3]
    except (TimeoutError, error.URLError, error.HTTPError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"LLM topic assignment failed: {exc}") from exc
