"""Notifier 抽象基类：每个通知渠道一个子类。

MVP 只有 MarkdownNotifier 一个实现，但接口按"将来 N 个"设计 —— 飞书、
Telegram、邮件都是新加一个 Notifier 子类即可。
"""

from abc import ABC, abstractmethod


class Notifier(ABC):
    name: str

    @abstractmethod
    def notify(self, events: list[dict]) -> None:
        """处理一批新事件。具体行为各子类实现（写文件 / 发消息 / 推送等）。"""
