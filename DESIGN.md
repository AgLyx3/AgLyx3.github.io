# Design System — Yixin Li Portfolio

## Color Palette

All colors are defined as CSS custom properties in `frontend/assets/styles.css` and `frontend/index.html` (self-contained).

### Paper — warm off-white ground
| Token | Hex | Use |
|---|---|---|
| `--paper` | `#F8F4EE` | Page background, card fills |
| `--paper-2` | `#E9D9C9` | Hovered card, secondary surface |
| `--paper-3` | `#E1CFBE` | Tertiary surface |
| `--paper-edge` | `#CFBEAE` | Borders, dividers |

### Ink — warm charcoal
| Token | Hex | Use |
|---|---|---|
| `--ink` | `#2F2C31` | Primary text, headings |
| `--ink-2` | `#4A4750` | Body text, secondary labels |
| `--ink-3` | `#716D73` | Muted labels, eyebrows, placeholders |
| `--ink-4` | `#9D97A0` | Disabled, very faint metadata |

### Accent — dusty editorial blue
| Token | Hex | Use |
|---|---|---|
| `--forest` | `#6E86AB` | Links, active nav, accent elements, bubble outlines |
| `--forest-hover` | `#5A7093` | Hover state for forest elements |
| `--forest-soft` | `#D8E0EC` | Light tint backgrounds, chip fills |

### Page Background Gradient
Applied on chat, graph, profile, topic, and experience pages:
```css
background:
  radial-gradient(circle at top left,
    rgba(110, 134, 171, 0.16) 0%,
    rgba(110, 134, 171, 0.04) 24%,
    rgba(248, 244, 238, 0) 48%),
  linear-gradient(180deg,
    rgba(216, 224, 236, 0.22) 0%,
    rgba(248, 244, 238, 0.68) 22%,
    rgba(248, 244, 238, 0.96) 100%);
```
Creates a subtle cool-blue bloom at the top-left corner fading to warm paper.

---

## Typography

Three fonts, each with a distinct role. Never mix roles.

### Autumn Brush — display
- Source: local `assets/AutumnBrush.otf`
- Use: page `<h1>` display headings only ("Talk to me.", "Memory Graph", "Profile Memory")
- Size: `clamp(36px, 5vw, 58px)` on content pages; `clamp(26px, 3.4vw, 42px)` on landing
- Weight: 400 (only weight available)
- Never use for body copy, labels, or UI chrome

### Playfair Display — reading serif
- Source: Google Fonts `Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500;1,600;1,700`
- Token: `--font-serif: 'Playfair Display', Georgia, serif`
- Use: chat message bodies, raw context/profile text, reading-weight content, brand name in topbar, italic dates
- Minimum weight: **400** (300 is unavailable — do not use)
- No `font-variation-settings` (Playfair Display is not a variable font)

### Geist Mono — UI chrome
- Source: Google Fonts `Geist+Mono:wght@400;500`
- Token: `--font-mono: 'Geist Mono', ui-monospace, 'Courier New', monospace`
- Use: nav links, eyebrow labels, buttons, mode toggles, card ID badges, chip tags, status text, metadata, footnotes
- Sizes: 10–13px for labels; 12–14px for buttons/nav

### System sans — fallback only
- Token: `--font-sans: -apple-system, 'Helvetica Neue', sans-serif`
- Use: `body` base default and `<input>`/`<textarea>` defaults only. Individual components always override with serif or mono.

---

## Bubble Design

Bubbles are the primary visual identity of the site — they represent memory topic nodes in the graph and carry that identity into the landing page layout.

### Visual anatomy
Each bubble is a layered SVG `<g>` element:

1. **Halo circle** — slightly larger than the bubble, low-opacity fill, appears on hover/focus to create a soft glow ring
2. **Fill circle** — radial gradient fill, feathers to transparent at the edge (not a hard-edge circle)
3. **Text label** — Playfair Display for topic names, Geist Mono for activation scores beneath

