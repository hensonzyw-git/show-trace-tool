"""macOS 系统通知 Notifier。

跑完 main.py 弹一个原生通知，告诉用户"今天 N 条新事件，看 digest"。
用 osascript（macOS 自带），不需要装 terminal-notifier 等额外依赖。

第一次跑会弹"是否允许 Python 发送通知"，授权后后续无感。
launchd 后台跑时通知会进 macOS 通知中心，用户解锁后能看到。

设计上跟 MarkdownNotifier 并列：Markdown 写文件给用户看完整内容，
macOS 通知作为"有新东西，去看 digest"的提醒。
"""

import subprocess

from notifiers.base import Notifier


class MacosNotifier(Notifier):
    name = "macos"

    def notify(self, events: list[dict]) -> None:
        if not events:
            return  # 无新事件不打扰

        title = "演出活动监控"
        subtitle = f"{len(events)} 条新事件"
        # 拿"按日期升序最近一条"作 message，让用户预览本次最有用的事件
        from notifiers.markdown import MarkdownNotifier

        def date_key(e):
            return MarkdownNotifier._date_key(e.get("event_date"))

        sorted_events = sorted(events, key=date_key)
        first_title = (sorted_events[0].get("title") or "").strip()[:70]
        message = first_title or "查看 data/digests/ 下今天的 markdown"

        # AppleScript 字符串需要双引号包裹 + 内部双引号转义
        def quote(s: str) -> str:
            return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

        script = (
            f"display notification {quote(message)} "
            f"with title {quote(title)} subtitle {quote(subtitle)}"
        )
        try:
            subprocess.run(
                ["osascript", "-e", script], check=False, timeout=5
            )
            print(f"[notify/macos] 已弹系统通知（{len(events)} 条新事件）")
        except Exception as e:
            print(f"[notify/macos] 发通知失败: {e}")
