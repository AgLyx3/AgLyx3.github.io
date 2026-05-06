#!/usr/bin/env python3
"""Local file-based workflow for topic candidate review."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "backend" / "data"
CANDIDATES_PATH = DATA_DIR / "topic_candidates.json"
ALIASES_PATH = DATA_DIR / "topic_aliases.json"
APPROVED_PATH = DATA_DIR / "topics.approved.json"


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    return "-".join(part for part in cleaned.split("-") if part) or "unknown"


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _load_candidates() -> dict[str, Any]:
    return _load_json(CANDIDATES_PATH, {"generated_at": None, "config": {}, "candidates": []})


def _save_candidates(payload: dict[str, Any]) -> None:
    _write_json(CANDIDATES_PATH, payload)


def _find_candidate(candidates: list[dict[str, Any]], candidate_id: str) -> dict[str, Any]:
    for candidate in candidates:
        if candidate.get("candidate_id") == candidate_id:
            return candidate
    raise ValueError(f"Candidate not found: {candidate_id}")


def cmd_list(_: argparse.Namespace) -> int:
    payload = _load_candidates()
    pending = [c for c in payload.get("candidates", []) if c.get("status") == "pending"]
    if not pending:
        print("No pending candidates.")
        return 0
    for candidate in pending:
        print(
            f"{candidate['candidate_id']}: phrase='{candidate['phrase']}', "
            f"distinct_sessions={candidate['distinct_sessions']}, mentions={candidate['mentions']}"
        )
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    now = datetime.now(UTC).isoformat()
    candidates_payload = _load_candidates()
    approved_payload = _load_json(APPROVED_PATH, {"topics": []})

    candidate = _find_candidate(candidates_payload.get("candidates", []), args.candidate_id)
    candidate["status"] = "approved"
    candidate["reviewed_at"] = now

    topic_name = args.topic_name or candidate["phrase"]
    topic = {
        "topic_id": f"topic-{_slug(topic_name)}",
        "name": topic_name,
        "source_candidate_id": candidate["candidate_id"],
        "approved_at": now,
    }
    approved_payload.setdefault("topics", []).append(topic)

    _save_candidates(candidates_payload)
    _write_json(APPROVED_PATH, approved_payload)
    print(f"Approved {candidate['candidate_id']} -> {topic['topic_id']}")
    return 0


def cmd_alias(args: argparse.Namespace) -> int:
    now = datetime.now(UTC).isoformat()
    candidates_payload = _load_candidates()
    aliases_payload = _load_json(ALIASES_PATH, {"aliases": []})

    candidate = _find_candidate(candidates_payload.get("candidates", []), args.candidate_id)
    candidate["status"] = "aliased"
    candidate["reviewed_at"] = now

    aliases_payload.setdefault("aliases", []).append(
        {
            "phrase": candidate["phrase"].lower(),
            "topic_id": args.topic_id,
            "created_at": now,
            "source_candidate_id": candidate["candidate_id"],
        }
    )

    _save_candidates(candidates_payload)
    _write_json(ALIASES_PATH, aliases_payload)
    print(f"Aliased {candidate['candidate_id']} -> {args.topic_id}")
    return 0


def cmd_reject(args: argparse.Namespace) -> int:
    now = datetime.now(UTC).isoformat()
    candidates_payload = _load_candidates()

    candidate = _find_candidate(candidates_payload.get("candidates", []), args.candidate_id)
    candidate["status"] = "rejected"
    candidate["reviewed_at"] = now
    candidate["reject_reason"] = args.reason

    _save_candidates(candidates_payload)
    print(f"Rejected {candidate['candidate_id']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Topic candidate local review CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List pending candidates")
    list_parser.set_defaults(func=cmd_list)

    approve_parser = subparsers.add_parser("approve", help="Approve candidate as official topic")
    approve_parser.add_argument("--candidate-id", required=True)
    approve_parser.add_argument("--topic-name", required=False)
    approve_parser.set_defaults(func=cmd_approve)

    alias_parser = subparsers.add_parser("alias", help="Alias candidate phrase to existing topic")
    alias_parser.add_argument("--candidate-id", required=True)
    alias_parser.add_argument("--topic-id", required=True)
    alias_parser.set_defaults(func=cmd_alias)

    reject_parser = subparsers.add_parser("reject", help="Reject candidate phrase")
    reject_parser.add_argument("--candidate-id", required=True)
    reject_parser.add_argument("--reason", default="noise")
    reject_parser.set_defaults(func=cmd_reject)

    return parser


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