### Radial gradient fill pattern
The gradient goes from ~90% opacity at center to 0% at the edge, creating a soft floating orb with no hard outline:
```
[0%,   opacity 0.90]
[62%,  opacity 0.85]
[82%,  opacity 0.55]
[93%,  opacity 0.18]
[100%, opacity 0.00]
```

### Hue palette
Nine named hues cycle across topic bubbles. Each hue defines a fill RGB and a text RGB:

| Name | Fill RGB | Text RGB |
|---|---|---|
| amber | `233,217,201` | `118,105,91` |
| cream | `243,236,227` | `125,116,107` |
| pearl | `231,226,222` | `116,110,113` |
| mist | `220,228,239` | `89,104,132` |
| blue | `196,208,228` | `84,100,128` |
| mirage | `168,185,214` | `70,86,115` |
| slate | `149,164,189` | `67,79,102` |
| smoke | `214,204,194` | `109,98,89` |
| dune | `223,212,198` | `116,104,88` |

The profile/anchor node always uses **mirage** and renders with a deeper anchor gradient variant.

### Drop shadows
- Topic bubbles: `feDropShadow dx=0 dy=10 stdDeviation=12 opacity=0.13`
- Profile bubble: `feDropShadow dx=0 dy=14 stdDeviation=16 opacity=0.17` (heavier, more grounded)

### Physics simulation (D3 force)
- `forceCollide` — keeps bubbles from overlapping, strength 0.9
- `forceManyBody` — gentle repulsion strength -40
- `forceX/Y` — weak pull toward center (strength 0.025), prevents drift to edges
- `alphaTarget: 0.06` — simulation never fully settles; bubbles drift perpetually
- Each bubble has a personal phase offset `_px`/`_py` and speed `_spd` (0.55–1.0), driving an independent sinusoidal drift wave

### Size scaling
Topic radius scales with activation score: `minRadius + ((activation - min) / range) * spread`  
Desktop range: 48–85px. Mobile range: 32–56px.

---

## Layout — Landing (Pre-Input)

**Concept:** The topic bubbles ARE the interface. They fill the full viewport as a living, clickable graph. Name, tagline, and an input bar float at center. No topbar. No navigation chrome. The whole screen is the entry point.

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│   ●[AI Agents]   ●[Memory]           ●[HCI]  ●[Research]│
│                                                          │
│  ●[Startup]           Yixin Li                          │
│               ●       I build products at…    ●[Ethics] │
│  ●[Eng]                                                  │
│         ●     ┌────────────────────────────┐    ●        │
│               │  Ask me anything…          │             │
│  ●[PM]        └────────────────────────────┘   ●[Photo] │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Key properties
- **Bubbles are interactive** — each bubble is a named topic node (AI Agents, Memory Systems, Startup, etc.). Clicking one pre-fills the input with a starter question. Users may edit or send as-is.
- **Bubble physics** — full-viewport D3 simulation with perpetual drift. Bubbles may partially bleed off screen edges. The graph is never static.
- **Identity block** — horizontally and vertically centered: name in Autumn Brush → short tagline in Playfair Display → input bar below.
- **Input bar** — wide pill, roughly 55–65% of viewport width. Playfair Display placeholder text `"Ask me anything…"`. Enter key or Send button submits.
- **No topbar** in this state. Navigation only appears after the chat panel opens.
- **Background** — warm paper `#F8F4EE` with the standard top-left blue gradient bloom.
- **Bubble state at landing** — all nodes at rest, equal visual weight (no highlights). The profile/center concept is conveyed by the identity text block, not a separate center node on landing.

### Topic prefill behavior
When a visitor clicks a bubble:
1. That bubble visually highlights (scale up + halo brightens, ~200ms)
2. The input bar pre-fills: *"What kind of [topic] did Yixin work on?"*
3. Input receives focus — visitor may send immediately or edit
4. Sending triggers the landing → chat transition

---

## Layout — Chat (Post-Input)

**Concept:** Bubbles migrate outward to become living side columns. A chat panel rises in the cleared center. The graph remains visible and interactive — visitors can click a side bubble at any time to inject a new topic into the conversation.

