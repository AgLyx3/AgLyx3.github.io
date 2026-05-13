"""Media surfacing service — pick and track outbound media per session."""

from __future__ import annotations

from app.services.db import get_conn, utc_now_iso


def _pick_unshown_experience_media(session_id: str, experience_ids: list[str]) -> dict | None:
    if not experience_ids:
        return None
    with get_conn() as conn:
        for experience_id in experience_ids:
            row = conn.execute(
                """
                SELECT em.id, em.url, em.media_type, em.caption
                FROM experience_media em
                WHERE em.experience_id = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM session_shown_media_keys ssm
                      WHERE ssm.session_id = ? AND ssm.media_key = ('experience:' || em.id)
                  )
                ORDER BY em.display_order ASC, em.id ASC
                LIMIT 1
                """,
                (experience_id, session_id),
            ).fetchone()
            if row is not None:
                return {
                    "id": row["id"],
                    "url": row["url"],
                    "media_type": row["media_type"],
                    "caption": row["caption"],
                    "source": "experience",
                }
    return None


def _pick_unshown_profile_media(session_id: str, profile_memory_ids: list[str]) -> dict | None:
    if not profile_memory_ids:
        return None
    placeholders = ",".join("?" * len(profile_memory_ids))
    with get_conn() as conn:
        row = conn.execute(
            f"""
            SELECT pm.id, pm.url, pm.media_type, pm.caption
            FROM profile_media pm
            WHERE pm.memory_id IN ({placeholders})
              AND NOT EXISTS (
                  SELECT 1 FROM session_shown_media_keys ssm
                  WHERE ssm.session_id = ? AND ssm.media_key = ('profile:' || pm.id)
              )
            ORDER BY pm.display_order ASC
            LIMIT 1
            """,
            (*profile_memory_ids, session_id),
        ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "url": row["url"],
        "media_type": row["media_type"],
        "caption": row["caption"],
        "source": "profile",
    }


def pick_unshown_media(
    session_id: str,
    *,
    experience_ids: list[str] | None = None,
    profile_memory_ids: list[str] | None = None,
) -> dict | None:
    """Return one unshown media item, prioritizing experience media before profile media.

    Respects citation order (caller passes experience_ids highest-score-first).
    Within a single experience, display_order breaks ties.
    """
    experience_media = _pick_unshown_experience_media(session_id, experience_ids or [])
    if experience_media is not None:
        return experience_media
    return _pick_unshown_profile_media(session_id, profile_memory_ids or [])


def mark_media_shown(session_id: str, media_id: int, *, source: str = "experience") -> None:
    """Record that a media item was surfaced in this session (idempotent)."""
    media_key = f"{source}:{media_id}"
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO session_shown_media_keys(session_id, media_key, shown_at) "
            "VALUES(?, ?, ?) ON CONFLICT DO NOTHING",
            (session_id, media_key, utc_now_iso()),
        )
        conn.commit()
