# Claude Code Project Rules

## Frontend Changes

**Always open the local file in a browser to verify before reporting a task as done.**

```bash
open /Users/lyx_computer/Desktop/AgLyx3.github.io/frontend/index.html
```

Check the golden path visually — do not rely on code review alone for UI/frontend work.

## Deployment

The frontend is a **separate Vercel project** (project ID `prj_0VQlazim8jLvy124ntEtUx4Ro97C`, `rootDirectory: frontend`).
Production domain: **www.yixinli.me**

The backend is a **separate Vercel project** (`prj_48EU70YMbbmK5kFo7FDUQJa5xO1k`) at **https://backend-green-zeta-37.vercel.app**. DB is Neon Postgres.

### Never deploy straight to production — preview first

`vercel deploy --prod` moves the live alias immediately. There is no rollback
on the current plan, so a bad production deploy is an outage you cannot undo,
only deploy your way out of.

Always deploy without `--prod` first, curl the preview URL, and only promote
once it answers correctly:

```bash
vercel deploy                      # preview, does not touch the live alias
vercel curl <preview-url>/health   # `vercel curl` handles deployment protection
```

Local tests and local `uvicorn` do **not** cover this. On 2026-08-27 a routing
change on Vercel's side broke every backend route while the app itself was
healthy and all 90 tests passed — only an HTTP request against a real
deployment could have caught it. See `design-decision-log.md` §26.

Note: backend preview deploys currently crash on import, because previews do
not inherit Production environment variables and `init_db()` at import time
falls back to SQLite on a read-only filesystem. Add `DATABASE_URL` and
`OPENAI_API_KEY` to the Preview environment before relying on a preview to
smoke-test the backend.

To deploy **frontend** changes (must run from repo root with project env vars — rootDirectory is set to `frontend` on the project):

```bash
cd /Users/lyx_computer/Desktop/AgLyx3.github.io && \
VERCEL_PROJECT_ID=prj_0VQlazim8jLvy124ntEtUx4Ro97C VERCEL_ORG_ID=team_DmPBnKVz79gxdj2KLxnfPetA vercel deploy --prod
```

To deploy **backend** changes:

```bash
cd /Users/lyx_computer/Desktop/AgLyx3.github.io/backend && vercel deploy --prod
```

Then verify the live site has the new code by diffing what production serves
against what you just built:

```bash
cd /Users/lyx_computer/Desktop/AgLyx3.github.io
for f in index.html portfolio.html chat.html; do
  diff -q <(curl -s "https://www.yixinli.me/$f") "frontend/$f" \
    && echo "$f: live matches local" || echo "$f: LIVE IS STALE"
done
```

Do not grep `assets/app.js`. No page has loaded it since the chat UI moved
inline into `chat.html`, but the dead file is still deployed and still contains
`backend-green`, so that check passes whether or not the deploy worked. A diff
against the local file is the only thing that proves the code you built is the
code being served.

Do not tell the user something is deployed until `vercel deploy --prod` finishes and curl confirms the new code is live.
If a deploy does break production, rebuild the previous known-good commit and deploy that before debugging. It both restores service and tells you whether your change was actually at fault — on 2026-08-27 it proved the change was innocent.
The root `.vercel/` project (`ag-lyx3-github-io`) is separate and not the live frontend.

## Design Shifts

If a discussion leads to a meaningful product, UX, schema, retrieval, or architecture shift, record it in:

`/Users/lyx_computer/Desktop/AgLyx3.github.io/design-decision-log.md`

Keep that log updated with:

- what the previous direction was
- what changed
- why it changed
- what the new intended direction is
