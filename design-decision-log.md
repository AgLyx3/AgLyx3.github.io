# Design Decisions Log

This document records the major product and architecture decisions made while building the interactive portfolio system.

It is meant to answer:

- what we started with
- what we changed
- why we changed it
- what the current intended direction is

It is not a full spec. `PRD.md` and `architecture.md` hold the fuller product and system design.

---

## 1. Original Direction

The project started as a graph-first interactive portfolio with:

- topic nodes
- experience nodes
- a chat interface
- activation-based graph updates after chat usage

The early backend model centered on:

- `topics`
- `experiences`
- `relevance_edges`

The early frontend also had multiple deep-dive pages and a dedicated profile-memory view.

### Why this was useful

This made the portfolio immediately interactive and gave a concrete demo of memory activation:

- user query
- retrieval
- activation change
- graph node size change

### What became problematic

Over time, several issues became clear:

1. the graph could become visually busy
2. topic-level follow-up questions were too generic
3. the memory model mixed different kinds of information
4. profile/background facts and work experiences were being treated too similarly
5. the retrieval fallback was too binary and sometimes robotic

---

## 2. Shift Away From a Heavy Profile UI

We originally added a dedicated profile-memory concept and an `About Me` style surface.

Later, the product direction changed:

- profile memory was still valuable
- but it did not need its own frontend page
- it mainly needed to help the assistant answer questions

### Decision

Keep profile memory as a backend memory layer, not a required frontend surface.

### Why

The current product does not need a separate UI for profile memory. The important function is:

- answering stable factual questions
- giving the assistant identity/background context

That is more important than visually browsing those rows.

---

## 3. Distinguishing Profile Memory From Experience Memory

We decided that `profile memory` and `experience memory` should not be treated as the same kind of record.

### Decision

Use two separate memory stores:

- `profile_memories`
- `experiences`

### Why

They serve different purposes.

#### Profile memory

Profile memory is for:

- stable identity/context facts
- current role
- education background
- interests
- fun facts

These are durable and not graph-driven.

#### Experience memory

Experience memory is for:

- concrete projects
- specific work examples
- research
- benchmarks
- product decisions

These are evidence-like memories that can connect to topics and drive exploration.

---

## 4. Simplifying Experience Schema

The earlier `experiences` schema carried legacy fields from earlier UI iterations:

- `summary`
- `details`
- `structured_json`
- `source`

This became more than the current product needed.

### Decision

Simplify `experiences` to:

- `id`
- `title`
- `raw_context`
- `experience_date`
- `activation`
- `created_at`

### Why

The current experience model only really needs:

- a concise title
- a raw memory body for retrieval
- an authored date for timeline/storytelling
- activation for graph behavior

This keeps experience memory closer to a true memory record instead of a UI-shaped content record.

### Tagging / topic relationship

We decided not to embed topics directly in the experience row.

Instead:

- `topics` remain separate
- `relevance_edges` remain the relationship table

This keeps the graph architecture intact while simplifying the memory payload itself.

---

## 5. Simplifying Profile Memory Schema

The earlier profile-memory schema used:

- `title`
- `raw_context`
- `structured_json`
- `source`
- `confidence`
- `created_at`
- `updated_at`

That turned out to be heavier than necessary for the current purpose.

### Decision

Simplify `profile_memories` to:

- `memory_id`
- `key`
- `value`
- `created_at`

### Why

Profile memory now exists mainly to answer stable factual questions. For that use case:

- `key`
- `value`

is enough.

Examples:

- `Current_role` -> `Product Manager at Continua AI`
- `Interest` -> `Movies, Bouldering, Musicals, Stage Photography`
- `Education_background` -> `B.A. with majors in Computer Science and Philosophy`
- `Fun_fact` -> `Peak moment singing: pretended to have 17 different types of voice for a song originally sung by 17 people`
- `Fun_fact_note` -> `I know it - i know people will ask about this!`

This also removes an unnecessary raw-to-structured duplication for profile memory.

---

## 6. Follow-Up Question Generation Changed From Topic-Led to Citation-Led

The original follow-up generation leaned too heavily on the selected topic label.

That caused repetitive prompts like:

- “What experience does Yixin have with accessibility?”
- “How did Yixin apply accessibility in practice?”

even after the assistant had already answered an accessibility question.

### Decision

Generate follow-up questions primarily from the retrieved experience titles used in the answer.

### Why

The better continuation point is not the topic itself, but the specific experiences that supported the answer.

Example:

If the answer used:

- `Interviewed users about accessibility pain points`
- `Built accessible product prototypes`
- `Built InclusiM as an accessibility startup`

then the next questions should drill into those experiences rather than repeating the topic name.

### Additional constraint

Do this cheaply:

- no extra model call
- no over-engineered semantic rewrite
- use the experience title as context
- smooth the grammar slightly so the question reads naturally

---

## 7. Retrieval Fallback Should Not Be Robotic

The original chat flow used:

- experience retrieval
- a hard gating rule
- exact fallback sentence when retrieval was weak

This caused awkward behavior for greetings and light chat.

### Problem

If a user says:

- `hi`
- `hello`
- `how are you`

the current hard fallback feels robotic because the system treats everything as a memory query.

### Decision

Introduce a routing layer before retrieval.

Target lanes:

- `small_talk`
- `profile`
- `experience`
- `blended`

### Why

Not every user message is a memory lookup request.

This allows:

- friendly non-memory responses for greetings
- profile-memory answers for stable factual questions
- experience-memory answers for work examples
- blended answers when background and work should be combined

This avoids both:

- robotic fallback on simple conversation
- forcing every question through one retrieval lane

---

## 8. Retrieval Should Not Be Tool-Calling First

