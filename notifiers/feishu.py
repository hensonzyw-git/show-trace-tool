"""飞书 webhook Notifier。

发一个 markdown 卡片到飞书群机器人。手机上能即时收到推送 + 点链接直达。

`.env` 没配 `FEISHU_WEBHOOK_URL` 时静默跳过，不影响其他 notifier。
适合 launchd 后台跑的场景 —— 你不在电脑前的时候手机也能收到推送。

设计：只推 Top 5（按日期升序、今天及以后），不推完整 digest —— 飞书消息有
长度限制，而且推完整列表反而让"快开始的几条"被淹没。完整 digest 仍在
本地 `data/digests/`，飞书消息末尾提示用户去那里看。
"""

import os
from datetime import datetime

import requests

from notifiers.base import Notifier

TOP_N = 5


class FeishuNotifier(Notifier):
    name = "feishu"

    def notify(self, events: list[dict]) -> None:
        webhook = os.environ.get("FEISHU_WEBHOOK_URL")
        if not webhook:
            return  # 未配置则静默跳过
        if not events:
            return

        # 复用 MarkdownNotifier 的日期排序逻辑（避免重复实现）
        from notifiers.markdown import MarkdownNotifier

        today = datetime.now().strftime("%Y-%m-%d")
        upcoming = sorted(
            [
                e for e in events
                if MarkdownNotifier._date_key(e.get("event_date")) >= today
            ],
            key=lambda e: MarkdownNotifier._date_key(e.get("event_date")),
        )[:TOP_N]

        # 主体 markdown
        lines: list[str] = [
            f"共 **{len(events)}** 条新事件（含已过期，仅展示最近 {len(upcoming)} 条）",
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

        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"📣 演出活动监控 - {today}",
                    },
                    "template": "blue",
                },
                "elements": [
                    {"tag": "markdown", "content": "\n".join(lines)},
                ],
            },
        }

        try:
            resp = requests.post(webhook, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[notify/feishu] 推送失败: {e}")
            return

        # 飞书机器人返回成功的字段历史上变过 (StatusCode / code)，兼容两种
        ok_codes = (data.get("StatusCode"), data.get("code"))
        if 0 in ok_codes:
            print(
                f"[notify/feishu] 推送成功（{len(events)} 条事件 / Top {len(upcoming)}）"
            )
        else:
            print(f"[notify/feishu] 推送返回异常: {data}")
