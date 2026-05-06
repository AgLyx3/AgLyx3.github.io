# Backend local workflows

## Guided topic auto-discovery (Option A)

This repository includes a file-based local workflow for topic candidate generation and review.

### 1) Generate topic candidates from sample query logs

Run from repo root:

`python3 scripts/topic_candidate_job.py`

Config thresholds are read from `backend/app/config.py` (and can be overridden with env vars):

- `CANDIDATE_MIN_DISTINCT_SESSIONS`
- `CANDIDATE_TIME_WINDOW_DAYS`
- `CANDIDATE_MAX_CONFIDENCE_TO_EXISTING_TOPIC`
- `CANDIDATE_AUTO_APPROVE_TOPICS`
- `TOPIC_LABELER_MODEL`
- `TOPIC_LABELER_API_BASE`
- `TOPIC_LABELER_TIMEOUT_SECONDS`

For LLM topic naming, set:

- `OPENAI_API_KEY`

Input sample logs:

- `backend/data/query_logs.sample.jsonl`

Output candidate artifact:

- `backend/data/topic_candidates.json`

Notes on topic naming:

- Topic names are LLM-generated from clustered sample queries.
- If LLM credentials are missing or labeling fails, candidate status is `pending_llm_label` and it is not auto-approved.

Auto-created topics artifact (when auto-approve enabled):

- `backend/data/topics.approved.json`

Notification stream for auto-created topics:

- `backend/data/topic_notifications.jsonl`

### 2) Review candidates locally with CLI

List pending candidates:

`python3 scripts/topic_review_cli.py list`

Approve candidate into official topic artifact:

`python3 scripts/topic_review_cli.py approve --candidate-id cand-agent-memory-evaluation`

Approve and override topic display name:

`python3 scripts/topic_review_cli.py approve --candidate-id cand-agent-memory-evaluation --topic-name "Agent Memory Evaluation"`

Alias candidate phrase to an existing topic id:

`python3 scripts/topic_review_cli.py alias --candidate-id cand-portfolio-graph-query-routing --topic-id topic-retrieval`

Reject candidate phrase:

`python3 scripts/topic_review_cli.py reject --candidate-id cand-portfolio-graph-query-routing --reason "too narrow"`

Artifacts updated by review:

- Approved topics: `backend/data/topics.approved.json`
- Aliases: `backend/data/topic_aliases.json`
- Candidate statuses: `backend/data/topic_candidates.json`
# Backend API (Lean v1)

Run locally:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Available endpoints:
- `GET /health`
- `POST /chat` (SSE stream: `token` events + `final` metadata event)
- `GET /graph`
- `GET /topics/notifications` (latest auto-topic creation notifications)
- `GET /topics/pending-memory` (auto-created topics with no memory yet)
- `GET /topics/memory-gaps` (queries that did not pass memory relevance gate)
- `POST /topics/{topic_id}/memories` (add manual memory content for a topic)
- `POST /topics/memories/ingest` (ingest memory and auto-assign topics via LLM if topic_ids omitted)

Required env vars for LLM chat:

- `OPENAI_API_KEY` (required)
- `CHAT_MODEL` (default: `gpt-4o-mini`)
- `CHAT_API_BASE` (default: `https://api.openai.com/v1`)
- `RETRIEVAL_TOP_K` (default: `3`)
- `RETRIEVAL_MIN_TOP_SCORE` (default: `0.22`)
- `RETRIEVAL_MIN_SCORE_GAP` (default: `0.04`)

Database:

- `DATABASE_URL` (default: `sqlite:///backend/data/app.db`)

Data safety rule:

- Query traffic (`POST /chat`) updates activation/count signals only.
- Query traffic updates counts only when retrieval confidence passes the gating thresholds.
- Query traffic does not create or edit memory details.
- Query traffic that misses memory relevance is recorded in `memory_query_gaps` for later backfill.
- Memory details are written only through memory ingest/backfill APIs.
