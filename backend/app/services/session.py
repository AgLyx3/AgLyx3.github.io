"""Ephemeral session state management for chat analytics and CTA rules."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.config import get_settings
from app.models.analytics import (
    SessionEnsureRequest,
    SessionMessageRecordRequest,
    SessionMessageRecordResult,
    SessionSnapshot,
    SessionTouchRequest,
)
from app.services.db import get_conn, utc_now_iso


def _row_to_snapshot(row) -> SessionSnapshot:
    return SessionSnapshot(
        session_id=row["session_id"],
        started_at=row["started_at"],
        last_seen_at=row["last_seen_at"],
        message_count=int(row["message_count"]),
        total_token_count=int(row["total_token_count"]),
        input_token_count=int(row["input_token_count"]),
        output_token_count=int(row["output_token_count"]),
        first_message_at=row["first_message_at"],
        depth_5_reached_at=row["depth_5_reached_at"],
        cta_mentioned=bool(row["cta_mentioned"]),
        cta_rejected=bool(row["cta_rejected"]),
        active_topic_id=row["active_topic_id"],
        last_ask_back_round=int(row["last_ask_back_round"] or 0),
        ask_back_pending=bool(row["ask_back_pending"]),
    )


def ensure_session(
    request: SessionEnsureRequest | str, *, active_topic_id: str | None = None
) -> SessionSnapshot:
    if isinstance(request, str):
        request = SessionEnsureRequest(session_id=request, active_topic_id=active_topic_id)
    now = utc_now_iso()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (request.session_id,),
        ).fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO sessions(
                    session_id, started_at, last_seen_at, message_count,
                    total_token_count, input_token_count, output_token_count,
                    first_message_at, depth_5_reached_at, cta_mentioned,
                    cta_rejected, active_topic_id, last_ask_back_round, ask_back_pending
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    request.session_id,
                    now,
                    now,
                    0,
                    0,
                    0,
                    0,
                    None,
                    None,
                    False,
                    False,
                    request.active_topic_id,
                    0,
                    False,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (request.session_id,),
            ).fetchone()
        return _row_to_snapshot(row)


def touch_session(request: SessionTouchRequest) -> SessionSnapshot:
    ensure_session(
        SessionEnsureRequest(session_id=request.session_id, active_topic_id=request.active_topic_id)
    )
    now = utc_now_iso()
    with get_conn() as conn:
        current = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (request.session_id,),
        ).fetchone()
        cta_mentioned = (
            bool(request.cta_mentioned)
            if request.cta_mentioned is not None
            else bool(current["cta_mentioned"])
        )
        cta_rejected = (
            bool(request.cta_rejected)
            if request.cta_rejected is not None
            else bool(current["cta_rejected"])
        )
        active_topic_id = request.active_topic_id if request.active_topic_id is not None else current["active_topic_id"]
        conn.execute(
            """
            UPDATE sessions
            SET last_seen_at = ?, cta_mentioned = ?, cta_rejected = ?, active_topic_id = ?
            WHERE session_id = ?
            """,
            (now, cta_mentioned, cta_rejected, active_topic_id, request.session_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (request.session_id,),
        ).fetchone()
        return _row_to_snapshot(row)


def record_user_message(request: SessionMessageRecordRequest) -> SessionMessageRecordResult:
    settings = get_settings()
    ensure_session(
        SessionEnsureRequest(session_id=request.session_id, active_topic_id=request.active_topic_id)
    )
    now = utc_now_iso()
    clean_message = request.message_text.strip()
    with get_conn() as conn:
        current = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (request.session_id,),
        ).fetchone()
        current_count = int(current["message_count"])
        current_total_tokens = int(current["total_token_count"])
        input_tokens = int(request.estimated_input_tokens)
        if current_count >= settings.max_messages_per_session:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Session message limit reached ({settings.max_messages_per_session}). Start a new session to continue.",
            )
        if input_tokens > settings.max_input_tokens_per_message:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"Message too large for chat input limit ({settings.max_input_tokens_per_message} tokens max)."
                ),
            )
        if current_total_tokens + input_tokens > settings.max_total_tokens_per_session:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Session token limit reached ({settings.max_total_tokens_per_session} total tokens). Start a new session to continue."
                ),
            )
        next_count = current_count + 1
        first_message_recorded = current["first_message_at"] is None
        first_message_at = now if first_message_recorded else current["first_message_at"]
        depth_5_reached = next_count >= 5 and current["depth_5_reached_at"] is None
        depth_5_reached_at = now if depth_5_reached else current["depth_5_reached_at"]
        active_topic_id = request.active_topic_id if request.active_topic_id is not None else current["active_topic_id"]
        conn.execute(
            """
            UPDATE sessions
            SET last_seen_at = ?,
                message_count = ?,
                total_token_count = ?,
                input_token_count = ?,
                first_message_at = ?,
                depth_5_reached_at = ?,
                active_topic_id = ?
            WHERE session_id = ?
            """,
            (
                now,
                next_count,
                current_total_tokens + input_tokens,
                int(current["input_token_count"]) + input_tokens,
                first_message_at,
                depth_5_reached_at,
                active_topic_id,
                request.session_id,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (request.session_id,),
        ).fetchone()

    return SessionMessageRecordResult(
        session=_row_to_snapshot(row),
        message_index_in_session=next_count,
        first_message_recorded=first_message_recorded,
        depth_5_reached=depth_5_reached,
    )


def record_assistant_response_tokens(*, session_id: str, estimated_output_tokens: int) -> SessionSnapshot:
    ensure_session(SessionEnsureRequest(session_id=session_id))
    now = utc_now_iso()
    with get_conn() as conn:
        current = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        conn.execute(
            """
            UPDATE sessions
            SET last_seen_at = ?,
                total_token_count = ?,
                output_token_count = ?
            WHERE session_id = ?
            """,
            (
                now,
                int(current["total_token_count"]) + int(estimated_output_tokens),
                int(current["output_token_count"]) + int(estimated_output_tokens),
                session_id,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return _row_to_snapshot(row)


def record_chat_message(request: SessionMessageRecordRequest) -> SessionMessageRecordResult:
    return record_user_message(request)


def record_ask_back(session_id: str, round: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET last_ask_back_round = ?, ask_back_pending = ? WHERE session_id = ?",
            (round, True, session_id),
        )
        conn.commit()


def clear_ask_back_pending(session_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET ask_back_pending = ? WHERE session_id = ?",
            (False, session_id),
        )
        conn.commit()


def snooze_ask_back(session_id: str, current_round: int) -> None:
    """Visitor ignored the ask-back question. Push the clock forward so we don't ask again soon."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET last_ask_back_round = ? WHERE session_id = ?",
            (current_round + 3, session_id),
        )
        conn.commit()
