"""Reusable daily collection pipeline.

Both the CLI worker (``main.py``) and the FastAPI manual trigger use this
module. Keeping the workflow here makes Phase 2/3 behave like a service without
breaking the existing launchd entrypoint.
"""

import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import yaml
from dotenv import load_dotenv

from db import (
    create_run,
    ensure_subscription_from_config,
    finish_run,
    get_unnotified_events,
    init_db,
    mark_notified,
    save_event_interest_score,
    try_acquire_run_lock,
    upsert_event,
)
from extractor import extract_events
from notifiers.feishu import FeishuNotifier
from notifiers.feishu_app import FeishuAppNotifier
from notifiers.macos import MacosNotifier
from notifiers.markdown import MarkdownNotifier
from sources.motianlun import MotianlunSource
from sources.showstart import ShowstartSource

# Damai needs patchright + a real Chrome; the cloud image does not install it
# (config.cloud.yaml keeps damai disabled). Import lazily so the API still boots
# when the browser stack is absent.
try:
    from sources.damai import DamaiSource
except ImportError:  # pragma: no cover - depends on optional browser deps
    DamaiSource = None
from app.paths import CONFIG_PATH, FIXTURE_DIR, RAW_DIR, ROOT
from app.preferences import get_current_interest_profile, score_events_for_interest

SOURCE_REGISTRY: dict[str, type] = {
    "showstart": ShowstartSource,
    "motianlun": MotianlunSource,
}
if DamaiSource is not None:
    SOURCE_REGISTRY["damai"] = DamaiSource


@dataclass
class PipelineStats:
    total_raw_captures: int = 0
    total_extracted_events: int = 0
    new_events: int = 0
    new_event_ids: list[str] = field(default_factory=list)
    notified_events: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.errors and self.total_raw_captures == 0 and self.total_extracted_events == 0:
            return "failed"
        if self.errors:
            return "partial_success"
        return "success"


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def bootstrap_subscription() -> dict[str, Any]:
    """Ensure the DB has a default subscription, seeded from config.yaml."""
    config = load_config()
    return ensure_subscription_from_config(config)


def _init_sources(sources_cfg: dict[str, Any]) -> list[Any]:
    sources = []
    disabled_sources = {
        name.strip()
        for name in os.environ.get("SHOW_TRACE_DISABLED_SOURCES", "").split(",")
        if name.strip()
    }
    for name, cls in SOURCE_REGISTRY.items():
        if name in disabled_sources:
            continue
        if (sources_cfg.get(name) or {}).get("enabled"):
            sources.append(cls())
    return sources


def init_profile_from_subscription() -> None:
    """Open GUI Chrome for Damai profile seeding, preserving the old CLI flow."""
    load_dotenv(ROOT / ".env")
    if DamaiSource is None:
        print("--init-profile 需要浏览器依赖（patchright），当前环境未安装。")
        return
    subscription = bootstrap_subscription()
    sources = _init_sources(subscription.get("sources") or {})
    damai = next((s for s in sources if isinstance(s, DamaiSource)), None)
    if not damai:
        print("--init-profile 仅大麦需要（sources.damai.enabled = true 才生效）")
        return

    artists = subscription.get("artists") or []
    local = subscription.get("local") or {}
    local_keywords = local.get("keywords") or []
    seed = artists[0] if artists else (local_keywords[0] if local_keywords else "周杰伦")
    print(f"[init-profile] 用 '{seed}' 打开大麦搜索页...")
    damai.init_profile(seed)


LOCK_BUSY_ERROR = "another run or import is already in progress"


def skipped_result(run_id: int | None) -> dict[str, Any]:
    """Response payload for a run that was rejected because one is in progress."""
    return {
        "run_id": run_id,
        "id": run_id,
        "status": "skipped",
        "total_raw_captures": 0,
        "total_extracted_events": 0,
        "new_events": 0,
        "new_event_ids": [],
        "notified_events": 0,
        "errors": [LOCK_BUSY_ERROR],
    }


def running_result(run_id: int) -> dict[str, Any]:
    """Response payload for a run that was accepted and is executing in the background."""
    return {
        "run_id": run_id,
        "id": run_id,
        "status": "running",
        "total_raw_captures": 0,
        "total_extracted_events": 0,
        "new_events": 0,
        "new_event_ids": [],
        "notified_events": 0,
        "errors": [],
    }


