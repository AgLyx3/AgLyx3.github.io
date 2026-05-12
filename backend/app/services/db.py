"""Database schema setup and seed helpers for local and deployed runtimes."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import sqlite3

from app.services.database_engine import (
    database_dialect,
    open_database_connection,
)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()

def get_conn():
    return open_database_connection()


def init_db() -> None:
    dialect = database_dialect()
    now = utc_now_iso()
    with get_conn() as conn:
        conn.executescript(_schema_script_for(dialect))
        _migrate_runtime_schema(conn, dialect, now)
        _seed_defaults(conn, now)
        conn.commit()


def _table_columns(conn, dialect: str, table_name: str) -> list[str]:
    if dialect == "postgres":
        rows = conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ?
            ORDER BY ordinal_position
            """,
            (table_name,),
        ).fetchall()
        return [row["column_name"] for row in rows]
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row["name"] if hasattr(row, "keys") else row[1] for row in rows]


def _profile_memories_ddl(dialect: str) -> str:
    return """
        CREATE TABLE profile_memories (
            memory_id TEXT PRIMARY KEY,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """


def _experiences_ddl(dialect: str) -> str:
    num_type = "DOUBLE PRECISION" if dialect == "postgres" else "REAL"
    return f"""
        CREATE TABLE experiences (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            raw_context TEXT NOT NULL DEFAULT '',
            experience_date TEXT NOT NULL DEFAULT '',
            base_weight {num_type} NOT NULL DEFAULT 0,
            activation {num_type} NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """


def _topics_ddl(dialect: str) -> str:
    num_type = "DOUBLE PRECISION" if dialect == "postgres" else "REAL"
    return f"""
        CREATE TABLE topics (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            base_weight {num_type} NOT NULL DEFAULT 0,
            activation {num_type} NOT NULL DEFAULT 0,
            approval_mode TEXT NOT NULL DEFAULT 'manual',
            source_candidate_id TEXT,
            created_at TEXT NOT NULL
        )
    """


def _drop_table(conn, table_name: str) -> None:
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")


def _rename_table(conn, dialect: str, old_name: str, new_name: str) -> None:
    conn.execute(f"ALTER TABLE {old_name} RENAME TO {new_name}")


def _migrate_sessions(conn, dialect: str) -> None:
    current = _table_columns(conn, dialect, "sessions")
    for col, stmt in [
        ("last_ask_back_round", "ALTER TABLE sessions ADD COLUMN last_ask_back_round INTEGER NOT NULL DEFAULT 0"),
        ("ask_back_pending", "ALTER TABLE sessions ADD COLUMN ask_back_pending INTEGER NOT NULL DEFAULT 0"),
    ]:
        if col not in current:
            conn.execute(stmt)
            conn.commit()


def _update_topic_weights(conn) -> None:
    new_weights = {
        "pm":        12.0,
        "ai-agents": 12.0,
        "eval":      13.0,
        "memory":     8.0,
        "startup":    4.0,
        "research":   5.5,
        "eng":        3.5,
        "access":     3.5,
        "ethics":     3.0,
        "photo":      2.5,
    }
    for topic_id, weight in new_weights.items():
        conn.execute(
            "UPDATE topics SET base_weight = ? WHERE id = ?",
            (weight, topic_id),
        )
    conn.commit()


def _migrate_runtime_schema(conn, dialect: str, now: str) -> None:
    _migrate_profile_memories(conn, dialect, now)
    _migrate_experiences(conn, dialect)
    _migrate_topics(conn, dialect)
    _migrate_sessions(conn, dialect)
    _update_topic_weights(conn)


def _migrate_profile_memories(conn, dialect: str, now: str) -> None:
    desired = ["memory_id", "key", "value", "created_at"]
    current = _table_columns(conn, dialect, "profile_memories")
    if current == desired:
        return

    legacy_name = "profile_memories_legacy"
    _drop_table(conn, legacy_name)
    _rename_table(conn, dialect, "profile_memories", legacy_name)
    conn.execute(_profile_memories_ddl(dialect))

    legacy_rows = conn.execute(f"SELECT * FROM {legacy_name}").fetchall()
    inserts: list[tuple[str, str, str, str]] = []
    for row in legacy_rows:
        if current == desired:
            inserts.append((row["memory_id"], row["key"], row["value"], row["created_at"]))
            continue
        base_id = row["memory_id"] if "memory_id" in row.keys() else "profile-memory"
        if base_id in {"profile_name", "profile_education", "profile_interests"}:
            continue
        raw_structured = row["structured_json"] if "structured_json" in row.keys() else None
        if not raw_structured:
            continue
        try:
            parsed = json.loads(raw_structured)
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(parsed, list):
            continue
        created_at = row["created_at"] if "created_at" in row.keys() else now
        for index, item in enumerate(parsed):
            if not isinstance(item, dict):
                continue
            key = str(item.get("key", "")).strip()
            value = str(item.get("value", "")).strip()
            if not key or not value:
                continue
            memory_id = f"{base_id}-{index + 1}"
            inserts.append((memory_id, key, value, created_at))

    if inserts:
        conn.executemany(
            "INSERT INTO profile_memories(memory_id, key, value, created_at) VALUES(?,?,?,?)",
            inserts,
        )
    _drop_table(conn, legacy_name)


