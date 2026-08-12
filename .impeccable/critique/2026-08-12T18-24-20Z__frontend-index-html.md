---
target: the page (index, portfolio, chat)
total_score: 22
max_score: 36
na_heuristics: 10
p0_count: 0
p1_count: 3
timestamp: 2026-08-12T18-24-20Z
slug: frontend-index-html
---
⚠️ DEGRADED: single-context (session rule forbids spawning sub-agents; Assessment A and B run sequentially in one context)

Target: `frontend/index.html`, `frontend/portfolio.html`, `frontend/chat.html`
Browser visualization: unavailable (Playwright not installed in this repo). No user-visible overlay was injected.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Chat is strong (typing dots, sr-only "thinking", `Sending…`, retry button). Portfolio filter gives zero feedback: no result count, no live region, no empty state. |
| 2 | Match System / Real World | 3 | "Yixin.exe" as the assistant's name is cute-jargon. Bubble `activation` scores (8.5, 6.2…) are unexplained numbers. "trained on my work" is inaccurate for a retrieval system. |
| 3 | User Control and Freedom | 2 | `index.html` sets `body { overflow: hidden }` with a `position: fixed` footer — on a short viewport the content clips with no scroll escape. Portfolio filters keep no URL state, so Back doesn't restore them. |
| 4 | Consistency and Standards | 2 | Tokens are triplicated across three files and have drifted from `DESIGN.md` (`--forest` is `#6E86AB` in the doc, `#536C89` in code). Index cards are borderless nebula glows; portfolio cards are bordered glass. Index has no topbar nav; the other two do. `aria-pressed` on the theme toggle only exists in chat.html. |
| 5 | Error Prevention | 2 | Message modal submits with `novalidate` and an empty textarea silently returns — pressing Send does nothing and says nothing. |
| 6 | Recognition Rather Than Recall | 3 | Index has no navigation at all; the two doors are the only way in and there's no signal the site has exactly two places. |
| 7 | Flexibility and Efficiency | 2 | Enter-to-send is present and hinted (good). No filter deep-links, no keyboard path into voice mode. |
| 8 | Aesthetic and Minimalist Design | 2 | Four simultaneous decorative background systems (starfield, milky-way band, meteors, floating dots) plus glass cards, plus a mono-caps eyebrow on nearly every unit. Content is clean; chrome is loud. |
| 9 | Error Recovery | 3 | The chat cold-start message is genuinely good: names the cause, sets an expectation, offers a Try again button. Portfolio filter has no empty state. |
| 10 | Help and Documentation | n/a | Personal portfolio; no docs surface exists or is expected. |
| **Total** | | **22/36** | **Acceptable (61%)** |

## Design Specificity Verdict

**LLM assessment.** Split verdict across the three surfaces.

`chat.html` is genuinely specific. Bubbles-as-memory-topic-nodes, sized by activation, floating on a D3 force simulation, and doubling as conversation entry points — that is a real idea that belongs to this product and could not be lifted onto another site unchanged. It's the strongest thing here.

`index.html` and `portfolio.html` are category-interchangeable. Swap the name and the copy and they are any AI-adjacent portfolio shipped in the last eighteen months: centered hero, symmetric card pair, dusty-blue-on-warm-paper, Playfair for the serif voice, a mono for every label, glassmorphic cards on a starfield. Nothing in the composition of those two pages is downstream of what Yixin actually builds.

The deepest problem is that the composition doesn't inherit the one good idea. The chat page invented a visual language (soft radial orbs, no hard edges, physics-driven placement) and then the landing and portfolio ignored it in favour of stock cards. The landing page even carries the fossil: `.door` is fully styled as a glass card at line 112, then completely overridden with `!important` into a nebula glow at line 176. The nebula was bolted onto a card that's still in the file.

**Deterministic scan.** `detect.mjs` returned 6 findings across 4 files, exit code 2:
- `overused-font` × 4 — Geist Mono in `assets/styles.css:1`, `chat.html:26`, `index.html:24`, `portfolio.html:20`
- `dark-glow` × 2 — zero-offset chromatic box-shadow on `#536c89` at `chat.html:1075` and `index.html:188`

Both are true positives. The detector under-reports here: it doesn't catch eyebrow density, separator abuse, decorative status pips, or the total absence of imagery, which are the bigger tells on this site.

## Overall Impression

The writing is better than the design. Card copy on the portfolio describes real mechanisms — Bayesian 2PL IRT over heterogeneous items, DBSCAN over `all-MiniLM-L6-v2`, per-turn Blocking vs Trusted scoping. That is specific, verifiable, and far above the empty-adjective norm for portfolio copy. It is being served inside chrome that reads as generated.

