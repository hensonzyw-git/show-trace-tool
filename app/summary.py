"""每日「当日摘要」结构化快照。

产品语义（见 PRD Q1）：
- 当日摘要 = 当前 keep 且未过期（含日期待定）的演出，按兴趣分降序，取前 N 条。
- **快照、每日一次、不实时**：在每次采集运行结束时重建当天快照（覆盖当天文件）；
  当天还没有快照时，读取最近一份（即"前一日"）。
- 不保留更早历史（每天都是从全量重新筛，旧快照无保留价值）；这里只按文件留存，
  读取永远取最新一份，旧文件可由运维自行清理。

实现上快照持久化当时入选的事件对象，保证入选集合、顺序、分数和展示字段一起冻结。
旧版仅包含 event_ids 的快照仍可读取，用于部署迁移。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.database import get_events_by_ids, list_events
from app.paths import DIGEST_DIR

SUMMARY_LIMIT = 30
SUMMARY_PREFIX = "summary_"


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _score(event: dict[str, Any]) -> int:
    score = event.get("interest_match_score")
    return score if isinstance(score, int) else -1


def build_daily_summary(*, limit: int = SUMMARY_LIMIT, day: str | None = None) -> dict[str, Any]:
    """Rebuild today's snapshot from keep + unexpired events, score desc.

    Returns the persisted snapshot payload. Safe to call repeatedly (overwrites
    the day's file). Tied to the pipeline run so "每日更新" follows the data refresh.
    """
    day = day or _today()
    # keep + 未过期(含 event_date 为空的待定)；date_from 过滤已在 list_events 处理空日期。
    candidates = list_events(interest_decision="keep", date_from=day, limit=500)
    ranked = sorted(candidates, key=_score, reverse=True)[:limit]
    payload = {
        "date": day,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "event_ids": [event["id"] for event in ranked],
        "events": ranked,
    }
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    (DIGEST_DIR / f"{SUMMARY_PREFIX}{day}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    return payload


def _latest_summary_path():
    if not DIGEST_DIR.exists():
        return None
    files = sorted(DIGEST_DIR.glob(f"{SUMMARY_PREFIX}*.json"), reverse=True)
    return files[0] if files else None


def read_daily_summary() -> dict[str, Any] | None:
    """Read today's snapshot, falling back to the most recent (前一日)."""
    today_path = DIGEST_DIR / f"{SUMMARY_PREFIX}{_today()}.json"
    path = today_path if today_path.exists() else _latest_summary_path()
    if path is None:
        return None
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    events = snapshot.get("events")
    if not isinstance(events, list):
        events = get_events_by_ids(snapshot.get("event_ids") or [])
    return {
        "date": snapshot.get("date"),
        "generated_at": snapshot.get("generated_at"),
        "events": events,
        "event_count": len(events),
    }
