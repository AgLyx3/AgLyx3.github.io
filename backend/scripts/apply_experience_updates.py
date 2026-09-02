"""Idempotently sync seed experiences/profile memories/edges into a live database.

`init_db()` only seeds when a table is empty, so editing `_seed_defaults` does not
reach an already-populated deployment. This script diffs the canonical seed against
the target database and upserts the difference. It never truncates, and it leaves
sessions, analytics, and runtime activation values untouched.

Run from backend/:

    set -a && source .env && set +a && .venv/bin/python scripts/apply_experience_updates.py --dry-run
    set -a && source .env && set +a && .venv/bin/python scripts/apply_experience_updates.py
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _canonical_seed(tmp_db: Path) -> dict[str, list[tuple]]:
    """Seed a throwaway SQLite database and read the canonical rows back out.

    Running init_db in a subprocess keeps the cached settings of this process
    pointed at the real target database.
    """
    env = dict(os.environ, DATABASE_URL=f"sqlite:///{tmp_db}", OPENAI_API_KEY="unused")
    subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, '.'); from app.services.db import init_db; init_db()"],
        cwd=_BACKEND_ROOT,
        env=env,
        check=True,
        capture_output=True,
    )
    con = sqlite3.connect(tmp_db)
    con.row_factory = sqlite3.Row
    try:
        return {
            "profile": [
                (r["memory_id"], r["key"], r["value"], r["created_at"])
                for r in con.execute("SELECT * FROM profile_memories ORDER BY created_at, memory_id")
            ],
            "experiences": [
                (
                    r["id"], r["title"], r["raw_context"], r["experience_date"],
                    r["base_weight"], r["created_at"],
                )
                for r in con.execute("SELECT * FROM experiences ORDER BY id")
            ],
            "edges": [
                (r["source_experience_id"], r["target_topic_id"], r["relevance"])
                for r in con.execute("SELECT * FROM relevance_edges ORDER BY source_experience_id, target_topic_id")
            ],
        }
    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="report the diff without writing")
    args = parser.parse_args()

    from app.services.database_engine import database_dialect
    from app.services.db import get_conn

    with tempfile.TemporaryDirectory() as tmp:
        seed = _canonical_seed(Path(tmp) / "seed.db")

    print(f"target dialect: {database_dialect()}")
    with get_conn() as conn:
        live_exp = {
            r["id"]: (r["title"], r["raw_context"])
            for r in conn.execute("SELECT id, title, raw_context FROM experiences").fetchall()
        }
        live_profile = {
            r["memory_id"]: (r["key"], r["value"])
            for r in conn.execute("SELECT memory_id, key, value FROM profile_memories").fetchall()
        }
        live_edges = {
            (r["source_experience_id"], r["target_topic_id"]): r["relevance"]
            for r in conn.execute(
                "SELECT source_experience_id, target_topic_id, relevance FROM relevance_edges"
            ).fetchall()
        }

        new_exp = [r for r in seed["experiences"] if r[0] not in live_exp]
        changed_exp = [
            r for r in seed["experiences"]
            if r[0] in live_exp and (r[1], r[2]) != live_exp[r[0]]
        ]
        new_profile = [r for r in seed["profile"] if r[0] not in live_profile]
        changed_profile = [
            r for r in seed["profile"]
            if r[0] in live_profile and (r[1], r[2]) != live_profile[r[0]]
        ]
        new_edges = [e for e in seed["edges"] if (e[0], e[1]) not in live_edges]
        changed_edges = [
            e for e in seed["edges"]
            if (e[0], e[1]) in live_edges and abs(live_edges[(e[0], e[1])] - e[2]) > 1e-9
        ]

        for label, rows, key in (
            ("new experience", new_exp, 0),
            ("updated experience", changed_exp, 0),
            ("new profile memory", new_profile, 1),
            ("updated profile memory", changed_profile, 1),
        ):
            for row in rows:
                print(f"  {label}: {row[key]}")
        for edge in new_edges:
            print(f"  new edge: {edge[0]} -> {edge[1]} ({edge[2]})")
        for edge in changed_edges:
            print(f"  updated edge: {edge[0]} -> {edge[1]} "
                  f"({live_edges[(edge[0], edge[1])]} -> {edge[2]})")

        total = (
            len(new_exp) + len(changed_exp) + len(new_profile)
            + len(changed_profile) + len(new_edges) + len(changed_edges)
        )
        if total == 0:
            print("nothing to apply; live database already matches the seed")
            return
        if args.dry_run:
            print(f"\ndry run: {total} change(s) not applied")
            return

        for row in new_exp + changed_exp:
            conn.execute(
                """
                INSERT INTO experiences(id, title, raw_context, experience_date, base_weight, activation, created_at)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    raw_context = excluded.raw_context,
                    experience_date = excluded.experience_date,
                    base_weight = excluded.base_weight
                """,
                (row[0], row[1], row[2], row[3], row[4], 0.0, row[5]),
            )
        for row in new_profile + changed_profile:
            conn.execute(
                """
                INSERT INTO profile_memories(memory_id, key, value, created_at)
                VALUES(?,?,?,?)
                ON CONFLICT(memory_id) DO UPDATE SET
                    key = excluded.key,
                    value = excluded.value
                """,
                row,
            )
        for edge in new_edges + changed_edges:
            conn.execute(
                """
                INSERT INTO relevance_edges(source_experience_id, target_topic_id, relevance)
                VALUES(?,?,?)
                ON CONFLICT(source_experience_id, target_topic_id) DO UPDATE SET
                    relevance = excluded.relevance
                """,
                edge,
            )
        conn.commit()
    print(f"\napplied {total} change(s)")


if __name__ == "__main__":
    main()
