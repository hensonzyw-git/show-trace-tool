"""Markdown 摘要 Notifier：把事件渲染成 Markdown 文件落到 data/digests/。

按 type（concert / exhibition / activity）分组，方便人眼扫读。
"""

from datetime import datetime
from pathlib import Path

from notifiers.base import Notifier

DIGEST_DIR = Path(__file__).resolve().parent.parent / "data" / "digests"

TYPE_LABEL = {
    "concert": "🎤 演唱会 / 演出",
    "exhibition": "🖼  展览",
    "activity": "🎉 活动",
}


class MarkdownNotifier(Notifier):
    name = "markdown"

    def notify(self, events: list[dict]) -> None:
        if not events:
            print("[notify/markdown] 无新事件，不生成摘要")
            return

        DIGEST_DIR.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        path = DIGEST_DIR / f"digest_{today}.md"

        # 按 type 分组
        by_type: dict[str, list[dict]] = {}
        for e in events:
            by_type.setdefault(e.get("type") or "other", []).append(e)

        lines: list[str] = [
            f"# 演出活动监控摘要 - {today}",
            "",
            f"共 **{len(events)}** 条新事件。",
            "",
        ]

        for typ in ("concert", "exhibition", "activity", "other"):
            group = by_type.get(typ)
            if not group:
                continue
            label = TYPE_LABEL.get(typ, typ)
            lines.append(f"## {label} ({len(group)} 条)")
            lines.append("")
            for e in group:
                lines.extend(self._render_event(e))
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")
        rel = path.relative_to(DIGEST_DIR.parent.parent)
        print(f"[notify/markdown] 摘要写入 {rel} ({len(events)} 条)")

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
        if e.get("source_url"):
            out.append(f"- 来源: [{e.get('source') or '?'}]({e['source_url']})")
        out.append("")
        return out