def _result_from_stats(run_id: int | None, stats: "PipelineStats") -> dict[str, Any]:
    """Response payload for a completed run."""
    return {
        "run_id": run_id,
        "id": run_id,
        "status": stats.status,
        "total_raw_captures": stats.total_raw_captures,
        "total_extracted_events": stats.total_extracted_events,
        "new_events": stats.new_events,
        "new_event_ids": stats.new_event_ids,
        "notified_events": stats.notified_events,
        "errors": stats.errors,
    }


def _run_and_finalize(
    run_id: int | None,
    subscription: dict[str, Any],
    *,
    use_fixture: bool,
    notify: bool,
) -> dict[str, Any]:
    """Execute the pipeline body and persist the outcome to ``run_id`` (if any).

    Caller is responsible for holding the run lock and creating the run row.
    """
    stats = PipelineStats()
    try:
        _run_pipeline_body(subscription, use_fixture=use_fixture, notify=notify, stats=stats)
    except Exception as e:
        stats.errors.append(f"pipeline: {e}")
        print(f"[pipeline] 失败: {e}")
    finally:
        if run_id is not None:
            finish_run(
                run_id,
                status=stats.status,
                total_raw_captures=stats.total_raw_captures,
                total_extracted_events=stats.total_extracted_events,
                new_events=stats.new_events,
                notified_events=stats.notified_events,
                error_summary="\n".join(stats.errors) if stats.errors else None,
            )
    return _result_from_stats(run_id, stats)


def run_pipeline(
    *,
    use_fixture: bool = False,
    notify: bool = True,
    trigger: str = "cli",
    record_run: bool = True,
) -> dict[str, Any]:
    """Run one full collection pass and optionally persist a run record.

    Guarded by a shared file lock: if a run/import is already in progress, this
    returns immediately with status "skipped" instead of starting another pass.
    """
    with try_acquire_run_lock() as acquired:
        if not acquired:
            print("[pipeline] 已有采集或导入在进行中，跳过本次触发")
            return skipped_result(None)

        load_dotenv(ROOT / ".env")
        init_db()
        subscription = bootstrap_subscription()
        run_id = create_run(trigger=trigger, fixture=use_fixture, notify=notify) if record_run else None
        return _run_and_finalize(run_id, subscription, use_fixture=use_fixture, notify=notify)


def run_pipeline_for_existing_run(
    run_id: int,
    *,
    use_fixture: bool = False,
    notify: bool = True,
) -> dict[str, Any]:
    """Run one collection pass for a run row that was already created.

    This lets the API return immediately after creating a run record while the
    actual worker continues in a FastAPI background task. The run row remains
    visible as ``running`` until this function updates it.
    """
    with try_acquire_run_lock() as acquired:
        if not acquired:
            finish_run(
                run_id,
                status="skipped",
                total_raw_captures=0,
                total_extracted_events=0,
                new_events=0,
                notified_events=0,
                error_summary=LOCK_BUSY_ERROR,
            )
            return skipped_result(run_id)

        load_dotenv(ROOT / ".env")
        init_db()
        subscription = bootstrap_subscription()
        return _run_and_finalize(run_id, subscription, use_fixture=use_fixture, notify=notify)


