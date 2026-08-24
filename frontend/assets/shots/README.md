# Project screenshots

Drop a file here named after the project's `data-shot` attribute in
`portfolio.html`. Nothing else needs editing.

| Project | Filename | Have one? |
|---|---|---|
| We Love Jupyter Notebook | `we-love-jupyter-notebook.png` | present |
| Remli | `remli.png` | — |
| Implicit Social Cognition Benchmark | `implicit-social-cognition-benchmark.png` | — |
| Continua Memory Evaluation | `continua-memory-evaluation.png` | — |
| Conversation Topic Analysis Tool | `conversation-topic-analysis.png` | — |
| Fix8 | `fix8.jpg` | present |
| User Studies in Human-Feature-Integration | `human-feature-research-poster.jpg` | present |

The portfolio preloads every `data-shot` path and only upgrades a card once the
file has actually decoded. A project with no screenshot keeps its glyph and
renders exactly as it did before this feature existed — so it is safe to leave
paths wired for work that has no image yet, and safe to add one later by
dropping the file in without touching the HTML. Changing a filename means
editing that card's `data-shot`.

Guidance:
- Landscape, roughly 16:10. Desktop hovers a ~410px preview out across the
  track; mobile shows the image inline at card width. Both are smaller than the
  file, so fine UI text will not read — prefer a shot with one clear focal area.
- Aim for at least ~1400px wide. The lightbox renders up to 1000px, so anything
  smaller than that gets upscaled and goes soft.
- PNG or JPG. Keep each under ~350KB; these load on page load, not on hover.
- Update `data-shot-alt` on the card when you add a file. It is the alt text and
  the lightbox caption, so it should describe the actual image.
