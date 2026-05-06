"""FastAPI entrypoint."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router
from .config import get_settings
from .services import RateLimiter, enforce_request_size, init_db

settings = get_settings()
limiter = RateLimiter(settings.rate_limit_per_minute)

app = FastAPI(title=settings.app_name, version=settings.app_version)
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    client_key = request.client.host if request.client else "unknown"
    limiter.check(client_key)
    if request.method in {"POST", "PUT", "PATCH"}:
        enforce_request_size(request, settings.max_request_size_bytes)
    return await call_next(request)


app.include_router(api_router)
