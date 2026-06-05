"""飞书 webhook Notifier。

发一个 markdown 卡片到飞书群机器人。手机上能即时收到推送 + 点链接直达。

`.env` 没配 `FEISHU_WEBHOOK_URL` 时静默跳过，不影响其他 notifier。
适合 launchd 后台跑的场景 —— 你不在电脑前的时候手机也能收到推送。

设计：只推 Top 5（按日期升序、今天及以后），不推完整 digest —— 飞书消息有
长度限制，而且推完整列表反而让"快开始的几条"被淹没。完整 digest 仍在
本地 `data/digests/`，飞书消息末尾提示用户去那里看。
"""

import os

import requests

from notifiers.base import Notifier
from notifiers.feishu_card import build_card


class FeishuNotifier(Notifier):
    name = "feishu"

    def notify(self, events: list[dict]) -> None:
        webhook = os.environ.get("FEISHU_WEBHOOK_URL")
        if not webhook:
            return  # 未配置则静默跳过
        if not events:
            return

        card, upcoming = build_card(events)
        payload = {"msg_type": "interactive", "card": card}

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
