"""Contact and outbound message persistence."""

from __future__ import annotations

import json
from urllib import error, request

from app.config import Settings, get_settings
from app.models.actions import ContactMessageRequest, ContactMessageResponse
from app.services.db import get_conn, utc_now_iso
from app.services.session import ensure_session


def _send_via_resend(
    *,
    settings: Settings,
    message_body: str,
    conversation_history: list | None = None,
) -> None:
    history_html = ""
    if conversation_history:
        rows = "".join(
            f"<tr><td style='padding:4px 8px;color:#888;white-space:nowrap'>{m.get('role','').capitalize()}</td>"
            f"<td style='padding:4px 8px'>{m.get('content','')}</td></tr>"
            for m in conversation_history
        )
        history_html = (
            "<h3 style='margin-top:24px'>Conversation history</h3>"
            f"<table style='border-collapse:collapse;width:100%'>{rows}</table>"
        )

    html = (
        "<div style='font-family:sans-serif;max-width:600px'>"
        "<h2>New message from your portfolio</h2>"
        f"<p style='font-size:16px'>{message_body}</p>"
        f"{history_html}"
        "</div>"
    )

    payload = {
        "from": settings.contact_from_email,
        "to": [settings.contact_to_email],
        "subject": "New message from your portfolio",
        "html": html,
    }
    req = request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            resp.read()
    except (error.URLError, error.HTTPError) as exc:
        raise RuntimeError(f"Resend delivery failed: {exc}") from exc


def create_contact_message(
    payload: ContactMessageRequest,
    settings: Settings | None = None,
) -> ContactMessageResponse:
    if settings is None:
        settings = get_settings()

    ensure_session(payload.session_id)
    created_at = utc_now_iso()
    conversation_json = None
    included_chat_history = payload.included_chat_history and bool(payload.conversation_history)
    history_dicts: list | None = None
    if included_chat_history:
        history_dicts = [m.model_dump(mode="json") for m in payload.conversation_history]
        conversation_json = json.dumps(history_dicts, ensure_ascii=True, separators=(",", ":"))

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO outbound_messages(
                session_id, message_body, included_chat_history, conversation_json, created_at, delivery_status
            ) VALUES(?,?,?,?,?,?)
            RETURNING message_id
            """,
            (
                payload.session_id,
                payload.message_body,
                included_chat_history,
                conversation_json,
                created_at,
                "recorded",
            ),
        )
        row = cursor.fetchone()
        message_id = int(row["message_id"] if hasattr(row, "keys") else row[0])
        conn.commit()

    delivery_status = "recorded"
    if settings.resend_api_key:
        try:
            _send_via_resend(
                settings=settings,
                message_body=payload.message_body,
                conversation_history=history_dicts,
            )
            delivery_status = "sent"
        except RuntimeError:
            delivery_status = "failed"

        with get_conn() as conn:
            conn.execute(
                "UPDATE outbound_messages SET delivery_status=? WHERE message_id=?",
                (delivery_status, message_id),
            )
            conn.commit()

    return ContactMessageResponse(
        message_id=message_id,
        delivery_status=delivery_status,
        included_chat_history=included_chat_history,
        created_at=created_at,
    )
