"""FastAPI entrypoint for the show trace service API."""

from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

from app.auth import require_api_token
from app.database import count_events, database_exists, list_events, read_digest
from app.paths import ROOT
load_dotenv(ROOT / ".env")

from app.pipeline import bootstrap_subscription, run_pipeline
from app.preferences import (
    get_current_interest_profile,
    parse_preference_feedback,
    score_events_for_interest,
)
from db import (
    create_run,
    finish_run,
    get_event_interest_score,
    get_unnotified_events,
    init_db,
    list_runs,
    mark_notified,
    save_event_interest_score,
    save_subscription,
    upsert_event,
)
from notifiers.feishu import FeishuNotifier
from notifiers.feishu_app import FeishuAppNotifier
from notifiers.markdown import MarkdownNotifier


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create schema + seed the default subscription once at boot, so request
    # handlers never run DDL on the hot read path (see H1 in CODE_REVIEW.md).
    init_db()
    bootstrap_subscription()
    yield


app = FastAPI(
    title="Show Trace Tool API",
    description="API for daily performance digests, subscriptions, and worker runs.",
    version="0.4.0",
    lifespan=lifespan,
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


class PreferenceFeedbackRequest(BaseModel):
    feedback: str = Field(min_length=1, max_length=2000)
    event_id: str | None = None
    rescore_existing: bool = True
    rescore_limit: int = Field(default=500, ge=0, le=500)


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
    interest_decision: Literal["keep", "maybe", "filter"] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    filters = {
        "city": city,
        "event_type": type,
        "source": source,
        "interest_decision": interest_decision,
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


@app.get("/api/preferences")
def get_preferences(_: None = Depends(require_api_token)) -> dict[str, Any]:
    return get_current_interest_profile()


@app.post("/api/preferences/feedback")
def update_preferences_from_feedback(
    payload: PreferenceFeedbackRequest,
    _: None = Depends(require_api_token),
) -> dict[str, Any]:
    result = parse_preference_feedback(payload.feedback)
    result["event_id"] = payload.event_id
    result["rescored_events"] = _rescore_existing_events(
        limit=payload.rescore_limit,
        enabled=payload.rescore_existing,
    )
    return result


def _rescore_existing_events(*, limit: int, enabled: bool) -> int:
    if not enabled or limit <= 0:
        return 0

    from db import get_events_for_interest_scoring

    profile = get_current_interest_profile()
    events = get_events_for_interest_scoring(limit=limit)
    scores = score_events_for_interest(events, profile)
    for event, score in zip(events, scores, strict=True):
        save_event_interest_score(event["id"], score)
    return len(events)


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
        event_payloads = [item.model_dump() for item in payload.events]

        # Upsert first; only score events that are new or have no score yet, so
        # re-importing the same event doesn't re-spend LLM tokens.
        upserted: list[dict[str, Any]] = []
        to_score: list[int] = []
        for event in event_payloads:
            event_id, is_new = upsert_event(event)
            if is_new:
                new_events += 1
            existing_score = None if is_new else get_event_interest_score(event_id)
            row = {
                "id": event_id,
                "is_new": is_new,
                "title": event["title"],
                "source": event["source"],
                "interest_score": existing_score,
                "_event": event,
            }
            if is_new or existing_score is None:
                to_score.append(len(upserted))
            upserted.append(row)

        if to_score:
            interest_profile = get_current_interest_profile()
            fresh_scores = score_events_for_interest(
                [upserted[i]["_event"] for i in to_score], interest_profile
            )
            for i, interest_score in zip(to_score, fresh_scores, strict=True):
                save_event_interest_score(upserted[i]["id"], interest_score)
                upserted[i]["interest_score"] = interest_score

        for row in upserted:
            row.pop("_event", None)
            imported.append(row)

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
