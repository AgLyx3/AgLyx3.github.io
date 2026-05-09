# Yixin Li — Raw Experience (deduplicated, unconfirmed)
> Sources: all PDF resume variants + my-story-rough-notes.md.
> Bullets marked [RESUME] came from PDFs only. Narrative detail marked [NOTES] came from story notes only.
> Items marked [NEEDS FILL] have placeholder outcomes — confirm before using.
> Nothing removed for fit — this is the full inventory to cut from.

---

## Education

- **Colby College**, Waterville, ME — B.A. Computer Science + Philosophy, May 2025 — GPA 3.98/4

---

## Product Manager, Continua AI
**Dec 2025 – present**

### Delivery & Ownership
- Drove PRD-to-build execution across 3 initiatives (agentic tools, stored memory, evaluation systems) for the core AI agent, translating concepts into detailed PRDs and prioritized tickets, coordinating dependencies across 5 engineers.
- Communicated product direction to leadership across all three initiative areas.
- Collaborated cross-functionally with leadership and go-to-market teams on marketing briefs, influencer recruitement, feature launches, and external communications (interviews with reporters).

### Memory Systems — Build Memory Architecture [NOTES]
- Built per-channel memory first (summary of previous conversation history, make inference to identify users with numbers (because users may use different names in group chat we want to make sure we know who we're addressing to and not cause confusion by conversation in group chat, high level interest/goal/identified opportunity for proactivity)), then redesigned to per-user memory (more fine grained than channel memory, privacy boundary across different categories of memory) to fix signal mixing and improve retrieval precision.
- Problem with per-channel: memory mixed signals from multiple users, accumulated context was not reusable across contexts, retrieval precision was weaker because the storage unit was the channel rather than the user.
- Core tradeoff: originally designed a more fine-grained data structure, but engineering estimated 1–2 extra weeks; prioritized a faster first version while setting clear quality guardrails.
- Built prompts and evaluation cases before development finished to define success criteria up front; used testing results to identify when quality was not acceptable and justify iteration.
- Defined success metrics and rollout plan before launch; aligned engineers working across memory and memory evaluation despite parallel project demands.
- [NEEDS FILL] Outcome: what changed in product quality, user experience, or launch timing.

### Agentic Poll Feature [NOTES — not in any resume]
- Built an agentic poll feature in a conversational AI product, allowing users to create and run polls in natural language.
- Core design problem: conversational input was ambiguous by default; had to distinguish between chatting, creating a poll, editing a poll, and voting — with risk of intent conflict with another agentic feature.
- Key product decisions: context-based options vs. free input; default to single vs. multiple choice; one active poll vs. multiple; poll close authority; what counts as a valid vote; reporting format.
- Wrote PRDs with required input, optional input, defaults, voting rules, reporting rules, and specific conversational examples; defined core interaction model: start, edit, vote, change vote.
- Maintained a running list of prioritized test cases; tested gradually from 2-person to 7-person groups; paired rollout with operational monitoring through the issue viewer board.
- [NEEDS FILL] Outcome: what launched, what failure rate decreased, what adoption data showed.

### Agentic Split / Sheet Feature [NOTES — not in any resume]
- Built another conversational AI workflow feature; good example of translating a fuzzy interaction into an implementation-ready spec.
- Core decision: chose to optimize the in-chat experience rather than a deeper Google Sheets integration based on interface and primary workflow fit.
- Clarified initialization logic, follow-up question logic, and when itemization should happen; updated PRD to be LLM-readable and specific enough that the model was not inventing behavior.
- Sat down with engineers to walk through each decision point rather than leaving ambiguity in the PRD.
- [NEEDS FILL] User pain context and outcome: what user workflow got easier or faster, what shipped.

### Evaluation & Benchmarking [RESUME + NOTES]
- Designed evaluation frameworks for production LLM systems to benchmark retrieval recall, precision, and consistency; defined structured and adversarial test cases to diagnose privacy leakage and edge-case failures.
- Owned evaluation and benchmarking for memory and latency (RAG recall/precision, memory usage correctness, TTFT/E2E latency).
- Selected and ran public external memory benchmarks — specifically **LoCoMo** and **EverMemBench** — evaluated which dimensions were most relevant to the product, configured setup, and used results to compare retrieval/memory strategies and identify tradeoffs.
- Designed internal test cases reflecting real product behavior that external benchmarks would miss; defined what success meant for the product, not just for a benchmark; validated whether external benchmark gains translated into better user experience.
- Defined structured evaluation test cases (LLM-as-judge, prompt-based) to assess model behavior under realistic scenarios, surfacing failure modes not captured by standard benchmarks.
- Used evaluation outputs to drive alignment on what to build, tune, or ship next; worked with engineering and research on instrumentation and experiment design.
- [NEEDS FILL] Outcome: what memory setup or product decision evaluation changed; what prevented a bad launch or accelerated iteration.
- Reduced edge-case failures by ~20% in internal testing by diagnosing system issues and prioritizing fixes through structured issue tracking.

### Prompt Engineering & AI Reliability
- Led prompt engineering experimentation for stored memory, iterating on system prompts and evaluation criteria to improve task completion consistency and reduce edge-case failures by ~20%.
- Improved reliability of AI agent by ~25% by designing evaluation frameworks to systematically reproduce failure modes and partnering with engineering to refine prompt logic and system behavior.

### Issue Viewer [RESUME + NOTES]
- Built and improved an internal issue viewer/observability tool serving both PMs and engineers with different use cases.
- Regularly monitored error rates; investigated logs and model outputs to identify false positive cases that were inflating apparent error rates.
- Diagnosed and resolved tool quality failures by analyzing false positives, redesigning issue bucketing logic (decision: fixed buckets vs. LLM-generated buckets), and iterating on prompts.
- Proposed grouping issues by user groups; used data to plan fixes and evaluate whether changes were effective.
- [NEEDS FILL] Outcome: what changed in issue quality, prioritization, or team behavior; what specific fix or bucket change was adopted.

### Metrics & Data
- Defined and operationalized success metrics (activation rate, error rate, group conversion) across 3 initiatives; queried product data using BigQuery (SQL) and Python on GCP to surface insights and guide iteration.
- Analyzed and synthesized 20+ weekly customer feedback items to surface recurring usability issues and inform high-impact product fixes.
- Conducted ongoing discovery with 10+ customers to identify workflow gaps, shaping customer segmentation and feature prioritization.

### Go-to-Market
- Shaped early go-to-market narrative by drafting the initial marketing brief, evaluating 10+ agencies and influencer partnerships, and aligning PR messaging for launch; supported 3+ external outreach and feature announcements, participated in press interviews.

### Engineering & Tooling
- Built customer-facing onboarding flows and internal AI tooling using React, TypeScript, and Python, rapidly prototyping workflows from customer feedback.
- Partnered with product and design to implement frontend components and event tracking and logging.

---

## Product Intern, Continua AI
**Jun 2025 – Nov 2025**

### User Research & Segment Decisions [RESUME + NOTES]
- Conducted 2 multi-round user research studies across 4 segments (n≈40), identifying low-fit segments and narrowing target ICP, directly influencing roadmap prioritization for 1 key initiative.
- Ran dedicated user interviews targeting professional users to explore PMF hypothesis: that the pain point was lost or chaotic context, and the product might help with scheduling workflows.
  - Defined user segments, created screening form, recruited users, ran interviews.
  - Learned: field workers had scheduling tasks but most important work happened through real-time communication handled in the moment; users with formal scheduling tasks already had dedicated tools with high integration expectations.
  - Decision: killed that user segment.
  - [NEEDS FILL] How many interviews; what evidence threshold led to the decision; what happened next.
- Redesigned onboarding flows for multi-user AI collaboration product, improving early user engagement by ~20% through rapid prototyping and iteration.

### Tooling & Prototyping
- Built 3 interactive prototypes and authored 5+ frontend/prompt improvements to refine onboarding; developed 1 internal tool that reduced manual workflows, improving team efficiency by ~10%.
- Implemented onboarding prompt workflows for distinct user segments, iterating on agent behavior and interaction design to improve user activation and feature discovery.

### Conversation Topic Clustering Tool [RESUME + NOTES]
- Built a topic clustering tool by extending an existing internal tool — talked with the engineer who built the original, identified an opportunity to extend it, aligned on algorithms and approaches with senior engineers, implemented using AI-assisted development.
- Used for internal observability and also for external communication with reporters.
- [NEEDS FILL] What manual process it replaced or accelerated; what measurable value it created.

### Process Improvement — Asana Migration [NOTES — not in any resume]
- In first month as intern, pushed the team to move from Google Docs (used for 2 years) to a real project management tool to improve visibility into issue status, ownership, and priority.
- Stakeholder constraint: CEO strongly preferred Google Docs; behavior change required preserving parts of the existing workflow.
- Gathered opinions through 1-on-1s; used a prototype to demonstrate benefits rather than argue abstractly; moved issues into Asana but used the Asana plugin inside Google Docs so the document stayed familiar while exposing status, owner, and priority. Migrated step by step instead of forcing a full switch.
- [NEEDS FILL] Whether the team moved fully or partially to Asana; what improved in execution or visibility.

### QA & Operations
- Owned daily QA testing; triaged 20+ weekly customer feedback items, identifying recurring usability issues and partnering with engineering to reduce post-release bugs and improve product stability.

---

## Machine Learning Intern, The Jackson Laboratory
**Jan 2025 – May 2025**

- Built an end-to-end ML pipeline for transcription, speaker diarization, and post-processing, leveraging LLMs to generate structured clinical summaries and recommendations from raw audio data.
- Improved genomic tumor boards meeting transcription accuracy by 15% and projected to save $24K/year by minimizing third-party correction costs via model tuning and prompt optimization.
- Evaluated multiple transcription evaluation methods (F1, fuzzy string-matching, WER, CER) and prioritized domain-specific WER/CER metrics to improve medical terminology validation across 15+ hours of clinical recordings.
- Collaborated with clinicians, program managers, and AI researchers to conduct data-driven validation across multiple audio and transcripts, experimenting with various speech-to-text models.

---

## Founder, InclusiM
**Oct 2024 – May 2025**

### Fundraising & Recognition
- Secured $5,000 in funding and placed 2nd at the Maine Startup Challenge; pitched on Greenlight Maine TV show.

### Discovery
- Assessed existing accessibility auditing tools through competitive analysis and conversations with developers and business owners, identifying unmet needs in integrating accessibility into existing workflows.
- Conducted 20+ customer discovery interviews to validate problem–solution fit.

### Build & Launch
- Built and deployed a multi-platform MVP: web application + Figma plugin + VS Code extension, using the MERN stack; embedded WCAG principles from the design phase.
- Integrated Docker, CI/CD workflows, and Pytest into the development pipeline; achieved 90% test coverage.
- Validated core user workflows in partnership with Colby Communications.

### Validation & Iteration
- Designed and ran A/B tests with 155 participants, driving a 10% lift in Lighthouse scores and higher audit click-through rates.
- Conducted user interviews with 3+ accessibility experts to identify workflow and integration gaps.

---

## Research Assistant, Computer Science Department, Colby College
**Oct 2023 – May 2025**

### User Research (Accessibility)
- Designed and ran 20+ user interviews with sighted and blind/low-vision users, synthesizing qualitative and quantitative insights to inform design decisions.
- Led 10+ usability studies comparing eye-tracking data correction methods, guiding non-technical participants through technical setups and translating findings into system improvements.

### ML & NLP
- Developed and optimized NLP pipelines using BERTTopic and spaCy for topic extraction and semantic clustering.
- Improved health prediction model performance to AUC 0.90 through systematic feature selection and processing of 20+ health datasets using scikit-learn.

---

## Skills (union across all variants)

**AI / Product**
0→1 product development, PRDs, roadmapping, user research, experimentation & A/B testing, model evaluation, prompt engineering, RAG, agentic systems, LLM-as-judge, privacy-aware AI design, LLM fine-tuning, adversarial testing, benchmarking

**Technical**
Python, SQL (PostgreSQL, MySQL), JavaScript/TypeScript, React, Node.js, REST/gRPC APIs, GraphQL, TensorFlow, PyTorch, scikit-learn, NLTK, spaCy, Transformers, LangChain, BERTTopic, BigQuery, pandas, NumPy, Docker, CI/CD, GCP, AWS, Kubernetes, Git

**Product & Design Tools**
Figma, Jira, Linear, Asana, Agile/Scrum, Accessibility (WCAG), event tracking & logging, activation & conversion analysis