The single biggest opportunity: the site has zero images. Three pages, seven projects, one published paper, one live agent, and not a single screenshot, figure, plot, or photograph. There are even two unused spot illustrations sitting in `assets/`. A portfolio that shows no work is the loudest possible signal that a page was written rather than designed, and it's the fix with the highest ratio of perceived-craft to effort.

## What's Working

1. **The palette is not a default.** Warm paper `#F8F4EE` against deep navy `#0B1024` with a dusty editorial blue accent is a real, considered pairing. It is not slate-900 + indigo-500. Keep it.
2. **The bubble metaphor.** Memory topics as force-simulated orbs, sized by activation, clickable into a prefilled question. It's a product idea expressed as an interface, which is what design specificity actually means.
3. **Motion discipline at the edges.** Every page has a blanket `prefers-reduced-motion` override, chat has a skip link, Escape closes the modal, and the cold-start error message is well written. The accessibility floor is higher than the surface suggests.

## Priority Issues

### [P1] Three type registers make the page read as generated
Playfair Display carries body copy at 14.5px, Geist Mono carries every kicker, tag, button, nav link and footer, and Autumn Brush carries the name. That specific triad — a high-contrast Didone serif for "editorial", a mono for "technical", a script for "personal" — is the most recognizable AI portfolio signature there is. Playfair in particular is on every list of LLM-favourite display serifs, and it is fragile at 14.5px because it's a display face being asked to do body work.

**Fix:** Cut to two. Move body and card copy to a sans display/text family with character (PP Neue Montreal, ABC Diatype, GT Walsheim, Söhne, Cabinet Grotesk). Keep one accent face and give it exactly one job. If the serif stays, it should set headlines only, and it should not be Playfair. Retire Geist Mono from UI chrome entirely — mono-for-labels is itself the tell, independent of which mono.

**Suggested command:** `/impeccable typeset`

### [P1] The page has no images
Seven projects, a published paper in *Behavior Research Methods*, a live agent, a benchmark with an IRT ability model, and every card is text + a hand-drawn SVG glyph + tag pills. `assets/spot-desk-laptop.svg` and `assets/spot-robot.svg` are in the repo and unused.

**Fix:** One real visual per card, at minimum for the top three. A screenshot of the Jupyter editor mid-edit. The IRT ability curve or the score distribution from the benchmark. A cluster scatter from the DBSCAN tool. A Fix8 before/after drift correction — that one is inherently visual and is currently described in prose. Give the lead project a full-width slot with a real image instead of the uniform 2-column grid.

**Suggested command:** `/impeccable layout`

### [P1] Mono-caps eyebrows and middle-dots on everything
Mechanical count against the ≤ ceil(sections/3) rule:
- `index.html`: 2 `.door-kicker` (`ASK ANYTHING`, `SEE THE WORK`) + an uppercase tracked footer, on a one-section page. Budget: 1.
- `portfolio.html`: `SELECTED WORK · 2023–2026` head-kicker + 7 `.card-status` pills in the same uppercase-mono-tracked signature.

The middle dot compounds it. `Yixin Li · 2026 · Email · GitHub · LinkedIn` appears on all three footers; the chat landing footer runs five of them; the portfolio kicker uses one more. The rule is max one per line. `2023–2026` also uses an en-dash where a hyphen belongs.

**Fix:** Delete `ASK ANYTHING` and `SEE THE WORK` outright — the door titles already say what they are. Delete `SELECTED WORK · 2023–2026`; `What I've built.` is the section label. In footers, replace the dot chain with spacing or a hairline.

**Suggested command:** `/impeccable distill`

### [P2] Four decorative background systems, none motivated
`index.html` simultaneously runs a 150-span twinkling starfield, a blurred rotated milky-way band, periodically spawned meteors, and 14 drifting light-mode dots. `portfolio.html` runs the starfield too. None of it says anything about the work, and the cosmic-gradient family is itself a strong AI signature. It's also 150+ absolutely-positioned animated elements on first paint.

**Fix:** Pick one and make it mean something. The obvious candidate: reuse the chat page's bubble field as the shared ambient layer across all three pages, so the background is the memory graph rather than generic space. That converts decoration into identity and unifies the site in one move. Drop the meteors and the milky-way band.

**Suggested command:** `/impeccable quieter`

### [P2] Accent color and shape systems are not locked
Portfolio status pips introduce green `#3f8256` and purple `#78579a` alongside the blue accent — three accent colors on a page that declares one. The pips themselves are decoration, not state: "Open Source" and "Benchmark" are categories, not live status, and they already duplicate the tag row below. Shape is also inconsistent: index doors are borderless (radius 0 with a blurred radial glow), portfolio cards are 20px glass, icon tiles are 12–14px, links and filters are pills.

