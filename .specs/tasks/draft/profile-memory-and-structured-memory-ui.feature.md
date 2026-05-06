---
title: Add profile memory node and structured memory detail UI
type: feature
status: draft
created_at: 2026-05-03
---

# Add profile memory node and structured memory detail UI

## Description

Extend the current portfolio memory demo so it shows two memory layers:

1. A stable `Profile Memory` layer that represents durable identity and background context.
2. The existing dynamic topic-and-experience memory graph, where topics vary in size based on activation and experiences connect to one or more topics.

The graph behavior for topics and experiences should remain conceptually the same. The main change is:

- add a fixed central `Profile Memory` node
- preserve floating topic nodes with activation-based sizing
- preserve experience-to-topic graph edges
- enrich memory details so both profile memories and experience memories can be viewed in:
  - `Structured` mode
  - `Full Context` mode

This should demonstrate how memory can be built from conversation history into:

- raw memory context
- a compact structured representation

without turning the graph itself into a schema diagram.

## Why

The portfolio should demonstrate a memory architecture that is legible to a hiring manager:

- stable, durable memory in the center
- evolving topic memory around it
- extracted structured memory derived from raw context

This should resemble a practical memory architecture demo rather than only a graph visualization.

## Scope

### In scope

- Add a fixed central `Profile Memory` node to the graph UI.
- Add backend storage for profile memories.
- Seed profile memory with initial durable facts about Yixin Li.
- Enrich experiences so each experience can expose:
  - raw context
  - structured view
- Add a detail UI that defaults to `Structured` mode and allows switching to `Full Context`.
- Keep structured mode limited to:
  - `Context`
  - `Action`
  - `Result`
- Keep all structured fields for a single raw memory visually grouped inside one bordered parent container.

### Out of scope

- Automatic conflict resolution across profile memories
- LLM-based extraction pipelines
- Changing topic activation policy further
- Converting structured fields into standalone graph nodes
- Replacing the current topic/experience graph model

### Implementation note: experience nodes are new visual elements

Experience nodes do not currently exist as visual graph nodes. Today, experiences are only accessible by navigating to `topic.html` after clicking a topic bubble. This feature adds experience nodes as clickable visual nodes in the graph, connected to their parent topic nodes by edges. This is new rendering work, not a change to existing experience graph semantics.

## User stories

### Story 1: Hiring manager views stable and dynamic memory separately

As a hiring manager
I want to see one stable profile node in the center and evolving topics around it
So that I can quickly understand the difference between durable identity memory and growing experience memory

### Story 2: User inspects profile memory as structured and raw context

As a user exploring the memory demo
I want to click the profile node and view profile memories in structured mode by default
So that I can understand how durable memories are represented compactly and trace them back to their original source context

### Story 3: User inspects experience memory without changing graph semantics

As a user exploring the graph
I want experience nodes to stay connected to topic nodes exactly as they are now
So that the graph meaning stays simple while the experience detail panel becomes richer

## Acceptance criteria

1. The graph view shows a fixed central node labeled `Profile Memory`.
2. The `Profile Memory` node does not change size based on activation.
3. Topic nodes remain visually separate from the center and continue to use activation-based sizing.
4. Experience nodes remain connected to topic nodes through the current edge model.
5. Clicking the `Profile Memory` node opens a detail view for profile memory rows.
6. Clicking an experience node opens a detail view for that experience memory row.
7. Both profile memory rows and experience memory rows support two views:
   - `Structured`
   - `Full Context`
8. `Structured` is the default view.
9. In `Structured` view, fields shown are limited to:
   - `Context`
   - `Action`
   - `Result`
10. The UI visually groups each structured memory under one outer bordered container representing one raw memory row.
11. `Full Context` view shows the original raw memory text for the same row.
12. The backend persists seeded profile memories separately from topic memory data.
13. The graph API returns enough data for the frontend to render the central profile node and the detail views for both profile and experience memory.

## Initial seeded profile memory

The initial profile memory seed should include these raw memory rows:

1. `My name is Yixin Li.`
2. `I got my bachelor degree with a double major in Philosophy and Computer Science from Colby College.`
3. `I like films, musicals, stage photography, and bouldering.`

The structured representation should use `Context`, `Action`, and `Result` only.

Example interpretation:

- Row 1
  - Context: personal identity information
  - Action: stated name
  - Result: Yixin Li identified as the person behind the portfolio

- Row 2
  - Context: educational background
  - Action: completed bachelor's degree with double major
  - Result: Philosophy and Computer Science background from Colby College

- Row 3
  - Context: personal interests
  - Action: shared long-term interests
  - Result: films, musicals, stage photography, and bouldering recorded as durable profile context

## Architecture overview

### Existing architecture to preserve

- `topics` remain the primary dynamic conceptual nodes
- `experiences` remain the graph units connected to topics
- `relevance_edges` continue to represent experience-to-topic relationships
- activation logic continues to apply to topic and experience graph behavior

