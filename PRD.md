# PRD — Interactive AI-Native Portfolio Exploration System

# 1. Product Overview

## Product Vision

Build an AI-native interactive portfolio experience that allows visitors to explore Yixin’s background through:

* an interactive topic graph to initiate first conversation topic
* direct conversational exploration with guided questions

The product should feel:

* exploratory,
* adaptive,
* conversational,
* visually alive,
* and curiosity-driven.

The system should NOT feel like:

* a static resume,
* a generic chatbot,
* or a traditional portfolio website.

---

# 2. Core Product Insight

Most first-time visitors do not know:

* what to ask,
* what are parts of Yixin’s background,
* or what topics are relevant to them.

Therefore:

* onboarding should not begin from a blank chat box,
* and users should not explicitly choose a persona ("i'm an engineer" or "i'm a hiring manager").

Instead:

* users begin from visually explorable topics,
* naturally self-select curiosity,
* and progressively build understanding and can jump across topics through exploration.

The system continuously:

* maintains conversational context,
* infers visitor interests,
* adapts follow-up suggestions,
* and guides toward appropriate next actions.

---

# 3. Product Goals

The system should help visitors:

* quickly understand who Yixin is,
* discover relevant areas of her background,
* explore topics interactively,
* build a coherent mental model of her experience,
* and naturally transition into professional interaction such as connecting on LinkedIn or send a message or schedule a chat.

The experience should optimize for:

* professional evaluation,
* networking,
* intellectual connection,
* and continued conversation.

---

# 4. Primary User Outcomes

## A. Professional Evaluation

Visitors want to:

* evaluate Yixin professionally,
* assess technical/product capability,
* understand role fit,
* and determine whether further discussion is worthwhile.

Typical outcomes:

* download resume
* scheduling a conversation.

---

## B. Professional / Intellectual Connection

Visitors want to:

* connect professionally,
* continue discussion,
* or discuss shared interests.

Typical outcomes:

* short free-form message.
* LinkedIn connection.

---

# 5. Core User Flow

# Step 1 — Landing Experience

The homepage centers around:

## Interactive Topic Graph

Center node:

### About Me

Connected topic nodes will include:

* AI Agents
* Memory Systems
* Evaluation & Benchmarking
* Startup & Entrepreneurship
* Software Development
* Product Management
* Academic Research
* Accessibility
* Photography & Videography
* AI Ethics & Philosophy

The graph immediately communicates:

* breadth of experience,
* interconnected interests,
* and exploratory interaction design.

---

# Step 2 — Topic Selection

Users begin by clicking a topic node.

Clicking a node:

* visually focuses/highlights the node,
* pre-fills a starter question in the chat input box below
* user hit the answer to start the conversation
* alternatively, they can directly input their questions without hitting any topic bubbles

Example:
User clicks:

### Memory Systems

Prefilled question:

> “What kind of memory systems did Yixin work on?”

Users may:

* send immediately,
* edit the question,
* or continue with custom wording.

This reduces:

* blank-page syndrome,
* onboarding friction,
* and cognitive load.

---

# Step 3 — Conversational Exploration

The AI responds with:

* concise contextual explanation,
* relevant experience/project context,
* Yixin’s role,
* what problems were being solved,
* and why the work mattered.

Responses should remain:

* third-person
* grounded,
* concise,
* contextual,
* and Yixin-centered.

The AI should avoid:

* textbook explanations,
* generic AI theory,
* or broad unrelated discussion.

Good:

> “At Continua AI, Yixin worked on retrieval-based memory systems for multi-user AI agents, including designing schemas for user/group context and evaluating retrieval correctness.”

Bad:

> “Memory systems are important because…”

---

# Step 4 — Suggested Follow-Ups

After each response, the system generates:

## A. Topic-specific follow-ups

Examples:

* How hands-on she is working on this?
* What was product vs technical?
* What are some decisions she made when owning the architecture?

AND

## B. Adjacent topic exploration

Examples:

* Evaluation & Benchmarking
* AI Agents
* Startup & Entrepreneur

This creates:

* conversational momentum,
* curiosity deepening,
* and exploratory navigation.

---

# Step 5 — Contextual CTA Surfacing

Persistent footer actions should always remain visible:

* Connect on LinkedIn
* Send Message
* Download Resume
* Schedule Time

In addition, the AI may mention a CTA inside the chat session once engagement is high enough.

---

## Evaluation-Oriented Signals

Examples:

* ownership questions,
* technical depth,
* impact,
* ambiguity,
* role fit.

Likely actions:

* Download Resume
* Schedule Time

