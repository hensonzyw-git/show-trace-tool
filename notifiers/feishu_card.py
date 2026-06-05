"""飞书卡片构造（webhook 版和自建应用版共用）。

两个 notifier（FeishuNotifier / FeishuAppNotifier）此前各自维护一份完全相同
的卡片渲染逻辑，改一处要记得改两处。抽到这里统一维护。
"""

from datetime import datetime
from typing import Any

TOP_N = 5


def _upcoming_events(events: list[dict], today: str) -> list[dict]:
    from notifiers.markdown import MarkdownNotifier

    return sorted(
        [e for e in events if MarkdownNotifier._date_key(e.get("event_date")) >= today],
        key=lambda e: MarkdownNotifier._date_key(e.get("event_date")),
    )[:TOP_N]


def build_card_lines(events: list[dict], today: str) -> tuple[list[str], list[dict]]:
    """返回 (markdown 行列表, 实际展示的 upcoming 事件)。

    events 是「全部待通知事件」（含已过期），卡片只展示最近 Top N 条。
    """
    upcoming = _upcoming_events(events, today)
    lines: list[str] = [
        f"共 **{len(events)}** 条待通知事件（含已过期，仅展示最近 {len(upcoming)} 条）",
        "",
    ]
    for i, e in enumerate(upcoming, 1):
        title = (e.get("title") or "?").strip()[:60]
        lines.append(f"**{i}. {title}**")
        if e.get("artist"):
            lines.append(f"艺人：{e['artist']}")
        loc = " / ".join(filter(None, [e.get("city"), e.get("venue")]))
        if loc:
            lines.append(f"📍 {loc}")
        if e.get("event_date"):
            lines.append(f"📅 {e['event_date']}")
        if e.get("price_info"):
            lines.append(f"💰 {e['price_info']}")
        if e.get("discovered_via"):
            lines.append(f"🔍 {e['discovered_via']}")
        if e.get("purchase_url"):
            lines.append(f"[→ 详情链接]({e['purchase_url']})")
        lines.append("")
    lines.append("---")
    lines.append(f"完整 digest 见本地 `data/digests/digest_{today}.md`")
    return lines, upcoming


def build_card(events: list[dict], today: str | None = None) -> tuple[dict[str, Any], list[dict]]:
    """构造飞书 interactive 卡片体。返回 (card, upcoming)。"""
    today = today or datetime.now().strftime("%Y-%m-%d")
    lines, upcoming = build_card_lines(events, today)
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"📣 演出活动监控 - {today}"},
            "template": "blue",
        },
        "elements": [{"tag": "markdown", "content": "\n".join(lines)}],
    }
    return card, upcoming
