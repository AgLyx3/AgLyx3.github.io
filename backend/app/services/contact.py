"""Contact and outbound message persistence."""

from __future__ import annotations

import json

from app.models.actions import ContactMessageRequest, ContactMessageResponse
from app.services.db import get_conn, utc_now_iso
from app.services.session import ensure_session


def create_contact_message(request: ContactMessageRequest) -> ContactMessageResponse:
    ensure_session(request.session_id)
    created_at = utc_now_iso()
    conversation_json = None
    included_chat_history = request.included_chat_history and bool(request.conversation_history)
    if included_chat_history:
        conversation_json = json.dumps(
            [message.model_dump(mode="json") for message in request.conversation_history],
            ensure_ascii=True,
            separators=(",", ":"),
        )

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO outbound_messages(
                session_id, message_body, included_chat_history, conversation_json, created_at, delivery_status
            ) VALUES(?,?,?,?,?,?)
            RETURNING message_id
            """,
            (
                request.session_id,
                request.message_body,
                int(included_chat_history),
                conversation_json,
                created_at,
                "recorded",
            ),
        )
        row = cursor.fetchone()
        message_id = int(row["message_id"] if hasattr(row, "keys") else row[0])
        conn.commit()

    return ContactMessageResponse(
        message_id=message_id,
        delivery_status="recorded",
        included_chat_history=included_chat_history,
        created_at=created_at,
    )
