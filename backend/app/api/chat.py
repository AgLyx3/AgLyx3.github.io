"""Chat API endpoint with SSE token stream and final metadata."""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.models import ChatFinalMetadata, ChatRequest
from app.services import (
    generate_chat_answer,
    hybrid_retrieve,
    log_memory_gap,
    sanitize_text,
    update_activation,
)

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat_endpoint(
    payload: ChatRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    client_key = request.client.host if request.client else "unknown"
    clean_message = sanitize_text(payload.message)
    result = hybrid_retrieve(clean_message, limit=settings.retrieval_top_k)
    use_memory = (
        result.top_score >= settings.retrieval_min_top_score
        and (result.top_score - result.second_score) >= settings.retrieval_min_score_gap
    )
    context_blocks = result.context_blocks if use_memory else []
    citations = result.citations if use_memory else []
    active_topics = result.active_topics if use_memory else []
    score_gap = result.top_score - result.second_score
    try:
        if use_memory:
            answer = generate_chat_answer(
                settings=settings,
                user_message=clean_message,
                context_blocks=context_blocks,
            )
        else:
            answer = (
                "Hmm, I do not have a strong memory about this yet, but Yixin may update this later. "
                "If you want, ask a related question and I can try nearby topics."
            )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    should_activate = use_memory and result.top_score >= settings.activation_min_top_score
    weighted_citations = [
        (citation.experience_id, citation.score)
        for citation in citations
        if citation.score >= settings.activation_min_citation_score
    ]
    if should_activate and weighted_citations:
        update_activation(
            session_id=payload.session_id or client_key,
            query=clean_message,
            cited_experiences=weighted_citations,
            alpha=settings.activation_increment_alpha,
        )
    elif not use_memory:
        log_memory_gap(
            query_text=clean_message,
            session_id=payload.session_id or client_key,
            top_score=result.top_score,
            score_gap=score_gap,
        )

    async def event_stream():
        for token in answer.split(" "):
            yield f"event: token\ndata: {json.dumps({'token': token + ' '})}\n\n"
            await asyncio.sleep(0.01)

        metadata = ChatFinalMetadata(active_topics=active_topics, citations=citations)
        yield f"event: final\ndata: {metadata.model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
