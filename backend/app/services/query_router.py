"""Deterministic heuristic query router — zero LLM calls."""

from __future__ import annotations

import re
from typing import Literal

ChatRoute = Literal["small_talk", "memory"]

_SMALL_TALK_RE = re.compile(
    r"^("
    r"hi|hello|hey|howdy|hiya|yo|sup|greetings"
    r"|good\s*(morning|afternoon|evening|day)"
    r"|hi\s+there|hello\s+there|hey\s+there"
    r"|how\s+are\s+you"
    r"|nice\s+to\s+(meet|talk)"
    r"|thanks?\s*!?|thank\s+you|thx|ty"
    r"|bye|goodbye|see\s+you|take\s+care|later|peace|cya"
    r"|what\s+can\s+you\s+do|who\s+are\s+you"
    r"|ok(ay)?|alright|sounds\s+good|got\s+it|cool|great|awesome"
    r")[\s!?.]*$",
    re.IGNORECASE,
)

def route_query(query: str) -> ChatRoute:
    """Classify a query into a top-level route without calling an LLM."""
    lower = query.lower().strip()

    if _SMALL_TALK_RE.match(lower):
        return "small_talk"

    return "memory"
