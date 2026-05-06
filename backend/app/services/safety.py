"""Safety helpers for sanitization and request controls."""

from collections import defaultdict, deque
import re
import time

from fastapi import HTTPException, Request, status


_SAFE_TEXT_RE = re.compile(r"[^\x09\x0A\x0D\x20-\x7E]")


def sanitize_text(value: str) -> str:
    """Strip control characters and clamp whitespace-heavy input."""
    cleaned = _SAFE_TEXT_RE.sub("", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class RateLimiter:
    """Simple in-memory fixed-window rate limiter by client IP."""

    def __init__(self, limit_per_minute: int) -> None:
        self.limit_per_minute = limit_per_minute
        self.window_seconds = 60
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.time()
        q = self._hits[key]
        while q and now - q[0] > self.window_seconds:
            q.popleft()
        if len(q) >= self.limit_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please retry shortly.",
            )
        q.append(now)


def enforce_request_size(request: Request, max_size_bytes: int) -> None:
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Request payload too large (>{max_size_bytes} bytes).",
        )
