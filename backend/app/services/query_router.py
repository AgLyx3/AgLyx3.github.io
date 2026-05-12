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
    r"|what\s+do\s+you\s+know"
    r"|what(\s+can)?\s+you\s+(tell|show|help)"
    r"|where\s+(do\s+i|should\s+i)\s+start"
    r"|ok(ay)?|alright|sounds\s+good|got\s+it|cool|great|awesome"
    r"|lol|haha|hm+|hmm+|interesting|nice|wow|whoa"
    r"|not\s+really|no\s+thanks?|nah|nope"
    r")[\s!?.]*$",
    re.IGNORECASE,
)

_VISITOR_STATEMENT_RE = re.compile(
    r"^(i\s+(am|'m|work|do|have|built|build|study|use|run|make|design|like|love|focus|specialize|help|lead|manage|create|develop|joined|started|co-founded|founded)|"
    r"i'(ve|d|ll)\s+\w+|"
    r"we\s+(are|'re|work|build|use|run|focus|specialize)|"
    r"my\s+(company|team|project|work|job|role|startup|background|experience|focus|name)|"
    r"our\s+(team|company|product|startup|work|project))",
    re.IGNORECASE,
)

_YIXIN_RE = re.compile(r"\b(yixin|she\b|her\b)", re.IGNORECASE)


def is_visitor_statement(query: str) -> bool:
    """True if the message looks like the visitor sharing something about themselves."""
    stripped = query.strip()
    if stripped.endswith("?"):
        return False
    if _YIXIN_RE.search(stripped):
        return False
    return bool(_VISITOR_STATEMENT_RE.match(stripped))


def route_query(query: str) -> ChatRoute:
    """Classify a query into a top-level route without calling an LLM."""
    lower = query.lower().strip()

    if _SMALL_TALK_RE.match(lower):
        return "small_talk"

    return "memory"
