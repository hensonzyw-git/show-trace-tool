"""FastAPI entrypoint for the show trace service API."""

from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

from app.auth import require_api_token
from app.database import count_events, database_exists, list_events, read_digest
from app.paths import ROOT
from app.pipeline import bootstrap_subscription, run_pipeline
from db import (
    create_run,
    finish_run,
    get_unnotified_events,
    list_runs,
    mark_notified,
    save_subscription,
    upsert_event,
)
from notifiers.feishu import FeishuNotifier
from notifiers.feishu_app import FeishuAppNotifier
from notifiers.markdown import MarkdownNotifier

load_dotenv(ROOT / ".env")

app = FastAPI(
    title="Show Trace Tool API",
    description="API for daily performance digests, subscriptions, and worker runs.",
    version="0.4.0",
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


class ImportEvent(BaseModel):
    type: Literal["concert", "exhibition", "activity"]
    title: str
    artist: str | None = None
    city: str | None = None
    venue: str | None = None
    event_date: str | None = None
    on_sale_time: str | None = None
    price_info: str | None = None
    purchase_url: str | None = None
    source: str
    source_url: str | None = None
    raw_ref: str | None = None
    discovered_via: str | None = None
    status: str = "rumored"

    @field_validator("title", "source")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class ImportEventsRequest(BaseModel):
    events: list[ImportEvent] = Field(default_factory=list, max_length=500)
    notify: bool = False
    trigger: str = "local-sync"


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


@app.post("/api/events/import")
def import_events(
    payload: ImportEventsRequest,
    _: None = Depends(require_api_token),
) -> dict[str, Any]:
    """Import structured events from local assisted/browser sources."""
    if not payload.events:
        raise HTTPException(status_code=400, detail="events must not be empty")

    run_id = create_run(trigger=payload.trigger, fixture=False, notify=payload.notify)
    imported: list[dict[str, Any]] = []
    new_events = 0
    errors: list[str] = []
    notified_events = 0

    try:
        for item in payload.events:
            event = item.model_dump()
            event_id, is_new = upsert_event(event)
            if is_new:
                new_events += 1
            imported.append(
                {
                    "id": event_id,
                    "is_new": is_new,
                    "title": event["title"],
                    "source": event["source"],
                }
            )

        if payload.notify:
            try:
                unnotified = get_unnotified_events()
                for notifier in (
                    MarkdownNotifier(),
                    FeishuNotifier(),
                    FeishuAppNotifier(),
                ):
                    notifier.notify(unnotified)
                mark_notified([event["id"] for event in unnotified])
                notified_events = len(unnotified)
            except Exception as e:
                errors.append(f"notify: {e}")
    except Exception as e:
        errors.append(f"import: {e}")

    status = "partial_success" if errors and imported else "failed" if errors else "success"
    finish_run(
        run_id,
        status=status,
        total_raw_captures=0,
        total_extracted_events=len(payload.events),
        new_events=new_events,
        notified_events=notified_events,
        error_summary="\n".join(errors) if errors else None,
    )
    if errors and not imported:
        raise HTTPException(status_code=500, detail=errors)

    return {
        "run_id": run_id,
        "status": status,
        "total_events": len(payload.events),
        "imported_events": len(imported),
        "new_events": new_events,
        "updated_events": len(imported) - new_events,
        "notified_events": notified_events,
        "errors": errors,
        "items": imported,
    }


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
