"""Chat API endpoint with SSE token stream and final metadata."""

import asyncio
import functools
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.models import (
    AnalyticsEventCreate,
    ChatFinalMetadata,
    ChatRequest,
    ChatSessionState,
    SessionMessageRecordRequest,
    SessionTouchRequest,
)
from app.services import (
    MEMORY_FALLBACK_RESPONSE,
    RateLimiter,
    build_adjacent_topics,
    build_follow_up_questions,
    clear_ask_back_pending,
    combined_memory_retrieve,
    detect_cta_rejection,
    estimate_tokens,
    ensure_session,
    generate_chat_answer,
    generate_small_talk_answer,
    is_general_work_query,
    log_memory_gap,
    log_analytics_event,
    record_ask_back,
    record_assistant_response_tokens,
    record_user_message,
    route_query,
    sanitize_text,
    should_offer_cta,
    topic_exploration_hint,
    touch_session,
    truncate_text_to_token_limit,
    update_activation,
)

router = APIRouter(tags=["chat"])
chat_rate_limiter = RateLimiter(get_settings().chat_rate_limit_per_minute)


def _separate_ask_back_question(answer: str) -> str:
    """Ensure a trailing ask-back question is its own paragraph."""
    stripped = answer.strip()
    if "\n\n" in stripped or not stripped.endswith("?"):
        return stripped
    for i in range(len(stripped) - 2, -1, -1):
        if stripped[i] in ".!?" and stripped[i + 1] == " ":
            prefix = stripped[: i + 1].rstrip()
            question = stripped[i + 1 :].strip()
            if prefix and question.endswith("?"):
                return prefix + "\n\n" + question
    return stripped


def _append_topic_hint(answer: str, *, is_mobile: bool) -> str:
    hint = topic_exploration_hint(is_mobile=is_mobile)
    if hint in answer:
        return answer
    trimmed = answer.rstrip()
    if trimmed.endswith(("!", "?", ".")):
        return f"{trimmed} {hint}"
    return f"{trimmed}. {hint}"


