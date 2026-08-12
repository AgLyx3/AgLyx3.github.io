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

## 6. Follow-Up Question Generation: Topic-Led → Citation-Led → Citation-Expanding

The original follow-up generation leaned too heavily on the selected topic label.

That caused repetitive prompts like:

- “What experience does Yixin have with accessibility?”
- “How did Yixin apply accessibility in practice?”

even after the assistant had already answered an accessibility question.

### First shift: Citation-led

Generate follow-up questions from the retrieved experience titles used in the answer, not from the topic label. The better continuation point is the specific evidence that supported the answer, not the category it belongs to.

### Second shift: Citation-expanding

Follow-ups no longer ask about the experiences already cited — those were just answered. Instead, they surface *adjacent* experiences the visitor hasn't touched yet: experiences that share the same topic edges but weren't retrieved in this turn.

This creates a naturally branching exploration path. Each answer closes out the experiences it used and opens a door to new ones. The visitor is always moving forward rather than circling the same ground.

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

### Original direction

Deployed with:

- Vercel for frontend
- Railway for backend
- Railway Postgres for persistent backend data

### What changed

Migrated the backend fully to Vercel. Railway's hobby tier caused recurring cold start problems — the backend would spin down and introduce multi-second delays on first request, breaking the chat experience.

Backend now runs on Vercel alongside the frontend, with Neon Postgres as the database (replacing Railway Postgres).

### Why

Vercel keeps functions warm more reliably at this tier and eliminates the cold start latency that Railway hobby imposed. Consolidating on one platform also simplifies deployment, environment variable management, and observability.

SQLite remains for local development only — Neon Postgres is the production store.

### Result

- Frontend: Vercel (`www.yixinli.me`)
- Backend: Vercel (`backend-green-zeta-37.vercel.app`)
- Database: Neon Postgres (production), SQLite (local dev)
- No Railway dependency remaining

---

## 10. Why Postgres Instead of RAG or Redis

### Decision

Use Postgres (SQLite locally) as the single data store. Do not use vector embeddings or a separate cache layer.

### Why not RAG (vector embeddings)

The corpus is tiny and hand-authored — roughly 20 experiences and 10 topics. Vector embeddings exist to find semantically similar documents across thousands of records where exact vocabulary does not match. At this scale, that machinery costs more in API calls and complexity than it recovers in recall.

The retrieval algorithm is a graph traversal, not a similarity search. That relational structure is exactly what Postgres is designed for. A vector store has no native concept of weighted edges between nodes.

Deterministic retrieval also makes the system easier to reason about and test. It is possible to assert exact experience IDs in `test_retrieval_e2e.py` without mocking anything, and to explain why a result scored high in terms of specific token overlaps and edge weights. Embedding-based retrieval loses that traceability.

### Why not Redis

Redis is a cache, not a primary data store for a graph with durable state. The activation system updates scores on experiences and topics after every session. That state needs to survive across restarts. Storing it in Redis would mean either accepting eviction risk or adding a persistence layer on top — which is just Postgres with extra steps.

Sessions, analytics events, contact messages, profile memories, experiences, and topic edges all live in one place. Adding Redis would mean two services, two connection pools, and two failure modes for a solo portfolio project.

### Result

One store handles everything: graph state, session tracking, analytics, and contact messages. The retrieval algorithm is deterministic, explainable, and testable. Vocabulary mismatch is handled without embeddings through a combination of four complementary layers described below.

---

## 11. Why This Specific Retrieval Design

The experience retrieval pipeline (`hybrid_retrieve`) combines four layers. Each one solves a failure mode the others can't handle alone.

**Final score formula:**
```
final_score = (0.6 × BM25_title + 0.4 × recall_raw_context) + 0.35 × topic_boost
```

**Layer 1 — BM25 on title (weight 0.6)**

The title is a dense, hand-authored summary of what the experience is about. BM25 token overlap on a short curated string is high-precision signal — if query tokens match the title, it's almost certainly a real match. It gets the higher weight because title matches are rarely false positives.

BM25 is strongest when visitors ask like a search engine using the same vocabulary as the content: *"What polling feature did Yixin build?"*, *"Tell me about eye-tracking research"*, *"What did she do at Jackson Lab?"*. It fails when visitors paraphrase — *"How does she handle making products people want?"* won't match `exp_customer_discovery` on tokens alone.

**Layer 2 — Recall score on raw_context (weight 0.4)**

`raw_context` is the full paragraph describing an experience — richer and longer than the title. It handles cases where the query uses vocabulary that isn't in the title but appears in the body. The lower weight reflects that longer text produces more incidental token overlaps, so it's better for recall than precision. Title catches the direct match; raw_context catches the paraphrase within the same experience.