### New architecture to add

- `profile_memories` becomes a separate durable memory store
- the graph API exposes a synthetic fixed `Profile Memory` node
- experience rows gain richer payload fields, but experience graph semantics do not change

### Data model direction

#### New table

`profile_memories`

Suggested fields:

- `memory_id`
- `title`
- `raw_context`
- `structured_json`
- `source`
- `confidence`
- `created_at`
- `updated_at`

#### Experience enrichment

Extend `experiences` with:

- `raw_context` — plain text string, the original memory passage
- `structured_json` — a single flat JSON object with exactly three string fields:

```json
{
  "context": "...",
  "action":  "...",
  "result":  "..."
}
```

The same schema applies to `profile_memories.structured_json`. Fields must always be present; use an empty string if a field is not applicable.

The current graph edge model should remain unchanged.

#### DB migration strategy

This is a demo/dev application. The migration approach is: delete the existing SQLite DB file and re-initialize from scratch with the updated schema and full seed data. No ALTER TABLE or backward-compatible migration is required.

### Retrieval and activation boundaries

- Profile memory should be durable and not activation-sized.
- Topic and experience memory should remain the dynamic graph layer.
- This task should not change graph activation logic except where needed to accommodate additional data fields.

## UI design direction

### Graph layout

- fixed center node: `Profile Memory`
- floating topic nodes around the center
- experience nodes rendered as smaller visual nodes, connected to their parent topic node by an edge, clickable to open the detail view

### Mobile layout

On mobile (height-encoded 2-column grid), the `Profile Memory` node appears as a pinned full-width row at the top of the grid, above the two topic columns. It does not participate in the height-encoding logic.

### Detail panels

Use one consistent detail pattern for profile memory rows and experience rows:

- outer bordered card = one raw memory row
- default tab/view = `Structured`
- secondary tab/view = `Full Context`

### Structured view

For now, structured mode should show only:

- `Context`
- `Action`
- `Result`

If a memory later supports multiple structured interpretations, all of them must remain visually grouped inside the same outer parent card.

### Full context view

Show the original raw memory text corresponding to that memory row.

## Expected file changes

Likely backend files:

- `backend/app/services/db.py`
- `backend/app/models/core.py`
- `backend/app/models/graph.py`
- `backend/app/services/retrieval.py`
- `backend/app/api/graph.py`

Likely frontend files:

- `frontend/graph.html`
- `frontend/assets/app.js`
- `frontend/assets/styles.css`

## Implementation process

### Step 1: Extend backend schema for profile memory and richer experiences

Goal:
Add durable profile memory storage and richer experience payload fields.

Success criteria:

- `profile_memories` table exists in DB init logic
- profile seed data (3 rows) is added with `structured_json` matching the pinned schema
- existing `experiences` seed data is re-seeded with `raw_context` and `structured_json` columns populated
- DB is wiped and re-initialized; no migration compatibility required

Risks:

- seed data for experiences must be authored manually since there is no LLM extraction pipeline

### Step 2: Extend graph API payload

Goal:
Expose data needed by the frontend for:

- fixed central profile node
- richer profile memory detail rows
- richer experience memory detail rows

Success criteria:

- `/graph` returns `profile_memories` array alongside the existing `topics`, `experiences`, and `edges` fields
- each experience object includes `raw_context` and `structured_json`
- each profile memory object includes `title`, `raw_context`, and `structured_json`
- existing `topics`, `experiences`, and `edges` keys are unchanged so the current frontend normalizer does not break

Risks:

- response shape changes breaking current frontend assumptions

### Step 3: Update graph rendering to include central profile node

Goal:
Render the profile memory node as a fixed center anchor while keeping topic and experience graph layout intact.

Success criteria:

- profile node is centered and fixed-size
- topic nodes remain activation-sized
- experience nodes still render from topic relationships

Risks:

- layout overlap
- loss of readability in smaller screens

### Step 4: Add unified memory detail UI

Goal:
Add a grouped memory detail interaction shared by profile and experience memories.

Success criteria:

- click interaction opens details for profile and experience nodes
- `Structured` view is default
- `Full Context` toggle works
- one outer border groups structured data under the same raw memory

Risks:

- UI complexity if graph and detail panel interactions compete

### Step 5: Visual polish and UX refinement

Goal:
Make the stable-vs-dynamic memory distinction legible and visually intentional.

Success criteria:

- profile node is visually distinct from topic nodes
- detail cards are easy to scan
- grouping hierarchy is obvious

Risks:

- overdesign that obscures the graph story

## Definition of done

- The graph shows a central fixed `Profile Memory` node.
- Topics and experiences still behave as graph entities the way they do today.
- Profile memory rows are seeded and viewable.
- Experience nodes support structured and full-context views without changing edge semantics.
- Structured mode defaults to `Context / Action / Result`.
- Each raw memory row is clearly grouped with its derived structured display.

