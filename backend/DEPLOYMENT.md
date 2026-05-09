# Backend Deployment

## Recommended Production Setup

- Host the FastAPI service on Railway
- Host the primary database on Railway Postgres
- Keep the frontend on GitHub Pages

## Environment Variables

Set these in Railway:

- `OPENAI_API_KEY`
- `DATABASE_URL`
- `ANALYTICS_WRITE_ENABLED=true`
- `CHAT_MODEL`
- `TOPIC_LABELER_MODEL`
- `CHAT_RATE_LIMIT_PER_MINUTE=6`
- `MAX_MESSAGES_PER_SESSION=15`
- `MAX_TOTAL_TOKENS_PER_SESSION=20000`
- `MAX_INPUT_TOKENS_PER_MESSAGE=1500`
- `MAX_OUTPUT_TOKENS_PER_RESPONSE=400`

Optional:

- `LINKEDIN_URL`
- `SCHEDULE_URL`
- `RESUME_URL`

## Local Development

1. Copy `backend/.env.example` to `backend/.env`
2. Set `OPENAI_API_KEY`
3. Keep `ANALYTICS_WRITE_ENABLED=false` locally if you do not want local engagement metrics saved
4. Run the backend

## Start Command

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Database Notes

- The backend now supports both `sqlite:///...` and `postgresql://...` `DATABASE_URL` values.
- Railway production should use Postgres.
- Local SQLite remains supported as a disposable development database, but production engagement metrics should live in Postgres.