**Layer 3 — Query expansion (`_expand_query`)**

Before any scoring, the query is expanded with a hand-authored synonym table. For example, "PM" expands to include "product management", "product manager"; "LLM" expands to "large language model". This catches the most common vocabulary mismatches without any model call — cheap, deterministic, and targeted at the specific domain vocabulary that appears in this corpus.

**Layer 4 — Topic-edge boost (weight 0.35)**

The query is first mapped to the topic graph (`_topic_distribution`), producing a weight for each topic based on how much the query overlaps with topic labels and descriptions. Then for each experience, the boost is: `query_topic_weight × edge_relevance` summed across all topics.

This solves the vocabulary mismatch that pure text matching can't handle. A visitor asking about *"personalization"* or *"context tracking"* doesn't match any experience title on tokens, but the topic graph bridges the gap — experiences strongly connected to the `memory` topic get pulled up because the query scores high on `memory`, and the `relevance_edges` table encodes that connection with pre-authored weights.

**Why all four together:**

- BM25 alone misses paraphrases
- raw_context recall alone produces noisy results from incidental overlap
- query expansion alone only covers known synonyms
- topic boost alone would ignore the actual query text and always surface the same experiences per topic

The layering means: exact vocabulary → title BM25; paraphrase within an experience → raw_context recall; known synonym → query expansion; conceptual mismatch → topic graph. Each layer rescues the failure mode of the one before it.

---

## 12. Topic Bubble Hierarchy — Positioning Signal Over Breadth Display

**Previous direction:** All topic bubbles had similar `base_weight` values (3.0–7.5) and shared the same color palette (a single `HUE_CYCLE` cycling through warm/cool tones indiscriminately). The intent was to give visitors freedom to explore any area, with activation size as the only hierarchy signal.

**What changed (size):** Topic `activation` values were tuned into a deliberate hierarchy:
- Largest: `ai-agents` (8.5), `eval` (8.0), `pm` (8.3)
- Mid: `memory` (6.5), `ethics` (6.8), `research` (6.5)
- Smaller: `eng` (6.0), `startup` (6.2), `access` (5.8), `photo` (4.9)

**What changed (color):** Bubbles now split into two semantic color families:
- **Blue family** (`blue`, `mirage`, `mist`, `slate`): professional/core work — AI Agents, Memory Systems, Evaluation & Benchmarking, Startup & Entrepreneurship, Software Development, Product Management
- **Warm family** (`amber`, `dune`, `smoke`, `cream`): personal/range signal — Academic Research, Accessibility, Photography & Videography, AI Ethics & Philosophy

**Why it changed:** Size alone wasn't enough to communicate what Yixin is known for vs. what rounds her out as a person. The color split adds a second visual axis: visitors can immediately read "blue = her core work" before clicking anything. The warm bubbles stay present and clickable but visually recede — signaling range without competing for attention.

**New intended direction:** Two axes of hierarchy working together — size signals relative depth within a category, color signals professional identity vs. personal range. The first impression should read: Yixin is an AI PM/researcher, and she also has an interesting life outside of that.

---

## 13. Router Layer Instead of Router Agent

**Previous direction:** No explicit routing — every message went through the same retrieval and generation pipeline regardless of intent. No small talk mode - easily fall back to robotic response.

**What changed:** A deterministic `route_query()` function classifies each message before any retrieval happens. Current routes: `small_talk` and `memory`.

**Why not a router agent:** A model-based router (calling an LLM to decide which lane to use) would add latency, cost, and a new failure mode on every single message — before the actual answer is even generated. At the current scale and query variety, the classification problem is simple enough that keyword patterns and heuristics outperform the overhead.

**Why a router layer works here:** The distinction between small talk and a genuine memory query is largely surface-level. "hi" vs. "what did Yixin build at Anthropic?" doesn't require semantic understanding — it requires pattern matching. A deterministic router is instantaneous, fully testable, and easy to extend with new routes as the product grows.

**New intended direction:** Keep the deterministic router as the first layer. If query complexity grows to the point where patterns can't classify reliably (e.g., ambiguous cross-domain queries, multi-intent messages), revisit a lightweight classifier model — but not a full LLM agent call.

---

## 14. Bot Asks Back — Making the Conversation Two-Directional

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

---

## 15. Current Intended Direction

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

## 16. Typography System Replacement (2026-08-12)

Triggered by an `/impeccable critique` + `design-taste-frontend` audit of `index.html`,
`portfolio.html`, and `chat.html`. Scored 22/36 on Nielsen heuristics.

### Previous direction

Three loaded type families, each with a role:

- **Autumn Brush** (local `.otf`) for the name / logotype
- **Playfair Display** (Google Fonts) for headings *and* body copy
- **Geist Mono** (Google Fonts) for all UI chrome: kickers, tags, buttons, nav, footers

