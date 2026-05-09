# Yixin Li — Raw Experience

---

## Education

- **Colby College**, Waterville, ME — B.A. Computer Science + Philosophy, May 2025 — GPA 3.98/4

---

## Product Manager, Continua AI
**Dec 2025 – present**

- Drove PRD-to-build execution across 3 AI agent initiatives (agentic tools, stored memory, evaluation systems), translating concepts into detailed PRDs and prioritized tickets, coordinating dependencies across 5 engineers. {tags: pm:1.0, ai-agents:0.6, eval:0.3}
- Communicated product direction to leadership across all three initiative areas; collaborated cross-functionally with go-to-market teams on marketing briefs, influencer recruitment, feature launches, and press interviews. {tags: pm:1.0}
- Built per-channel memory for a group conversational AI product that tracks shared context, infers user identities across a channel, and identifies each user's interests and the group's shared goals — making the agent more proactive and contextually relevant. {tags: memory:1.0, ai-agents:0.6, pm:0.3}
- Added a per-user memory layer on top of channel memory, giving the agent finer-grained per-person memory that persists across conversations — fixing signal mixing inherent in channel-level summaries, improving retrieval precision, and enabling cross-channel personalization through a privacy gate that controls what carries over. {tags: memory:1.0, ai-agents:0.6, pm:0.3}
- Navigated a speed-vs-quality tradeoff in memory architecture: chose to ship a faster first version when the ideal fine-grained design would have added 1–2 weeks, while setting explicit quality guardrails and a clear iteration path. {tags: pm:1.0, memory:0.6}
- Built evaluation test cases and prompts before memory development finished to define success criteria up front; used pre-launch testing to identify gaps between implementation and production requirements, preventing an unqualified launch. {tags: eval:1.0, memory:0.6, pm:0.3}
- Memory outcome: improved memory eval scores, passed local privacy test cases, and validated the path to the more fine-grained data architecture in a follow-on iteration. {tags: memory:1.0, eval:0.6}
- Designed and shipped an agentic polling feature enabling users to create, vote on, and manage polls through natural language; resolved the core design challenge of distinguishing chat, poll creation, editing, and voting without conflicting with a concurrent agentic feature. {tags: ai-agents:1.0, pm:1.0}
- Defined key polling product decisions up front — context-based vs. free input, single vs. multiple choice defaults, concurrent poll support, close authority, valid vote definition, and reporting format — specified in PRDs with annotated conversational examples. {tags: pm:1.0, ai-agents:0.6}
- Staged the poll rollout from 2-person to 7-person groups while maintaining a prioritized test case list; paired launch with live monitoring through the issue viewer. {tags: pm:1.0, ai-agents:0.3}
- Poll outcome: soft-launched to reporters interested in the feature for early feedback. {tags: pm:0.6, ai-agents:0.3}
- Designed a conversational expense-splitting feature letting users request a multi-person split in plain text, with a Google Sheets-backed tracking sheet generated automatically — eliminating the need for third-party apps or manual receipt forwarding. {tags: ai-agents:1.0, pm:1.0}
- Made the core split/sheet product decision to optimize for the in-chat workflow over a deeper Google Sheets integration; wrote the PRD to be LLM-readable and precise enough that the model was not inventing behavior, and walked through every decision point with engineers directly. {tags: pm:1.0, ai-agents:0.6}
- Owned evaluation frameworks for production LLM systems covering memory quality (RAG recall/precision, memory usage correctness) and latency (TTFT/E2E latency). {tags: eval:1.0, memory:0.6, ai-agents:0.3}
- Replaced a single aggregate latency metric with task-specific latency buckets — recall tasks (memory tool calls), generate tasks (documents or images), and pure responses with no tools — giving the team clearer signal on where agent performance needed improvement. {tags: eval:1.0, ai-agents:0.6}
- Selected and ran external memory benchmarks LoCoMo and EverMemBench; evaluated which dimensions were most relevant to a multi-person conversational product, configured matched setups, and used results to compare retrieval and memory strategies. {tags: eval:1.0, memory:1.0}
- Designed internal evaluation test cases reflecting real product behavior that external benchmarks would miss; validated whether gains on external benchmarks translated into better user experience; reduced edge-case failures by ~20% in internal testing. {tags: eval:1.0, memory:0.6}
- Evaluation outcome: results drove a shift from a prompt-driven memory approach to a more fine-grained architecture, and surfaced incorrect benchmark numbers circulating internally that were corrected before external communication. {tags: eval:1.0, memory:0.6}
- Built and iterated on an internal observability tool (issue viewer) for PMs tracking product quality and engineers debugging failures; identified false positives inflating apparent error rates by ~25%, bringing the dashboard significantly closer to reality. {tags: eng:0.6, eval:0.6, pm:0.6}
- Redesigned the issue bucketing system from daily LLM-generated buckets (which caused semantically similar errors to land in different buckets across days) to an inheritance-based update model, making grouping stable and comparable over time. {tags: eng:0.6, eval:0.6, ai-agents:0.3}
- Issue viewer outcome: error rate dropped ~25% after false positive removal; engineers adopted the tool for daily debugging; issue grouping became consistent enough to track trends week over week. {tags: eng:0.3, eval:0.3, pm:0.3}
- Conducted ~10 customer discovery interviews with startup employees, segmented by role — operators and coordinators (PMs, tech leads, ops) vs. engineers — to explore pain points around AI tool use and identify coordination and execution gaps; used findings to narrow the ICP. {tags: pm:1.0, research:0.3}
- Defined and operationalized success metrics (activation rate, error rate, group conversion) across 3 initiatives; queried product data using BigQuery and Python to surface insights and guide iteration. {tags: pm:1.0, eval:0.3}
- Shaped early go-to-market narrative by drafting the initial marketing brief, evaluating 10+ agencies and influencer partnerships, and aligning PR messaging across 3+ external announcements and press interviews. {tags: pm:0.6}
- Built customer-facing onboarding flows and internal AI tooling using React, TypeScript, and Python; implemented frontend components and event tracking to measure user interaction patterns. {tags: eng:1.0, pm:0.3}

