"""主流程：config → 抓取 → 落盘 → LLM 抽取 → 入库去重 → Markdown 通知。

两个并行维度：
- 维度 1：artists（关注艺人，全国巡演不限城市）
- 维度 2：local.keywords + local.city（上海本地发现）

支持 `--fixture` 模式：跳过抓取，从 data/fixtures/{source}_{query}.html
读预置 HTML，用于在抓取暂不可用时验证抽取链路。

支持 `--init-profile` 模式：开 GUI Chrome 让用户手动浏览一次大麦，
建立 .browser-profile/，后续 headless 跑就复用这个 profile。
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from db import get_unnotified_events, init_db, mark_notified, upsert_event
from extractor import extract_events
from notifiers.markdown import MarkdownNotifier
from sources.damai import DamaiSource

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.yaml"
RAW_DIR = ROOT / "data" / "raw"
FIXTURE_DIR = ROOT / "data" / "fixtures"


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _run_one(
    source,
    *,
    query: str,
    city: str | None,
    description: str,
    label: str,
    use_fixture: bool,
) -> list[dict]:
    """跑一次"抓取 + 抽取"，返回结构化事件列表。"""
    mode = "fixture" if use_fixture else "live"
    print(f"\n=== {source.name} | {label} | {mode} ===")
    fetched_at = datetime.now()

    if use_fixture:
        fixture = FIXTURE_DIR / f"{source.name}_{query}.html"
        if not fixture.exists():
            print(f"[fixture] 找不到 {fixture.relative_to(ROOT)}，跳过")
            return []
        raw = fixture.read_text(encoding="utf-8")
        url = f"fixture://{fixture.name}"
        raw_ref = str(fixture.relative_to(ROOT))
        print(f"[fixture] 使用 {fixture.relative_to(ROOT)} ({len(raw):,} 字节)")
    else:
        try:
            url, raw = source.fetch_raw(query, city=city)
        except Exception as e:
            print(f"[fetch] 失败: {e}")
            return []
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
    for e in events:
        e["raw_ref"] = raw_ref
    print(f"[extract] 抽到 {len(events)} 条结构化记录")
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description="演出活动监控")
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="跳过真实抓取，从 data/fixtures/ 读预置 HTML（用于验证抽取链路）",
    )
    parser.add_argument(
        "--init-profile",
        action="store_true",
        help="开 GUI Chrome 让你手动浏览一次大麦，养 .browser-profile/（首次必跑）",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    config = load_config()

    artists: list[str] = config.get("artists") or []
    local: dict = config.get("local") or {}
    local_city: str | None = local.get("city")
    local_keywords: list[str] = local.get("keywords") or []
    sources_cfg: dict = config.get("sources") or {}

    if not sources_cfg.get("damai", {}).get("enabled", False):
        print("damai 源未启用 (config.yaml: sources.damai.enabled = true).")
        return

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    source = DamaiSource()

    if args.init_profile:
        seed = artists[0] if artists else (local_keywords[0] if local_keywords else "周杰伦")
        print(f"[init-profile] 用 '{seed}' 打开大麦搜索页...")
        source.init_profile(seed)
        return

    if not artists and not local_keywords:
        print("config.yaml 里 artists 和 local.keywords 都为空，无事可做。")
        return

    init_db()
    all_events: list[dict] = []

    # 维度 1: 关注艺人，全国巡演都看
    for artist in artists:
        events = _run_one(
            source,
            query=artist,
            city=None,
            description=f"与艺人「{artist}」相关的演唱会 / 演出场次（任何城市）",
            label=f"艺人={artist} (全国)",
            use_fixture=args.fixture,
        )
        all_events.extend(events)

    # 维度 2: 上海本地发现
    for keyword in local_keywords:
        events = _run_one(
            source,
            query=keyword,
            city=local_city,
            description=f"在「{local_city}」举办的{keyword}相关的演出 / 展览 / 活动",
            label=f"本地={keyword}@{local_city}",
            use_fixture=args.fixture,
        )
        all_events.extend(events)

    # 入库 + 去重
    new_count = 0
    for e in all_events:
        _, is_new = upsert_event(e)
        if is_new:
            new_count += 1
    print(f"\n=== 入库: {len(all_events)} 条抽取结果中 {new_count} 条是新事件 ===")

    # 通知（只处理 notified_at IS NULL 的）
    unnotified = get_unnotified_events()
    notifier = MarkdownNotifier()
    notifier.notify(unnotified)
    mark_notified([e["id"] for e in unnotified])

    if all_events:
        print(f"\n=== 本次共处理 {len(all_events)} 条事件，通知 {len(unnotified)} 条 ===")
    else:
        print("\n=== 本次未抽到任何结构化事件 ===")


if __name__ == "__main__":
    main()
