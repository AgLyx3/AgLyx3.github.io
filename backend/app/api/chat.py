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
    detect_cta_rejection,
    estimate_tokens,
    ensure_session,
    generate_chat_answer,
    hybrid_retrieve,
    log_memory_gap,
    log_analytics_event,
    record_assistant_response_tokens,
    record_user_message,
    sanitize_text,
    should_offer_cta,
    touch_session,
    truncate_text_to_token_limit,
    update_activation,
)

router = APIRouter(tags=["chat"])
chat_rate_limiter = RateLimiter(get_settings().chat_rate_limit_per_minute)


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

    result = hybrid_retrieve(clean_message, limit=settings.retrieval_top_k)
    use_memory = (
        result.top_score >= settings.retrieval_min_top_score
        and (result.top_score - result.second_score) >= settings.retrieval_min_score_gap
    )
    context_blocks = result.context_blocks if use_memory else []
    citations = result.citations if use_memory else []
    active_topics = result.active_topics if use_memory else []
    score_gap = result.top_score - result.second_score
    follow_up_questions = (
        build_follow_up_questions(
            user_message=clean_message,
            active_topic_id=payload.active_topic_id,
            active_topics=active_topics,
            citations=citations,
            topics=result.topics,
        )
        if use_memory
        else []
    )
    adjacent_topics = (
        build_adjacent_topics(
            active_topic_id=payload.active_topic_id,
            active_topics=active_topics,
            citations=citations,
            topics=result.topics,
            edges=result.edges,
        )
        if use_memory
        else []
    )
    cta_mention = should_offer_cta(
        user_message=clean_message,
        message_index=message_index,
        cta_already_mentioned=payload.cta_already_mentioned or session_snapshot.cta_mentioned,
        cta_rejected=cta_rejected,
    )
    try:
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
        if use_memory:
            answer = await asyncio.to_thread(
                functools.partial(
                    generate_chat_answer,
                    settings=settings,
                    user_message=clean_message,
                    context_blocks=context_blocks,
                    citations=citations,
                    active_topic_id=payload.active_topic_id,
                    prefill_origin=payload.prefill_origin,
                    message_index=message_index,
                    follow_up_questions=follow_up_questions,
                    adjacent_topics=adjacent_topics,
                    cta_mention=cta_mention,
                    max_output_tokens=output_token_budget,
                )
            )
        else:
            answer = MEMORY_FALLBACK_RESPONSE
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    answer = truncate_text_to_token_limit(answer, output_token_budget)
    output_tokens = estimate_tokens(answer)
    session_snapshot = record_assistant_response_tokens(
        session_id=session_id,
        estimated_output_tokens=output_tokens,
    )
    should_activate = use_memory and result.top_score >= settings.activation_min_top_score
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
    elif not use_memory:
        log_memory_gap(
            query_text=clean_message,
            session_id=session_id,
            top_score=result.top_score,
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

    async def event_stream():
        words = answer.split()  # split() collapses all whitespace, no empty tokens
        for i, word in enumerate(words):
            suffix = " " if i < len(words) - 1 else ""
            yield f"event: token\ndata: {json.dumps({'token': word + suffix})}\n\n"
            await asyncio.sleep(0.01)

        metadata = ChatFinalMetadata(
            active_topics=active_topics,
            citations=citations,
            follow_up_questions=follow_up_questions,
            adjacent_topics=adjacent_topics,
            cta_mention=cta_mention,
            session_state=final_session_state,
        )
        yield f"event: final\ndata: {metadata.model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