---

## Connection-Oriented Signals

Examples:

* startup curiosity,
* shared interests,
* AI/product discussions,
* future directions.

Likely actions:

* Connect on LinkedIn
* Send Message

---

## CTA Mention Rules

The footer CTA area is always visible.

In-chat CTA mention rules:

* AI may mention a CTA only after meaningful engagement has happened in the session.
* Recommended threshold: after the visitor has sent at least 5 messages.
* AI may also mention a CTA earlier if the visitor explicitly asks about next steps, contact, resume, or scheduling.
* AI may mention a CTA at most once per chat session.
* If the user ignores or rejects the CTA, the AI must not mention it again in the same session.
* The AI should not interrupt an answer just to push a CTA.
* CTA mention should appear after the main answer, not before it.

---

# 6. Unified Conversational Session

All exploration for a visitor should occur inside:

## ONE persistent session.

Different topic explorations should NOT create separate conversations.

The AI should continuously maintain:

* explored topics,
* previous questions,
* conversational trajectory,
* inferred interests,
* graph state,
* and prior context.

This enables:

* coherent personalization,
* better follow-up generation,
* non-repetitive responses,
* and smoother conversational progression.

Example:
User explores:

* AI Agents
  → Memory Systems
  → Evaluation Infrastructure

The AI should understand:

> the visitor is likely interested in technical/system-oriented aspects of Yixin’s work.

---

# 7. Dynamic Topic Graph Visualization

The topic graph should evolve dynamically throughout the sessions.

The graph should visually represent:

* explored topics,
* discussion emphasis,
* and conversational relationships.

Potential dynamic behaviors:

* frequently explored nodes grow larger (but not obvious during session but accumulated after multiple users)
* recently explored nodes highlight

The graph acts as:

* visual memory,
* exploration history,
* and personalization surface.

---

# 8. Graph Weighting System

Graph state should NOT update purely based on mention frequency.

Instead:
node importance should be calculated through a weighted combination of:

1. topic clicks,
2. and conversational exploration.

---

## A. Topic Click Weight (High Weight)

Explicit node clicks represent:

> intentional curiosity.

Therefore clicks should carry significantly higher weight.

Examples:

* clicking “Memory Systems”
* clicking “AI Agents”
* clicking “Startup”

Possible weighting:

* initial click: +10
* repeated revisit: +4 to +6

Clicks strongly influence:

* node prominence,
* adjacent topic surfacing,
* and inferred visitor interests.

---

## B. Conversational Exploration Weight (Moderate Weight)

Conversation contributes softer reinforcement.

Signals include:

* follow-up questions,
* repeated references,
* semantic topic extraction,
* sustained discussion depth.

Possible weighting:

* direct follow-up: +2
* repeated mention: +1

This captures:

> evolving curiosity.

while preserving:

> initial exploration intent.

# Suggested Internal Node State

Each node may maintain:

* base_weight
* click_weight
* conversational_weight

This score influences:

* node size,
* highlight intensity,
* recommendation ranking,
* and graph centrality.

---

# 9. Core Actions

# A. Connect on LinkedIn

Open LinkedIn profile.

Optional:

* suggested connection message copy.

---

# B. Send Yixin a Message

Embedded free-form message flow that'll directly send to Yixin's set email.

Fields:

* Message

Important:
Users should optionally be able to:

## Include current conversation history.

Example checkbox:

> Include this conversation with my message

This allows Yixin to understand:

* explored topics,
* visitor interests,
* and prior conversational context.

This improves:

* continuity,
* personalization,
* and follow-up quality.

Privacy rule:

* session history is not stored persistently by default.
* session history is only included externally when the user explicitly checks:

> Include this conversation with my message

---

# C. Download Resume

One-click PDF download.

Potential future variants:

* AI PM
* Technical PM
* Startup-focused

---

# D. Schedule Time

AI will send out a link that users can click and find a slot on Yixin's calendar

---

# 10. AI Behavior Requirements

The AI should:

* maintain persistent conversational continuity,
* adapt to graph state,
* infer visitor curiosity from exploration behavior,
* provide concise grounded responses,
* encourage adjacent exploration,
* and surface contextual follow-ups.

The AI should NOT:

* behave like a generic chatbot,
* generate long textbook explanations,
* dominate the interface,
* or drift into unrelated open-ended discussion.

---

## Testable AI Constraints

The AI must:

* answer in third person.
* answer the visitor’s question before suggesting follow-ups.
* stay concise, typically within 2-5 sentences.
* stay grounded in Yixin’s actual memories and experiences.
* avoid generic textbook explanations unless directly necessary to answer context.
* avoid inventing details not supported by memory.