### What changed

Cut to **two** loaded families:

- **Autumn Brush** stays, but is now restricted to the logotype only (`--font-display`)
- **Satoshi** (Fontshare, variable 300-900 roman + italic, two files) replaces
  *both* Playfair Display and Geist Mono (`--font-sans`)
- Inline `<code>` moved to a system monospace stack (`--font-code`), no webfont

Also removed as part of the same pass:

- The mono-caps eyebrows: `ASK ANYTHING`, `SEE THE WORK` (index),
  `SELECTED WORK · 2023-2026` (portfolio), and the uppercase treatment on
  `.msg-role` and `.landing-foot` (chat)
- All 6 em-dashes in visible copy and metadata
- The portfolio subhead's restatement of its own `<h1>` and `<meta description>`

Added: `:focus-visible` rules on `portfolio.html`, which previously had none anywhere.

### Why it changed

1. **The triad was the single loudest AI tell on the site.** High-contrast Didone
   serif for "editorial" + mono for "technical" + script for "personal" is the
   signature of generated portfolio design. The bundled detector independently
   flagged Geist Mono as an overused face in all three files.
2. **Playfair was doing work it is not built for.** It set card body copy at
   14.5px; it is a display face and is fragile at reading sizes.
3. **Monospace was a costume.** All 18 mono usages in `chat.html` were UI chrome.
   None were code, data, or measurement.
4. **Eyebrows are banned outright** by the craft floor, not merely discouraged.
   The heading already carries the label's job.

### New intended direction

Two families, seven roles, one scale:

| Role | Face | Size | Weight | Tracking |
|---|---|---|---|---|
| Logotype | Autumn Brush | clamp | 400 | - |
| Display h1 | Satoshi | clamp(34-54px) | 600 | -0.03em |
| Card heading | Satoshi | 21px | 600 | -0.02em |
| Body / reading | Satoshi | 15.5px | 400 | 0 |
| Lede | Satoshi | 17px | 400 | -0.005em |
| Label / meta | Satoshi | 12.5px | 500 | 0, sentence case |
| Control | Satoshi | 13px | 500 | 0 |
| Code | system mono | 0.88em | 400 | 0 |

Emphasis is italic or weight **within Satoshi**, never a second family.
No uppercase + wide-tracking micro-labels anywhere.

### Still open (not done in this pass)

- **No images anywhere on the site.** Highest-value remaining fix; blocked on
  screenshots Yixin will supply. Layout slots not yet cut.
- Portfolio status pips introduce green + purple alongside the blue accent,
  breaking the single-accent lock.
- Radius scale is still mixed (doors 0, cards 20px, icon tiles 12-14px, pills).
- Theme hard-codes `dark` and ignores `prefers-color-scheme` on all three pages.
- `frontend/assets/styles.css` is dead: no HTML file links it.
- Design tokens remain triplicated across the three files with no shared source.

---

## 17. Ambient Bubble Field on Portfolio (2026-08-12, experimental)

### Previous direction

`portfolio.html` had only the dark-mode starfield. The soft-orb visual language
lived exclusively in `chat.html`, where bubbles are D3 force-simulated,
interactive memory-topic nodes.

### What changed

Added `#bubblefield` to `portfolio.html`: eight ambient orbs using the same
material as the chat bubbles (radial fill feathering to transparent, no outline),
drifting slowly, layered in front of the starfield and behind the content column.

Deliberate constraints:

- **Not D3.** Portfolio does not load `d3.min.js`; 280KB for decoration is not worth it.
- **Not interactive and not labeled.** These are planets, not nodes.
- **Curated fixed layout, not random**, so orbs stay clear of the reading column
  on every load. Hues lifted from the chat bubble palette (blue = work, warm = personal).
- Transform-only animation, `pointer-events: none`, honored by the existing
  blanket `prefers-reduced-motion` override.

### Why it changed

The galaxy is a deliberate concept, not decoration: the chat bubbles read as
planets, so the starfield is the world they live in. The critique's initial
recommendation to cut the galaxy was **retracted** on that basis. The real problem
was that the landing and portfolio pages did not speak the visual language the
chat page had already invented, so their backgrounds read as generic space.

### New intended direction

The bubble/planet field becomes the shared ambient layer across all three pages,
turning decoration into identity. **Status: experimental on `portfolio.html` only,
pending visual review.** If it holds, `index.html`'s cruder light-mode `.dot`
field should be replaced with the same orb system.

---

## 18. Logotype and Self-Hosted Fonts (2026-08-12)

### Previous direction

Autumn Brush (local 659KB `.otf`) as the logotype, with Satoshi and Britney
loaded remotely from Fontshare via `<link>`.