def _run_pipeline_body(
    subscription: dict[str, Any],
    *,
    use_fixture: bool,
    notify: bool,
    stats: PipelineStats,
) -> None:
    artists: list[str] = subscription.get("artists") or []
    local: dict[str, Any] = subscription.get("local") or {}
    local_city: str | None = local.get("city")
    local_keywords: list[str] = local.get("keywords") or []
    sources_cfg: dict[str, Any] = subscription.get("sources") or {}

    sources = _init_sources(sources_cfg)
    if not sources:
        msg = "没有启用任何 source（subscriptions.sources.*.enabled = true）"
        print(msg)
        stats.errors.append(msg)
        return

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if not artists and not local_keywords:
        msg = "订阅里的 artists 和 local.keywords 都为空，无事可做。"
        print(msg)
        stats.errors.append(msg)
        return

    all_events: list[dict[str, Any]] = []
    tasks = _build_tasks(artists, local_city, local_keywords)

    total_fetch_count = 0
    for source in sources:
        print(f"\n>>>>> source: {source.name} (interval={source.fetch_interval_range}) <<<<<")
        for task in tasks:
            if total_fetch_count > 0 and not use_fixture:
                lo, hi = source.fetch_interval_range
                interval = random.uniform(lo, hi)
                print(f"\n[interval] {interval:.1f}s ({source.name})")
                time.sleep(interval)
            events, captured, error = _run_one(
                source,
                query=task["query"],
                city=task["city"],
                description=task["description"],
                label=task["label"],
                use_fixture=use_fixture,
            )
            if captured:
                stats.total_raw_captures += 1
            if error:
                stats.errors.append(error)
            stats.total_extracted_events += len(events)
            all_events.extend(events)
            total_fetch_count += 1

    # Upsert first, then score only the events that are genuinely new this run.
    # Duplicate dicts across tasks collapse to the same id (is_new=False on the
    # second hit), so each new event is scored exactly once — and we avoid
    # re-spending LLM tokens re-scoring events already in the DB. Profile-change
    # rescoring is handled separately by /preferences/feedback and the backfill
    # script.
    new_to_score: list[tuple[str, dict[str, Any]]] = []
    for event in all_events:
        event_id, is_new = upsert_event(event)
        if is_new:
            stats.new_events += 1
            stats.new_event_ids.append(event_id)
            new_to_score.append((event_id, event))

    if new_to_score:
        interest_profile = get_current_interest_profile()
        scores = score_events_for_interest([e for _, e in new_to_score], interest_profile)
        for (event_id, _), interest_score in zip(new_to_score, scores, strict=True):
            save_event_interest_score(event_id, interest_score)
    print(
        f"\n=== 入库: {len(all_events)} 条抽取结果中 "
        f"{stats.new_events} 条是新事件 ==="
    )

    unnotified = get_unnotified_events()
    if notify:
        for notifier in (
            MarkdownNotifier(),
            MacosNotifier(),
            FeishuNotifier(),
            FeishuAppNotifier(),
        ):
            notifier.notify(unnotified)
        mark_notified([event["id"] for event in unnotified])
        stats.notified_events = len(unnotified)
    else:
        print(f"[notify] 跳过通知（{len(unnotified)} 条未通知事件保持原样）")

    if all_events:
        print(
            f"\n=== 本次共处理 {len(all_events)} 条事件，"
            f"通知 {stats.notified_events} 条 ==="
        )
    else:
        print("\n=== 本次未抽到任何结构化事件 ===")


def _build_tasks(
    artists: list[str],
    local_city: str | None,
    local_keywords: list[str],
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for artist in artists:
        tasks.append(
            {
                "query": artist,
                "city": None,
                "description": f"与艺人「{artist}」相关的演唱会 / 演出场次（任何城市）",
                "label": f"艺人={artist} (全国)",
            }
        )
    for keyword in local_keywords:
        tasks.append(
            {
                "query": keyword,
                "city": local_city,
                "description": f"在「{local_city}」举办的{keyword}相关的演出 / 展览 / 活动",
                "label": f"本地={keyword}@{local_city}",
            }
        )
    return tasks


def _run_one(
    source,
    *,
    query: str,
    city: str | None,
    description: str,
    label: str,
    use_fixture: bool,
) -> tuple[list[dict[str, Any]], bool, str | None]:
    """Run fetch + extraction for one source/task."""
    mode = "fixture" if use_fixture else "live"
    print(f"\n=== {source.name} | {label} | {mode} ===")
    fetched_at = datetime.now()

    if use_fixture:
        fixture = FIXTURE_DIR / f"{source.name}_{query}.html"
        if not fixture.exists():
            print(f"[fixture] 找不到 {fixture.relative_to(ROOT)}，跳过")
            return [], False, None
        raw = fixture.read_text(encoding="utf-8")
        url = f"fixture://{fixture.name}"
        raw_ref = str(fixture.relative_to(ROOT))
        print(f"[fixture] 使用 {fixture.relative_to(ROOT)} ({len(raw):,} 字节)")
    else:
        try:
            url, raw = source.fetch_raw(query, city=city)
        except Exception as e:
            error = f"{source.name} | {label}: {e}"
            print(f"[fetch] 失败: {e}")
            return [], False, error
        if not raw:
            print(f"[fetch] {source.name} 跳过此查询（不支持，如 city 未配置）")
            return [], False, None
        raw_path = source.raw_path(RAW_DIR, query, fetched_at)
        raw_path.write_text(raw, encoding="utf-8")
        raw_ref = _display_path(raw_path)
        print(f"[fetch] OK, HTML {len(raw):,} 字节 → {raw_ref}")

    events = extract_events(
        raw,
        description=description,
        source_url=url,
        source_name=source.name,
    )
    for event in events:
        event["raw_ref"] = raw_ref
        event["discovered_via"] = source.discovered_via(query, city)
    print(f"[extract] 抽到 {len(events)} 条结构化记录")
    return events, True, None


def _display_path(path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)