```
┌─────────────────────────────────────────────────────────┐
│  ●[Memory]  ┌──── topbar ──────────────────┐  ●[HCI]    │
│             │ Yixin Li     About  Chat  Mem │            │
│  ●[Eng]     ├──────────────────────────────┤  ●[Ethics] │
│             │                              │            │
│  ●[Photo]   │  ╔══ Yixin ══╗              │   ●[AI]    │
│             │  ║ Response… ║              │            │
│  ●          │         ╔══ You ══╗         │   ●        │
│             │         ║ Message ║         │            │
│  ●[Startup] │  ╔══ Yixin ══╗              │   ●[PM]    │
│             │  ║ Follow-up ║              │            │
│             │  [chip] [chip] [chip]       │            │
│             ├──────────────────────────────┤            │
│             │  › Ask anything…    [Send]  │            │
│             └──────────────────────────────┘            │
│             ┌──────────────────────────────┐            │
│             │ LinkedIn  Message  Resume  Schedule│       │
│             └──────────────────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

### Key properties
- **Chat panel** — centered column, `max-width ~760px`, full viewport height. Glassmorphism surface: `rgba(255,255,255,0.72)` + `backdrop-filter: blur(10px)`. Topbar inside the panel top.
- **Message thread** — scrollable area between topbar and composer. Playfair Display for all message text. Alternating alignment: Yixin responses left-aligned (dark/paper style), user messages right-aligned (light/outlined style).
- **Follow-up suggestions** — after each Yixin response, up to 3 chip-style suggestion buttons appear inline below the message. Geist Mono, `border-radius: 999px`. Clicking one pre-fills the composer.
- **Composer** — same visual input bar from landing, now docked at the panel bottom. Playfair Display. Enter or Send button.
- **Side bubbles** — bubble physics simulation continues on both flanks. Clicking any side bubble injects that topic into the conversation (same prefill behavior as landing). Explored/active bubbles are larger and more vivid; unvisited bubbles are smaller and muted.
- **Bubble column width** — roughly 18–20% of viewport per side, leaving ~60% for the chat panel.
- **CTA footer** — persistent strip below the chat panel (or docked to page bottom). Four actions always visible: LinkedIn · Send Message · Download Resume · Schedule Time. Geist Mono, small, unobtrusive. Fades in as part of the chat panel entrance.

### Dynamic bubble state in chat
- **Visited/explored** — bubbles for topics already discussed grow slightly and increase opacity. Visual cue that the visitor has explored this area.
- **Currently active topic** — the most recently clicked/discussed topic bubble pulses its halo gently.
- **Unvisited** — lower opacity, smaller. Suggests there is more to discover.

---

## Layout Transition — Landing → Chat

Fires when the visitor submits a message (from the landing input bar, or after clicking a topic bubble).

### Sequence
```
0ms   — visitor hits Enter / clicks Send
0ms   — input bar animates: shrinks slightly, begins translating toward panel-bottom position
80ms  — bubble simulation force fields shift: forceX/Y pushes bubbles outward to side columns
180ms — chat panel surface fades in + slides up (translateY 20px → 0)
        topbar and message thread area appear
