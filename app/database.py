"""Read-only database helpers for the Phase 1 API.

The existing root-level ``db.py`` remains the write path for the local worker.
This module gives the API a small query surface without changing the current
daily pipeline.
"""

from contextlib import contextmanager
from datetime import datetime
from typing import Any
import sqlite3

from app.paths import DB_PATH, DIGEST_DIR, ROOT
from db import apply_pragmas


@contextmanager
def _conn():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    apply_pragmas(c)
    try:
        yield c
    finally:
        c.close()


def database_exists() -> bool:
    return DB_PATH.exists()


def list_events(
    *,
    city: str | None = None,
    event_type: str | None = None,
    source: str | None = None,
    interest_decision: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return events with lightweight filters for the first API milestone."""
    # DB schema is created once at app startup (see app.api lifespan), so the
    # read path no longer triggers a DDL write-lock on every request.
    if not database_exists():
        return []

    where: list[str] = []
    params: list[Any] = []

    if city:
        where.append("city = ?")
        params.append(city)
    if event_type:
        where.append("type = ?")
        params.append(event_type)
    if source:
        where.append("source = ?")
        params.append(source)
    if interest_decision:
        where.append("scores.decision = ?")
        params.append(interest_decision)
    if date_from:
        where.append("event_date >= ?")
        params.append(date_from)
    if date_to:
        where.append("event_date <= ?")
        params.append(date_to)

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    params.extend([limit, offset])

    with _conn() as c:
        rows = c.execute(
            f"""
            SELECT
                events.*,
                scores.decision AS interest_decision,
                scores.match_score AS interest_match_score,
                scores.interest_category AS interest_category,
                scores.reason AS interest_reason,
                scores.uncertainty AS interest_uncertainty,
                scores.scored_at AS interest_scored_at
            FROM events
            LEFT JOIN event_interest_scores AS scores
                ON scores.event_id = events.id
            {clause}
            ORDER BY events.event_date IS NULL, events.event_date ASC, events.first_seen DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def count_events(
    *,
    city: str | None = None,
    event_type: str | None = None,
    source: str | None = None,
    interest_decision: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> int:
    if not database_exists():
        return 0

    where: list[str] = []
    params: list[Any] = []
    if city:
        where.append("city = ?")
        params.append(city)
    if event_type:
        where.append("type = ?")
        params.append(event_type)
    if source:
        where.append("source = ?")
        params.append(source)
    if interest_decision:
        where.append("scores.decision = ?")
        params.append(interest_decision)
    if date_from:
        where.append("event_date >= ?")
        params.append(date_from)
    if date_to:
        where.append("event_date <= ?")
        params.append(date_to)

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with _conn() as c:
        row = c.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM events
            LEFT JOIN event_interest_scores AS scores
                ON scores.event_id = events.id
            {clause}
            """,
            params,
        ).fetchone()
    return int(row["count"] if row else 0)


def read_digest(day: str | None = None) -> dict[str, Any] | None:
    """Read a generated Markdown digest from disk."""
    digest_date = day or datetime.now().strftime("%Y-%m-%d")
    path = DIGEST_DIR / f"digest_{digest_date}.md"
    if not path.exists():
        return None

    markdown = path.read_text(encoding="utf-8")
    return {
        "date": digest_date,
        "markdown": markdown,
        "path": str(path.relative_to(ROOT)),
        "event_count": _extract_event_count(markdown),
    }


def _extract_event_count(markdown: str) -> int | None:
    for line in markdown.splitlines():
        if line.startswith("共 **") and "** 条" in line:
            count_text = line.removeprefix("共 **").split("** 条", 1)[0]
            try:
                return int(count_text)
            except ValueError:
                return None
    return None
