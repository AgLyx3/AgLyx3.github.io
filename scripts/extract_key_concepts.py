"""One-time script: use gpt-4o-mini to extract key concepts per experience and store in DB.

Run from repo root:
    cd backend && ../.venv/bin/python ../scripts/extract_key_concepts.py
Or:
    cd backend && python ../scripts/extract_key_concepts.py  (if venv is active)

Re-running is safe — skips experiences that already have key_concepts unless --force is passed.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

# Allow importing app modules when running from backend/
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.db import get_conn

SYSTEM_PROMPT = """\
You extract the 5-8 most important concepts from a work experience description.

Rules:
- Include: core domain concepts ("memory quality", "retrieval precision"), named capabilities \
("personalization", "agent performance"), specific artifacts/benchmarks ("LoCoMo", "EverMemBench"), \
and the product/system name ("conversational AI product", "LLM systems").
- Include quantifiable outcomes as short phrases ("~20% reduction", "1-2 weeks").
- Exclude: implementation steps, generic process terms ("stakeholder interviews", "project tracking"), \
role descriptions, company names (those are captured elsewhere).
- Keep phrases short: 1-4 words each.

Return strict JSON: {"concepts": ["concept1", "concept2", ...]}"""


def extract_for_experience(title: str, raw_context: str, api_key: str) -> list[str]:
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Title: {title}\n\n{raw_context}"},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    content = data["choices"][0]["message"]["content"]
    return [str(c).strip() for c in json.loads(content).get("concepts", []) if str(c).strip()]


def main():
    force = "--force" in sys.argv
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Try loading from .env
        env_path = Path(__file__).parent.parent / "backend" / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found")
        sys.exit(1)

    with get_conn() as conn:
        rows = conn.execute("SELECT id, title, raw_context, key_concepts FROM experiences ORDER BY id").fetchall()

    print(f"Found {len(rows)} experiences")
    updated = 0
    for row in rows:
        exp_id, title, raw_context, existing = row["id"], row["title"], row["raw_context"], row["key_concepts"]
        if existing and not force:
            print(f"  skip  {exp_id} (already has concepts)")
            continue
        try:
            concepts = extract_for_experience(title, raw_context, api_key)
            with get_conn() as conn:
                conn.execute(
                    "UPDATE experiences SET key_concepts = ? WHERE id = ?",
                    (json.dumps(concepts), exp_id),
                )
                conn.commit()
            print(f"  done  {exp_id}: {concepts}")
            updated += 1
        except Exception as e:
            print(f"  ERROR {exp_id}: {e}")

    print(f"\nDone — updated {updated} experiences.")


if __name__ == "__main__":
    main()
