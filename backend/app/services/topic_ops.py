"""Database-backed topic notification and memory curation helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.config import get_settings
from app.models import (
    MemoryGapRecord,
    MemoryIngestRequest,
    MemoryIngestResponse,
    TopicMemoryCreateRequest,
    TopicMemoryRecord,
    TopicNotification,
    TopicPendingMemory,
)
from app.services.db import get_conn
from app.services.llm import assign_memory_topics_with_llm


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    return "-".join(part for part in cleaned.split("-") if part) or "topic"


def _derive_summary(details: str, limit: int = 240) -> str:
    text = " ".join(details.split()).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def list_topic_notifications(limit: int = 50) -> list[TopicNotification]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT event, created_at, topic_id, topic_name, candidate_id, distinct_sessions, mentions
            FROM topic_notifications
            ORDER BY event_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        TopicNotification(
            event=row["event"],
            created_at=row["created_at"],
            topic_id=row["topic_id"],
            topic_name=row["topic_name"],
            candidate_id=row["candidate_id"],
            distinct_sessions=int(row["distinct_sessions"]),
            mentions=int(row["mentions"]),
        )
        for row in rows
    ]


def log_memory_gap(*, query_text: str, session_id: str, top_score: float, score_gap: float) -> None:
    now = datetime.now(UTC).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO memory_query_gaps(query_text, session_id, top_score, score_gap, created_at)
            VALUES(?,?,?,?,?)
            """,
            (query_text.strip(), session_id.strip(), float(top_score), float(score_gap), now),
        )
        conn.commit()


def list_memory_gaps(limit: int = 100) -> list[MemoryGapRecord]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT gap_id, query_text, session_id, top_score, score_gap, created_at
            FROM memory_query_gaps
            ORDER BY gap_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        MemoryGapRecord(
            gap_id=int(row["gap_id"]),
            query_text=str(row["query_text"]),
            session_id=str(row["session_id"]),
            top_score=float(row["top_score"]),
            score_gap=float(row["score_gap"]),
            created_at=str(row["created_at"]),
        )
        for row in rows
    ]


def create_topic_memory(topic_id: str, payload: TopicMemoryCreateRequest) -> TopicMemoryRecord:
    now = datetime.now(UTC).isoformat()
    memory_id = f"mem-{_slug(topic_id)}-{uuid4().hex[:10]}"
    derived_summary = _derive_summary(payload.details)
    record = TopicMemoryRecord(
        memory_id=memory_id,
        topic_id=topic_id,
        title=payload.title.strip(),
        summary=derived_summary,
        details=payload.details.strip(),
        source=payload.source.strip(),
        created_at=now,
    )
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO topic_memories(memory_id, topic_id, title, summary, details, source, created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                record.memory_id,
                record.topic_id,
                record.title,
                record.summary,
                record.details,
                record.source,
                record.created_at,
            ),
        )
        experience_id = f"exp-{_slug(record.title)}-{record.memory_id[-6:]}"
        conn.execute(
            """
            INSERT INTO experiences(
                id, title, raw_context, experience_date, activation, created_at
            )
            VALUES(?,?,?,?,?,?)
            """,
            (
                experience_id,
                record.title,
                record.details,
                "",
                0.0,
                record.created_at,
            ),
        )
        conn.execute(
            """
            INSERT INTO relevance_edges(source_experience_id, target_topic_id, relevance)
            VALUES(?,?,?)
            ON CONFLICT(source_experience_id, target_topic_id)
            DO UPDATE SET relevance = excluded.relevance
            """,
            (experience_id, topic_id, 0.85),
        )
        conn.commit()
    return record


def ingest_memory(payload: MemoryIngestRequest) -> MemoryIngestResponse:
    settings = get_settings()
    with get_conn() as conn:
        topic_rows = conn.execute("SELECT id, label, description FROM topics ORDER BY label").fetchall()
    topic_catalog = [
        {"id": str(row["id"]), "label": str(row["label"]), "description": str(row["description"])}
        for row in topic_rows
    ]

    if payload.topic_ids:
        assigned = payload.topic_ids[:3]
        assignment_mode = "manual_topic_ids"
    else:
        assigned = assign_memory_topics_with_llm(
            settings=settings,
            title=payload.title,
            details=payload.details,
            topics=topic_catalog,
        )
        assignment_mode = "llm_assigned"

    if not assigned:
        assigned = ["topic_memory"] if any(t["id"] == "topic_memory" for t in topic_catalog) else []
        assignment_mode = "fallback_default"
    if not assigned:
        raise ValueError("No topics available for assignment")

    now = datetime.now(UTC).isoformat()
    memory_id = f"mem-{uuid4().hex[:10]}"
    experience_id = f"exp-{_slug(payload.title)}-{memory_id[-6:]}"
    derived_summary = _derive_summary(payload.details)
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO topic_memories(memory_id, topic_id, title, summary, details, source, created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                memory_id,
                assigned[0],
                payload.title.strip(),
                derived_summary,
                payload.details.strip(),
                payload.source.strip(),
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO experiences(
                id, title, raw_context, experience_date, activation, created_at
            )
            VALUES(?,?,?,?,?,?)
            """,
            (
                experience_id,
                payload.title.strip(),
                payload.details.strip(),
                "",
                0.0,
                now,
            ),
        )
        for index, topic_id in enumerate(assigned):
            relevance = max(0.5, 0.9 - 0.15 * index)
            conn.execute(
                """
                INSERT INTO relevance_edges(source_experience_id, target_topic_id, relevance)
                VALUES(?,?,?)
                ON CONFLICT(source_experience_id, target_topic_id)
                DO UPDATE SET relevance = excluded.relevance
                """,
                (experience_id, topic_id, relevance),
            )
        conn.commit()

    return MemoryIngestResponse(
        memory_id=memory_id,
        experience_id=experience_id,
        assigned_topics=assigned,
        assignment_mode=assignment_mode,
    )


def list_topics_pending_memory() -> list[TopicPendingMemory]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT t.id AS topic_id, t.label AS topic_name, t.created_at AS created_at,
                   COUNT(m.memory_id) AS memory_count
            FROM topics t
            LEFT JOIN topic_memories m ON m.topic_id = t.id
            WHERE t.approval_mode = 'auto'
            GROUP BY t.id, t.label, t.created_at
            HAVING COUNT(m.memory_id) = 0
            ORDER BY t.created_at DESC
            """
        ).fetchall()
    return [
        TopicPendingMemory(
            topic_id=row["topic_id"],
            topic_name=row["topic_name"],
            created_at=row["created_at"],
            memory_count=int(row["memory_count"]),
        )
        for row in rows
    ]