def _migrate_experiences(conn, dialect: str) -> None:
    desired = ["id", "title", "raw_context", "experience_date", "base_weight", "activation", "created_at"]
    current = _table_columns(conn, dialect, "experiences")
    if current == desired:
        return

    legacy_name = "experiences_legacy"
    _drop_table(conn, legacy_name)
    _rename_table(conn, dialect, "experiences", legacy_name)
    conn.execute(_experiences_ddl(dialect))

    legacy_rows = conn.execute(f"SELECT * FROM {legacy_name}").fetchall()
    inserts: list[tuple[str, str, str, str, float, float, str]] = []
    for row in legacy_rows:
        raw_context = ""
        if "raw_context" in row.keys() and row["raw_context"]:
            raw_context = row["raw_context"]
        elif "details" in row.keys() and row["details"]:
            raw_context = row["details"]
        elif "summary" in row.keys() and row["summary"]:
            raw_context = row["summary"]
        old_activation = float(row["activation"] if "activation" in row.keys() else 0.0)
        old_base_weight = float(row["base_weight"] if "base_weight" in row.keys() else old_activation)
        inserts.append(
            (
                row["id"],
                row["title"],
                raw_context,
                row["experience_date"] if "experience_date" in row.keys() else "",
                old_base_weight,
                0.0,
                row["created_at"],
            )
        )

    if inserts:
        conn.executemany(
            """
            INSERT INTO experiences(id, title, raw_context, experience_date, base_weight, activation, created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            inserts,
        )
    _drop_table(conn, legacy_name)


def _migrate_topics(conn, dialect: str) -> None:
    desired = ["id", "label", "description", "base_weight", "activation", "approval_mode", "source_candidate_id", "created_at"]
    current = _table_columns(conn, dialect, "topics")
    if current == desired:
        return

    legacy_name = "topics_legacy"
    _drop_table(conn, legacy_name)
    _rename_table(conn, dialect, "topics", legacy_name)
    conn.execute(_topics_ddl(dialect))

    legacy_rows = conn.execute(f"SELECT * FROM {legacy_name}").fetchall()
    inserts = []
    for row in legacy_rows:
        old_activation = float(row["activation"] if "activation" in row.keys() else 0.0)
        old_base_weight = float(row["base_weight"] if "base_weight" in row.keys() else old_activation)
        inserts.append((
            row["id"],
            row["label"],
            row["description"] if "description" in row.keys() else "",
            old_base_weight,
            0.0,
            row["approval_mode"] if "approval_mode" in row.keys() else "manual",
            row["source_candidate_id"] if "source_candidate_id" in row.keys() else None,
            row["created_at"],
        ))

    if inserts:
        conn.executemany(
            """
            INSERT INTO topics(id, label, description, base_weight, activation, approval_mode, source_candidate_id, created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            inserts,
        )
    _drop_table(conn, legacy_name)


def _schema_script_for(dialect: str) -> str:
    if dialect == "postgres":
        return """
            CREATE TABLE IF NOT EXISTS topics (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                base_weight DOUBLE PRECISION NOT NULL DEFAULT 0,
                activation DOUBLE PRECISION NOT NULL DEFAULT 0,
                approval_mode TEXT NOT NULL DEFAULT 'manual',
                source_candidate_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS profile_memories (
                memory_id TEXT PRIMARY KEY,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS experiences (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                raw_context TEXT NOT NULL DEFAULT '',
                experience_date TEXT NOT NULL DEFAULT '',
                base_weight DOUBLE PRECISION NOT NULL DEFAULT 0,
                activation DOUBLE PRECISION NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS relevance_edges (
                source_experience_id TEXT NOT NULL,
                target_topic_id TEXT NOT NULL,
                relevance DOUBLE PRECISION NOT NULL,
                PRIMARY KEY (source_experience_id, target_topic_id)
            );
            CREATE TABLE IF NOT EXISTS topic_notifications (
                event_id BIGSERIAL PRIMARY KEY,
                event TEXT NOT NULL,
                created_at TEXT NOT NULL,
                topic_id TEXT NOT NULL,
                topic_name TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                distinct_sessions INTEGER NOT NULL,
                mentions INTEGER NOT NULL,
                labeling_mode TEXT
            );
            CREATE TABLE IF NOT EXISTS topic_memories (
                memory_id TEXT PRIMARY KEY,
                topic_id TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                details TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memory_query_gaps (
                gap_id BIGSERIAL PRIMARY KEY,
                query_text TEXT NOT NULL,
                session_id TEXT NOT NULL,
                top_score DOUBLE PRECISION NOT NULL,
                score_gap DOUBLE PRECISION NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS analytics_events (
                event_id BIGSERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                event_name TEXT NOT NULL,
                event_payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                total_token_count INTEGER NOT NULL DEFAULT 0,
                input_token_count INTEGER NOT NULL DEFAULT 0,
                output_token_count INTEGER NOT NULL DEFAULT 0,
                first_message_at TEXT,
                depth_5_reached_at TEXT,
                cta_mentioned BOOLEAN NOT NULL DEFAULT FALSE,
                cta_rejected BOOLEAN NOT NULL DEFAULT FALSE,
                active_topic_id TEXT,
                last_ask_back_round INTEGER NOT NULL DEFAULT 0,
                ask_back_pending BOOLEAN NOT NULL DEFAULT FALSE
            );
            CREATE TABLE IF NOT EXISTS outbound_messages (
                message_id BIGSERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                message_body TEXT NOT NULL,
                included_chat_history BOOLEAN NOT NULL DEFAULT FALSE,
                conversation_json TEXT,
                created_at TEXT NOT NULL,
                delivery_status TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_analytics_events_session
                ON analytics_events(session_id, event_name, created_at);
            CREATE INDEX IF NOT EXISTS idx_sessions_last_seen
                ON sessions(last_seen_at);
            CREATE INDEX IF NOT EXISTS idx_outbound_messages_session
                ON outbound_messages(session_id, created_at);
        """
    return """
            CREATE TABLE IF NOT EXISTS topics (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                base_weight REAL NOT NULL DEFAULT 0,
                activation REAL NOT NULL DEFAULT 0,
                approval_mode TEXT NOT NULL DEFAULT 'manual',
                source_candidate_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS profile_memories (
                memory_id TEXT PRIMARY KEY,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS experiences (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                raw_context TEXT NOT NULL DEFAULT '',
                experience_date TEXT NOT NULL DEFAULT '',
                base_weight REAL NOT NULL DEFAULT 0,
                activation REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS relevance_edges (
                source_experience_id TEXT NOT NULL,
                target_topic_id TEXT NOT NULL,
                relevance REAL NOT NULL,
                PRIMARY KEY (source_experience_id, target_topic_id)
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
            CREATE TABLE IF NOT EXISTS topic_memories (
                memory_id TEXT PRIMARY KEY,
                topic_id TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                details TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memory_query_gaps (
                gap_id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT NOT NULL,
                session_id TEXT NOT NULL,
                top_score REAL NOT NULL,
                score_gap REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS analytics_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                event_name TEXT NOT NULL,
                event_payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                total_token_count INTEGER NOT NULL DEFAULT 0,
                input_token_count INTEGER NOT NULL DEFAULT 0,
                output_token_count INTEGER NOT NULL DEFAULT 0,
                first_message_at TEXT,
                depth_5_reached_at TEXT,
                cta_mentioned INTEGER NOT NULL DEFAULT 0,
                cta_rejected INTEGER NOT NULL DEFAULT 0,
                active_topic_id TEXT,
                last_ask_back_round INTEGER NOT NULL DEFAULT 0,
                ask_back_pending INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS outbound_messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message_body TEXT NOT NULL,
                included_chat_history INTEGER NOT NULL DEFAULT 0,
                conversation_json TEXT,
                created_at TEXT NOT NULL,
                delivery_status TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_analytics_events_session
                ON analytics_events(session_id, event_name, created_at);
            CREATE INDEX IF NOT EXISTS idx_sessions_last_seen
                ON sessions(last_seen_at);
            CREATE INDEX IF NOT EXISTS idx_outbound_messages_session
                ON outbound_messages(session_id, created_at);
        """


def _seed_defaults(conn, now: str) -> None:
    topic_count = conn.execute("SELECT COUNT(*) AS c FROM topics").fetchone()["c"]
    if topic_count == 0:
        conn.executemany(
            "INSERT INTO topics(id,label,description,base_weight,activation,created_at) VALUES(?,?,?,?,?,?)",
            [
                ("ai-agents", "AI Agents", "Agentic systems, conversational AI features, and multi-step LLM workflows.", 12.0, 0.0, now),
                ("memory", "Memory", "Memory architecture, retrieval systems, and personalization in AI.", 8.0, 0.0, now),
                ("eval", "Eval", "Model evaluation, benchmarking, and measurement of AI system quality.", 13.0, 0.0, now),
                ("startup", "Startup", "Founding, fundraising, and building products from zero.", 4.0, 0.0, now),
                ("eng", "Engineering", "Software development, tooling, and technical implementation.", 3.5, 0.0, now),
                ("pm", "Product Management", "Product strategy, PRDs, roadmapping, and cross-functional execution.", 12.0, 0.0, now),
                ("research", "Research", "Academic research, user studies, and published work.", 5.5, 0.0, now),
                ("access", "Accessibility", "Accessible design, WCAG, and inclusive product development.", 3.5, 0.0, now),
                ("photo", "Photography", "Stage and event photography.", 2.5, 0.0, now),
                ("ethics", "Ethics", "AI ethics, governance, and responsible technology.", 3.0, 0.0, now),
            ],
        )

    profile_count = conn.execute("SELECT COUNT(*) AS c FROM profile_memories").fetchone()["c"]
    if profile_count == 0:
        conn.executemany(
            "INSERT INTO profile_memories(memory_id, key, value, created_at) VALUES(?,?,?,?)",
            [
                (
                    "profile_current_role",
                    "Current_role",
                    "Product Manager at Continua AI, working on conversational AI products",
                    now,
                ),
                (
                    "profile_interest",
                    "Interest",
                    "Movies, Bouldering, Musicals, Stage Photography",
                    now,
                ),
                (
                    "profile_education_background",
                    "Education_background",
                    "B.A. with majors in Computer Science and Philosophy",
                    now,
                ),
                (
                    "profile_fun_fact",
                    "Fun_fact",
                    "Peak moment singing: pretended to have 17 different types of voice for a song originally sung by 17 people",
                    now,
                ),
                (
                    "profile_fun_fact_note",
                    "Fun_fact_note",
                    "I know it - i know people will ask about this!",
                    now,
                ),
            ],
        )

    exp_count = conn.execute("SELECT COUNT(*) AS c FROM experiences").fetchone()["c"]
    if exp_count == 0:
        experience_rows = [
            (
                "exp_continua_overview",
                "working as PM at Continua AI, an early-stage conversational AI startup",
                "",
                "",
                "2025-12",
                (
                    "Product builder (AKA a product manager who codes daily) at Continua AI "
                    "(Dec 2025–present), an early-stage startup building a multi-user "
                    "conversational AI product. Yixin works on the conversational AI product directly — "
                    "owning features end-to-end from PRD to launch."
                ),
                None,
                7.0,
                "seed",
                now,
            ),
            (
                "exp_pm_delivery",
                "driving PRD-to-build product delivery across AI agent initiatives",
                "",
                "",
                "2025-12",
                (
                    "Drove PRD-to-build execution across 3 AI agent initiatives (agentic tools, stored memory, "
                    "evaluation systems), translating concepts into detailed PRDs and prioritized tickets, "
                    "coordinating dependencies across 5 engineers. Communicated product direction to leadership "
                    "across all three initiative areas; collaborated cross-functionally with go-to-market teams "
                    "on marketing briefs, influencer recruitment, feature launches, and press interviews. "
                    "Defined and operationalized success metrics (activation rate, error rate, group conversion) "
                    "across 3 initiatives; queried product data using BigQuery and Python to surface insights "
                    "and guide iteration."
                ),
                None,
                6.5,
                "seed",
                now,
            ),
            (
                "exp_memory_architecture",
                "building per-channel and per-user memory for a group AI product",
                "",
                "",
                "2025-12",
                (
                    "Built per-channel memory for a group conversational AI product that tracks shared context, "
                    "infers user identities across a channel, and identifies each user's interests and the "
                    "group's shared goals — making the agent more proactive and contextually relevant. "
                    "Added a per-user memory layer on top of channel memory, giving the agent finer-grained "
                    "per-person memory that persists across conversations — fixing signal mixing inherent in "
                    "channel-level summaries, improving retrieval precision, and enabling cross-channel "
                    "personalization through a privacy gate that controls what carries over. "
                    "Navigated a speed-vs-quality tradeoff in memory architecture: chose to ship a faster "
                    "first version when the ideal fine-grained design would have added 1-2 weeks, while "
                    "setting explicit quality guardrails and a clear iteration path. "
                    "Built evaluation test cases and prompts before memory development finished to define "
                    "success criteria up front; used pre-launch testing to identify gaps between implementation "
                    "and production requirements, preventing an unqualified launch. "
                    "Memory outcome: improved memory eval scores, passed local privacy test cases, and "
                    "validated the path to the more fine-grained data architecture in a follow-on iteration."
                ),
                None,
                7.5,
                "seed",
                now,
            ),
            (
                "exp_agentic_poll",
                "designing and shipping the agentic polling feature",
                "",
                "",
                "2025-12",
                (
                    "Designed and shipped an agentic polling feature enabling users to create, vote on, and "
                    "manage polls through natural language; resolved the core design challenge of distinguishing "
                    "chat, poll creation, editing, and voting without conflicting with a concurrent agentic feature. "
                    "Defined key polling product decisions up front — context-based vs. free input, single vs. "
                    "multiple choice defaults, concurrent poll support, close authority, valid vote definition, "
                    "and reporting format — specified in PRDs with annotated conversational examples. "
                    "Staged the poll rollout from 2-person to 7-person groups while maintaining a prioritized "
                    "test case list; paired launch with live monitoring through the issue viewer. "
                    "Poll outcome: soft-launched to reporters interested in the feature for early feedback."
                ),
                None,
                6.5,
                "seed",
                now,
            ),
            (
                "exp_agentic_split",
                "designing the conversational expense-splitting feature",
                "",
                "",
                "2025-12",
                (
                    "Designed a conversational expense-splitting feature letting users request a multi-person "
                    "split in plain text, with a Google Sheets-backed tracking sheet generated automatically "
                    "— eliminating the need for third-party apps or manual receipt forwarding. "
                    "Made the core split/sheet product decision to optimize for the in-chat workflow over a "
                    "deeper Google Sheets integration; wrote the PRD to be LLM-readable and precise enough "
                    "that the model was not inventing behavior, and walked through every decision point with "
                    "engineers directly."
                ),
                None,
                6.0,
                "seed",
                now,
            ),
            (
                "exp_eval_frameworks",
                "owning evaluation frameworks for production LLM systems at Continua",
                "",
                "",
                "2025-12",
                (
                    "Owned evaluation frameworks for production LLM systems covering memory quality "
                    "(RAG recall/precision, memory usage correctness) and latency (TTFT/E2E latency). "
                    "Replaced a single aggregate latency metric with task-specific latency buckets — "
                    "recall tasks (memory tool calls), generate tasks (documents or images), and pure "
                    "responses with no tools — giving the team clearer signal on where agent performance "
                    "needed improvement. "
                    "Selected and ran external memory benchmarks LoCoMo and EverMemBench; evaluated which "
                    "dimensions were most relevant to a multi-person conversational product, configured "
                    "matched setups, and used results to compare retrieval and memory strategies. "
                    "Designed internal evaluation test cases reflecting real product behavior that external "
                    "benchmarks would miss; validated whether gains on external benchmarks translated into "
                    "better user experience; reduced edge-case failures by ~20% in internal testing. "
                    "Evaluation outcome: results drove a shift from a prompt-driven memory approach to a "
                    "more fine-grained architecture, and surfaced incorrect benchmark numbers circulating "
                    "internally that were corrected before external communication."
                ),
                None,
                7.0,
                "seed",
                now,
            ),
            (
                "exp_issue_viewer",
                "building and improving the internal issue viewer observability tool",
                "",
                "",
                "2025-12",
                (
                    "Built and iterated on an internal observability tool (issue viewer) for PMs tracking "
                    "product quality and engineers debugging failures; identified false positives inflating "
                    "apparent error rates by ~25%, bringing the dashboard significantly closer to reality. "
                    "Redesigned the issue bucketing system from daily LLM-generated buckets (which caused "
                    "semantically similar errors to land in different buckets across days) to an "
                    "inheritance-based update model, making grouping stable and comparable over time. "
                    "Issue viewer outcome: error rate dropped ~25% after false positive removal; engineers "
                    "adopted the tool for daily debugging; issue grouping became consistent enough to track "
                    "trends week over week."
                ),
                None,
                5.5,
                "seed",
                now,
            ),
            (
                "exp_customer_discovery",
                "conducting customer discovery interviews to narrow the ICP",
                "",
                "",
                "2025-12",
                (
                    "Conducted ~10 customer discovery interviews with startup employees, segmented by role "
                    "— operators and coordinators (PMs, tech leads, ops) vs. engineers — to explore pain "
                    "points around AI tool use and identify coordination and execution gaps; used findings "
                    "to narrow the ICP."
                ),
                None,
                5.0,
                "seed",
                now,
            ),
            (
                "exp_gtm",
                "shaping the go-to-market narrative and influencer strategy at Continua",
                "",
                "",
                "2025-12",
                (
                    "Shaped early go-to-market narrative by drafting the initial marketing brief, evaluating "
                    "10+ agencies and influencer partnerships, and aligning PR messaging across 3+ external "
                    "announcements and press interviews."
                ),
                None,
                4.0,
                "seed",
                now,
            ),
            (
                "exp_continua_eng",
                "building customer-facing onboarding and internal tooling at Continua",
                "",
                "",
                "2025-06",
                (
                    "Built customer-facing onboarding flows and internal AI tooling using React, TypeScript, "
                    "and Python; implemented frontend components and event tracking to measure user interaction "
                    "patterns. "
                    "Extended an existing internal analytics tool into a topic clustering system — identified "
                    "the opportunity, aligned with the original engineer on algorithms and approach, and "
                    "implemented using AI-assisted development; reduced the effort to share user conversation "
                    "trends with reporters from a multi-step manual process to a single click, and used it "
                    "internally for product observability."
                ),
                None,
                5.0,
                "seed",
                now,
            ),
            (
                "exp_intern_user_research",
                "running multi-round user research to narrow the ICP at Continua",
                "",
                "",
                "2025-06",
                (
                    "Conducted 2 multi-round user research studies across 4 segments (n~40), identifying "
                    "low-fit segments and narrowing the target ICP, directly influencing roadmap "
                    "prioritization for 1 key initiative. "
                    "Ran 5 user interviews to test whether the product could serve professional scheduling "
                    "workflows; found that field workers handled coordination in the moment through real-time "
                    "communication rather than structured task tracking, while users with formal scheduling "
                    "needs already had dedicated tools and high integration expectations — killed the segment."
                ),
                None,
                5.0,
                "seed",
                now,
            ),
            (
                "exp_intern_onboarding",
                "redesigning onboarding flows for the multi-user AI collaboration product",
                "",
                "",
                "2025-06",
                (
                    "Redesigned onboarding flows for the multi-user AI collaboration product through rapid "
                    "prototyping and iteration with engineering, improving early user engagement by ~20%. "
                    "Built 3 interactive prototypes and authored 5+ frontend and prompt improvements to "
                    "refine onboarding; developed 1 internal tool that reduced manual workflows, improving "
                    "team efficiency by ~10%. "
                    "Owned daily QA testing; triaged 20+ weekly customer feedback items, identified recurring "
                    "usability issues, and partnered with engineering to reduce post-release bugs and improve "
                    "product stability."
                ),
                None,
                4.5,
                "seed",
                now,
            ),
            (
                "exp_asana_migration",
                "migrating the team from Google Docs to Asana for project tracking",
                "",
                "",
                "2025-06",
                (
                    "Identified that the team had tracked all work in Google Docs for two years, limiting "
                    "visibility into status, ownership, and priority; built alignment through 1-on-1s, "
                    "demonstrated value with a working prototype, and introduced Asana via its Google Docs "
                    "plugin to reduce behavior change friction — team migrated fully within a week."
                ),
                None,
                3.5,
                "seed",
                now,
            ),
            (
                "exp_jackson_lab",
                "building an ML pipeline for clinical meeting transcription at Jackson Lab",
                "",
                "",
                "2025-01",
                (
                    "Built an end-to-end ML pipeline for transcription, speaker diarization, and "
                    "post-processing of genomic tumor board meetings, using LLMs to generate structured "
                    "clinical summaries from raw audio. "
                    "Improved transcription accuracy by 15% through model tuning and prompt optimization, "
                    "reducing reliance on third-party correction tools and projecting $24K/year in savings. "
                    "Designed and ran evaluation experiments across F1, fuzzy string-matching, WER, and CER; "
                    "selected domain-specific WER/CER as the primary framework to improve validation of "
                    "specialized medical terminology across 15+ hours of clinical recordings. "
                    "Collaborated with clinicians, program managers, and AI researchers to validate model "
                    "outputs and iterate on system performance in a production-facing clinical workflow."
                ),
                None,
                5.5,
                "seed",
                now,
            ),
            (
                "exp_inclusim",
                "founding InclusiM, an accessibility auditing startup, during college",
                "",
                "",
                "2024-10",
                (
                    "While still in college, Yixin founded InclusiM, an accessibility auditing startup. "
                    "Pitched at 3 pitch competitions and placed 2nd at the Maine Startup Challenge. "
                    "Identified unmet needs in accessibility tooling through competitive analysis and 20+ "
                    "discovery interviews with developers and business owners; validated problem-solution "
                    "fit before building. "
                    "Built and deployed a multi-platform accessibility auditing MVP — web application, "
                    "Figma plugin, and VS Code extension — using the MERN stack, embedding WCAG principles "
                    "from the design phase and validating core workflows in partnership with Colby "
                    "Communications. "
                    "Integrated Docker, CI/CD, and Pytest into the development pipeline; achieved 90% "
                    "test coverage. "
                    "Designed and ran A/B tests with 155 participants, driving a 10% lift in Lighthouse "
                    "scores and higher audit click-through rates; conducted additional interviews with 3+ "
                    "accessibility experts to identify workflow and integration gaps."
                ),
                None,
                6.0,
                "seed",
                now,
            ),
            (
                "exp_research_overview",
                "academic research across HCI, ML, and AI ethics at Colby College",
                "",
                "",
                "2023-10",
                (
                    "Conducted research across multiple labs at Colby College (2023–2025): "
                    "usability studies on eye-tracking fixation correction methods, published in "
                    "Behavior Research Methods; human-ML feature integration studying how human "
                    "knowledge affects trust in AI predictions, published at ACM IUI 2025; "
                    "VR visualizations and accessibility interviews with blind and low-vision "
                    "users at the INSITE Lab; and independent papers on AI ethics covering "
                    "moral dilemma benchmarks and AI-generated art governance."
                ),
                None,
                5.0,
                "seed",
                now,
            ),
            (
                "exp_insite_lab",
                "VR visualization and accessibility research at the Colby INSITE Lab",
                "",
                "",
                "2024-05",
                (
                    "Designed interactive VR visualizations of Gulf of Maine seafloor data to support "
                    "stakeholder engagement in offshore wind farm siting decisions. "
                    "Conducted 20+ interviews with blind and low-vision participants to inform the design "
                    "of an NLP-powered spreadsheet interface for accessible data interaction; analyzed "
                    "transcripts using NLP-assisted methods to identify patterns in how participants "
                    "interact with data tools. "
                    "Poster: 'Virtual Offshore Wind Turbines: Mooring Line Design Evaluation by Gulf of "
                    "Maine Commercial Fishing Stakeholders.' Colby Undergraduate Summer Research Retreat, 2024."
                ),
                None,
                4.0,
                "seed",
                now,
            ),
            (
                "exp_eye_tracking_research",
                "researching eye-tracking correction methods and LLM trust with Dr. Al Madi",
                "",
                "",
                "2023-10",
                (
                    "Conducted 10+ usability studies comparing eye-tracking fixation correction methods, "
                    "analyzing how different correction techniques influence data interpretation in reading "
                    "research; benchmarked four existing correction tools and documented methodological "
                    "trade-offs in a 40-page technical report. "
                    "Designed experimental setups using PyGaze to investigate how users interpret and "
                    "develop trust in outputs generated by large language models. "
                    "Publication: 'Combining Automation and Expertise: A Semi-automated Approach to "
                    "Correcting Eye Tracking Data in Reading Tasks.' Behavior Research Methods, 2025."
                ),
                None,
                4.5,
                "seed",
                now,
            ),
            (
                "exp_human_feature_research",
                "studying how human knowledge influences trust in AI predictions",
                "",
                "",
                "2024-05",
                (
                    "Designed surveys and collected responses from 200+ participants to study how human "
                    "knowledge and contextual information influence trust in AI predictions; analyzed "
                    "results using statistical methods. "
                    "Curated and integrated data from 20+ public datasets; conducted feature selection "
                    "and evaluation experiments on incorporating human knowledge into ML model predictions. "
                    "Publication: 'User Studies in Human-Feature-Integration.' ACM Conference on "
                    "Intelligent User Interfaces (ACM IUI), 2025. "
                    "Presentation: 'Designing Human Experiments for Integrating Human Features into "
                    "Machine Learning.' Colby Undergraduate Summer Research Retreat, Blitz Section, 2024."
                ),
                None,
                4.5,
                "seed",
                now,
            ),
            (
                "exp_ethics_ai_benchmarks",
                "analyzing moral dilemma benchmarks and alignment mechanisms in AI",
                "",
                "",
                "2025-01",
                (
                    "Conducted an interdisciplinary analysis of moral-dilemma benchmarks in AI, mapping "
                    "human moral decision factors (cognitive, emotional, socio-cultural) to technical "
                    "alignment mechanisms (rule-based, RLHF, hybrid); produced a working paper evaluating "
                    "benchmark validity for moral decision-making in LLMs."
                ),
                None,
                3.5,
                "seed",
                now,
            ),
            (
                "exp_ethics_ai_art",
                "analyzing copyright and ethics in AI-generated art",
                "",
                "",
                "2023-01",
                (
                    "Analyzed the legal and ethical landscape of AI-generated art — copyright frameworks, "
                    "training data ownership, deontological and utilitarian ethics — and developed "
                    "governance proposals including updated IP definitions, ethical dataset standards, "
                    "and a consent registry for artists."
                ),
                None,
                3.0,
                "seed",
                now,
            ),
            (
                "exp_photography",
                "stage, event, and documentary photography",
                "",
                "",
                "2022-01",
                (
                    "Yixin shoots stage and event photography — live performances, speakers, and candid "
                    "moments in real time. She's also drawn to documentary-style work: images that tell "
                    "a story or capture something fleeting. "
                    "You can browse her full photography portfolio here: "
                    "https://photography-portfolio-cyan-eight.vercel.app"
                ),
                None,
                3.0,
                "seed",
                now,
            ),
        ]
        conn.executemany(
            """
            INSERT INTO experiences(
                id, title, raw_context, experience_date, base_weight, activation, created_at
            ) VALUES(?,?,?,?,?,?,?)
            """,
            [(row[0], row[1], row[5] or row[3] or row[2], row[4], row[7], 0.0, row[9]) for row in experience_rows],
        )

    edge_count = conn.execute("SELECT COUNT(*) AS c FROM relevance_edges").fetchone()["c"]
    if edge_count == 0:
        conn.executemany(
            "INSERT INTO relevance_edges(source_experience_id,target_topic_id,relevance) VALUES(?,?,?)",
            [
                # exp_continua_overview
                ("exp_continua_overview", "pm", 1.0),
                ("exp_continua_overview", "startup", 0.6),
                ("exp_continua_overview", "ai-agents", 0.6),
                # exp_pm_delivery
                ("exp_pm_delivery", "pm", 1.0),
                ("exp_pm_delivery", "ai-agents", 0.6),
                ("exp_pm_delivery", "eval", 0.3),
                # exp_memory_architecture
                ("exp_memory_architecture", "memory", 1.0),
                ("exp_memory_architecture", "ai-agents", 0.6),
                ("exp_memory_architecture", "eval", 0.6),
                ("exp_memory_architecture", "pm", 0.3),
                # exp_agentic_poll
                ("exp_agentic_poll", "ai-agents", 1.0),
                ("exp_agentic_poll", "pm", 1.0),
                # exp_agentic_split
                ("exp_agentic_split", "ai-agents", 1.0),
                ("exp_agentic_split", "pm", 1.0),
                # exp_eval_frameworks
                ("exp_eval_frameworks", "eval", 1.0),
                ("exp_eval_frameworks", "memory", 0.6),
                ("exp_eval_frameworks", "ai-agents", 0.3),
                # exp_issue_viewer
                ("exp_issue_viewer", "eng", 0.6),
                ("exp_issue_viewer", "eval", 0.6),
                ("exp_issue_viewer", "pm", 0.6),
                # exp_customer_discovery
                ("exp_customer_discovery", "pm", 1.0),
                ("exp_customer_discovery", "research", 0.3),
                # exp_gtm
                ("exp_gtm", "pm", 0.6),
                # exp_continua_eng
                ("exp_continua_eng", "eng", 1.0),
                ("exp_continua_eng", "pm", 0.3),
                # exp_intern_user_research
                ("exp_intern_user_research", "pm", 1.0),
                ("exp_intern_user_research", "research", 0.6),
                # exp_intern_onboarding
                ("exp_intern_onboarding", "pm", 1.0),
                ("exp_intern_onboarding", "eng", 0.3),
                # exp_asana_migration
                ("exp_asana_migration", "pm", 1.0),
                # exp_jackson_lab
                ("exp_jackson_lab", "eng", 1.0),
                ("exp_jackson_lab", "eval", 0.3),
                ("exp_jackson_lab", "research", 0.3),
                # exp_inclusim
                ("exp_inclusim", "startup", 1.0),
                ("exp_inclusim", "access", 1.0),
                ("exp_inclusim", "eng", 0.6),
                ("exp_inclusim", "pm", 0.3),
                ("exp_inclusim", "research", 0.3),
                # exp_research_overview
                ("exp_research_overview", "research", 1.0),
                ("exp_research_overview", "access", 0.3),
                ("exp_research_overview", "ethics", 0.3),
                ("exp_research_overview", "eval", 0.3),
                # exp_insite_lab
                ("exp_insite_lab", "research", 1.0),
                ("exp_insite_lab", "access", 1.0),
                # exp_eye_tracking_research
                ("exp_eye_tracking_research", "research", 1.0),
                # exp_human_feature_research
                ("exp_human_feature_research", "research", 1.0),
                ("exp_human_feature_research", "eval", 0.3),
                # exp_ethics_ai_benchmarks
                ("exp_ethics_ai_benchmarks", "ethics", 1.0),
                ("exp_ethics_ai_benchmarks", "research", 0.6),
                ("exp_ethics_ai_benchmarks", "eval", 0.3),
                # exp_ethics_ai_art
                ("exp_ethics_ai_art", "ethics", 1.0),
                ("exp_ethics_ai_art", "research", 0.6),
                # exp_photography
                ("exp_photography", "photo", 1.0),
            ],
        )