@router.post("/chat")
async def chat_endpoint(
    payload: ChatRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    client_key = request.client.host if request.client else "unknown"
    session_id = payload.session_id or client_key
    clean_message = sanitize_text(payload.message)
    input_tokens = estimate_tokens(clean_message)
    if input_tokens > settings.max_input_tokens_per_message:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Message too large for chat input limit ({settings.max_input_tokens_per_message} tokens max)."
            ),
        )

    chat_rate_limiter.check(
        f"chat-session:{session_id}", limit_per_minute=settings.chat_rate_limit_per_minute
    )
    chat_rate_limiter.check(
        f"chat-ip:{client_key}", limit_per_minute=settings.chat_rate_limit_per_minute
    )

    session_update = record_user_message(
        SessionMessageRecordRequest(
            session_id=session_id,
            message_text=clean_message,
            message_origin=payload.prefill_origin or "manual",
            active_topic_id=payload.active_topic_id,
            estimated_input_tokens=input_tokens,
        )
    )
    message_index = payload.message_index or session_update.message_index_in_session
    cta_rejected = payload.cta_rejected or detect_cta_rejection(clean_message)
    if cta_rejected != session_update.session.cta_rejected or payload.active_topic_id is not None:
        session_snapshot = touch_session(
            SessionTouchRequest(
                session_id=session_id,
                active_topic_id=payload.active_topic_id,
                cta_rejected=cta_rejected,
            )
        )
    else:
        session_snapshot = session_update.session

    if session_update.first_message_recorded:
        log_analytics_event(
            AnalyticsEventCreate(
                session_id=session_id,
                event_name="chat_first_message_sent",
                payload={
                    "message_text": clean_message,
                    "message_length": len(clean_message),
                    "message_origin": payload.prefill_origin or "manual",
                    "active_topic_id": payload.active_topic_id,
                },
            )
        )
    log_analytics_event(
        AnalyticsEventCreate(
            session_id=session_id,
            event_name="chat_message_sent",
            payload={
                "message_index_in_session": message_index,
                "message_length": len(clean_message),
                "message_origin": payload.prefill_origin or "manual",
                "active_topic_id": payload.active_topic_id,
            },
        )
    )
    if session_update.depth_5_reached:
        log_analytics_event(
            AnalyticsEventCreate(
                session_id=session_id,
                event_name="chat_depth_reached",
                payload={"message_count": message_index},
            )
        )

    cta_mention = should_offer_cta(
        user_message=clean_message,
        message_index=message_index,
        cta_already_mentioned=payload.cta_already_mentioned or session_snapshot.cta_mentioned,
        cta_rejected=cta_rejected,
    )

    remaining_token_budget = max(
        0,
        settings.max_total_tokens_per_session - session_snapshot.total_token_count,
    )
    if remaining_token_budget <= 0:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Session token limit reached ({settings.max_total_tokens_per_session} total tokens). Start a new session to continue."
            ),
        )
    output_token_budget = min(settings.max_output_tokens_per_response, remaining_token_budget)

    is_ask_back_response = session_snapshot.ask_back_pending
    if is_ask_back_response:
        clear_ask_back_pending(session_id)

    original_route = route_query(clean_message)
    route = "memory" if is_ask_back_response else original_route

    # Only treat as a visitor answer if they actually responded personally (not a Yixin query).
    # If original_route == "memory" they're asking about Yixin — treat as normal query, no bridging.
    visitor_context: str | None = clean_message if (is_ask_back_response and original_route != "memory") else None

    if is_ask_back_response and visitor_context:
        log_analytics_event(
            AnalyticsEventCreate(
                session_id=session_id,
                event_name="visitor_ask_back_answered",
                payload={
                    "response_text": clean_message[:500],
                    "message_index": session_update.message_index_in_session,
                },
            )
        )

    current_round = session_update.message_index_in_session
    should_ask_back = (
        not is_ask_back_response
        and route != "small_talk"
        and (current_round - session_snapshot.last_ask_back_round) >= 3
    )
    if should_ask_back:
        record_ask_back(session_id, current_round)
        log_analytics_event(
            AnalyticsEventCreate(
                session_id=session_id,
                event_name="chat_ask_back_sent",
                payload={
                    "message_index": current_round,
                    "active_topic_id": payload.active_topic_id,
                },
            )
        )

    try:
        is_mobile = payload.viewport_width is not None and payload.viewport_width <= 880
        if route == "small_talk":
            answer = await asyncio.to_thread(
                functools.partial(
                    generate_small_talk_answer,
                    settings=settings,
                    user_message=clean_message,
                    is_mobile=is_mobile,
                    message_index=message_index,
                )
            )
            profile_context: list[str] = []
            experience_context: list[str] = []
            citations = []
            active_topics: list[str] = []
            score_gap = 0.0
            follow_up_questions: list[str] = []
            adjacent_topics = []
            memory_sources: list[str] = []
            use_memory = False
            experience_result = None

        else:  # "memory"
            # On Turn B (visitor answering the bot's question), their personal answer
            # won't match Yixin's experience embeddings. Blend the active topic into
            # the query so retrieval actually finds relevant Yixin context.
            if is_ask_back_response and visitor_context:
                topic_hint = (payload.active_topic_id or "").replace("-", " ")
                retrieval_query = f"{topic_hint} {clean_message}".strip() if topic_hint else clean_message
            else:
                retrieval_query = clean_message

            combined_result = combined_memory_retrieve(
                retrieval_query,
                profile_limit=settings.profile_retrieval_top_k,
                experience_limit=settings.retrieval_top_k,
            )
            profile_result = combined_result.profile
            experience_result = combined_result.experience
            score_gap = experience_result.top_score - experience_result.second_score
            experience_passes = experience_result.top_score >= settings.retrieval_min_top_score and (
                experience_result.top_score >= settings.retrieval_strong_top_score
                or score_gap >= settings.retrieval_min_score_gap
            )
            if is_ask_back_response:
                experience_passes = True  # always bridge, never fall back on visitor answer turns

            profile_passes = (
                profile_result.top_score >= settings.profile_retrieval_min_top_score
                and bool(profile_result.context_blocks)
            )

            memory_sources = []
            if profile_passes:
                memory_sources.append("profile")
            if experience_passes:
                memory_sources.append("experience")

            max_blocks = max(1, settings.memory_context_max_blocks)
            if experience_passes:
                experience_context = experience_result.context_blocks[:max_blocks]
                remaining_blocks = max_blocks - len(experience_context)
            else:
                experience_context = []
                remaining_blocks = max_blocks
            profile_context = (
                profile_result.context_blocks[:remaining_blocks]
                if profile_passes and remaining_blocks > 0
                else []
            )

            use_memory = bool(memory_sources) or is_ask_back_response
            citations = experience_result.citations if experience_passes else []
            active_topics = experience_result.active_topics if experience_passes else []

            if should_ask_back:
                follow_up_questions = []
                adjacent_topics = []
            else:
                follow_up_questions = (
                    build_follow_up_questions(
                        user_message=clean_message,
                        active_topic_id=payload.active_topic_id,
                        active_topics=active_topics,
                        citations=citations,
                        topics=experience_result.topics,
                    )
                    if experience_passes
                    else []
                )
                adjacent_topics = (
                    build_adjacent_topics(
                        active_topic_id=payload.active_topic_id,
                        active_topics=active_topics,
                        citations=citations,
                        topics=experience_result.topics,
                        edges=experience_result.edges,
                        limit=max(0, 3 - len(follow_up_questions)),
                    )
                    if experience_passes
                    else []
                )
            if use_memory:
                answer = await asyncio.to_thread(
                    functools.partial(
                        generate_chat_answer,
                        settings=settings,
                        user_message=clean_message,
                        profile_context=profile_context,
                        experience_context=experience_context,
                        citations=citations,
                        active_topic_id=payload.active_topic_id,
                        prefill_origin=payload.prefill_origin,
                        message_index=message_index,
                        follow_up_questions=follow_up_questions,
                        adjacent_topics=adjacent_topics,
                        cta_mention=cta_mention,
                        max_output_tokens=output_token_budget,
                        ask_visitor_question=should_ask_back,
                        visitor_context=visitor_context,
                    )
                )
            else:
                answer = await asyncio.to_thread(
                    functools.partial(
                        generate_small_talk_answer,
                        settings=settings,
                        user_message=clean_message,
                        is_mobile=is_mobile,
                        message_index=message_index,
                    )
                )

    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if message_index <= 3 and is_general_work_query(clean_message):
        answer = _append_topic_hint(answer, is_mobile=is_mobile)

    answer = truncate_text_to_token_limit(answer, output_token_budget)
    if should_ask_back:
        answer = _separate_ask_back_question(answer)

    # If the answer ends with a visitor-directed question (spontaneous or controlled),
    # suppress follow-up chips — the visitor should answer the question, not jump topics.
    if answer.strip().endswith("?"):
        follow_up_questions = []
        adjacent_topics = []
    output_tokens = estimate_tokens(answer)
    session_snapshot = record_assistant_response_tokens(
        session_id=session_id,
        estimated_output_tokens=output_tokens,
    )

    if route == "memory" and experience_result is not None:
        should_activate = (
            "experience" in memory_sources
            and experience_result.top_score >= settings.activation_min_top_score
        )
        weighted_citations = [
            (citation.experience_id, citation.score)
            for citation in citations
            if citation.score >= settings.activation_min_citation_score
        ]
        if should_activate and weighted_citations:
            update_activation(
                session_id=session_id,
                cited_experiences=weighted_citations,
                alpha=settings.activation_increment_alpha,
            )
        elif "experience" not in memory_sources:
            log_memory_gap(
                query_text=clean_message,
                session_id=session_id,
                top_score=experience_result.top_score,
                score_gap=score_gap,
            )

    if cta_mention is not None:
        session_snapshot = touch_session(
            SessionTouchRequest(
                session_id=session_id,
                cta_mentioned=True,
                cta_rejected=cta_rejected,
                active_topic_id=payload.active_topic_id,
            )
        )

    final_session_state = ChatSessionState(
        session_id=session_snapshot.session_id,
        active_topic_id=session_snapshot.active_topic_id,
        prefill_origin=payload.prefill_origin,
        message_index=message_index,
        cta_already_mentioned=session_snapshot.cta_mentioned,
        cta_rejected=session_snapshot.cta_rejected,
        first_message_recorded=session_update.first_message_recorded,
        depth_5_reached=session_update.depth_5_reached,
    )

    if route == "small_talk" or not use_memory:
        response_mode = "small_talk"
    elif set(memory_sources) == {"profile", "experience"}:
        response_mode = "blended"
    elif memory_sources == ["profile"]:
        response_mode = "profile"
    elif memory_sources == ["experience"]:
        response_mode = "experience"
    else:
        response_mode = None

    async def event_stream():
        # Split on paragraph breaks first to preserve them, then tokenize words within each paragraph
        paragraphs = answer.split("\n\n")
        tokens: list[str] = []
        for p_idx, para in enumerate(paragraphs):
            words = para.split()
            for w_idx, word in enumerate(words):
                tokens.append(word + (" " if w_idx < len(words) - 1 else ""))
            if p_idx < len(paragraphs) - 1:
                tokens.append("\n\n")
        for tok in tokens:
            yield f"event: token\ndata: {json.dumps({'token': tok})}\n\n"
            await asyncio.sleep(0.01)

        metadata = ChatFinalMetadata(
            active_topics=active_topics,
            citations=citations,
            follow_up_questions=follow_up_questions,
            adjacent_topics=adjacent_topics,
            cta_mention=cta_mention,
            session_state=final_session_state,
            route=route,
            memory_sources=memory_sources,
            response_mode=response_mode,
        )
        yield f"event: final\ndata: {metadata.model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
