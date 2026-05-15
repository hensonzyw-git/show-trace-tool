"""Source 抽象基类：每个抓取平台实现一个子类。

两个职责：
- fetch_raw(query, city): 拿到原始内容（HTML/JSON 文本）和实际请求 URL
- raw_path(...):          决定原始内容落盘的文件名

city 是可选的 —— 调用方按"维度"决定是否传：
- 艺人维度（artists）→ city=None，全国都看
- 本地维度（local）  → city=指定城市
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path


class Source(ABC):
    name: str  # 子类设置，作为 raw 文件名前缀和事件来源标识

    @abstractmethod
    def fetch_raw(self, query: str, city: str | None = None) -> tuple[str, str]:
        """返回 (实际请求 URL, 原始内容文本)。city=None 不带城市过滤。"""
        ...

    def raw_path(self, raw_dir: Path, query: str, fetched_at: datetime) -> Path:
        stamp = fetched_at.strftime("%Y%m%dT%H%M")
        safe_query = query.replace("/", "_").replace(" ", "_")
        return raw_dir / f"{self.name}_{stamp}_{safe_query}.html"
