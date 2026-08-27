"""Langfuse tracing shim.

Wraps the Langfuse SDK so the rest of the app can instrument freely without
caring whether tracing is configured. Every helper degrades to a no-op when the
keys are absent, the package is missing, or the SDK itself raises —
observability must never be able to take the chat endpoint down with it.

Serverless note: Vercel freezes the instance once a response finishes, and the
SDK batches spans on a background thread. Call `flush()` before the request
path ends — for streaming responses that means inside the generator's `finally`
block, not before the StreamingResponse is returned.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: Any = None
_init_attempted = False

# Payload keys whose values are visitor-authored rather than Yixin's own
# content. Redacted before leaving the box when LANGFUSE_MASK_PII is on.
_PII_KEYS = frozenset({"visitor_context", "user_message", "transcript"})
_REDACTED = "[redacted]"


def _mask(*, data: Any, **_kwargs: Any) -> Any:
    """Recursively redact visitor-authored fields. See MaskFunction protocol."""
    if isinstance(data, dict):
        return {
            key: (_REDACTED if key in _PII_KEYS and value else _mask(data=value))
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [_mask(data=item) for item in data]
    return data


def _get_client() -> Any:
    """Return a configured Langfuse client, or None if tracing is off."""
    global _client, _init_attempted
    if _init_attempted:
        return _client
    _init_attempted = True

    settings = get_settings()
    if not (
        settings.langfuse_enabled
        and settings.langfuse_public_key
        and settings.langfuse_secret_key
    ):
        return None

    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            environment=settings.langfuse_environment,
            mask=_mask if settings.langfuse_mask_pii else None,
        )
    except Exception:  # pragma: no cover - defensive, never break the request
        logger.warning("Langfuse init failed; tracing disabled", exc_info=True)
        _client = None
    return _client


def tracing_enabled() -> bool:
    return _get_client() is not None


class _NullSpan:
    """Stand-in returned when tracing is off, so call sites stay unconditional."""

    def update(self, **_kwargs: Any) -> None:
        return None

    def score(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class _Span:
    """Thin wrapper that swallows SDK errors from instrumentation call sites."""

    def __init__(self, span: Any) -> None:
        self._span = span

    def update(self, **kwargs: Any) -> None:
        try:
            self._span.update(**kwargs)
        except Exception:  # pragma: no cover - defensive
            logger.debug("Langfuse span update failed", exc_info=True)

    def score(self, name: str, value: float | str, comment: str | None = None) -> None:
        """Attach a trace-level score (survives past this span's lifetime)."""
        try:
            self._span.score_trace(name=name, value=value, comment=comment)
        except Exception:  # pragma: no cover - defensive
            logger.debug("Langfuse score failed", exc_info=True)


@contextmanager
def observe(
    name: str,
    *,
    as_type: str = "span",
    trace_id: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    **kwargs: Any,
) -> Iterator[Any]:
    """Open an observation. Yields a no-op handle when tracing is disabled.

    `trace_id` attaches this observation to an existing trace — used to stitch
    a voice turn's separate HTTP requests (chat, TTS, transcript) into one.
    `session_id`/`tags` are trace-level and propagate to every child span.
    """
    client = _get_client()
    span_cm = None
    if client is not None:
        try:
            trace_context = {"trace_id": trace_id} if trace_id else None
            span_cm = client.start_as_current_observation(
                name=name, as_type=as_type, trace_context=trace_context, **kwargs
            )
        except Exception:  # pragma: no cover - defensive
            logger.debug("Langfuse span start failed; continuing untraced", exc_info=True)
            span_cm = None

    # Exactly one yield on every path. Errors raised by the caller's block must
    # propagate untouched — the span records them, it does not swallow them.
    if span_cm is None:
        yield _NullSpan()
        return

    with span_cm as span:
        if session_id or tags:
            from langfuse import propagate_attributes

            with propagate_attributes(session_id=session_id, tags=tags):
                yield _Span(span)
        else:
            yield _Span(span)


def score_current_trace(
    name: str, value: float | str, comment: str | None = None
) -> None:
    """Score whatever trace is active, from code that holds no span handle."""
    client = _get_client()
    if client is None:
        return
    try:
        client.score_current_trace(name=name, value=value, comment=comment)
    except Exception:  # pragma: no cover - defensive
        logger.debug("Langfuse trace score failed", exc_info=True)


def trace_id_for(seed: str) -> str | None:
    """Deterministic trace id from a seed, so separate requests can share a trace."""
    client = _get_client()
    if client is None:
        return None
    try:
        return client.create_trace_id(seed=seed)
    except Exception:  # pragma: no cover - defensive
        return None


def flush() -> None:
    """Block until buffered spans are sent. Required before a serverless freeze."""
    client = _get_client()
    if client is None:
        return
    try:
        client.flush()
    except Exception:  # pragma: no cover - defensive
        logger.debug("Langfuse flush failed", exc_info=True)


def _reset_for_tests() -> None:
    """Drop the memoised client so tests can toggle configuration."""
    global _client, _init_attempted
    _client = None
    _init_attempted = False
