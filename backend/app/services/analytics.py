"""Analytics event persistence."""

from __future__ import annotations

import json

from app.config import get_settings
from app.models.analytics import (
    AnalyticsEventCreate,
    AnalyticsEventRecord,
    AnalyticsEventValidation,
)
from app.services.db import get_conn, utc_now_iso


def log_analytics_event(event: AnalyticsEventCreate) -> AnalyticsEventRecord:
    AnalyticsEventValidation(event_name=event.event_name, payload=event.payload)
    created_at = utc_now_iso()
    settings = get_settings()
    if not settings.analytics_write_enabled:
        return AnalyticsEventRecord(
            event_id=0,
            session_id=event.session_id,
            event_name=event.event_name,
            payload=event.payload,
            created_at=created_at,
        )
    payload_json = json.dumps(event.payload, ensure_ascii=True, separators=(",", ":"))
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO analytics_events(session_id, event_name, event_payload_json, created_at)
            VALUES(?,?,?,?)
            RETURNING event_id
            """,
            (event.session_id, event.event_name, payload_json, created_at),
        )
        row = cursor.fetchone()
        event_id = int(row["event_id"] if hasattr(row, "keys") else row[0])
        conn.commit()
    return AnalyticsEventRecord(
        event_id=event_id,
        session_id=event.session_id,
        event_name=event.event_name,
        payload=event.payload,
        created_at=created_at,
    )
