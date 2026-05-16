"""飞书自建应用 Notifier (open-apis/im/v1/messages)。

跟 FeishuNotifier (webhook) 的区别：
- webhook 绑某个群，只能推到那个群，配置简单 (一个 URL)
- self-built app 用 app_id + app_secret 换 token，能推到任何 chat / user /
  email，更灵活，但要在飞书开放平台后台申请 im:message:send_as_bot 权限

需要在 `.env` 配（缺任何一个就静默跳过）：
- FEISHU_APP_ID       = cli_xxxxxx
- FEISHU_APP_SECRET   = xxxxxx
- FEISHU_RECEIVE_ID   = oc_xxx (chat_id) / ou_xxx (open_id) / 邮箱
- FEISHU_RECEIVE_ID_TYPE = chat_id (默认) | open_id | email | user_id

flow:
1. POST /auth/v3/tenant_access_token/internal {app_id, app_secret} → token
2. POST /im/v1/messages?receive_id_type=... + Bearer token → 发 card
"""

import json
import os
from datetime import datetime

import requests

from notifiers.base import Notifier

TOP_N = 5
TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
SEND_MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"


class FeishuAppNotifier(Notifier):
    name = "feishu-app"

    def notify(self, events: list[dict]) -> None:
        app_id = os.environ.get("FEISHU_APP_ID")
        app_secret = os.environ.get("FEISHU_APP_SECRET")
        receive_id = os.environ.get("FEISHU_RECEIVE_ID")
        receive_id_type = os.environ.get("FEISHU_RECEIVE_ID_TYPE", "chat_id")

        if not (app_id and app_secret and receive_id):
            return  # 未配置则静默跳过
        if not events:
            return

        # 1. 拿 tenant_access_token
        try:
            r = requests.post(
                TOKEN_URL,
                json={"app_id": app_id, "app_secret": app_secret},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[notify/feishu-app] token 请求失败: {e}")
            return
        if data.get("code") != 0 or "tenant_access_token" not in data:
            print(f"[notify/feishu-app] token 返回异常: {data}")
            return
        token = data["tenant_access_token"]

        # 2. 构造 markdown card（跟 FeishuNotifier webhook 版同形）
        from notifiers.markdown import MarkdownNotifier

        today = datetime.now().strftime("%Y-%m-%d")
        upcoming = sorted(
            [
                e for e in events
                if MarkdownNotifier._date_key(e.get("event_date")) >= today
            ],
            key=lambda e: MarkdownNotifier._date_key(e.get("event_date")),
        )[:TOP_N]

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

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📣 演出活动监控 - {today}",
                },
                "template": "blue",
            },
            "elements": [{"tag": "markdown", "content": "\n".join(lines)}],
        }

        # 3. 调 im/v1/messages —— content 必须是 JSON-encoded 字符串（不是 dict）
        payload = {
            "receive_id": receive_id,
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False),
        }
        try:
            r = requests.post(
                f"{SEND_MESSAGE_URL}?receive_id_type={receive_id_type}",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                timeout=10,
            )
            r.raise_for_status()
            result = r.json()
        except Exception as e:
            print(f"[notify/feishu-app] 发消息失败: {e}")
            return

        if result.get("code") == 0:
            print(
                f"[notify/feishu-app] 推送成功（{len(events)} 条事件 / "
                f"Top {len(upcoming)} / receive_id_type={receive_id_type}）"
            )
        else:
            print(f"[notify/feishu-app] 推送返回异常: {result}")
