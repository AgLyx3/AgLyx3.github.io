"""Per-query activation updates persisted in SQLite."""

import time

from app.services.db import get_conn


def get_activation_snapshot() -> tuple[dict[str, float], dict[str, float]]:
    with get_conn() as conn:
        topics = conn.execute("SELECT id, activation FROM topics").fetchall()
        experiences = conn.execute("SELECT id, activation FROM experiences").fetchall()
    topic_map = {row["id"]: float(row["activation"]) for row in topics}
    exp_map = {row["id"]: float(row["activation"]) for row in experiences}
    return topic_map, exp_map


def apply_decay(decay_lambda: float = 0.01, dt_days: float = 1.0) -> None:
    factor = 2.718281828 ** (-decay_lambda * dt_days)
    with get_conn() as conn:
        conn.execute("UPDATE topics SET activation = activation * ?", (factor,))
        conn.execute("UPDATE experiences SET activation = activation * ?", (factor,))
        conn.commit()


def update_activation(
    session_id: str,
    query: str,
    cited_experiences: list[tuple[str, float]],
    alpha: float = 1.0,
) -> None:
    if not cited_experiences:
        return
    if not session_id:
        session_id = f"anon-{int(time.time())}"
    _ = query

    with get_conn() as conn:
        for exp_id, score in cited_experiences:
            contribution = alpha * max(float(score), 0.0)
            if contribution <= 0:
                continue
            conn.execute(
                "UPDATE experiences SET activation = activation + ? WHERE id = ?",
                (contribution, exp_id),
            )
            edges = conn.execute(
                "SELECT target_topic_id, relevance FROM relevance_edges WHERE source_experience_id = ?",
                (exp_id,),
            ).fetchall()
            for row in edges:
                conn.execute(
                    "UPDATE topics SET activation = activation + ? WHERE id = ?",
                    (float(row["relevance"]) * contribution, row["target_topic_id"]),
                )
        conn.commit()