### What changed

**Logotype: Autumn Brush → Britney → Ephesis.** Autumn Brush was rejected as a
brush script; Britney was rejected once seen rendering correctly. Ephesis is a
fine calligraphic script (a pen, not a brush), self-hosted at 9.6KB.

**All fonts are now self-hosted** in `frontend/assets/fonts/`. This was not a
preference. Two real defects forced it:

1. **Fontshare serves protocol-relative URLs** (`//cdn.fontshare.com/...`). On a
   `file://` page these resolve to `file://cdn.fontshare.com/...` and fail
   silently. Every local review up to this point had been looking at system
   fallback fonts, not the intended type.
2. **Fontshare drops families from combined requests.** Requesting
   `satoshi@1,2` and `britney@1` in one URL returned Satoshi only. This would
   have shipped broken to production, not just to local preview.

Discovered because Yixin sent a screenshot of the rendered page. Worth recording:
the earlier verification checked file integrity and the absence of old font names,
never that a font actually rendered. Font payload went 659KB → ~100KB.

### Script-specific rules now encoded

- **Weight 400 only.** Ephesis ships one weight; 500+ triggers synthetic bolding.
- **Larger em.** Scripts have small x-heights; the landing runs
  `clamp(46px, 13.5vw, 68px)` to `clamp(56px, 7.4vw, 112px)`.
- **Descender headroom.** `line-height: 1.2` plus `padding-bottom: 0.06em`, since
  "Yixin" carries a `y` descender.
- Topbar lockup is 33px, larger than a sans would need at the same optical size.

### New intended direction

Two self-hosted families, never remote. Preview locally over HTTP, never
`file://` — web fonts are always fetched in CORS mode and Chrome treats `file://`
pages as opaque origins, so fonts silently fail there even when self-hosted.

---

## 19. Landing Rebuilt as an Asymmetric List (2026-08-12)

### Previous direction

Two symmetric cards side by side, each: icon tile in a rounded square → title →
description → arrow CTA. A nebula glow had been painted over the cards, but the
card anatomy underneath was untouched — `.door` was still fully styled as a glass
card and then overridden with `!important`.

### What changed

Replaced with an **asymmetric two-column layout**: the name and tagline hold the
left, two hairline-separated rows hold the right. No cards, no icon tiles, no
symmetry, no arrows, and no hand-drawn SVG icons anywhere on the page.

Marker iteration is worth recording, because two candidates were rejected for the
same underlying reason:

- **Arrow** — generic.
- **4-point sparkle** — rejected: that glyph is the Gemini / Copilot "AI magic"
  mark. Swapping one AI tell for another is not progress.
- **Orb** (chosen) — the site's own bubble at glyph scale. Needs no SVG at all.

Also considered and rejected for now: a split-halves layout with a moving divider
(kept as reference in the decision history; the moving line can be driven by
`transform` on an absolutely positioned rule, with each half's content following
at half the travel, if it is ever revived).

### Animation correctness

The first implementation stuttered. Three genuine causes, all fixed:

1. **A gradient carrying `currentColor` cannot be interpolated.** Gradients are
   not transitionable, so the colour change repainted in discrete steps. The orb
   is now a solid `background-color` with a `box-shadow` glow.
2. **`padding-left` was animated on hover**, forcing a layout pass every frame.
   The text now slides via `transform: translateX(13px)` while the row, its
   hairlines, and the orb stay anchored. It also reads better.
3. **Three overlapping durations** (340/340/460ms) meant nothing landed together.
   All motion now shares `--way-dur: 420ms` and one easing curve.

`filter: drop-shadow` was replaced with `box-shadow`, which does not
re-rasterise the element on every frame of a scale.

### Mobile

- `body` is a flex column at `min-height: 100dvh`; `.wrap` takes `flex: 1 0 auto`.
  Previously `.wrap` forced its own full viewport while content sat pinned to the
  top, leaving a large void and pushing the footer past the fold.
- **Full-bleed hairlines** below 640px: `.ways` gets negative inline margins so the
  rules reach both screen edges, while text stays on the 22px margin.
- `@media (hover: none)`: the orb renders in the accent colour at rest, and
  neither text nor orb moves, so nothing shifts under a thumb.
- Breakpoints at 860px (columns stack) and 640px (phone), not one breakpoint.

Verified with headless Chrome at 360x640, 390x844, 768x1024, 1280x560 and
1440x900: **overflow is 0 at every size**, rules measure full viewport width on
phones, and row height is 89-107px against a 44px tap-target minimum.

### Also fixed here

`body { overflow: hidden }` (a P0-adjacent trap from the original audit) is gone;
short viewports could previously clip content with no way to scroll to it.