---

## Product Intern, Continua AI
**Jun 2025 – Nov 2025**

- Conducted 2 multi-round user research studies across 4 segments (n≈40), identifying low-fit segments and narrowing the target ICP, directly influencing roadmap prioritization for 1 key initiative. {tags: pm:1.0, research:0.6}
- Ran 5 user interviews to test whether the product could serve professional scheduling workflows; found that field workers handled coordination in the moment through real-time communication rather than structured task tracking, while users with formal scheduling needs already had dedicated tools and high integration expectations — killed the segment. {tags: pm:1.0, research:0.6}
- Redesigned onboarding flows for the multi-user AI collaboration product through rapid prototyping and iteration with engineering, improving early user engagement by ~20%. {tags: pm:1.0, eng:0.3}
- Built 3 interactive prototypes and authored 5+ frontend and prompt improvements to refine onboarding; developed 1 internal tool that reduced manual workflows, improving team efficiency by ~10%. {tags: eng:0.6, pm:0.6}
- Extended an existing internal analytics tool into a topic clustering system — identified the opportunity, aligned with the original engineer on algorithms and approach, and implemented using AI-assisted development; reduced the effort to share user conversation trends with reporters from a multi-step manual process to a single click, and used it internally for product observability. {tags: eng:1.0, pm:0.6}
- Identified that the team had tracked all work in Google Docs for two years, limiting visibility into status, ownership, and priority; built alignment through 1-on-1s, demonstrated value with a working prototype, and introduced Asana via its Google Docs plugin to reduce behavior change friction — team migrated fully within a week. {tags: pm:1.0}
- Owned daily QA testing; triaged 20+ weekly customer feedback items, identified recurring usability issues, and partnered with engineering to reduce post-release bugs and improve product stability. {tags: pm:0.6, eng:0.3}

---

## Machine Learning Intern, The Jackson Laboratory
**Jan 2025 – May 2025**

- Built an end-to-end ML pipeline for transcription, speaker diarization, and post-processing of genomic tumor board meetings, using LLMs to generate structured clinical summaries from raw audio. {tags: eng:1.0, research:0.3}
- Improved transcription accuracy by 15% through model tuning and prompt optimization, reducing reliance on third-party correction tools and projecting $24K/year in savings. {tags: eng:0.6, eval:0.3}
- Designed and ran evaluation experiments across F1, fuzzy string-matching, WER, and CER; selected domain-specific WER/CER as the primary framework to improve validation of specialized medical terminology across 15+ hours of clinical recordings. {tags: eval:1.0, research:0.6}
- Collaborated with clinicians, program managers, and AI researchers to validate model outputs and iterate on system performance in a production-facing clinical workflow. {tags: research:0.6, eng:0.3}

