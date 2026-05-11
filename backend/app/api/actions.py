"""Action tracking and contact endpoints."""

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models import (
    ActionTrackRequest,
    ActionTrackResponse,
    AnalyticsEventCreate,
    ContactMessageRequest,
    ContactMessageResponse,
    ResumeDownloadRequest,
    SessionEnsureRequest,
)
from app.services import create_contact_message, log_analytics_event
from app.services.session import ensure_session

router = APIRouter(tags=["actions"])


def _track_and_respond(
    *,
    event_name: str,
    action_type: str,
    session_id: str,
    message_count_before_action: int,
    payload: dict,
    target_url: str | None = None,
) -> ActionTrackResponse:
    click_event = log_analytics_event(
        AnalyticsEventCreate(
            session_id=session_id,
            event_name="cta_footer_clicked",
            payload={
                "action_type": action_type,
                "message_count_before_action": message_count_before_action,
            },
        )
    )
    final_event = log_analytics_event(
        AnalyticsEventCreate(
            session_id=session_id,
            event_name=event_name,
            payload={**payload, "message_count_before_action": message_count_before_action},
        )
    )
    return ActionTrackResponse(
        action_type=action_type,
        tracked=True,
        target_url=target_url,
        tracked_at=final_event.created_at or click_event.created_at,
    )


@router.post("/actions/linkedin", response_model=ActionTrackResponse)
def track_linkedin(
    payload: ActionTrackRequest,
    settings: Settings = Depends(get_settings),
) -> ActionTrackResponse:
    ensure_session(SessionEnsureRequest(session_id=payload.session_id))
    return _track_and_respond(
        event_name="linkedin_profile_opened",
        action_type="linkedin",
        session_id=payload.session_id,
        message_count_before_action=payload.message_count_before_action,
        payload={},
        target_url=payload.target_url or settings.linkedin_url,
    )


@router.post("/actions/resume", response_model=ActionTrackResponse)
def track_resume(
    payload: ResumeDownloadRequest,
    settings: Settings = Depends(get_settings),
) -> ActionTrackResponse:
    ensure_session(SessionEnsureRequest(session_id=payload.session_id))
    return _track_and_respond(
        event_name="resume_download_started",
        action_type="download_resume",
        session_id=payload.session_id,
        message_count_before_action=payload.message_count_before_action,
        payload={
            "resume_variant": payload.resume_variant,
        },
        target_url=payload.target_url or settings.resume_url,
    )


@router.post("/actions/schedule", response_model=ActionTrackResponse)
def track_schedule(
    payload: ActionTrackRequest,
    settings: Settings = Depends(get_settings),
) -> ActionTrackResponse:
    ensure_session(SessionEnsureRequest(session_id=payload.session_id))
    return _track_and_respond(
        event_name="schedule_time_opened",
        action_type="schedule_time",
        session_id=payload.session_id,
        message_count_before_action=payload.message_count_before_action,
        payload={},
        target_url=payload.target_url or settings.schedule_url,
    )


@router.post("/contact", response_model=ContactMessageResponse)
def send_contact_message(
    payload: ContactMessageRequest,
    settings: Settings = Depends(get_settings),
) -> ContactMessageResponse:
    ensure_session(SessionEnsureRequest(session_id=payload.session_id))
    response = create_contact_message(payload, settings=settings)
    log_analytics_event(
        AnalyticsEventCreate(
            session_id=payload.session_id,
            event_name="message_sent_to_yixin",
            payload={
                "included_chat_history": payload.included_chat_history,
                "message_length": len(payload.message_body),
                "message_count_before_send": payload.message_count_before_send,
            },
        )
    )
    return response
