"""Database schema setup and seed helpers for local and deployed runtimes."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3

from app.services.database_engine import (
    database_dialect,
    open_database_connection,
    sqlite_db_path,
)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()

def _should_reset_db(path: Path) -> bool:
    if not path.exists():
        return False

    conn = sqlite3.connect(path)
    try:
        table_rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        tables = {row[0] for row in table_rows}
        if "profile_memories" not in tables:
            return True

        required_tables = {"analytics_events", "sessions", "outbound_messages"}
        if not required_tables.issubset(tables):
            return False

        session_columns = {row[1] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()}
        required_session_columns = {"total_token_count", "input_token_count", "output_token_count"}
        if not required_session_columns.issubset(session_columns):
            return True

        experience_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(experiences)").fetchall()
        }
        required_columns = {"raw_context", "structured_json", "experience_date"}
        if not required_columns.issubset(experience_columns):
            return True

        sample_profile = conn.execute(
            "SELECT structured_json FROM profile_memories ORDER BY created_at, memory_id LIMIT 1"
        ).fetchone()
        if sample_profile is None:
            return False
        try:
            parsed = json.loads(sample_profile[0])
            return not isinstance(parsed, list)
        except (json.JSONDecodeError, ValueError):
            return True
    finally:
        conn.close()


def get_conn():
    return open_database_connection()


def init_db() -> None:
    dialect = database_dialect()
    if dialect == "sqlite":
        path = sqlite_db_path()
        if _should_reset_db(path):
            path.unlink(missing_ok=True)

    now = utc_now_iso()
    with get_conn() as conn:
        conn.executescript(_schema_script_for(dialect))
        _seed_defaults(conn, now)
        conn.commit()


def _schema_script_for(dialect: str) -> str:
    if dialect == "postgres":
        return """
            CREATE TABLE IF NOT EXISTS topics (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                activation DOUBLE PRECISION NOT NULL DEFAULT 0,
                approval_mode TEXT NOT NULL DEFAULT 'manual',
                source_candidate_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS profile_memories (
                memory_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                raw_context TEXT NOT NULL,
                structured_json TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'seed',
                confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS experiences (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                details TEXT NOT NULL DEFAULT '',
                experience_date TEXT NOT NULL DEFAULT '',
                raw_context TEXT NOT NULL DEFAULT '',
                structured_json TEXT NOT NULL,
                activation DOUBLE PRECISION NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT 'seed',
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
                active_topic_id TEXT
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
                activation REAL NOT NULL DEFAULT 0,
                approval_mode TEXT NOT NULL DEFAULT 'manual',
                source_candidate_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS profile_memories (
                memory_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                raw_context TEXT NOT NULL,
                structured_json TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'seed',
                confidence REAL NOT NULL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS experiences (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                details TEXT NOT NULL DEFAULT '',
                experience_date TEXT NOT NULL DEFAULT '',
                raw_context TEXT NOT NULL DEFAULT '',
                structured_json TEXT NOT NULL,
                activation REAL NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT 'seed',
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
                active_topic_id TEXT
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


def _structured_json(*, context: str, action: str, result: str) -> str:
    return json.dumps(
        {
            "context": context.strip(),
            "action": action.strip(),
            "result": result.strip(),
        }
    )


def _profile_structured_json(*fields: tuple[str, str]) -> str:
    return json.dumps(
        [
            {"key": key.strip(), "value": value.strip()}
            for key, value in fields
            if key.strip() and value.strip()
        ]
    )


def _seed_defaults(conn, now: str) -> None:
    topic_count = conn.execute("SELECT COUNT(*) AS c FROM topics").fetchone()["c"]
    if topic_count == 0:
        conn.executemany(
            "INSERT INTO topics(id,label,description,activation,created_at) VALUES(?,?,?,?,?)",
            [
                (
                    "ai-agents",
                    "AI Agents",
                    "Agentic systems, conversational AI features, and multi-step LLM workflows.",
                    7.0,
                    now,
                ),
                (
                    "memory",
                    "Memory",
                    "Memory architecture, retrieval systems, and personalization in AI.",
                    7.5,
                    now,
                ),
                (
                    "eval",
                    "Eval",
                    "Model evaluation, benchmarking, and measurement of AI system quality.",
                    6.5,
                    now,
                ),
                (
                    "startup",
                    "Startup",
                    "Founding, fundraising, and building products from zero.",
                    5.0,
                    now,
                ),
                (
                    "eng",
                    "Engineering",
                    "Software development, tooling, and technical implementation.",
                    5.5,
                    now,
                ),
                (
                    "pm",
                    "Product Management",
                    "Product strategy, PRDs, roadmapping, and cross-functional execution.",
                    7.0,
                    now,
                ),
                (
                    "research",
                    "Research",
                    "Academic research, user studies, and published work.",
                    5.0,
                    now,
                ),
                (
                    "access",
                    "Accessibility",
                    "Accessible design, WCAG, and inclusive product development.",
                    5.0,
                    now,
                ),
                (
                    "photo",
                    "Photography",
                    "Stage and event photography.",
                    3.0,
                    now,
                ),
                (
                    "ethics",
                    "Ethics",
                    "AI ethics, governance, and responsible technology.",
                    4.0,
                    now,
                ),
            ],
        )

    profile_count = conn.execute("SELECT COUNT(*) AS c FROM profile_memories").fetchone()["c"]
    if profile_count == 0:
        conn.executemany(
            """
            INSERT INTO profile_memories(
                memory_id, title, raw_context, structured_json, source, confidence, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            [
                (
                    "profile_name",
                    "Name",
                    "My name is Yixin Li.",
                    _profile_structured_json(("Name", "Yixin Li")),
                    "seed",
                    1.0,
                    now,
                    now,
                ),
                (
                    "profile_education",
                    "Education",
                    "I got my bachelor degree with a double major in Philosophy and Computer Science from Colby College.",
                    _profile_structured_json(
                        ("Bachelor_school", "Colby College"),
                        ("Bachelor_major", "Philosophy"),
                        ("Bachelor_major", "Computer Science"),
                    ),
                    "seed",
                    1.0,
                    now,
                    now,
                ),
                (
                    "profile_interests",
                    "Interests",
                    "I like films, musicals, stage photography, and bouldering.",
                    _profile_structured_json(
                        ("Interest", "Films"),
                        ("Interest", "Musicals"),
                        ("Interest", "Stage photography"),
                        ("Interest", "Bouldering"),
                    ),
                    "seed",
                    1.0,
                    now,
                    now,
                ),
            ],
        )

    exp_count = conn.execute("SELECT COUNT(*) AS c FROM experiences").fetchone()["c"]
    if exp_count == 0:
        conn.executemany(
            """
            INSERT INTO experiences(
                id, title, summary, details, experience_date, raw_context, structured_json, activation, source, created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            [
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
                    _structured_json(
                        context="PM at Continua AI leading 3 AI agent initiatives from concept to shipped product.",
                        action="Drove PRD-to-build execution, coordinated across 5 engineers, defined success metrics, and communicated product direction to leadership and go-to-market teams.",
                        result="Shipped multiple AI agent initiatives with defined metrics, aligned stakeholders, and clear operational handoffs.",
                    ),
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
                    _structured_json(
                        context="Group conversational AI product needed memory that tracked shared context and individual user patterns across channels.",
                        action="Built per-channel memory first, then added a per-user layer on top with a privacy gate; shipped a faster first version under a speed-vs-quality tradeoff, with eval test cases defined before development finished.",
                        result="Improved memory eval scores, passed privacy test cases, and validated the path to a more fine-grained architecture.",
                    ),
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
                    _structured_json(
                        context="Conversational AI product needed a polling feature where natural language input could mean chatting, creating, editing, or voting.",
                        action="Designed the interaction model and key product decisions upfront in PRDs with conversational examples; staged rollout from 2 to 7 people with live monitoring.",
                        result="Soft-launched to reporters for early feedback with no ambiguity failures in the core interaction model.",
                    ),
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
                    _structured_json(
                        context="Users needed to split expenses in a conversational AI without switching to third-party apps.",
                        action="Designed the split/sheet feature optimizing for in-chat workflow over deep Google Sheets integration; wrote a precise LLM-readable PRD and walked engineers through every decision point.",
                        result="Shipped a conversational expense-splitting workflow with automatic Google Sheets generation.",
                    ),
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
                    _structured_json(
                        context="Production LLM systems at Continua needed rigorous evaluation of memory quality and latency.",
                        action="Designed eval frameworks, replaced aggregate latency with task-specific buckets, ran LoCoMo and EverMemBench, and built internal test cases for production behavior external benchmarks missed.",
                        result="Reduced edge-case failures by ~20%, drove a shift to fine-grained memory architecture, and corrected internal benchmark errors before external communication.",
                    ),
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
                    _structured_json(
                        context="PMs and engineers needed an observability tool to track product quality and debug failures.",
                        action="Built and iterated on an issue viewer, identified false positives inflating error rates by ~25%, and redesigned bucketing from LLM-generated daily buckets to an inheritance-based model.",
                        result="Error rate dropped ~25% after false positive removal; engineers adopted it for daily debugging and issue grouping became stable week-over-week.",
                    ),
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
                    _structured_json(
                        context="Needed to understand how startup employees experience AI tool pain points across different roles.",
                        action="Conducted ~10 customer discovery interviews segmented by operators/coordinators vs. engineers to map coordination and execution gaps.",
                        result="Used findings to narrow the ICP and inform feature prioritization.",
                    ),
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
                    _structured_json(
                        context="Continua AI needed early go-to-market narrative and external communications aligned across launches.",
                        action="Drafted the initial marketing brief, evaluated 10+ agencies and influencer partnerships, and aligned PR messaging for 3+ announcements and press interviews.",
                        result="Established the early GTM narrative and external communication foundation for feature launches.",
                    ),
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
                    _structured_json(
                        context="Continua AI needed frontend onboarding flows and internal analytics tooling.",
                        action="Built customer-facing onboarding in React/TypeScript/Python with event tracking, and extended an internal analytics tool into a topic clustering system.",
                        result="Reduced manual reporting effort to a single click and created measurable user interaction tracking.",
                    ),
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
                    _structured_json(
                        context="Needed to test whether a professional scheduling workflow was a viable product-market fit for Continua.",
                        action="Ran 2 multi-round studies across 4 segments (n~40) including dedicated interviews testing the scheduling hypothesis.",
                        result="Killed the scheduling segment after finding it was a poor fit; narrowed ICP and influenced roadmap prioritization.",
                    ),
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
                    _structured_json(
                        context="Multi-user AI collaboration product had low early user engagement and unclear onboarding.",
                        action="Redesigned onboarding flows through rapid prototyping, built 3 interactive prototypes, improved prompts, and ran QA with weekly feedback triage.",
                        result="Improved early user engagement by ~20% and reduced post-release bugs through structured QA.",
                    ),
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
                    _structured_json(
                        context="Team had tracked all work in Google Docs for 2 years, limiting visibility into status, ownership, and priority.",
                        action="Built alignment through 1-on-1s, demonstrated value with a prototype, and introduced Asana via its Google Docs plugin to reduce behavior change friction.",
                        result="Team migrated fully within a week.",
                    ),
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
                    _structured_json(
                        context="Jackson Laboratory needed automated transcription and clinical summaries from genomic tumor board meeting audio.",
                        action="Built an end-to-end ML pipeline for transcription, speaker diarization, and post-processing; tuned models and optimized prompts; designed and ran WER/CER evaluation.",
                        result="Improved transcription accuracy by 15%, projected $24K/year in savings, and validated a domain-specific evaluation framework across 15+ hours of clinical recordings.",
                    ),
                    5.5,
                    "seed",
                    now,
                ),
                (
                    "exp_inclusim",
                    "founding InclusiM, an accessibility auditing startup",
                    "",
                    "",
                    "2024-10",
                    (
                        "Secured $5,000 in funding and placed 2nd at the Maine Startup Challenge; pitched on "
                        "the Greenlight Maine TV show. "
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
                    _structured_json(
                        context="Developers and businesses had no integrated accessibility auditing workflow for modern product stacks.",
                        action="Validated problem-solution fit through 20+ discovery interviews, built a multi-platform MVP (web app, Figma plugin, VS Code extension) using the MERN stack, and ran A/B tests with 155 participants.",
                        result="Secured $5K funding, placed 2nd at Maine Startup Challenge, achieved 90% test coverage, and drove a 10% lift in Lighthouse scores.",
                    ),
                    6.0,
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
                    _structured_json(
                        context="Stakeholders making offshore wind farm siting decisions needed better data visualization; blind and low-vision users needed accessible data interaction tools.",
                        action="Designed VR visualizations of seafloor data and conducted 20+ interviews with blind and low-vision participants to inform NLP-powered spreadsheet interface design.",
                        result="Published a poster on VR-based stakeholder engagement and produced design insights for accessible data interfaces.",
                    ),
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
                    _structured_json(
                        context="Eye-tracking research lacked consensus on which fixation correction methods were most reliable; separate thread investigated LLM trust.",
                        action="Conducted 10+ usability studies comparing correction methods, benchmarked four tools, and designed PyGaze experiments on LLM trust.",
                        result="Published in Behavior Research Methods; produced a 40-page technical report documenting correction method trade-offs.",
                    ),
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
                    _structured_json(
                        context="Open question in ML: does incorporating human knowledge into model predictions improve trust and performance?",
                        action="Designed surveys (n=200+), integrated data from 20+ public datasets, and ran feature selection experiments with Dr. Isaac Lage.",
                        result="Published at ACM IUI 2025; presented at Colby Summer Research Retreat.",
                    ),
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
                    _structured_json(
                        context="AI alignment research lacks rigorous evaluation of whether moral-dilemma benchmarks capture real human ethical reasoning.",
                        action="Conducted interdisciplinary analysis mapping human moral decision factors to technical alignment mechanisms across rule-based, RLHF, and hybrid approaches.",
                        result="Produced a working paper evaluating benchmark validity for LLM moral decision-making.",
                    ),
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
                    _structured_json(
                        context="AI-generated art raised unresolved questions about copyright, training data ownership, and creative consent.",
                        action="Analyzed copyright frameworks, ownership structures, and deontological/utilitarian ethics; developed governance proposals.",
                        result="Produced proposals including updated IP definitions, ethical dataset standards, and a consent registry for artists.",
                    ),
                    3.0,
                    "seed",
                    now,
                ),
            ],
        )

    edge_count = conn.execute("SELECT COUNT(*) AS c FROM relevance_edges").fetchone()["c"]
    if edge_count == 0:
        conn.executemany(
            "INSERT INTO relevance_edges(source_experience_id,target_topic_id,relevance) VALUES(?,?,?)",
            [
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
            ],
        )
