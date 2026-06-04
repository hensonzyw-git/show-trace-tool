"""Backfill event interest scores for existing events."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from app.preferences import get_current_interest_profile, score_events_for_interest
from db import (
    DEFAULT_INTEREST_PROFILE_ID,
    get_events_for_interest_scoring,
    get_events_missing_interest_scores,
    save_event_interest_score,
)


def main() -> None:
    args = _parse_args()
    profile = get_current_interest_profile()
    total = 0

    while True:
        if args.all:
            events = get_events_for_interest_scoring(limit=args.batch_size)
        else:
            events = get_events_missing_interest_scores(
                profile_id=DEFAULT_INTEREST_PROFILE_ID,
                limit=args.batch_size,
            )
        if not events:
            break
        scores = score_events_for_interest(events, profile)
        for event, score in zip(events, scores, strict=True):
            if not args.dry_run:
                save_event_interest_score(event["id"], score)
        total += len(events)
        print(f"Backfilled {total} events")
        if args.once or args.all:
            break

    print(f"Done: {total} events {'checked' if args.dry_run else 'scored'}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score existing events that do not have interest scores yet."
    )
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--once", action="store_true", help="Process one batch only")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Rescore existing events up to --batch-size",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write scores")
    return parser.parse_args()


if __name__ == "__main__":
    main()
