# Claude Code Project Rules

## Frontend Changes

**Always open the local file in a browser to verify before reporting a task as done.**

```bash
open /Users/lyx_computer/Desktop/AgLyx3.github.io/frontend/index.html
```

Check the golden path visually — do not rely on code review alone for UI/frontend work.

## Deployment

The frontend is a **separate Vercel project** inside the `frontend/` subdirectory.
Production domain: **www.yixinli.me**

To deploy frontend changes:

```bash
cd /Users/lyx_computer/Desktop/AgLyx3.github.io/frontend && vercel deploy --prod
```

Then verify the live site has the new code:

```bash
curl -s "https://www.yixinli.me" | grep -o "TOPICS\|<some-unique-string>"
```

Do not tell the user something is deployed until `vercel deploy --prod` finishes and curl confirms the new code is live.
The root `.vercel/` project (`ag-lyx3-github-io`) is separate and not the live frontend.

## Design Shifts

If a discussion leads to a meaningful product, UX, schema, retrieval, or architecture shift, record it in:

`/Users/lyx_computer/Desktop/AgLyx3.github.io/design-decision-log.md`

Keep that log updated with:

- what the previous direction was
- what changed
- why it changed
- what the new intended direction is