280ms — input bar arrives at docked position at panel bottom
380ms — bubbles settle into side-column positions
420ms — first user message fades in to thread
440ms — CTA footer fades in below panel
500ms — typing indicator (three-dot pulse) appears as response loads
```

### Animation specs
- Bubble scatter: `cubic-bezier(0.2, 0.7, 0.2, 1)`, staggered per bubble (0–80ms random offset)
- Chat panel rise: `opacity 0→1` + `translateY(20px)→0`, 320ms `ease-out`
- Input bar morph: position transition 280ms `ease-in-out`; no size change — just repositions
- Message entrance: `opacity 0→1`, 160ms, `ease-out`

### Reverse (not yet designed)
A future "reset" action in the topbar could reverse the sequence back to the landing state with conversation cleared. Not in MVP scope.

---

## Follow-Up Suggestions

After each Yixin response, up to 3 suggestion chips appear inline below the message bubble.

### Two types (per PRD)
- **Topic-specific follow-ups** — deeper questions about the current subject (e.g. "How hands-on was she?" / "What decisions did she own?")
- **Adjacent topic chips** — neighboring topic bubbles to explore next (e.g. "Evaluation & Benchmarking" / "AI Agents")

### Visual treatment
```css
font-family: var(--font-mono);
font-size: 12px;
font-weight: 500;
padding: 5px 12px;
border: 1px solid rgba(110, 134, 171, 0.18);
border-radius: 999px;
background: rgba(255, 255, 255, 0.72);
color: var(--forest);
```
Clicking a chip:
- Pre-fills the composer with the question text (question chips), or
- Pre-fills the composer with a starter question and highlights the corresponding side bubble (topic chips)

---

## CTA Footer

A persistent strip that remains visible below the chat panel throughout the session.

### Four actions
| Label | Action |
|---|---|
| Connect on LinkedIn | Opens LinkedIn profile in new tab |
| Send Message | Opens embedded message flow (free-form + optional chat history checkbox) |
| Download Resume | Triggers PDF download |
| Schedule Time | Opens calendar scheduling link |

### Visual treatment
- Geist Mono, `font-size: 11–12px`, `letter-spacing: 0.05em`
- Minimal — does not compete with the chat panel
- Fades in as part of the chat panel entrance (~440ms into transition)
- Always visible; does not scroll away

### In-chat CTA mention rules (AI behavior)
- AI may mention a CTA in the chat thread only after the visitor has sent ≥ 5 messages
- At most once per session
- Only after completing the answer, never before it
- If ignored or rejected, never mentioned again in the same session

---

## Dynamic Graph State

The topic graph evolves visually as visitors explore. Node prominence reflects accumulated interest signals.

### Weight sources (per PRD)
| Signal | Weight |
|---|---|
| Initial topic bubble click | +10 |
| Repeated click / revisit | +4–6 |
| Follow-up question on topic | +2 |
| Repeated mention in conversation | +1 |

### Visual mapping
| State | Bubble appearance |
|---|---|
| Unvisited | Base size, ~60% opacity |
| Lightly explored | Base size, ~80% opacity |
| Moderately explored | Slightly larger (+~15% radius), full opacity |
| Heavily explored | Noticeably larger (+~25%), full opacity, halo subtly glows |
| Currently active | Halo pulses gently (CSS animation, ~2s cycle) |

The profile/center node (About Me) is always rendered at maximum prominence — it is the fixed anchor.

---

## Component Patterns

### Topbar / Site header
```css
font-family: var(--font-serif);   /* brand name */
font-family: var(--font-mono);    /* nav links */
padding: 20px 32px;
border-bottom: 1px solid var(--paper-edge);
```
Active nav link: `aria-current="page"` → `color: var(--ink)`. Inactive: `color: var(--ink-3)`.

### Page eyebrow
```css
font-family: var(--font-mono);
font-size: 11px;
font-weight: 500;
letter-spacing: 0.07em;
text-transform: uppercase;
color: var(--ink-3);
```

### Glassmorphism card (chat thread, experience panels)
```css
background: rgba(255, 255, 255, 0.72);
border: 1px solid rgba(110, 134, 171, 0.18);
border-radius: 24px;
backdrop-filter: blur(10px);
box-shadow: inset 0 1px 0 rgba(255,255,255,0.65),
            0 14px 36px rgba(110, 134, 171, 0.08);
```

### Paper card (profile records, plain content)
```css
background: var(--paper);
border: 1px solid var(--paper-edge);
border-radius: var(--radius); /* 4px */
```

### Mode toggle (Full Context / Timeline / Structured)
```css
/* container */
border: 1px solid var(--paper-edge);
border-radius: 999px;
background: rgba(239, 239, 234, 0.9);

/* active button */
background: var(--ink);
color: var(--paper);
font-family: var(--font-mono);
```