**Fix:** Delete the `.pip` dots. Render status as plain small text in the single accent, or fold the category into the existing tag row. Then pick one radius scale and apply it everywhere.

**Suggested command:** `/impeccable polish`

### [P2] Copy has LLM cadence and factual slack
Specific strings:
- "I build products at the intersection of Human and AI." — "at the intersection of" is stock LLM connective tissue, and the line is duplicated verbatim on `index.html` and the `chat.html` landing.
- "Wander through the things I've made: working code, live demos, papers, prototypes, and everything in between. Come have a look." — a colon-led list of five plus "and everything in between" plus "Come have a look" is three filler moves in one sentence.
- "A conversational agent trained on my work… It answers in real time." — it retrieves, it isn't trained. "In real time" adds nothing.
- Portfolio stacks three restatements: kicker `SELECTED WORK`, headline `What I've built.`, body `Selected work I've built — AI benchmarks, memory evaluations…`, which also duplicates the `<meta name="description">` verbatim.
- 6 em-dashes in visible copy (1 in `index.html`, 5 in `portfolio.html`), plus the chat error string.
- "Yixin.exe" as the assistant role label.

**Fix:** Rewrite the tagline to a concrete claim about what you build. Cut the portfolio subhead entirely — the headline and the cards carry it. Replace every em-dash with a period, comma, or colon. Rename `Yixin.exe`.

**Suggested command:** `/impeccable clarify`

### [P3] Accessibility and platform gaps
- `portfolio.html` has no `:focus-visible` rule anywhere — filter buttons, card links, and the theme toggle have no visible keyboard focus.
- Theme defaults to hard-coded `'dark'` and never consults `prefers-color-scheme`, on all three pages.
- Dark-mode `--ink-4: #646890` on `#0B1024` is roughly 4.2:1 — below AA for normal text, and it's the placeholder color, set in italic.
- Portfolio filtering mutates `card.hidden` with no `aria-live` announcement and no empty state.
- Google Fonts loaded via `<link>` rather than self-hosted, so the display faces flash.
- Every icon on all three pages is a hand-rolled SVG path.

**Suggested command:** `/impeccable audit`

## Persona Red Flags

**Jordan (First-Timer)** — Lands on `index.html` and sees a name, one sentence, and two glowing shapes with no borders. There is no navigation, so the two doors are the entire site and nothing says so. "Chat with my agent" doesn't say what the agent knows or why they'd ask it. Highest-risk moment: on a 13" laptop with browser chrome, `overflow: hidden` plus the fixed footer means Jordan may see clipped content and have no scroll affordance to recover.

**Riley (Stress Tester)** — Opens the message modal, hits Send with an empty textarea: nothing happens, no error, no focus move. Filters the portfolio to `Dev Tool`, hits Back: filter state is gone, because it lives only in DOM `hidden` attributes. Tabs through the portfolio: no focus ring appears anywhere. Loads the site with the backend cold: gets the good "Connection hiccup" message, which is the one edge case handled well.

**Casey (Distracted Mobile)** — `index.html` switches to `overflow: auto` under 640px, so mobile is actually safer than desktop here. But the landing fires a 150-span starfield, a blurred milky-way layer, and a meteor loop before showing content, and none of the three pages preload the local `AutumnBrush.otf` (659KB) — the name flashes in a fallback. The chat CTA footer offers LinkedIn, Send Message, Email, and Schedule side by side: four buttons, all the same intent, no primary.

## Minor Observations

- The portfolio grid holds 7 cards in 2 columns, leaving a visible orphan cell in the last row.
- Three filter chips for 7 items across 2 categories is UI theatre; the whole set fits on one screen.
- All 7 cards carry identical visual weight. A peer-reviewed paper and an internal Streamlit tool look the same. There is no lead piece.
- `index.html` lines 112–119 fully style `.door` as a glass card, then line 176 overrides all of it with `!important`. Dead code that documents a prior iteration.
- `DESIGN.md` has drifted from the implementation (`--forest`, and it doesn't mention the nebula-door treatment or the galaxy layer at all).
- Design tokens are copy-pasted into three separate `<style>` blocks with no shared source, which is how the drift happened.

## Questions to Consider

- The chat page invented a visual language. Why don't the other two pages speak it?
- If you deleted every eyebrow, every pip, and every middle dot, what would actually be lost?
- What does a visitor need to believe after eight seconds on the landing page, and is a symmetric pair of glowing cards the fastest way to make them believe it?
- Which single project would you want a hiring manager to see first, and does the current uniform grid let you say so?