---

## Founder, InclusiM
**Oct 2024 – May 2025**

- Secured $5,000 in funding and placed 2nd at the Maine Startup Challenge; pitched on the Greenlight Maine TV show. {tags: startup:1.0}
- Identified unmet needs in accessibility tooling through competitive analysis and 20+ discovery interviews with developers and business owners; validated problem–solution fit before building. {tags: startup:0.6, access:0.6, pm:0.3, research:0.3}
- Built and deployed a multi-platform accessibility auditing MVP — web application, Figma plugin, and VS Code extension — using the MERN stack, embedding WCAG principles from the design phase and validating core workflows in partnership with Colby Communications. {tags: eng:1.0, access:1.0, startup:0.6}
- Integrated Docker, CI/CD, and Pytest into the development pipeline; achieved 90% test coverage. {tags: eng:1.0, startup:0.3}
- Designed and ran A/B tests with 155 participants, driving a 10% lift in Lighthouse scores and higher audit click-through rates; conducted additional interviews with 3+ accessibility experts to identify workflow and integration gaps. {tags: research:0.6, access:0.6, startup:0.3}

---

## INSITE Lab Research Assistant, Colby College
**May 2024 – May 2025 | Mentor: Dr. Stacy A. Doore**

- Designed interactive VR visualizations of Gulf of Maine seafloor data to support stakeholder engagement in offshore wind farm siting decisions. {tags: research:1.0, eng:0.3}
- Conducted 20+ interviews with blind and low-vision participants to inform the design of an NLP-powered spreadsheet interface for accessible data interaction; analyzed transcripts using NLP-assisted methods to identify patterns in how participants interact with data tools. {tags: research:1.0, access:1.0}
- Poster: "Virtual Offshore Wind Turbines: Mooring Line Design Evaluation by Gulf of Maine Commercial Fishing Stakeholders." Colby Undergraduate Summer Research Retreat, 2024. (with Yuyang Wang) {tags: research:0.6}

---

## Research Assistant, Colby College
**Oct 2023 – May 2025 | Mentor: Dr. Naser Al Madi**

- Conducted 10+ usability studies comparing eye-tracking fixation correction methods, analyzing how different correction techniques influence data interpretation in reading research; benchmarked four existing correction tools and documented methodological trade-offs in a 40-page technical report. {tags: research:1.0}
- Designed experimental setups using PyGaze to investigate how users interpret and develop trust in outputs generated by large language models. {tags: research:1.0, eval:0.3}
- Publication: "Combining Automation and Expertise: A Semi-automated Approach to Correcting Eye Tracking Data in Reading Tasks." *Behavior Research Methods*, 2025. (with Al Madi, Torra, Tariq) {tags: research:1.0}

---

## Summer Research Assistant, Colby College
**May 2024 – Aug 2024 | Mentor: Dr. Isaac Lage**

- Designed surveys and collected responses from 200+ participants to study how human knowledge and contextual information influence trust in AI predictions; analyzed results using statistical methods. {tags: research:1.0, eval:0.3}
- Curated and integrated data from 20+ public datasets; conducted feature selection and evaluation experiments on incorporating human knowledge into ML model predictions. {tags: research:1.0, eng:0.3}
- Publication: "User Studies in Human-Feature-Integration." *ACM Conference on Intelligent User Interfaces (ACM IUI)*, 2025. (with Lefebvre, Parbhoo, Doshi-Velez, Lage) {tags: research:1.0}
- Presentation: "Designing Human Experiments for Integrating Human Features into Machine Learning." Colby Undergraduate Summer Research Retreat, Blitz Section, 2024. {tags: research:0.6}

---

## Independent Research

- Conducted an interdisciplinary analysis of moral-dilemma benchmarks in AI, mapping human moral decision factors (cognitive, emotional, socio-cultural) to technical alignment mechanisms (rule-based, RLHF, hybrid); produced a working paper evaluating benchmark validity for moral decision-making in LLMs. (2025) {tags: ethics:1.0, research:0.6, eval:0.3}
- Analyzed the legal and ethical landscape of AI-generated art — copyright frameworks, training data ownership, deontological and utilitarian ethics — and developed governance proposals including updated IP definitions, ethical dataset standards, and a consent registry for artists. (2023) {tags: ethics:1.0, research:0.6}
