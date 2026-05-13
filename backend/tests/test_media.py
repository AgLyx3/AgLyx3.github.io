"""Tests for media selection behavior."""

from __future__ import annotations

from app.services.db import get_conn, utc_now_iso
from app.services.media import mark_media_shown, pick_unshown_media


def test_pick_unshown_media_prefers_experience_media(test_db):
    now = utc_now_iso()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO profile_memories(memory_id, key, value, created_at) VALUES(?,?,?,?)",
            ("profile_media_test_pref", "Current_role", "Product Manager", now),
        )
        conn.execute(
            "INSERT OR REPLACE INTO experiences(id, title, raw_context, experience_date, base_weight, activation, created_at) VALUES(?,?,?,?,?,?,?)",
            ("exp_media_test_pref", "Experience media test", "details", "2026-05", 1.0, 0.0, now),
        )
        conn.execute(
            "INSERT INTO experience_media(experience_id, url, media_type, caption, display_order) VALUES(?,?,?,?,?)",
            ("exp_media_test_pref", "https://example.com/experience.jpg", "image", "experience", 0),
        )
        conn.execute(
            "INSERT INTO profile_media(memory_id, url, media_type, caption, display_order) VALUES(?,?,?,?,?)",
            ("profile_media_test_pref", "https://example.com/profile.jpg", "image", "profile", 0),
        )
        conn.commit()

    media = pick_unshown_media(
        "media-pref-session",
        experience_ids=["exp_media_test_pref"],
        profile_memory_ids=["profile_media_test_pref"],
    )

    assert media is not None
    assert media["source"] == "experience"
    assert media["caption"] == "experience"


def test_pick_unshown_media_prefers_first_cited_experience_over_lower_display_order_elsewhere(test_db):
    now = utc_now_iso()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO experiences(id, title, raw_context, experience_date, base_weight, activation, created_at) VALUES(?,?,?,?,?,?,?)",
            ("exp_media_rank_a", "Experience rank A", "details", "2026-05", 1.0, 0.0, now),
        )
        conn.execute(
            "INSERT OR REPLACE INTO experiences(id, title, raw_context, experience_date, base_weight, activation, created_at) VALUES(?,?,?,?,?,?,?)",
            ("exp_media_rank_b", "Experience rank B", "details", "2026-05", 1.0, 0.0, now),
        )
        conn.execute(
            "INSERT INTO experience_media(experience_id, url, media_type, caption, display_order) VALUES(?,?,?,?,?)",
            ("exp_media_rank_a", "https://example.com/top-cited.jpg", "image", "top cited", 1),
        )
        conn.execute(
            "INSERT INTO experience_media(experience_id, url, media_type, caption, display_order) VALUES(?,?,?,?,?)",
            ("exp_media_rank_b", "https://example.com/lower-ranked.jpg", "image", "lower ranked", 0),
        )
        conn.commit()

    media = pick_unshown_media(
        "media-rank-session",
        experience_ids=["exp_media_rank_a", "exp_media_rank_b"],
        profile_memory_ids=[],
    )

    assert media is not None
    assert media["source"] == "experience"
    assert media["caption"] == "top cited"


def test_pick_unshown_media_falls_back_to_profile_media(test_db):
    now = utc_now_iso()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO profile_memories(memory_id, key, value, created_at) VALUES(?,?,?,?)",
            ("profile_media_test_fallback", "Education", "Colby College", now),
        )
        conn.execute(
            "INSERT INTO profile_media(memory_id, url, media_type, caption, display_order) VALUES(?,?,?,?,?)",
            ("profile_media_test_fallback", "https://example.com/profile-only.jpg", "image", "profile only", 0),
        )
        conn.commit()

    media = pick_unshown_media(
        "media-fallback-session",
        experience_ids=[],
        profile_memory_ids=["profile_media_test_fallback"],
    )

    assert media is not None
    assert media["source"] == "profile"
    assert media["caption"] == "profile only"


def test_mark_media_shown_hides_only_matching_source_media(test_db):
    now = utc_now_iso()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO profile_memories(memory_id, key, value, created_at) VALUES(?,?,?,?)",
            ("profile_media_test_seen", "Interest", "Photography", now),
        )
        conn.execute(
            "INSERT OR REPLACE INTO experiences(id, title, raw_context, experience_date, base_weight, activation, created_at) VALUES(?,?,?,?,?,?,?)",
            ("exp_media_test_seen", "Experience shown test", "details", "2026-05", 1.0, 0.0, now),
        )
        conn.execute(
            "INSERT INTO experience_media(experience_id, url, media_type, caption, display_order) VALUES(?,?,?,?,?)",
            ("exp_media_test_seen", "https://example.com/exp-shown.jpg", "image", "exp shown", 0),
        )
        conn.execute(
            "INSERT INTO profile_media(memory_id, url, media_type, caption, display_order) VALUES(?,?,?,?,?)",
            ("profile_media_test_seen", "https://example.com/profile-shown.jpg", "image", "profile shown", 0),
        )
        conn.commit()

    first_media = pick_unshown_media(
        "media-seen-session",
        experience_ids=["exp_media_test_seen"],
        profile_memory_ids=["profile_media_test_seen"],
    )
    assert first_media is not None
    assert first_media["source"] == "experience"

    mark_media_shown("media-seen-session", first_media["id"], source=first_media["source"])

    second_media = pick_unshown_media(
        "media-seen-session",
        experience_ids=["exp_media_test_seen"],
        profile_memory_ids=["profile_media_test_seen"],
    )
    assert second_media is not None
    assert second_media["source"] == "profile"


def test_mark_media_shown_advances_to_second_cited_experience(test_db):
    now = utc_now_iso()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO experiences(id, title, raw_context, experience_date, base_weight, activation, created_at) VALUES(?,?,?,?,?,?,?)",
            ("exp_media_next_a", "Experience next A", "details", "2026-05", 1.0, 0.0, now),
        )
        conn.execute(
            "INSERT OR REPLACE INTO experiences(id, title, raw_context, experience_date, base_weight, activation, created_at) VALUES(?,?,?,?,?,?,?)",
            ("exp_media_next_b", "Experience next B", "details", "2026-05", 1.0, 0.0, now),
        )
        conn.execute(
            "INSERT INTO experience_media(experience_id, url, media_type, caption, display_order) VALUES(?,?,?,?,?)",
            ("exp_media_next_a", "https://example.com/next-a.jpg", "image", "first cited", 0),
        )
        conn.execute(
            "INSERT INTO experience_media(experience_id, url, media_type, caption, display_order) VALUES(?,?,?,?,?)",
            ("exp_media_next_b", "https://example.com/next-b.jpg", "image", "second cited", 0),
        )
        conn.commit()

    first_media = pick_unshown_media(
        "media-next-session",
        experience_ids=["exp_media_next_a", "exp_media_next_b"],
        profile_memory_ids=[],
    )
    assert first_media is not None
    assert first_media["caption"] == "first cited"

    mark_media_shown("media-next-session", first_media["id"], source=first_media["source"])

    second_media = pick_unshown_media(
        "media-next-session",
        experience_ids=["exp_media_next_a", "exp_media_next_b"],
        profile_memory_ids=[],
    )
    assert second_media is not None
    assert second_media["caption"] == "second cited"
