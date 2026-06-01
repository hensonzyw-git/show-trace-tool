"""Reusable daily collection pipeline.

Both the CLI worker (``main.py``) and the FastAPI manual trigger use this
module. Keeping the workflow here makes Phase 2/3 behave like a service without
breaking the existing launchd entrypoint.
"""

import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
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
    upsert_event,
)
from extractor import extract_events
from notifiers.feishu import FeishuNotifier
from notifiers.feishu_app import FeishuAppNotifier
from notifiers.macos import MacosNotifier
from notifiers.markdown import MarkdownNotifier
from sources.damai import DamaiSource
from sources.motianlun import MotianlunSource
from sources.showstart import ShowstartSource

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
RAW_DIR = ROOT / "data" / "raw"
FIXTURE_DIR = ROOT / "data" / "fixtures"

SOURCE_REGISTRY: dict[str, type] = {
    "damai": DamaiSource,
    "showstart": ShowstartSource,
    "motianlun": MotianlunSource,
}


@dataclass
class PipelineStats:
    total_raw_captures: int = 0
    total_extracted_events: int = 0
    new_events: int = 0
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
    for name, cls in SOURCE_REGISTRY.items():
        if (sources_cfg.get(name) or {}).get("enabled"):
            sources.append(cls())
    return sources


def init_profile_from_subscription() -> None:
    """Open GUI Chrome for Damai profile seeding, preserving the old CLI flow."""
    load_dotenv(ROOT / ".env")
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


def run_pipeline(
    *,
    use_fixture: bool = False,
    notify: bool = True,
    trigger: str = "cli",
    record_run: bool = True,
) -> dict[str, Any]:
    """Run one full collection pass and optionally persist a run record."""
    load_dotenv(ROOT / ".env")
    init_db()
    subscription = bootstrap_subscription()
    run_id = create_run(trigger=trigger, fixture=use_fixture, notify=notify) if record_run else None
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

    result = {
        "run_id": run_id,
        "status": stats.status,
        "total_raw_captures": stats.total_raw_captures,
        "total_extracted_events": stats.total_extracted_events,
        "new_events": stats.new_events,
        "notified_events": stats.notified_events,
        "errors": stats.errors,
    }
    if run_id is not None:
        result["id"] = run_id
    return result


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

    for event in all_events:
        _, is_new = upsert_event(event)
        if is_new:
            stats.new_events += 1
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
        raw_ref = str(raw_path.relative_to(ROOT))
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
