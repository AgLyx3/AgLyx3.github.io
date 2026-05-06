#!/usr/bin/env python3
"""Generate topic candidates from local query log samples."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib import error, request

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "backend" / "data"
QUERY_LOG_PATH = DATA_DIR / "query_logs.sample.jsonl"
CANDIDATES_PATH = DATA_DIR / "topic_candidates.json"
APPROVED_PATH = DATA_DIR / "topics.approved.json"
NOTIFICATIONS_PATH = DATA_DIR / "topic_notifications.jsonl"
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import get_settings

STOPWORDS = {
    "a",
    "an",
    "about",
    "and",
    "for",
    "how",
    "i",
    "in",
    "is",
    "me",
    "my",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "with",
}


@dataclass(frozen=True)
class QueryEvent:
    """Normalized query log event."""

    timestamp: datetime
    session_id: str
    query: str
    topic_confidence: float


def _parse_timestamp(raw: str) -> datetime:
    value = raw.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(UTC)


def _load_events(path: Path) -> list[QueryEvent]:
    if not path.exists():
        return []

    events: list[QueryEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        events.append(
            QueryEvent(
                timestamp=_parse_timestamp(payload["timestamp"]),
                session_id=str(payload["session_id"]).strip(),
                query=str(payload["query"]).strip(),
                topic_confidence=float(payload.get("topic_confidence", 0.0)),
            )
        )
    return events


def _candidate_id(phrase: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in phrase).strip("-")
    squashed = "-".join(part for part in cleaned.split("-") if part)
    return f"cand-{squashed or 'unknown'}"


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    return "-".join(part for part in cleaned.split("-") if part) or "unknown"


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _append_notification(record: dict[str, Any]) -> None:
    line = json.dumps(record, separators=(",", ":"))
    with NOTIFICATIONS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _db_path() -> Path:
    settings = get_settings()
    raw = settings.database_url.strip()
    if raw.startswith("sqlite:///"):
        return REPO_ROOT / raw.removeprefix("sqlite:///")
    return REPO_ROOT / "backend" / "data" / "app.db"


def _init_db() -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS topics (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                activation REAL NOT NULL DEFAULT 0,
                approval_mode TEXT NOT NULL DEFAULT 'manual',
                source_candidate_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS topic_notifications (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT NOT NULL,
                created_at TEXT NOT NULL,
                topic_id TEXT NOT NULL,
                topic_name TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                distinct_sessions INTEGER NOT NULL,
                mentions INTEGER NOT NULL,
                labeling_mode TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


@contextmanager
def _get_conn():
    path = _db_path()
    conn = sqlite3.connect(path)
    try:
        yield conn
    finally:
        conn.close()


def _tokenize(text: str) -> list[str]:
    tokens = []
    current = []
    for ch in text.lower():
        if ch.isalnum():
            current.append(ch)
            continue
        if current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


def _cluster_key(query: str) -> str:
    tokens = [tok for tok in _tokenize(query) if tok not in STOPWORDS and len(tok) > 2]
    if not tokens:
        return query.lower().strip()
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    top = sorted(counts, key=lambda token: (-counts[token], token))[:3]
    return " ".join(top)


def _llm_topic_label(
    *,
    api_key: str | None,
    api_base: str,
    model: str,
    timeout_seconds: int,
    sample_queries: list[str],
) -> dict[str, str] | None:
    if not api_key:
        return None
    prompt = (
        "You are creating portfolio topic labels from visitor queries.\n"
        "Given sample queries, return strict JSON with keys:\n"
        '- "topic_name": concise 2-5 word canonical topic label\n'
        '- "topic_description": one short sentence (<= 120 chars)\n'
        "Do not include markdown.\n"
        f"Sample queries: {json.dumps(sample_queries)}"
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{api_base.rstrip('/')}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except (TimeoutError, error.URLError, error.HTTPError):
        return None

    try:
        parsed = json.loads(raw)
        content = parsed["choices"][0]["message"]["content"]
        obj = json.loads(content)
        name = str(obj.get("topic_name", "")).strip()
        description = str(obj.get("topic_description", "")).strip()
        if not name:
            return None
        return {"topic_name": name, "topic_description": description}
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None


def main() -> int:
    settings = get_settings()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _init_db()

    now = datetime.now(UTC)
    cutoff = now - timedelta(days=settings.candidate_time_window_days)
    events = _load_events(QUERY_LOG_PATH)
    api_key = os.getenv("OPENAI_API_KEY")

    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "distinct_sessions": set(),
            "mentions": 0,
            "max_confidence": 0.0,
            "sample_queries": [],
        }
    )

    for event in events:
        if event.timestamp < cutoff:
            continue
        if event.topic_confidence > settings.candidate_max_confidence_to_existing_topic:
            continue
        key = _cluster_key(event.query)
        grouped[key]["mentions"] += 1
        grouped[key]["distinct_sessions"].add(event.session_id)
        grouped[key]["max_confidence"] = max(grouped[key]["max_confidence"], event.topic_confidence)
        if len(grouped[key]["sample_queries"]) < 8 and event.query not in grouped[key]["sample_queries"]:
            grouped[key]["sample_queries"].append(event.query)

    candidates = []
    for cluster_key, stats in grouped.items():
        distinct_sessions = len(stats["distinct_sessions"])
        if distinct_sessions < settings.candidate_min_distinct_sessions:
            continue
        sample_queries = stats["sample_queries"] or [cluster_key]
        label = _llm_topic_label(
            api_key=api_key,
            api_base=settings.topic_labeler_api_base,
            model=settings.topic_labeler_model,
            timeout_seconds=settings.topic_labeler_timeout_seconds,
            sample_queries=sample_queries,
        )
        if label is None:
            topic_name = cluster_key
            topic_description = ""
            labeling_mode = "llm_unavailable"
            initial_status = "pending_llm_label"
        else:
            topic_name = label["topic_name"]
            topic_description = label["topic_description"]
            labeling_mode = "llm"
            initial_status = "pending"
        candidates.append(
            {
                "candidate_id": _candidate_id(topic_name),
                "phrase": cluster_key,
                "topic_name": topic_name,
                "topic_description": topic_description,
                "labeling_mode": labeling_mode,
                "sample_queries": sample_queries,
                "status": initial_status,
                "distinct_sessions": distinct_sessions,
                "mentions": stats["mentions"],
                "max_confidence_to_existing_topic": round(stats["max_confidence"], 4),
                "created_at": now.isoformat(),
            }
        )

    candidates.sort(key=lambda item: (-item["distinct_sessions"], -item["mentions"], item["topic_name"]))

    approved_payload = _load_json(APPROVED_PATH, {"topics": []})
    existing_topic_ids = {topic.get("topic_id") for topic in approved_payload.get("topics", [])}
    existing_source_candidates = {
        topic.get("source_candidate_id") for topic in approved_payload.get("topics", [])
    }
    auto_created = 0
    if settings.candidate_auto_approve_topics:
        for candidate in candidates:
            if candidate["labeling_mode"] != "llm":
                continue
            topic_id = f"topic-{_slug(candidate['topic_name'])}"
            if topic_id in existing_topic_ids or candidate["candidate_id"] in existing_source_candidates:
                candidate["status"] = "auto_approved"
                continue

            candidate["status"] = "auto_approved"
            candidate["reviewed_at"] = now.isoformat()
            new_topic = {
                "topic_id": topic_id,
                "name": candidate["topic_name"],
                "description": candidate["topic_description"],
                "source_candidate_id": candidate["candidate_id"],
                "approved_at": now.isoformat(),
                "approval_mode": "auto",
                "labeling_mode": candidate["labeling_mode"],
            }
            approved_payload.setdefault("topics", []).append(new_topic)
            existing_topic_ids.add(topic_id)
            existing_source_candidates.add(candidate["candidate_id"])
            auto_created += 1
            with _get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO topics(id,label,description,activation,approval_mode,source_candidate_id,created_at)
                    VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        topic_id,
                        candidate["topic_name"],
                        candidate["topic_description"],
                        0.0,
                        "auto",
                        candidate["candidate_id"],
                        now.isoformat(),
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO topic_notifications(
                        event, created_at, topic_id, topic_name, candidate_id,
                        distinct_sessions, mentions, labeling_mode
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        "topic_auto_created",
                        now.isoformat(),
                        topic_id,
                        candidate["topic_name"],
                        candidate["candidate_id"],
                        candidate["distinct_sessions"],
                        candidate["mentions"],
                        candidate["labeling_mode"],
                    ),
                )
                conn.commit()
            _append_notification(
                {
                    "event": "topic_auto_created",
                    "created_at": now.isoformat(),
                    "topic_id": topic_id,
                    "topic_name": candidate["topic_name"],
                    "candidate_id": candidate["candidate_id"],
                    "distinct_sessions": candidate["distinct_sessions"],
                    "mentions": candidate["mentions"],
                    "labeling_mode": candidate["labeling_mode"],
                }
            )

    _write_json(APPROVED_PATH, approved_payload)
    artifact = {
        "generated_at": now.isoformat(),
        "config": {
            "candidate_min_distinct_sessions": settings.candidate_min_distinct_sessions,
            "candidate_time_window_days": settings.candidate_time_window_days,
            "candidate_max_confidence_to_existing_topic": settings.candidate_max_confidence_to_existing_topic,
            "candidate_auto_approve_topics": settings.candidate_auto_approve_topics,
            "topic_labeler_model": settings.topic_labeler_model,
        },
        "candidates": candidates,
    }
    _write_json(CANDIDATES_PATH, artifact)

    print(f"Processed events: {len(events)}")
    print(f"Generated candidates: {len(candidates)}")
    print(f"Auto-created topics: {auto_created}")
    print(f"Wrote: {CANDIDATES_PATH}")
    print(f"Wrote: {APPROVED_PATH}")
    if auto_created > 0:
        print(f"Appended notifications: {NOTIFICATIONS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
