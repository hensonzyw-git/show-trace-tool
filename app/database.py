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


@contextmanager
def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
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
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return events with lightweight filters for the first API milestone."""
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
            SELECT *
            FROM events
            {clause}
            ORDER BY event_date IS NULL, event_date ASC, first_seen DESC
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
    if date_from:
        where.append("event_date >= ?")
        params.append(date_from)
    if date_to:
        where.append("event_date <= ?")
        params.append(date_to)

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with _conn() as c:
        row = c.execute(f"SELECT COUNT(*) AS count FROM events {clause}", params).fetchone()
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
