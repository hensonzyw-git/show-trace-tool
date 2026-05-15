"""里程碑 0 主流程：config → 抓取 → 落盘 → LLM 抽取 → print。

刻意不做：入库、去重、通知。这些是里程碑 1 的事。

支持 `--fixture` 模式：跳过抓取，从 data/fixtures/{source}_{artist}.html 读
预置 HTML 走抽取。用于在抓取源遇到反爬或暂时不可用时，独立验证 LLM 抽取链路。
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from extractor import extract_events
from sources.damai import DamaiSource

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.yaml"
RAW_DIR = ROOT / "data" / "raw"
FIXTURE_DIR = ROOT / "data" / "fixtures"


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="演出活动监控 - 里程碑 0")
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="跳过真实抓取，从 data/fixtures/ 读预置 HTML（用于验证抽取链路）",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    config = load_config()

    artists: list[str] = config.get("artists") or []
    city: str | None = config.get("city")
    sources_cfg: dict = config.get("sources") or {}

    if not artists:
        print("config.yaml 里 artists 为空，请至少配置一个艺人。")
        return

    if not sources_cfg.get("damai", {}).get("enabled", False):
        print("damai 源未启用 (config.yaml: sources.damai.enabled = true).")
        return

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    source = DamaiSource(city=city)
    all_events: list[dict] = []

    mode_label = "fixture" if args.fixture else "live"
    for artist in artists:
        print(f"\n=== {source.name} | 艺人: {artist} | 城市: {city} | 模式: {mode_label} ===")
        fetched_at = datetime.now()

        if args.fixture:
            fixture_file = FIXTURE_DIR / f"{source.name}_{artist}.html"
            if not fixture_file.exists():
                print(f"[fixture] 找不到 {fixture_file.relative_to(ROOT)}，跳过 {artist}")
                continue
            raw = fixture_file.read_text(encoding="utf-8")
            url = f"fixture://{fixture_file.name}"
            print(f"[fixture] 使用 {fixture_file.relative_to(ROOT)} ({len(raw):,} 字节)")
        else:
            try:
                url, raw = source.fetch_raw(artist)
            except Exception as e:
                print(f"[fetch] 失败: {e}")
                continue
            raw_path = source.raw_path(RAW_DIR, artist, fetched_at)
            raw_path.write_text(raw, encoding="utf-8")
            print(f"[fetch] OK, HTML {len(raw):,} 字节 → {raw_path.relative_to(ROOT)}")

        events = extract_events(raw, artist=artist, source_url=url)
        print(f"[extract] 抽到 {len(events)} 条结构化记录")
        for e in events:
            print(json.dumps(e, ensure_ascii=False, indent=2))
        all_events.extend(events)

    print()
    if all_events:
        print(f"=== 共 {len(all_events)} 条事件 ===")
    else:
        print("=== 本次未抽到任何结构化事件 ===")


if __name__ == "__main__":
    main()
