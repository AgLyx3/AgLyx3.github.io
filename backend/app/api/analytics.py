"""Analytics ingest API."""

from fastapi import APIRouter, Depends

from app.api.auth import require_admin_key
from app.models import (
    AnalyticsEventCreate,
    AnalyticsIngestResponse,
    SessionEnsureRequest,
)
from app.services import log_analytics_event
from app.services.session import ensure_session

router = APIRouter(tags=["analytics"])


@router.post("/events", response_model=AnalyticsIngestResponse, dependencies=[Depends(require_admin_key)])
@router.post("/analytics/events", response_model=AnalyticsIngestResponse, include_in_schema=False, dependencies=[Depends(require_admin_key)])
def create_event(payload: AnalyticsEventCreate) -> AnalyticsIngestResponse:
    ensure_session(
        SessionEnsureRequest(
            session_id=payload.session_id,
            active_topic_id=str(payload.payload.get("topic_id") or "").strip() or None,
        )
    )
    event = log_analytics_event(payload)
    return AnalyticsIngestResponse(accepted=True, event=event)
