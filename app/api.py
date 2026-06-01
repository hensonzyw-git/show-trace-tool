"""FastAPI entrypoint for the service-side Phase 1 API."""

from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query

from app.database import count_events, database_exists, list_events, read_digest

app = FastAPI(
    title="Show Trace Tool API",
    description="Read-only API for daily performance and activity digests.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "database": "ready" if database_exists() else "missing",
    }


@app.get("/api/events")
def get_events(
    city: str | None = None,
    type: Literal["concert", "exhibition", "activity"] | None = None,
    source: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    filters = {
        "city": city,
        "event_type": type,
        "source": source,
        "date_from": date_from,
        "date_to": date_to,
    }
    return {
        "items": list_events(limit=limit, offset=offset, **filters),
        "total": count_events(**filters),
        "limit": limit,
        "offset": offset,
    }


@app.get("/api/digests/today")
def get_today_digest() -> dict[str, Any]:
    digest = read_digest()
    if digest is None:
        raise HTTPException(status_code=404, detail="Today's digest has not been generated")
    return digest
