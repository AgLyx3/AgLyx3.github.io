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

---

## 20. Landing Portrait Becomes an Overlapping Print Pair (2026-08-16)

### Previous direction

One portrait sat behind the landing identity at low opacity, then resolved into a
crisp angled print when the name or image was hovered, focused, or tapped.

### What changed

The landing now uses two overlapping portraits: the warm calligraphy photograph
and a more formal full-length portrait. Both use the same intersecting horizontal
and vertical alpha masks at rest, then crossfade into crisp, oppositely angled
prints as one reveal group. Hovering an individual print raises it within the pair.

### Why

The pair shows two complementary sides of Yixin without adding explanatory copy
or another page section. The overlapping-print treatment was selected over a
scattered composition and a rigid side-by-side diptych because it preserves the
landing's editorial character and keeps the photographs connected to the name.

### Layout and interaction constraints

- On desktop, the complete foreground pair must end before the navigation column;
  it may overlap the name and tagline but not “Talk to me” or “See what I've built.”
- On mobile, both prints remain above the action rows and inside the viewport.
- Touch uses an explicit reveal state: tapping the name or either portrait opens
  the pair; tapping either open portrait or any blank page area closes it.
- Desktop hover and keyboard focus retain the same reveal behavior.

### New intended direction

The overlapping pair is the production landing treatment. Temporary comparison
views are not part of the shipped navigation or product surface.
## 21. Ambient pixel constellation system across the frontend (review branch)

- Previous direction: The homepage used soft photographic masks and circular ambient marks, the portfolio used blurred glass cards and large gradient orbs, and the chat page used smooth D3 topic bubbles.
- What changed: The `pixel-site-system` worktree applies the chat Cluster study as a shared visual system. Ambient decoration becomes low-opacity square-pixel constellations, interface surfaces use crisp geometry and restrained hard shadows, and metadata uses monospaced type while the calligraphic name and readable content typography remain intact.
- Why: Repeating the same pixel atmosphere, geometry, and interaction language makes the three frontend experiences feel authored as one system without turning photographs or long-form content into retro pixel art.
- New intended direction: Use pixels for atmosphere, boundaries, status marks, and relationship cues; preserve photography, the Ephesis identity mark, and Satoshi content text. Maintain explicit exclusion zones around interactive content and reduce pixel density on mobile.
## 22. Landing Background: Constellation Field, Adapted from ThreeUI (2026-08-22)

