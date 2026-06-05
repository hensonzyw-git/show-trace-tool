"""Markdown 摘要 Notifier：把事件渲染成 Markdown 文件落到 data/digests/。

结构：
- 顶部 `⭐ 最近就开始 (Top N)`：今天及以后的事件按日期升序前 N 条，让用户
  打开 digest 就看到"快开始的几条"，不用从分组列表里翻
- 主体按 type 分组（concert / exhibition / activity / other），加 emoji
- 每个 type 组内按日期升序（近的优先）

事件渲染包含 discovered_via（"在哪 App 复现搜索"）和 purchase_url
（桌面直接打开），分别覆盖两种使用模式。
"""

import re
from datetime import datetime

from app.paths import DIGEST_DIR
from notifiers.base import Notifier

TYPE_LABEL = {
    "concert": "🎤 演唱会 / 演出",
    "exhibition": "🖼  展览",
    "activity": "🎉 活动",
}

# 抓取常见日期格式的首个匹配，规范成 YYYY-MM-DD 用于排序。
# 兼容 "2026-06-20"、"2026.05.16-05.17"、"2026年5月20日" 等
DATE_PATTERN = re.compile(r"(\d{4})[-./年](\d{1,2})[-./月](\d{1,2})")

TOP_N = 5
NO_DATE_KEY = "9999-12-31"


class MarkdownNotifier(Notifier):
    name = "markdown"

    def notify(self, events: list[dict]) -> None:
        if not events:
            print("[notify/markdown] 无待通知事件，不生成摘要")
            return

        DIGEST_DIR.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        path = DIGEST_DIR / f"digest_{today}.md"

        lines: list[str] = [
            f"# 演出活动监控摘要 - {today}",
            "",
            f"共 **{len(events)}** 条待通知事件。",
            "",
        ]

        # Top N：今天及以后开始的事件，按日期升序前 N 条
        upcoming = sorted(
            [e for e in events if self._date_key(e.get("event_date")) >= today],
            key=lambda e: self._date_key(e.get("event_date")),
        )[:TOP_N]
        if upcoming:
            lines.append("---")
            lines.append("")
            lines.append(f"## ⭐ 最近就开始 (Top {len(upcoming)})")
            lines.append("")
            for e in upcoming:
                lines.extend(self._render_event(e))
            lines.append("")

        # 主体：只显示今天及以后的事件（过期演出 + 抽不到日期的归到末尾隐藏区，
        # 它们对"我要买票看什么"决策无价值）。按 type 分组，组内按日期升序。
        fresh = [e for e in events if self._date_key(e.get("event_date")) >= today]
        hidden_count = len(events) - len(fresh)

        by_type: dict[str, list[dict]] = {}
        for e in fresh:
            by_type.setdefault(e.get("type") or "other", []).append(e)

        lines.append("---")
        lines.append("")
        for typ in ("concert", "exhibition", "activity", "other"):
            group = by_type.get(typ)
            if not group:
                continue
            group_sorted = sorted(
                group, key=lambda e: self._date_key(e.get("event_date"))
            )
            label = TYPE_LABEL.get(typ, typ)
            lines.append(f"## {label} ({len(group)} 条，按日期排序)")
            lines.append("")
            for e in group_sorted:
                lines.extend(self._render_event(e))
            lines.append("")

        if hidden_count:
            lines.append("---")
            lines.append("")
            lines.append(f"_另有 {hidden_count} 条事件已过期或无日期信息，已隐藏。_")
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")
        rel = path.relative_to(DIGEST_DIR.parent.parent)
        print(f"[notify/markdown] 摘要写入 {rel} ({len(events)} 条)")

    @staticmethod
    def _date_key(date_str) -> str:
        """从 event_date 提取首个日期，规范成 YYYY-MM-DD。无法解析返回排末尾的值。"""
        if not date_str:
            return NO_DATE_KEY
        m = DATE_PATTERN.search(str(date_str))
        if not m:
            return NO_DATE_KEY
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"

    @staticmethod
    def _render_event(e: dict) -> list[str]:
        title = (e.get("title") or "(无标题)").strip()
        out = [f"### {title}"]
        if e.get("artist"):
            out.append(f"- 艺人: {e['artist']}")
        loc = " / ".join(filter(None, [e.get("city"), e.get("venue")]))
        if loc:
            out.append(f"- 地点: {loc}")
        if e.get("event_date"):
            out.append(f"- 日期: {e['event_date']}")
        if e.get("on_sale_time"):
            out.append(f"- 开票: {e['on_sale_time']}")
        if e.get("price_info"):
            out.append(f"- 票价: {e['price_info']}")
        if e.get("discovered_via"):
            out.append(f"- 🔍 在哪看到: {e['discovered_via']}")
        if e.get("purchase_url"):
            out.append(f"- [→ 桌面直接打开详情页]({e['purchase_url']})")
        out.append("")
        return out