If relevant memory is weak or unavailable, the AI must say:

> I am not sure about this based on my memory about Yixin. Wanna ask something different?

Follow-up generation constraints:

* after each answer, the system may show adjacent follow-ups.
* follow-up suggestions should include at most:
  * 3 adjacent questions
  * or 3 adjacent topics
* follow-up suggestions should be relevant to the immediately preceding exchange.
* follow-up suggestions should not repeat the same CTA mention logic.

---

# 11. MVP Scope

## Included

* Interactive topic graph
* Dynamic graph visualization
* Weighted graph update system
* Shared persistent session
* AI-generated topic explanations
* Suggested follow-up questions
* Adjacent topic exploration
* LinkedIn CTA
* Resume download
* Messaging flow
* Scheduling integration
* Optional chat-history sharing

---

## Excluded (MVP)

* Long-term accounts
* Cross-session memory
* Autonomous agents
* Voice/avatar systems
* Real-time browsing
* Multi-user collaboration
* Advanced personalization infrastructure
* complex intent-modeling for CTA selection beyond explicit rules

---

# 12. Success Metrics

## Engagement

* average messages sent per user
* topic prefill interaction rate
* chat start rate
* 5-message completion rate

---

## Conversion

* LinkedIn clicks
* resume downloads
* messages sent
* scheduled conversations
* action completion rate

---

## Quality

* percentage of sent messages that include chat history
* repeat visitors
* inbound opportunity quality
* conversation continuation quality

---

## Success Metric Targets

Primary engagement goal:

* average messages sent per user >= 5

Core funnel counts:

* number of users who click a topic node and trigger prefill
* number of users who send their first message
* number of users who reach 5 messages
* number of users who complete at least one action:
  * LinkedIn click
  * send message
  * download resume
  * schedule time

---

## Explicit Event Definitions

### 1. `topic_prefill_clicked`

Fire when:

* a visitor clicks a topic bubble and the chat input is populated with a starter question.

Properties:

* `session_id`
* `topic_id`
* `topic_label`
* `prefill_text`
* `timestamp`

Used for:

* topic prefill interaction rate

---

### 2. `chat_first_message_sent`

Fire when:

* the visitor successfully sends their first chat message in the current session.

Properties:

* `session_id`
* `message_text`
* `message_length`
* `message_origin`
  * `topic_prefill`
  * `manual`
* `active_topic_id` if any
* `timestamp`

Used for:

* chat start rate

---

### 3. `chat_message_sent`

Fire when:

* any user message is successfully submitted to the chat backend.

Properties:

* `session_id`
* `message_index_in_session`
* `message_length`
* `message_origin`
  * `topic_prefill`
  * `manual`
* `active_topic_id` if any
* `timestamp`

Used for:

* average messages sent per user
* 5-message completion rate

---

### 4. `chat_depth_reached`

Fire when:

* the visitor reaches 5 total user-sent messages in the current session for the first time.

Properties:

* `session_id`
* `message_count`
* `timestamp`

Used for:

* 5-message completion rate

---

### 5. `cta_footer_clicked`

Fire when:

* the visitor clicks one of the persistent footer actions.

Properties:

* `session_id`
* `action_type`
  * `linkedin`
  * `send_message`
  * `download_resume`
  * `schedule_time`
* `message_count_before_action`
* `timestamp`

Used for:

* action completion rate
* per-action conversion counts

---

### 6. `message_sent_to_yixin`

Fire when:

* the visitor completes the embedded message flow successfully.

Properties:

* `session_id`
* `included_chat_history`
  * `true`
  * `false`
* `message_length`
* `message_count_before_send`
* `timestamp`

Used for:

* send message completions
* percentage of sent messages that include chat history

---

### 7. `resume_download_started`

Fire when:

* the visitor clicks the resume download action and the file download is initiated.

Properties:

* `session_id`
* `resume_variant`
* `message_count_before_action`
* `timestamp`

Used for:

* resume download conversions

---

### 8. `linkedin_profile_opened`

Fire when:

* the visitor clicks the LinkedIn action and the outbound link is opened.

Properties:

* `session_id`
* `message_count_before_action`
* `timestamp`

Used for:

* LinkedIn conversion count

---

### 9. `schedule_time_opened`

Fire when:

* the visitor clicks the scheduling action and the calendar link is opened.

Properties:

* `session_id`
* `message_count_before_action`
* `timestamp`

Used for:

* schedule-time conversion count

---
