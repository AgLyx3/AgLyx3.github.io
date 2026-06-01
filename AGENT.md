# Agent Project Rules

## Git

**Do not auto commit changes.** Only create a commit if the user explicitly asks for one.

**Do not use `gh` to push branches or create pull requests** unless the user explicitly asks. When a branch is ready, share the GitHub URL for the user to open the PR manually.

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

To deploy **frontend** changes (must run from repo root with project env vars — rootDirectory is set to `frontend` on the project):

```bash
cd /Users/lyx_computer/Desktop/AgLyx3.github.io && \
VERCEL_PROJECT_ID=prj_0VQlazim8jLvy124ntEtUx4Ro97C VERCEL_ORG_ID=team_DmPBnKVz79gxdj2KLxnfPetA vercel deploy --prod
```

To deploy **backend** changes:

```bash
cd /Users/lyx_computer/Desktop/AgLyx3.github.io/backend && vercel deploy --prod
```

Then verify the live site has the new code:

```bash
curl -s "https://www.yixinli.me/assets/app.js" | grep "backend-green"
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
