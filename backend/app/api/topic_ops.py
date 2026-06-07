"""APIs for auto-topic notifications and manual memory backfill."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import require_admin_key
from app.models import (
    MemoryGapRecord,
    MemoryIngestRequest,
    MemoryIngestResponse,
    TopicMemoryCreateRequest,
    TopicMemoryRecord,
    TopicNotification,
    TopicPendingMemory,
)
from app.services import (
    create_topic_memory,
    ingest_memory,
    list_memory_gaps,
    list_topic_notifications,
    list_topics_pending_memory,
)

router = APIRouter(prefix="/topics", tags=["topics"], dependencies=[Depends(require_admin_key)])


@router.get("/notifications", response_model=list[TopicNotification])
def get_topic_notifications(limit: int = Query(default=50, ge=1, le=500)) -> list[TopicNotification]:
    return list_topic_notifications(limit=limit)


@router.get("/pending-memory", response_model=list[TopicPendingMemory])
def get_topics_pending_memory() -> list[TopicPendingMemory]:
    return list_topics_pending_memory()


@router.get("/memory-gaps", response_model=list[MemoryGapRecord])
def get_memory_gaps(limit: int = Query(default=100, ge=1, le=1000)) -> list[MemoryGapRecord]:
    return list_memory_gaps(limit=limit)


@router.post("/{topic_id}/memories", response_model=TopicMemoryRecord)
def post_topic_memory(topic_id: str, payload: TopicMemoryCreateRequest) -> TopicMemoryRecord:
    return create_topic_memory(topic_id=topic_id, payload=payload)


@router.post("/memories/ingest", response_model=MemoryIngestResponse)
def post_memory_ingest(payload: MemoryIngestRequest) -> MemoryIngestResponse:
    try:
        return ingest_memory(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


