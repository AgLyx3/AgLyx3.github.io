"""Truncate all app tables on Postgres and re-run init_db (fresh seed data).

Run from repo root or backend/:

    cd backend && set -a && source .env && set +a && .venv/bin/python scripts/reset_postgres_seed.py

DATABASE_URL must be postgresql://... (e.g. Railway public TCP proxy, not *.railway.internal).
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.services.database_engine import database_dialect  # noqa: E402
from app.services.db import get_conn, init_db  # noqa: E402

_TABLES = (
    "relevance_edges",
    "topic_memories",
    "topic_notifications",
    "memory_query_gaps",
    "outbound_messages",
    "analytics_events",
    "sessions",
    "experiences",
    "profile_memories",
    "topics",
)


def main() -> None:
    if database_dialect() != "postgres":
        print("This script only runs when DATABASE_URL starts with postgresql://", file=sys.stderr)
        sys.exit(1)

    truncate_sql = "TRUNCATE TABLE " + ", ".join(_TABLES) + " RESTART IDENTITY CASCADE"
    with get_conn() as conn:
        conn.execute(truncate_sql)
        conn.commit()

    init_db()
    print("done: truncated app tables and re-applied schema + seed defaults")


if __name__ == "__main__":
    main()
