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

### Never push to `main`

**Both Vercel projects auto-deploy on push to `main`.** Git integration is
enabled, so `git push origin main` creates a **Production** deployment on the
frontend and the backend within seconds. There is no preview step and no
confirmation. Pushing to `main` *is* deploying to production.

There is no rollback on the current plan, so an untested push to `main` is an
outage you cannot undo, only deploy your way out of.

So: **never commit or push to `main`.** When the user says "push", that means
push a branch to the remote, open a PR, and merge it. Every change goes:

```bash
git checkout -b <branch>           # never work on main
git push -u origin <branch>        # builds a Preview; production is untouched
gh pr create                       # then verify the preview before merging
gh pr merge                        # merging to main is what ships to production
```

A branch push is safe — it only builds a Preview. The merge is the deploy, so
the preview URL must be verified *before* merging, not after.

`vercel deploy --prod` also moves the live alias immediately, so the same rule
applies to it: do not run it. Use `vercel deploy` without `--prod` if you need
a one-off preview outside the PR flow.

Verified 2026-09-02: pushing two commits to `main` produced Production
deployments on both projects (`vercel ls` showed both at Environment=Production
within a minute of the push).

Local tests and local `uvicorn` do **not** cover this. On 2026-08-27 a routing
change on Vercel's side broke every backend route while the app itself was
healthy and all 90 tests passed — only an HTTP request against a real
deployment could have caught it. See `design-decision-log.md` §26.

Note: backend preview deploys currently crash on import, because previews do
not inherit Production environment variables and `init_db()` at import time
falls back to SQLite on a read-only filesystem. Add `DATABASE_URL` and
`OPENAI_API_KEY` to the Preview environment before relying on a preview to
smoke-test the backend.

Merging the PR deploys both projects. Nothing else needs to be run.

If you need a **preview** outside the PR flow, deploy without `--prod`. Frontend
must run from the repo root with the project env vars, because `rootDirectory`
is set to `frontend` on the project:

```bash
cd /Users/lyx_computer/Desktop/AgLyx3.github.io && \
VERCEL_PROJECT_ID=prj_0VQlazim8jLvy124ntEtUx4Ro97C VERCEL_ORG_ID=team_DmPBnKVz79gxdj2KLxnfPetA vercel deploy
```

```bash
cd /Users/lyx_computer/Desktop/AgLyx3.github.io/backend && vercel deploy
```

`init_db()` runs at import in `app/main.py`, so any schema migration ships with
the merge and runs against Neon on the next cold start. A healthy `/health`
after the merge means it applied; a 502 across every route means it did not.

After the merge, verify the live site has the new code by diffing what
production serves against what you built:

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

Do not tell the user something is deployed until the PR is merged and curl confirms the new code is live. Do not call a branch push "deployed" — it only built a preview.
If a deploy does break production, put the previous known-good commit back on `main` through the same PR flow before debugging. It both restores service and tells you whether your change was actually at fault — on 2026-08-27 it proved the change was innocent.
The root `.vercel/` project (`ag-lyx3-github-io`) is separate and not the live frontend.

## Design Shifts

If a discussion leads to a meaningful product, UX, schema, retrieval, or architecture shift, record it in:

`/Users/lyx_computer/Desktop/AgLyx3.github.io/design-decision-log.md`

Keep that log updated with:

- what the previous direction was
- what changed
- why it changed
- what the new intended direction is
