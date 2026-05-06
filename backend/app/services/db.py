"""SQLite database setup and helpers for lean v1 backend."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3

from app.config import get_settings


def _db_path() -> Path:
    settings = get_settings()
    raw = settings.database_url.strip()
    if raw.startswith("sqlite:///"):
        relative = raw.removeprefix("sqlite:///")
        return Path(__file__).resolve().parents[3] / relative
    return Path(__file__).resolve().parents[2] / "data" / "app.db"


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
        raw = sample_profile[0]
        return not str(raw).lstrip().startswith("[")
    finally:
        conn.close()


@contextmanager
def get_conn():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    path = _db_path()
    if _should_reset_db(path):
        path.unlink(missing_ok=True)

    now = datetime.now(UTC).isoformat()
    with get_conn() as conn:
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
                summary TEXT NOT NULL,
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
            """
        )
        _seed_defaults(conn, now)
        conn.commit()


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


def _seed_defaults(conn: sqlite3.Connection, now: str) -> None:
    topic_count = conn.execute("SELECT COUNT(*) AS c FROM topics").fetchone()["c"]
    if topic_count == 0:
        conn.executemany(
            "INSERT INTO topics(id,label,description,activation,created_at) VALUES(?,?,?,?,?)",
            [
                (
                    "topic_accessibility",
                    "Accessibility",
                    "Accessible product design and inclusive AI experiences.",
                    4.4,
                    now,
                ),
                (
                    "topic_eval",
                    "Eval",
                    "Benchmark design, model evaluation, and apples-to-apples comparisons.",
                    5.8,
                    now,
                ),
                (
                    "topic_memory_architecture",
                    "Memory Architecture",
                    "Retrieval design, memory organization, and grounded assistant behavior.",
                    4.9,
                    now,
                ),
                (
                    "topic_software_development",
                    "Software Development",
                    "Implementation work, tooling, and product engineering.",
                    5.1,
                    now,
                ),
                (
                    "topic_startup_founding",
                    "Startup/Founding",
                    "Startup building, pitching, and product direction setting.",
                    3.2,
                    now,
                ),
                (
                    "topic_user_studies",
                    "User Studies",
                    "User interviews, qualitative research, and product insight gathering.",
                    3.6,
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
                    _profile_structured_json(
                        ("Name", "Yixin Li"),
                    ),
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
                    "exp_inclusim_foundation",
                    "Built InclusiM as an AI-for-accessibility startup in college",
                    "Developed the initial product direction around accessible AI experiences and real user needs.",
                    "Worked on InclusiM in college as an AI-for-accessibility startup and shaped the early product around inclusive user experiences.",
                    "2021-09",
                    "Worked on InclusiM in college as an AI-for-accessibility startup, focusing on how AI could better serve accessibility needs and how the product direction should reflect real user pain points.",
                    _structured_json(
                        context="Built an accessibility-focused startup during college.",
                        action="Defined the product direction for InclusiM around inclusive AI experiences and user needs.",
                        result="Established the foundation for the startup's accessibility and product story.",
                    ),
                    4.2,
                    "seed",
                    now,
                ),
                (
                    "exp_accessibility_prototypes",
                    "Built accessible product prototypes and interaction flows",
                    "Implemented product ideas and iterated on accessible interaction patterns based on feedback.",
                    "Built product prototypes and refined accessible interaction flows based on what users and stakeholders found most usable.",
                    "2022-02",
                    "Built and iterated on accessible product prototypes, testing interaction patterns and refining the flows so the product better matched accessibility needs in practice.",
                    _structured_json(
                        context="Needed to turn accessibility ideas into workable product interactions.",
                        action="Built prototypes and iterated on accessible interaction flows using feedback.",
                        result="Produced more usable product patterns grounded in accessibility constraints.",
                    ),
                    3.9,
                    "seed",
                    now,
                ),
                (
                    "exp_eval_tooling",
                    "Built internal tooling to normalize benchmark runs",
                    "Wrote scripts and wrappers to standardize evaluation inputs, outputs, and comparison reports.",
                    "Built internal evaluation tooling to keep benchmark runs consistent and comparable across experiments.",
                    "2024-06",
                    "Built internal scripts and wrappers to normalize benchmark runs, standardizing prompts, result collection, and comparison reports so evals could be compared more cleanly.",
                    _structured_json(
                        context="Benchmark runs needed consistent setup across experiments.",
                        action="Built internal tooling to normalize evaluation inputs, outputs, and reporting.",
                        result="Made benchmark comparisons more repeatable and easier to trust.",
                    ),
                    4.7,
                    "seed",
                    now,
                ),
                (
                    "exp_memory_design",
                    "Designed retrieval and memory organization patterns",
                    "Worked on how an assistant should store, retrieve, and ground information across conversations.",
                    "Designed memory architecture patterns for retrieval, organization, and grounded assistant responses.",
                    "2024-09",
                    "Worked on retrieval and memory organization patterns for an assistant, thinking through how information should be stored, retrieved, and grounded across conversations.",
                    _structured_json(
                        context="Assistant behavior depended on better storage and retrieval patterns.",
                        action="Designed memory organization and retrieval patterns for grounded multi-turn behavior.",
                        result="Created a clearer memory architecture for how the assistant should recall and use information.",
                    ),
                    5.5,
                    "seed",
                    now,
                ),
                (
                    "exp_accessibility_interviews",
                    "Interviewed users about accessibility pain points",
                    "Collected qualitative feedback that directly influenced product direction and feature priorities.",
                    "Ran user interviews focused on accessibility pain points and used the findings to guide product choices.",
                    "2022-01",
                    "Interviewed users about accessibility pain points, documented the qualitative feedback, and used that feedback to steer product direction and feature prioritization.",
                    _structured_json(
                        context="Needed grounded user insight on accessibility pain points.",
                        action="Conducted user interviews and synthesized the qualitative feedback.",
                        result="The findings directly influenced product direction and feature priorities.",
                    ),
                    2.8,
                    "seed",
                    now,
                ),
                (
                    "exp_locomo_benchmarking",
                    "Ran LoCoMo and EverMemBenchmark across matched configurations",
                    "Executed long-memory benchmarks with carefully aligned prompts, context windows, and scoring settings.",
                    "Ran LoCoMo and EverMemBenchmark with matched configurations to make the comparison as apples-to-apples as possible.",
                    "2024-07",
                    "Ran LoCoMo and EverMemBenchmark for the company, spending significant time aligning prompts, context windows, and scoring configuration so the final comparison would be as apples-to-apples as possible.",
                    _structured_json(
                        context="Needed a fair long-memory benchmark comparison across systems.",
                        action="Aligned LoCoMo and EverMemBenchmark configurations across prompts, context windows, and scoring.",
                        result="Produced a more credible apples-to-apples benchmark comparison.",
                    ),
                    6.4,
                    "seed",
                    now,
                ),
                (
                    "exp_startup_competition",
                    "Won Maine Startup Challenge and pitched at Greenlight Maine",
                    "Validated the startup direction through competition wins and public pitching.",
                    "Won Maine Startup Challenge and attended Greenlight Maine as part of building startup momentum.",
                    "2022-04",
                    "Won Maine Startup Challenge and pitched at Greenlight Maine, using those moments to validate the startup story and gain external feedback on the direction.",
                    _structured_json(
                        context="Needed outside validation for the startup direction.",
                        action="Pitched the startup publicly and competed in startup events.",
                        result="The direction gained validation through competition success and public exposure.",
                    ),
                    2.3,
                    "seed",
                    now,
                ),
                (
                    "exp_eval_blogs",
                    "Wrote technical blog posts explaining benchmark tradeoffs",
                    "Published writing that documented setup decisions, caveats, and what the benchmark results actually meant.",
                    "Wrote blog posts that explained how benchmark choices affected interpretation of the results.",
                    "2024-08",
                    "Wrote technical blog posts around the benchmarking work, documenting setup tradeoffs, caveats, and what readers should actually take away from the results.",
                    _structured_json(
                        context="Benchmark work needed to be communicated clearly to others.",
                        action="Wrote technical blog posts explaining setup decisions and benchmark tradeoffs.",
                        result="Captured the evaluation rationale in a form that others could understand and reuse.",
                    ),
                    3.1,
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
                ("exp_accessibility_interviews", "topic_accessibility", 0.72),
                ("exp_accessibility_interviews", "topic_startup_founding", 0.31),
                ("exp_accessibility_interviews", "topic_user_studies", 0.95),
                ("exp_accessibility_prototypes", "topic_accessibility", 0.83),
                ("exp_accessibility_prototypes", "topic_software_development", 0.91),
                ("exp_accessibility_prototypes", "topic_user_studies", 0.46),
                ("exp_eval_blogs", "topic_eval", 0.88),
                ("exp_eval_blogs", "topic_software_development", 0.35),
                ("exp_eval_tooling", "topic_eval", 0.76),
                ("exp_eval_tooling", "topic_memory_architecture", 0.49),
                ("exp_eval_tooling", "topic_software_development", 0.95),
                ("exp_inclusim_foundation", "topic_accessibility", 0.93),
                ("exp_inclusim_foundation", "topic_software_development", 0.38),
                ("exp_inclusim_foundation", "topic_startup_founding", 0.84),
                ("exp_locomo_benchmarking", "topic_eval", 0.97),
                ("exp_locomo_benchmarking", "topic_memory_architecture", 0.54),
                ("exp_locomo_benchmarking", "topic_software_development", 0.68),
                ("exp_memory_design", "topic_eval", 0.42),
                ("exp_memory_design", "topic_memory_architecture", 0.96),
                ("exp_memory_design", "topic_software_development", 0.63),
                ("exp_startup_competition", "topic_accessibility", 0.41),
                ("exp_startup_competition", "topic_startup_founding", 0.94),
            ],
        )
