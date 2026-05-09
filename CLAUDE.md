# Claude Code Project Rules

## Frontend Changes

**Always open the local file in a browser to verify before reporting a task as done.**

```bash
open /Users/lyx_computer/Desktop/AgLyx3.github.io/frontend/index.html
```

Check the golden path visually — do not rely on code review alone for UI/frontend work.

## Deployment

Changes to `frontend/index.html` or `PRD.md` are not live until committed and pushed to `main`.
GitHub Pages serves from the repo; local edits are invisible to the deployed site.
Always commit + push after frontend fixes, or explicitly tell the user the changes are local only.
