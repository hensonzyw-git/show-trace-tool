"""FastAPI entrypoint for the show trace service API."""

from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from app.auth import require_api_token
from app.database import count_events, database_exists, list_events, read_digest
from app.paths import ROOT
from app.pipeline import bootstrap_subscription, run_pipeline
from db import list_runs, save_subscription

load_dotenv(ROOT / ".env")

app = FastAPI(
    title="Show Trace Tool API",
    description="API for daily performance digests, subscriptions, and worker runs.",
    version="0.3.0",
)


class LocalSubscription(BaseModel):
    city: str | None = None
    keywords: list[str] = Field(default_factory=list)


class SubscriptionPayload(BaseModel):
    artists: list[str] = Field(default_factory=list)
    local: LocalSubscription = Field(default_factory=LocalSubscription)
    sources: dict[str, dict[str, Any]] = Field(default_factory=dict)


class RunRequest(BaseModel):
    fixture: bool = False
    notify: bool = True


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "database": "ready" if database_exists() else "missing",
    }


@app.get("/api/events")
def get_events(
    _: None = Depends(require_api_token),
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
def get_today_digest(_: None = Depends(require_api_token)) -> dict[str, Any]:
    digest = read_digest()
    if digest is None:
        raise HTTPException(status_code=404, detail="Today's digest has not been generated")
    return digest


@app.get("/api/subscriptions")
def get_default_subscription(_: None = Depends(require_api_token)) -> dict[str, Any]:
    return bootstrap_subscription()


@app.put("/api/subscriptions")
def update_default_subscription(
    payload: SubscriptionPayload,
    _: None = Depends(require_api_token),
) -> dict[str, Any]:
    return save_subscription(payload.model_dump())


@app.post("/api/runs")
def create_manual_run(
    payload: RunRequest,
    _: None = Depends(require_api_token),
) -> dict[str, Any]:
    return run_pipeline(
        use_fixture=payload.fixture,
        notify=payload.notify,
        trigger="api",
    )


@app.get("/api/runs")
def get_runs(
    _: None = Depends(require_api_token),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return {
        "items": list_runs(limit=limit, offset=offset),
        "limit": limit,
        "offset": offset,
    }