We considered whether profile memory and experience memory should become separate tools that the model explicitly chooses to call.

### Decision

Do not make them model-selected tools for now.

Use a deterministic router first.

### Why

Tool-calling would add:

- more complexity
- more cost
- more debugging surface

The current product does not need it yet.

A deterministic router is:

- cheaper
- easier to reason about
- easier to test
- easier to tune

If needed later, tool-like retrieval can be added after the routing model is mature.

---

## 9. Deployment and Persistence Decisions

We moved from a local-only mindset to a deployed system with:

- Vercel for frontend
- Railway for backend
- Railway Postgres for persistent backend data

### Why

GitHub Pages was fine for static hosting, but not for the backend.

SQLite was acceptable for local development, but not ideal for persistent production metrics and engagement tracking.

### Result

The system now supports:

- local development
- deployed backend persistence
- production analytics/session storage

while still keeping the codebase relatively lightweight.

---

## 10. Why Postgres Instead of RAG or Redis

### Decision

Use Postgres (SQLite locally) as the single data store. Do not use vector embeddings or a separate cache layer.

### Why not RAG (vector embeddings)

The corpus is tiny and hand-authored — roughly 20 experiences and 10 topics. Vector embeddings exist to find semantically similar documents across thousands of records where exact vocabulary does not match. At this scale, that machinery costs more in API calls and complexity than it recovers in recall.

More importantly, the retrieval algorithm is a graph traversal, not a similarity search. `hybrid_retrieve` does three things: BM25-style token overlap on the experience title, recall scoring on `raw_context`, and a topic boost that walks `experience → topic → query` using pre-weighted `relevance_edges`. That relational structure is exactly what Postgres is designed for. A vector store has no native concept of weighted edges between nodes.

Deterministic retrieval also makes the system easier to reason about and test. It is possible to assert exact experience IDs in `test_retrieval_e2e.py` without mocking anything, and to explain why a result scored high in terms of specific token overlaps and edge weights. Embedding-based retrieval loses that traceability.

### Why not Redis

Redis is a cache, not a primary data store for a graph with durable state. The activation system updates scores on experiences and topics after every session. That state needs to survive across restarts. Storing it in Redis would mean either accepting eviction risk or adding a persistence layer on top — which is just Postgres with extra steps.

Sessions, analytics events, contact messages, profile memories, experiences, and topic edges all live in one place. Adding Redis would mean two services, two connection pools, and two failure modes for a solo portfolio project.

### Result

One store handles everything: graph state, session tracking, analytics, and contact messages. The retrieval algorithm is deterministic, explainable, and testable. Vocabulary mismatch is handled with a small query expansion table in code rather than embedding distance.

---

## 11. Current Intended Direction

At the moment, the intended architecture is:

### Memory layers

- `profile_memories` for stable factual identity/background data
- `experiences` for concrete work evidence
- `topics` and `relevance_edges` for graph structure

### Chat behavior

- route first
- retrieve from the right memory lane
- answer concisely and grounded
- use citation-led follow-ups
- avoid robotic fallback for greetings

### Product goal

The assistant should feel:

- exploratory
- grounded
- specific
- and human

not like a generic RAG chatbot and not like a static resume.

---

## Topic bubble hierarchy — positioning signal over breadth display

**Previous direction:** All topic bubbles had similar `base_weight` values (3.0–7.5), producing a relatively flat visual spread across 10 topics. The intent was to give visitors freedom to explore any area.

**What changed:** Topic `base_weight` values were restructured into three tiers:
- Primary (9.0–9.0): `ai-agents`, `memory`, `eval`, `pm`
- Secondary (5.5–6.0): `eng`, `research`, `startup`
- Personality signal (2.5–4.0): `access`, `ethics`, `photo`

**Why it changed:** A flat bubble field reads as "person who's done many things" rather than "expert with range." Without visual hierarchy, a recruiter's first impression is breadth, not depth. The topic bubbles are the first interactive element visitors see — they should communicate identity, not just offer a menu.

**New intended direction:** The visual weight of the bubbles tells the story before anyone reads anything: Yixin is an AI product PM with a research foundation. Accessibility, ethics, and photography remain present as personality and range signals, but are visually subordinate. As real visitor queries accumulate, `activation` will naturally reinforce or rebalance this hierarchy based on actual interest.

---

## 12. Bot Asks Back — Making the Conversation Two-Directional

**Previous direction:** The chat was entirely one-directional. The assistant answered visitor questions but never asked anything back or adapted to who the visitor is.

**What changed:** The bot now occasionally asks the visitor a short, personalizing question — about their own work, what they're building, or what brought them here. This happens at most once every 3 rounds (1 round = 1 user message + 1 bot answer). When the visitor answers, the bot acknowledges their interest and bridges to Yixin's most relevant experience.

**Two-turn lifecycle:**
- Turn A (bot asks): Response ends with a natural question directed at the visitor. Follow-up suggestion chips are suppressed so the visitor isn't distracted.
- Turn B (visitor answers): Route is forced to `memory`, retrieval threshold is bypassed so we always have context to bridge from. The LLM acknowledges what the visitor shared, then bridges to Yixin's relevant work. No additional question — let the visitor continue at their own pace.

**Why this matters:** The conversation feels like a dialogue rather than an FAQ. It signals that the assistant is curious about who the visitor is, and it lets Yixin's experience feel personally relevant rather than generic.

**Technical implementation:**
- `last_ask_back_round` and `ask_back_pending` columns added to sessions table (migrated automatically)
- Deterministic trigger: `current_round - last_ask_back_round >= 3`
- `ask_visitor_question` flag injected into LLM prompt JSON when triggered
- `visitor_context` injected on the answer turn so the LLM bridges naturally
- Never triggers on `small_talk` route