> **Outcome (2026-08-23): adopted, alongside the pixel clusters rather than
> instead of them.** The section below was written as a replacement for the
> landing's background layers, which is no longer accurate. It was briefly
> pulled from the homepage on the argument that the field and the ambient pixel
> clusters were doing the same job in the same corners in conflicting shape
> languages. The portfolio settled it: that page runs the constellation, the
> clusters and the starfield together and reads well, so the homepage now uses
> the same recipe — constellation canvas, four pixel clusters, and the starfield
> at the thinned 70 (§23 covers the portfolio's own use of the renderer).


### Previous direction

The landing page carried two mutually exclusive background layers:

- **dark** — 150 absolutely-positioned `.star` spans twinkling on a CSS keyframe,
  plus the milky-way band and periodic meteors
- **light** — 14 blurred `.dot` spans drifting on an 18s loop, described in the
  source as the "light-mode bubble motif"

### What changed

The light-mode dots are gone. Both themes now share a single `<canvas>` background
(`frontend/assets/constellation.js`): 26–62 drifting nodes that draw a link
whenever two fall within a viewport-scaled radius, with a gentle pull toward the
cursor. The dark starfield, milky-way band, and meteors are untouched — the
network now sits under them as a second, slower layer.

The starfield was **thinned from 150 stars to 70** at the same time, with peak
twinkle opacity dropped from a 0.50–1.00 range to 0.42–0.82 and the halo from
0.55 to 0.45 alpha. At the old density the two glowing layers read as speckle
and the network lost its structure; the stars are the far layer now. Densities
of 150 / 95 / 70 / 50 were compared in headless Chrome — 95 still speckles, 50
stops reading as a sky.

The renderer is adapted from **ConstellationField** in
[ThreeUI Community](https://github.com/MengTo/threeui) (MIT).

### Why it changed

- The dots read as dust rather than as anything. A node/link network reads as the
  connective layer the site is actually about — "Human and AI", a retrieval graph
  behind the chat agent — so the background finally says something.
- Light mode had the weaker of the two treatments and now has parity with dark.
- One canvas replaces 14 (light) / 150 (dark, partially) animated DOM nodes.

### Why the library itself was not adopted

ThreeUI ships as `@designcodeio/threeui`, a **React** package whose components
wrap full standalone HTML demo documents in an iframe (each pulling Tailwind CDN,
GSAP, and Iconify). This frontend is vanilla HTML/CSS/JS with no build step,
deployed as static files. Taking the package would have meant introducing React,
a bundler, and a build to the Vercel project in exchange for one background
effect.

Most of the catalogue is also not "3D" in the sense the name suggests — the
constellation family is plain 2D canvas; only a subset (portal-field, wireframe
forms) actually loads three.js.

So: **borrow the renderer, not the dependency.** The lifted file is ~220 lines
with zero dependencies and no build step. The same approach is available for any
other component in that repo if one is wanted later.

### Adaptations made to the upstream renderer

- Colours read from `--forest-rgb` at runtime instead of a hard-coded gold, with
  a `MutationObserver` on `data-theme` so the field re-tints on theme toggle
  rather than restarting. Alphas differ per theme — ink on cream carries much
  further than glow on navy.
- Node count and link radius scale with viewport width (26 / 44 / 62).
- `prefers-reduced-motion` paints one static frame instead of skipping the field
  entirely, so the texture survives without motion. Upstream rendered nothing.
- Loop parks on `visibilitychange`; DPR capped at 2; `resize` debounced 150ms.
- Pointer gravity is gated on `(hover: hover)` — it was dead weight on touch.

### Current intended direction

The constellation is the landing page's background in both themes. The portfolio
page was deliberately left alone: it already runs its own **bubble field** (§17),
a motif shared with the chat page, and adding a network beneath it would be a
third ambient layer competing with an intentional one. Two pages, two
backgrounds, on purpose — revisit only if the bubble field is retired.

Verified in headless Chrome at 1440x900 and 390x844, both themes, plus live theme
toggle and `prefers-reduced-motion: reduce`: no console errors, no horizontal
overflow, backing store correctly capped at 2x on a 3x device.


---

## 23. Portfolio Rebuilt as a Star Track (2026-08-23)

### Previous direction

`portfolio.html` was a two-column card grid (`.grid`, `repeat(2, 1fr)`, 22px gap)
over two ambient background layers: the 150-star dark starfield and the
**ambient bubble field** from §17 — eight curated drifting orbs, the chat page's
memory-orb motif reused as "planets in the same galaxy".

### What changed

The grid became a **path**. One meandering line runs down the page and the eight
projects are strung along it as *stations*, alternating left and right, each
joined to the line by a short spur that lands on a lit node.

- **The track** is an SVG drawn in `frontend/assets/star-track.js` from
  *measured* geometry — a sine meander (24px amplitude / 430px wavelength on
  desktop, 8px / 300px narrow), sampled every 7px as a polyline, stroked through
  a gradient that fades at both ends so it reads as passing through the page.
  Faint dust is scattered along it, seeded per-y so a redraw does not reshuffle
  the sky.
- **Stations** each take their own grid row — sharing a row is what makes a
  two-column grid; taking turns down the page is what makes a track. A -86px
  interlock margin claws back the dead space that leaves, so consecutive cards
  overlap along the spine.
- **3D.** `.stations` carries `perspective: 1500px`. Each card rests at
  `rotateY(3.4deg) rotate(1deg)`, hinged on the edge facing the track, so the
  two sides read as panels opening off one spine. Hover squares the card up
  (`rotateY(0) translateZ(30px)`); the mark and title sit at `translateZ(18px)`
  so the card has real depth rather than being a flat rectangle that happens to
  be rotated. Tilt is capped at ~4deg — past that, body text shimmers on a
  low-DPI screen.
- **The bubble field was removed.** With a lit track running down the page,
  stars, a node network *and* drifting orbs was three ambient layers competing
  for the same attention. The orb motif still lives on the chat page.
- The **constellation field** (§20) was added here, and the starfield thinned to
  70 dimmed stars, matching the landing page.

### Narrow screens

The track leaves the middle and runs down the left margin; every card sits to
its right in one column. The meander flattens (8px), the tilt eases to 2deg and
then 1.4deg below 560px, and the interlock margin goes to zero. `--track-gutter`
in the stylesheet must stay twice `baseX` in `star-track.js` — the two are
commented as a pair.

### Why measured rather than hard-coded

Card heights differ, fonts swap in after first paint, and the filter buttons
change how many cards exist. Every node, spur and path point is computed from
`getBoundingClientRect` on redraw, driven by a `ResizeObserver` on the rail plus
a `portfolio:filtered` event the filter script dispatches. Sides and rows are
assigned over the **visible** set, so filtering never leaves two cards on the
same side of the spine.

Two bugs this surfaced, both fixed:

1. Nodes were skipped whenever the spur was shorter than `spurMin` — which is
   *every* spur on a narrow screen, so mobile had no nodes at all. Only the spur
   is skipped now; the node always marks the station.
2. The interlock margin comes from `.station + .station`, which is DOM
   adjacency. When a filter hid the first card, the next one inherited the
   pull-up and rode into the filter row above it, covering the buttons. Only the
   first *visible* station is exempt, and only JS knows which that is.

### Current intended direction

The portfolio is a scroll journey along one path, not a grid to scan. Verified
in headless Chrome at 1440, 1024, 900 and 390 wide, both themes, through every
filter cycle, plus hover and `prefers-reduced-motion: reduce` (cards sit square,
entrance and perspective drop, the track stays — it is structure, not motion).
No page errors, no horizontal overflow at any width.

## 24. Chat Bubble Shadow Without an SVG Filter, and Inert Offscreen Surfaces (2026-08-22)

### Previous direction

Every `.bubble-node` carried `filter="url(#fshadow)"`, an `feDropShadow`, and the
landing's offscreen surfaces (chat panel, CTA footer, both modals, voice overlay)
were hidden with `opacity: 0` alone.

### What changed

The drop shadow is now a `<circle>` filled with a radial gradient, and every
surface that is not currently visible carries `inert`.

### Why it changed

iOS Safari rasterises an SVG filter region into an offscreen buffer it does not
scale to `devicePixelRatio`. On a 3x iPhone each bubble was painted at roughly
1x and upscaled — visibly pixelated, labels included, because the filter wrapped
the whole `<g>`. A gradient is vector geometry and resolves at whatever the
device paints at.

Separately, `opacity: 0` hides a surface visually but leaves its controls in the
tab order. A keyboard user walked 17 invisible stops and never reached a topic
within 26 tabs. `aria-hidden` on `#bubbleCanvas` compounded it by stripping all
ten `role="button"` bubbles from the accessibility tree while `tabindex="0"` kept
them focusable.

### New intended direction

No SVG filters on the bubble canvas — shadows are gradient geometry. Visibility
and focusability stay in step: anything faded out is `inert`, synced off computed
style rather than hand-maintained at each state transition. Bubble labels shrink
to fit the circle's chord at each line's own y offset, since `wrapLabel` only
breaks between words.


---

## Portfolio screenshots: the node becomes a junction

### Previous direction

Every portfolio card was text-only: glyph, status pill, title, one paragraph,
tags, links. Adding images meant either cutting prose to make room or admitting
a visible hole on the roughly half of the work that has no screenshot.

### What changed

Screenshots are an optional overlay layer rather than a field in the card. Each
card carries a `data-shot` path; the script preloads it and only upgrades the
card once the file actually decodes. On success the 44px glyph tile becomes a
thumbnail button. Hovering the card opens a preview **on the other side of the
track**, in the column the alternating layout leaves empty at that row, joined
to the same node the card hangs off by its own spur. The tile also taps through
to a lightbox. No prose was removed.

An earlier pass floated the preview outward into the page margin instead. That
was wrong: the container caps at 1080px, so the margin is only ~244px at a
1440px screen, and the preview had to either shrink to a stamp or sit on top of
the card title. The opposite column is ~410px at every desktop width, because
it is sized off the container rather than off the viewport, and the reveal
below ~1360px no longer has to switch itself off.

### Why it changed

Four constraints drove the shape:

1. **Not all work has an image, and it must not show.** Authoring image markup
   per-card would make a card without one look unfinished. Deciding at runtime,
   on whether the file loads, makes a missing screenshot indistinguishable from
   a project that never had one — and makes adding one later a matter of
   dropping a file into `assets/shots/`, touching no HTML.

2. **The rail is drawn from measured card geometry.** `star-track.js` anchors
   each node at `ANCHOR = 48` (26px padding + half the 44px mark) and redraws
   from `getBoundingClientRect`. Any reveal that changed a card's height or
   widened its top row would drag every node below it off its spur. So the
   trigger reuses the mark's existing box instead of sitting beside it, and the
   preview is absolutely positioned. Nothing in this feature can reflow.

3. **The preview cannot live inside the card.** The card is rotated in 3D and
   straightens on hover, so anything inside it inherits a transform that no
   spur drawn in the flat SVG underneath could ever meet. The preview is a
   child of the station, which carries no transform — the same reason
   `star-track.js` measures the station rather than the card.

4. **Hover-only content does not exist on a phone.** The same tile is a real
   button to a lightbox, which is the path that works on every input.

### New intended direction

The track is no longer only a spine to hang cards off — a node can be a
junction, with prose on one side of the line and the artifact on the other.
`star-track.js` now publishes each node's measured position on its station
(`data-node-x` / `data-node-y`) and fires `portfolio:trackdrawn` after every
redraw, so other features can attach to the track's geometry without
duplicating the meander maths. The hover spur is drawn into its own overlay SVG
rather than the rail's, because `draw()` empties that one on every redraw and
would otherwise erase the spur mid-hover.

Below 861px there is no opposite column — the track moves to the left margin
and one column of cards runs beside it — so the preview and its spur are
dropped and the screenshot goes **inline in the card**, under the title, above
the prose, tapping through to the lightbox for detail.

Mobile is not a degraded desktop here, it is a different affordance. The first
pass left the phone with only the 44px tile, and a 44px tile with a 9px corner
tick is not something anyone taps — the images would have been invisible to
every phone visitor, which defeats the reason for adding them. Inline spends
scroll, the cheap resource on a phone, and the tile reverts to the project's
glyph because a thumbnail of a picture sitting 20px below it is noise.

Reflowing the card inline is safe *because it is static*: the rail measures card
heights and a ResizeObserver redraws, so the track follows. The desktop preview
could never be inline for the same reason it could never live inside the card —
it changes height per hover, and the track cannot chase a pointer. Every image
carries its intrinsic width/height from the preload probe so it reserves its
aspect ratio and never shoves the track after first paint.
Transient overlap of a *neighbouring* card is accepted: stations interlock by
-86px, so a preview will sometimes cover the tags of the card above it. It is
opaque, bordered and on top, and it belongs to whatever is being hovered.

## 25. Pipeline Observability: Langfuse Cloud (2026-08-27)

### Previous direction

The only record of what the chat agent did was `analytics_events` in Postgres
(`services/analytics.py`) — event names and small payloads, written for product
funnel questions: how many turns, did the CTA fire, was a topic opened.

Nothing captured the agent's internals. When an answer came out wrong there was
no way to tell whether retrieval had handed the model nothing, whether the
scores had fallen just under `retrieval_min_top_score`, or which memory blocks
were in the prompt. The `MEMORY_FALLBACK_RESPONSE` path — the bot saying "I
don't have enough real context" — was completely unmeasured, despite being the
clearest single signal that the memory graph has a hole.

### What changed

Langfuse Cloud is now the store for pipeline internals. `analytics_events`
stays exactly as it was; the two answer different questions and neither
replaces the other.

Langfuse over LangSmith, on three counts. Retention: 30 days on the free tier
against 14, which is the window to notice a bad answer and turn it into a test
case. Portability: Langfuse is OpenTelemetry-native, so instrumentation is not
locked to the vendor and can move to a self-hosted instance if visitor-data
residency ever becomes a hard requirement rather than a preference. Fit:
LangSmith's real advantage is depth of LangChain/LangGraph integration, and
this backend uses neither — `services/llm.py` calls Chat Completions with raw
`urllib`, so that advantage is dead weight here.

Self-hosting Langfuse was considered and rejected for now. v4 needs Postgres,
ClickHouse, Redis and blob storage across two containers — none of which runs
on Vercel — so it means renting and maintaining a box for a portfolio site.

### New intended direction

`services/tracing.py` is a shim, not a direct SDK dependency scattered through
the app. Every helper is a no-op when the keys are absent, the package is
missing, or the SDK raises. Observability must never be able to take the chat
endpoint down, and instrumentation call sites must not need an `if` around
them.

**Text mode** is one trace per turn: a `chat-turn` root, a `retrieval` child
recording top score, score gap and the thresholds it was judged against, and a
`chat-completion` generation carrying prompt, output and token usage. Every
turn is scored `memory_fallback` 0 or 1, so the fallback rate is a rate rather
than an anecdote.

**Voice mode needed a different shape.** One voice turn is three HTTP requests
plus a browser-to-AssemblyAI WebSocket the backend never sees, so there is no
server-side object tying it together. The browser now mints a `turn_id` per
turn and sends it on `/chat` and `/voice/tts`; the backend derives a
deterministic trace id from it (`create_trace_id(seed=…)`), so the separate
requests land on one trace.

Two deliberate asymmetries there. Speech-to-text is reported back by the client
to `POST /voice/turn` rather than traced server-side, because otherwise the most
common cause of a bad voice answer — a misheard question — leaves no evidence
at all; the transcript's confidence is attached as a score. And text-to-speech
is called once per sentence, so tracing every call would triple a voice turn's
trace cost to learn nothing: successful synthesis is summarised in a single
`tts` span for the turn, while failures get their own span, because an answer
that never becomes audio is exactly the bug that is otherwise silent.

The cost of that shape: spans created at report time do not carry true
wall-clock timing, so durations are recorded as metadata instead.

**Flushing is the sharp edge.** Vercel freezes the instance once a response
finishes and the SDK batches spans on a background thread, so `flush()` runs in
the SSE generator's `finally` — not before the `StreamingResponse` is returned,
and in a `finally` so a visitor closing the tab mid-answer still ships the
trace. Getting this wrong loses traces silently, which is indistinguishable
from the integration not working.

Tracing stays off until `LANGFUSE_ENABLED=true` and the keys are set, and
`LANGFUSE_MASK_PII` (on by default) redacts visitor-authored text before
anything leaves the box. Visitors are strangers who did not opt into a
third-party trace store.

Masking by key name alone was not enough, and the first pass shipped that way:
it caught the root span's `user_message` but missed the two places the visitor's
words actually travel — the retrieval query, and the prompt itself, where the
message sits inside `messages[].content`. The mask now also walks chat messages.
A visitor's plain-text history turn is dropped wholesale; the current turn is
parsed as the JSON payload it is, and only `visitor_question` and
`visitor_context` are blanked inside it. The system prompt, the assistant's own
prior turns, and the retrieved `profile_context` / `experience_context` all
survive — none of that is visitor data, and it is the reason to read a prompt at
all. A trace that redacted everything would be private and useless.
