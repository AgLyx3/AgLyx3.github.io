"""Safety helpers for sanitization and request controls."""

from collections import defaultdict, deque
import math
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

    def check(self, key: str, *, limit_per_minute: int | None = None) -> None:
        now = time.time()
        q = self._hits[key]
        active_limit = limit_per_minute or self.limit_per_minute
        while q and now - q[0] > self.window_seconds:
            q.popleft()
        if len(q) >= active_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please retry shortly.",
            )
        q.append(now)


def estimate_tokens(value: str) -> int:
    cleaned = sanitize_text(value)
    if not cleaned:
        return 0
    return max(1, math.ceil(len(cleaned) / 4))


def truncate_text_to_token_limit(value: str, max_tokens: int) -> str:
    cleaned = sanitize_text(value)
    if max_tokens <= 0 or not cleaned:
        return ""
    if estimate_tokens(cleaned) <= max_tokens:
        return cleaned

    words = cleaned.split(" ")
    kept: list[str] = []
    for word in words:
        candidate = " ".join([*kept, word]).strip()
        if estimate_tokens(candidate) > max_tokens:
            break
        kept.append(word)
    return " ".join(kept).strip()


async def enforce_request_size(request: Request, max_size_bytes: int) -> None:
    body = await request.body()
    if len(body) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Request payload too large (>{max_size_bytes} bytes).",
        )
